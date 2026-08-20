import pathlib

from playwright.sync_api import sync_playwright

SITE = pathlib.Path("/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/site")
QUERIES = ["setback countess", "flood risk", "heritage conservation area",
           "affordable housing levy", "spit junction", "biodivrsity"]

# Reports, for the top hits, the character gap between the query terms on that page.
PROBE = """
(q) => {
  const terms = q.toLowerCase().match(/[a-z0-9][a-z0-9'&/-]*/g).filter(t=>t.length>1);
  const rows = [...document.querySelectorAll('#results .r')].slice(0,6);
  return rows.map(r => {
    const page = +r.querySelector('.rh i').textContent.trim().replace('p.','');
    const badge = r.querySelector('.rh u') ? r.querySelector('.rh u').textContent : '';
    const di = window.IDX.M.findIndex(m => m[1] === page);
    const text = window.IDX.T[di].toLowerCase();
    const pos = terms.map(t => {
      const out = []; let f = 0, k;
      while ((k = text.indexOf(t, f)) > -1) { out.push(k); f = k + 1; }
      return out;
    });
    const missing = pos.filter(p => !p.length).length;
    let span = null;
    if (!missing) {
      let best = Infinity;
      for (const a of pos[0]) {
        let lo = a, hi = a + terms[0].length;
        for (let i = 1; i < pos.length; i++) {
          let nearest = pos[i].reduce((b,c) => Math.abs(c-a) < Math.abs(b-a) ? c : b);
          lo = Math.min(lo, nearest); hi = Math.max(hi, nearest + terms[i].length);
        }
        best = Math.min(best, hi - lo);
      }
      span = best;
    }
    return {sec: r.querySelector('.rh b').textContent, page, missing, span, badge,
            snip: r.querySelector('.rs').textContent.slice(0,62)};
  });
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1440, "height": 950})
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto((SITE / "index.html").as_uri())
    p.wait_for_function("window.IDX && window.IDX.V.length>0")

    for q in QUERIES:
        p.fill("#q", "")
        p.fill("#q", q)
        p.wait_for_function(f"()=>sessionStorage.getItem('mmp.query')==={q!r}", timeout=15000)
        p.wait_for_function("()=>document.querySelectorAll('#results .r, #results .empty').length>0", timeout=15000)
        n = p.locator("#results .r").count()
        ms = p.locator(".rcount").inner_text().split("·")[-1].strip() if p.locator(".rcount").count() else "-"
        print(f"\n{q!r}  ({n} hits, {ms})")
        if not n:
            print("   no matches")
            continue
        for r in p.evaluate(PROBE, q):
            gap = "gap=%s" % r["span"] if r["missing"] == 0 else f"MISSING {r['missing']}"
            print(f"   p.{r['page']:<5} {r['sec']:<3} {gap:<12} badge={r['badge']:<9} {r['snip']}")

    print("\nJS errors:", errs[:4] if errs else "none")
    b.close()
