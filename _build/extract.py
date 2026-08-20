import collections
import json
import re
import time

import pymupdf

SRC = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/src.pdf"
OUT = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/pages.jsonl"

BOILERPLATE = re.compile(
    r"^\s*(Extraordinary Council Meeting.*|Mosman Council|Page \d+ of \d+)\s*$",
    re.IGNORECASE,
)

doc = pymupdf.open(SRC)
total = doc.page_count

sizes = collections.Counter()
for i in range(0, total, 7):
    for blk in doc[i].get_text("dict")["blocks"]:
        if blk.get("type") != 0:
            continue
        for line in blk["lines"]:
            for span in line["spans"]:
                sizes[round(span["size"], 1)] += len(span["text"].strip())
body_size = sizes.most_common(1)[0][0]
print("body font size", body_size, flush=True)

start = time.time()
with open(OUT, "w", encoding="utf-8") as out:
    for i in range(total):
        page = doc[i]
        d = page.get_text("dict")
        blocks = []
        for blk in d["blocks"]:
            if blk.get("type") != 0:
                continue
            for line in blk["lines"]:
                text = "".join(s["text"] for s in line["spans"]).strip()
                if not text or BOILERPLATE.match(text):
                    continue
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                size = max(s["size"] for s in spans)
                bold = any("bold" in s["font"].lower() or s["flags"] & 16 for s in spans)
                blocks.append(
                    {
                        "t": text,
                        "s": round(size, 1),
                        "b": bold,
                        "y": round(line["bbox"][1], 1),
                        "x": round(line["bbox"][0], 1),
                    }
                )
        images = []
        for im in page.get_images(full=True):
            xref = im[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            for r in rects:
                if r.width < 40 or r.height < 40:
                    continue
                images.append(
                    {
                        "xref": xref,
                        "bbox": [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)],
                        "w": round(r.width),
                        "h": round(r.height),
                    }
                )
        out.write(
            json.dumps(
                {"page": i + 1, "body_size": body_size, "blocks": blocks, "images": images},
                ensure_ascii=False,
            )
            + "\n"
        )
        if (i + 1) % 100 == 0:
            rate = (i + 1) / (time.time() - start)
            print(f"{i + 1}/{total}  {rate:.0f} pg/s  eta {(total - i - 1) / rate:.0f}s", flush=True)

print("DONE", OUT, f"{time.time() - start:.0f}s", flush=True)
