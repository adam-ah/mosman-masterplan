# AGENTS.md

Decisions that cost time to find. Don't re-derive them wrong.

## Source
- Source PDF: 658 MB, 1,495 pages, born-digital (Aspose). Lives in the parent dir, untouched.
- **All 1,495 pages have a real text layer. Never OCR.**
- `pymupdf4llm` auto-enables `rapidocr` (installed globally) → ~1 s/page for nothing. Don't use it. Raw PyMuPDF `get_text("dict")` is 45 ms/page → 63 s for the whole doc.
- `/mnt/c` was *not* a bottleneck (170 MB/s). Don't "optimise" by copying to /tmp.

## Figures
- Render **composited page regions**, never embedded image XObjects. The PDF stores maps as tiles — one page holds 4,328 of them; extracting XObjects yields thousands of unreadable slivers.
- Render each figure at its **native DPI** (median 202, cap 200–450), `MAX_EDGE=4000`. Below native throws away detail; above native only adds bytes. A flat 180 dpi + 1500 px cap was the original too-blurry bug.
- 767 unique figures / 188 MB. 589 of 595 image pages produce figures; the other 6 hold only sub-threshold thumbnails.

## Search
- Runs from `file://` too, where **`fetch` is blocked → no SPA**. Query lives in `sessionStorage` and search re-runs per page load (1–8 ms), which is why deep links and Back work.
- **Proximity is computed at query time** from the page text already shipped for snippets. Do *not* add positions to the inverted index — it would grow 3.5 MB for no gain.
- Multi-word = all-term tier first; partial matches only when <8 full matches, penalised 0.12× and badged `partial`.
- Scroll-to-hit **must self-correct** (re-checks at 180/450/900/1600 ms). Lazy figures above the target shift layout after the first `scrollIntoView`; a single call lands ~1400 px off.

## Mobile
- <860 px: sidebar is an off-canvas drawer, **closed by default**. Open-by-default covered 90% of a 390 px screen (109% at 320 px).
- Top bar carries prev/next hit buttons because `J`/`K` is keyboard-only — without them results can't be walked by touch.
- Touch targets ≥44 px.

## Publishing
- GitHub Pages, not S3: free, and S3 static hosting is HTTP-only (HTTPS needs CloudFront). 190 MB vs the 1 GB site cap.
- **Personal account only: `adam-ah` / `adam@nethosting.hu`. Never the AvreoAI or Zancon-Alpha orgs.** Git identity is pinned repo-locally; target `adam-ah/<repo>` explicitly.
- Content is Mosman Municipal Council's, in a public search-indexable repo. Credited in README.
- Git history holds 184 MB of WebP. Re-pushing re-rendered figures adds another full copy permanently — flatten history instead of accumulating.

## Build order
`extract.py` → `figures.py` → `build_site.py` → `build_index.py` → `build_md.py` (all in `_build/`).
`build_site.py` wipes `sections/` first; it used to leave orphan files when a section title changed.

## Testing gotcha
Playwright must wait on `sessionStorage.getItem('mmp.query')`, not just `#results .r` presence — the 70 ms debounce means you otherwise read the *previous* query's results and every query looks identical. This produced two false bug reports.

## Known gaps
Tables are text in reading order, not markdown tables. Some headings missed where the source put heading + body on one line. No in-page pan/zoom for figures (tap opens full size).
