# Mosman Masterplan — offline browser

Converted from `Extraordinary Council Meeting__31 ... (1).pdf`
(1,495 pages, Mosman Municipal Council, 26 August 2026).

## Use it

Open **`index.html`** in any browser. No server, no internet, no build step.

The search sidebar is persistent — results stay put while you click through them.

| Key | Does |
| --- | --- |
| `/` | Focus search |
| `J` / `K` | Jump to next / previous hit (works across attachments) |
| `↑` `↓` | Same, while the search box has focus |
| `\` | Show/hide the sidebar |

Fuzzy matching is built in: `biodivrsity` finds *Biodiversity Assessment*, `hertiage` finds *heritage*.
Results deep-link to the exact page (`sections/04-d-heritage-review.html#p439`), and the
landed-on page is highlighted. Click any figure to open it full size.

### Multi-word queries are proximity-ranked

A query like `setback countess` returns pages containing **both** terms, ranked by how close
together they appear — not pages containing either one, and not only exact phrases. Each hit
is badged with the distance:

| Badge | Meaning |
| --- | --- |
| `phrase` | the terms are adjacent |
| `7w apart` | 7 words between the closest occurrences |
| `partial` | not every term is on this page — always ranked below full matches, and shown only when there are too few full matches |

## Layout

| Path | What |
| --- | --- |
| `index.html` | Search sidebar + attachment index |
| `sections/` | 19 HTML files, one per attachment (A–R plus front matter) |
| `markdown/` | Same content as `.md`, one file per attachment — for RAG / LLM ingest |
| `images/` | 767 deduplicated figures (WebP), 200–450 dpi |
| `search-index.js` | Inverted index + trigram fuzzy index + page text (3.5 MB) |
| `app.js`, `style.css` | Search engine and styling |
| `_build/` | The scripts that generated all of this |

## How the search works

Everything is precomputed into `search-index.js`: an inverted index over 11,782 terms,
a trigram index for fuzzy matching, and the full text of all 1,495 pages for snippets.
Postings are base-36 delta-encoded and decoded lazily on first use, so startup stays fast.

Ranking combines idf-weighted term frequency with exact (1.0) / prefix (0.62) / fuzzy
(0.45–0.3) match weights and a term-coverage factor. Multi-word queries then get a
proximity pass: for each candidate page a sliding window finds the **smallest span of text
containing all query terms**, and the score is multiplied by `1 + 5·e^(−gap/110)`, so
adjacent terms outrank distant ones. Contiguous phrases get a further 1.8×.

Proximity needs term positions, which the inverted index doesn't store — but the full page
text is already shipped for snippets, so positions are computed at query time on the top 500
candidates only. That keeps the index the same size and still lands in **1–8 ms**.

Because `file://` blocks `fetch`, the sidebar cannot be a single-page app. Instead the query
is kept in `sessionStorage` and the search re-runs on each page load — at a few milliseconds
it is imperceptible, and it means deep links and the back button work normally.

## Image resolution

Each figure is rendered at its own **native** resolution — the DPI at which the PDF actually
stored it (median 202, up to 450) — rather than a flat guess. Rendering above native adds
bytes without detail; below it throws detail away.

Figures are composited *page regions*, not raw embedded images. This matters: the PDF stores
its maps as thousands of small tiles (one page held 4,328 of them), so extracting embedded
images directly would yield thousands of unreadable slivers.

## Notes on fidelity

- Text comes from the PDF's own text layer — no OCR, so no transcription errors.
- Headings are inferred from font size, weight and numbering; a few are missed where the
  source put a heading and body text on the same line.
- Tables appear as text in reading order, not as reconstructed markdown tables.
- 589 of the 595 image-bearing pages produced figures; the other 6 held only sub-threshold
  thumbnails (under ~46×34 pt).
