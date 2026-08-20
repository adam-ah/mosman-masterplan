import html
import json
import os
import re
import shutil
import unicodedata

BASE = "/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad"
SITE = f"{BASE}/site"
PAGES = f"{BASE}/pages.jsonl"
FIGS = f"{BASE}/figures.json"

TOC = [
    (4, "A"), (274, "B"), (331, "C"), (415, "D"), (538, "E"), (720, "F"),
    (770, "G"), (815, "H"), (816, "I"), (832, "J"), (1205, "K"), (1254, "L"),
    (1258, "M"), (1265, "N"), (1269, "O"), (1287, "P"), (1291, "Q"), (1375, "R"),
]

rows = [json.loads(l) for l in open(PAGES, encoding="utf-8")]
by_page = {r["page"]: r for r in rows}
figures = {int(k): v for k, v in json.load(open(FIGS)).items()}
total_pages = len(rows)

DOC_TITLE = "Mosman Masterplan"
DOC_SUB = "Extraordinary Council Meeting — Additional Attachments — 26 August 2026"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:60]


def cover_title(page_no, letter):
    blocks = by_page[page_no]["blocks"]
    big = [b for b in blocks if b["s"] > 15]
    parts = []
    for b in sorted(big, key=lambda b: b["y"]):
        t = b["t"].strip()
        if t == letter or len(t) <= 1:
            continue
        t = re.sub(rf"{re.escape(letter)}$", "", t).strip()
        if t and t.lower() not in ("august 2026",):
            parts.append(t)
    return re.sub(r"\s+", " ", " ".join(parts).strip())


sections = [{"letter": "", "title": "Front Matter & Agenda", "first": 1, "last": 3}]
bounds = [(TOC[i][0], TOC[i + 1][0] - 1 if i + 1 < len(TOC) else total_pages, TOC[i][1])
          for i in range(len(TOC))]
for first, last, letter in bounds:
    t = cover_title(first, letter)
    if not t:
        junk = re.compile(r"^(august 2026|mosman|council|attachment [\d.]+ mosman)$", re.I)
        heads = [b for b in by_page[first]["blocks"] if b["s"] >= 10 and not junk.match(b["t"].strip())]
        t = heads[0]["t"][:70] if heads else f"Attachment {letter} (divider)"
    sections.append({"letter": letter, "title": t, "first": first, "last": last})

for i, s in enumerate(sections):
    s["id"] = i
    s["label"] = f"{s['letter']} {s['title']}".strip()
    s["file"] = f"sections/{i:02d}-{slugify(s['label'])}.html"
    s["pages"] = s["last"] - s["first"] + 1
    s["figs"] = sum(len(figures.get(p, [])) for p in range(s["first"], s["last"] + 1))


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


def render_page(pno, base):
    out, para = [], []
    prev_y = None

    def flush():
        if para:
            out.append("<p>" + html.escape(" ".join(para)) + "</p>")
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
            out.append(f'<h2 class="cover">{html.escape(t)}</h2>')
        elif s >= base * 1.45:
            flush()
            out.append(f"<h3>{html.escape(t)}</h3>")
        elif (s >= base * 1.15 and b["b"] and len(t) < 120) or is_numbered_heading(t):
            flush()
            out.append(f"<h4>{html.escape(t)}</h4>")
        else:
            para.append(t)
    flush()
    for f in figures.get(pno, []):
        out.append(
            f'<figure><a href="../images/{f["src"]}" target="_blank" '
            f'title="Open full size ({f["w"]}&times;{f["h"]}, {f["dpi"]} dpi)">'
            f'<img loading="lazy" decoding="async" src="../images/{f["src"]}" '
            f'width="{f["w"]}" height="{f["h"]}" alt="Figure on page {pno}"></a></figure>'
        )
    return "\n".join(out)


