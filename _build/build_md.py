import json
import os
import re

BASE = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad"
MD = f"{BASE}/site/markdown"

rows = [json.loads(l) for l in open(f"{BASE}/pages.jsonl", encoding="utf-8")]
by_page = {r["page"]: r for r in rows}
figures = {int(k): v for k, v in json.load(open(f"{BASE}/figures.json")).items()}
sections = json.load(open(f"{BASE}/sections.json"))

os.makedirs(MD, exist_ok=True)


def body_size_for(first, last):
    c = {}
    for p in range(first, last + 1):
        for b in by_page[p]["blocks"]:
            c[b["s"]] = c.get(b["s"], 0) + len(b["t"])
    return max(c, key=lambda k: c[k]) if c else 9.0


NUM_HEAD = re.compile(r"^\d+(\.\d+){0,3}\.?\s+\S")
CAPS_HEAD = re.compile(r"^[^a-z]{6,90}$")


def is_numbered_heading(t):
    if not NUM_HEAD.match(t) or len(t) > 90 or " " not in t:
        return False
    num, rest = t.split(None, 1)
    if not rest:
        return False
    if CAPS_HEAD.match(rest):
        return True
    return "." in num and rest[:1].isupper() and len(t) < 70 and not rest.endswith(".")


def page_md(pno, base):
    out = []
    para = []
    prev_y = None

    def flush():
        if para:
            out.append(" ".join(para))
            para.clear()

    for b in by_page[pno]["blocks"]:
        t = b["t"].strip()
        if not t:
            continue
        s = b["s"]
        gap = None if prev_y is None else b["y"] - prev_y
        prev_y = b["y"]
        if gap is not None and (gap > base * 1.9 or gap < -base):
            flush()
        if s >= base * 2.2 and len(t) <= 60:
            flush()
            out.append(f"## {t}")
        elif s >= base * 1.45:
            flush()
            out.append(f"### {t}")
        elif (s >= base * 1.15 and b["b"] and len(t) < 120) or is_numbered_heading(t):
            flush()
            out.append(f"#### {t}")
        else:
            para.append(t)
    flush()
    for f in figures.get(pno, []):
        out.append(f'![Figure on page {pno}](../images/{f["src"]})')
    return "\n\n".join(out)


index_lines = [
    "# Mosman Masterplan — Additional Attachments",
    "",
    "Extraordinary Council Meeting, 26 August 2026. Mosman Municipal Council.",
    f"{len(rows)} pages, {len(sections)} attachments, {sum(len(v) for v in figures.values())} figures.",
    "",
    "| # | Attachment | Pages | File |",
    "| --- | --- | --- | --- |",
]

for s in sections:
    base = body_size_for(s["first"], s["last"])
    name = f"{s['id']:02d}-{re.sub(r'[^a-z0-9]+', '-', s['label'].lower()).strip('-')[:60]}.md"
    parts = [
        "---",
        f"title: {s['label']}",
        f"source: Extraordinary Council Meeting - Additional Attachments - 26 August 2026",
        f"pages: {s['first']}-{s['last']}",
        "---",
        "",
        f"# {s['label']}",
        "",
    ]
    for p in range(s["first"], s["last"] + 1):
        parts.append(f"<!-- page {p} -->")
        body = page_md(p, base)
        if body:
            parts.append(body)
    with open(f"{MD}/{name}", "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts).replace("\n\n\n", "\n\n") + "\n")
    index_lines.append(f"| {s['letter'] or '—'} | {s['title']} | {s['first']}–{s['last']} | [{name}]({name}) |")
    print(f"{name}  ({s['pages']} pages)")

with open(f"{MD}/README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(index_lines) + "\n")

total = sum(os.path.getsize(f"{MD}/{f}") for f in os.listdir(MD))
print(f"markdown total {total / 1e6:.1f} MB in {len(os.listdir(MD))} files")
