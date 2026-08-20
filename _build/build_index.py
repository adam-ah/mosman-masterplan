import json
import re
from collections import defaultdict

BASE = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad"
SITE = f"{BASE}/site"

rows = [json.loads(l) for l in open(f"{BASE}/pages.jsonl", encoding="utf-8")]
sections = json.load(open(f"{BASE}/sections.json"))

TOKEN = re.compile(r"[a-z0-9][a-z0-9'&/-]*")
STOP = set(
    "the a an and or of to in for on at by is are was were be been it its this that "
    "with as from will shall may can not no if then than which who whom whose has have "
    "had do does did but so such into over under out up down we you they he she i".split()
)


def b36(n):
    if n == 0:
        return "0"
    d = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    while n:
        s = d[n % 36] + s
        n //= 36
    return s


sec_of = {}
for s in sections:
    for p in range(s["first"], s["last"] + 1):
        sec_of[p] = s["id"]

texts = []
metas = []
postings = defaultdict(list)

for di, r in enumerate(rows):
    pno = r["page"]
    text = " ".join(b["t"] for b in r["blocks"])
    text = re.sub(r"\s+", " ", text).strip()
    texts.append(text)
    metas.append([sec_of.get(pno, 0), pno])
    tf = defaultdict(int)
    for m in TOKEN.finditer(text.lower()):
        w = m.group(0).strip("'-&/")
        if len(w) < 2 or w in STOP:
            continue
        tf[w] += 1
    for w, c in tf.items():
        postings[w].append((di, c))

vocab = sorted(postings)
vidx = {w: i for i, w in enumerate(vocab)}

post_enc = []
for w in vocab:
    lst = postings[w]
    prev = 0
    parts = []
    for di, c in lst:
        parts.append(b36(di - prev) + ("" if c == 1 else "." + b36(min(c, 35))))
        prev = di
    post_enc.append(",".join(parts))

tri = defaultdict(list)
for i, w in enumerate(vocab):
    if len(w) < 3:
        continue
    padded = f"${w}$"
    for j in range(len(padded) - 2):
        g = padded[j : j + 3]
        if not tri[g] or tri[g][-1] != i:
            tri[g].append(i)

tri_keys = sorted(tri)
tri_enc = []
for g in tri_keys:
    prev = 0
    parts = []
    for i in tri[g]:
        parts.append(b36(i - prev))
        prev = i
    tri_enc.append(",".join(parts))

payload = {
    "V": vocab,
    "P": post_enc,
    "TK": tri_keys,
    "TG": tri_enc,
    "T": texts,
    "M": metas,
    "S": [
        {"i": s["id"], "l": s["letter"], "t": s["title"], "f": s["file"],
         "a": s["first"], "b": s["last"]}
        for s in sections
    ],
}

out = f"{SITE}/search-index.js"
with open(out, "w", encoding="utf-8") as f:
    f.write("window.IDX=")
    json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
    f.write(";")

import os

print(f"vocab={len(vocab)} trigrams={len(tri_keys)} docs={len(texts)}")
print(f"index size = {os.path.getsize(out) / 1e6:.1f} MB")
