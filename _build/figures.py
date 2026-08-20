import hashlib
import io
import json
import os
import sys
import time

import pymupdf
from PIL import Image

BASE = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad"
SRC = f"{BASE}/src.pdf"
PAGES = f"{BASE}/pages.jsonl"
IMGDIR = f"{BASE}/site/images"
MANIFEST = f"{BASE}/figures.json"

MIN_DPI = 200
MAX_DPI = 450
MAX_EDGE = 4000
QUALITY = 84
MIN_W = 46.0
MIN_H = 34.0
MIN_AREA = 3500.0
PAD = 3.0
BOILERPLATE_PAGES = 25

ONLY = {int(x) for x in sys.argv[1:]} or None

os.makedirs(IMGDIR, exist_ok=True)


def cluster(items):
    groups = []
    for it in items:
        r = pymupdf.Rect(it["bbox"])
        hit = [g for g in groups if (g["r"] + (-14, -14, 14, 14)).intersects(r)]
        if hit:
            m = hit[0]
            for g in hit[1:]:
                m["r"] |= g["r"]
                m["px"] += g["px"]
                groups.remove(g)
            m["r"] |= r
            m["px"] += it["px"]
        else:
            groups.append({"r": pymupdf.Rect(r), "px": it["px"]})
    return groups


doc = pymupdf.open(SRC)
rows = [json.loads(l) for l in open(PAGES, encoding="utf-8")]
seen = {}
figures = {}
start = time.time()
todo = [r for r in rows if r["images"] and (ONLY is None or r["page"] in ONLY)]

for n, row in enumerate(todo):
    pno = row["page"]
    page = doc[pno - 1]
    parea = page.rect.get_area()

    pixels = {}
    for im in page.get_images(full=True):
        pixels[im[0]] = im[2] * im[3]

    items = [{"bbox": i["bbox"], "px": pixels.get(i["xref"], 0)} for i in row["images"]]
    out = []
    for g in cluster(items):
        rect = g["r"]
        if rect.width < MIN_W or rect.height < MIN_H or rect.get_area() < MIN_AREA:
            continue
        if rect.get_area() / parea > 0.85:
            rect = page.rect
        clip = (rect + (-PAD, -PAD, PAD, PAD)) & page.rect
        area_in = max(clip.get_area() / 5184.0, 1e-6)
        native = (g["px"] / area_in) ** 0.5 if g["px"] else MIN_DPI
        dpi = int(min(max(native, MIN_DPI), MAX_DPI))
        try:
            pix = page.get_pixmap(dpi=dpi, clip=clip, annots=False)
        except Exception as e:
            print(f"  page {pno} clip fail: {e}", flush=True)
            continue
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if max(img.size) > MAX_EDGE:
            img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=QUALITY, method=4)
        data = buf.getvalue()
        h = hashlib.blake2b(data, digest_size=8).hexdigest()
        if h not in seen:
            name = f"{h}.webp"
            with open(f"{IMGDIR}/{name}", "wb") as fh:
                fh.write(data)
            seen[h] = name
        out.append({"src": seen[h], "bbox": [round(v, 1) for v in clip],
                    "w": img.size[0], "h": img.size[1], "dpi": dpi})
    if out:
        figures[pno] = out
    if (n + 1) % 25 == 0:
        el = time.time() - start
        rate = (n + 1) / el
        mb = sum(os.path.getsize(f"{IMGDIR}/{f}") for f in os.listdir(IMGDIR)) / 1e6
        print(f"{n + 1}/{len(todo)}  {len(seen)} uniq  {mb:.0f}MB  {rate:.1f} pg/s  "
              f"eta {(len(todo) - n - 1) / rate / 60:.1f} min", flush=True)

if ONLY is None:
    spread = {}
    for pno, figs in figures.items():
        for f in figs:
            spread.setdefault(f["src"], set()).add(pno)
    boilerplate = {s for s, pgs in spread.items() if len(pgs) > BOILERPLATE_PAGES}
    for pno in list(figures):
        kept = [f for f in figures[pno] if f["src"] not in boilerplate]
        if kept:
            figures[pno] = kept
        else:
            del figures[pno]
    for s in boilerplate:
        p = f"{IMGDIR}/{s}"
        if os.path.exists(p):
            os.remove(p)
    print(f"dropped {len(boilerplate)} boilerplate images", flush=True)
    json.dump(figures, open(MANIFEST, "w"), indent=0)

dpis = [f["dpi"] for v in figures.values() for f in v]
total_mb = sum(os.path.getsize(f"{IMGDIR}/{f}") for f in os.listdir(IMGDIR)) / 1e6
print(f"DONE figures={sum(len(v) for v in figures.values())} unique={len(seen)} "
      f"size={total_mb:.1f}MB dpi_min={min(dpis) if dpis else 0} dpi_max={max(dpis) if dpis else 0}",
      flush=True)