def shell_open(root, title):
    nav = "".join(
        f'<a class="navitem" href="{root}{s["file"]}" data-sec="{s["id"]}">'
        f'<span class="l">{html.escape(s["letter"]) or "&mdash;"}</span>'
        f'<span class="n">{html.escape(s["title"])}</span></a>'
        for s in sections
    )
    return f"""<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{root}style.css">
<div class="shell">
<aside class="side" id="side">
  <a class="brand" href="{root}index.html">&#9632; {DOC_TITLE}</a>
  <div class="qbox">
    <input id="q" type="search" placeholder="Search {total_pages} pages&hellip;" autocomplete="off" spellcheck="false">
    <button id="qclear" title="Clear search">&times;</button>
  </div>
  <div id="hint" class="hint">Press <kbd>/</kbd> to search &middot; <kbd>J</kbd>/<kbd>K</kbd> next/prev hit</div>
  <div id="results"></div>
  <nav id="secnav" class="secnav">{nav}</nav>
</aside>
<button id="toggle" title="Toggle sidebar (\\)">&#9776;</button>
<div class="content">
<header class="mbar">
  <button id="mmenu" aria-label="Contents and search">&#9776;</button>
  <button id="msearch" class="mq">Search {total_pages} pages&hellip;</button>
  <span id="mcount" class="mcount"></span>
  <button id="mprev" aria-label="Previous hit" disabled>&#8249;</button>
  <button id="mnext" aria-label="Next hit" disabled>&#8250;</button>
</header>"""


SHELL_CLOSE = f"""</div></div>
<script src="{{root}}search-index.js"></script><script src="{{root}}app.js"></script>"""


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


shutil.rmtree(f"{SITE}/sections", ignore_errors=True)
os.makedirs(f"{SITE}/sections", exist_ok=True)

for i, s in enumerate(sections):
    base = body_size_for(s["first"], s["last"])
    parts = [shell_open("../", f"{s['label']} — {DOC_TITLE}"),
             '<main class="doc">',
             f'<div class="sechead"><span class="letter">{html.escape(s["letter"]) or "&mdash;"}</span>'
             f'<h1>{html.escape(s["title"])}</h1>'
             f'<p class="meta">Pages {s["first"]}&ndash;{s["last"]} &middot; '
             f'{plural(s["pages"], "page")} &middot; {plural(s["figs"], "figure")}</p></div>']
    for p in range(s["first"], s["last"] + 1):
        parts.append(f'<section class="pg" id="p{p}"><a class="pnum" href="#p{p}">{p}</a>')
        parts.append(render_page(p, base))
        parts.append("</section>")
    prev_s = sections[i - 1] if i > 0 else None
    next_s = sections[i + 1] if i + 1 < len(sections) else None
    nav = ['<nav class="pager">']
    nav.append(f'<a href="../{prev_s["file"]}">&larr; {html.escape(prev_s["label"])}</a>' if prev_s else "<span></span>")
    nav.append(f'<a href="../{next_s["file"]}">{html.escape(next_s["label"])} &rarr;</a>' if next_s else "<span></span>")
    nav.append("</nav>")
    parts.append("".join(nav))
    parts.append("</main>")
    parts.append(SHELL_CLOSE.format(root="../"))
    write(f"{SITE}/{s['file']}", "\n".join(parts))

cards = "".join(
    f'<a class="card" href="{s["file"]}">'
    f'<span class="letter">{html.escape(s["letter"]) or "&mdash;"}</span>'
    f'<span class="ct"><strong>{html.escape(s["title"])}</strong>'
    f'<em>pp. {s["first"]}&ndash;{s["last"]} &middot; {plural(s["pages"], "page")} '
    f'&middot; {plural(s["figs"], "figure")}</em></span></a>'
    for s in sections
)

write(f"{SITE}/index.html",
      shell_open("", DOC_TITLE)
      + f"""<main class="home-main">
  <h1>{DOC_TITLE}</h1>
  <p class="sub">{DOC_SUB}</p>
  <p class="stats">{total_pages} pages &middot; {len(sections)} attachments &middot;
     {sum(len(v) for v in figures.values())} figures &middot; fully offline</p>
  <div class="cards">{cards}</div>
</main>"""
      + SHELL_CLOSE.format(root=""))

json.dump(sections, open(f"{BASE}/sections.json", "w"), indent=1)
print("sections:", len(sections), "| figures:", sum(len(v) for v in figures.values()))
