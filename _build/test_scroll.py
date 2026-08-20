import pathlib

from playwright.sync_api import sync_playwright

SITE = pathlib.Path("/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/site")

# Is the primary highlight actually inside the viewport, and what is on screen?
VIS = """
() => {
  const p = document.querySelector('mark.hit.primary');
  const out = {marks: document.querySelectorAll('mark.hit').length, primary: !!p};
  if (p) {
    const r = p.getBoundingClientRect();
    out.inView = r.top >= 0 && r.bottom <= innerHeight;
    out.top = Math.round(r.top);
    out.word = p.textContent;
    // text visible around the highlight
    const sec = p.closest('.pg');
    const full = sec.textContent;
    const idx = full.indexOf(p.textContent);
    out.context = full.slice(Math.max(0, idx - 110), idx + 130).replace(/\\s+/g, ' ');
  }
  return out;
}
"""

CASES = [("setback countess", 3), ("affordable housing levy", 2), ("flood risk", 1)]

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))

    for query, nth in CASES:
        p.goto((SITE / "index.html").as_uri())
        p.wait_for_function("window.IDX && window.IDX.V.length>0")
        p.fill("#q", "")
        p.fill("#q", query)
        p.wait_for_function(f"()=>sessionStorage.getItem('mmp.query')==={query!r}", timeout=15000)
        p.wait_for_function("()=>document.querySelectorAll('#results .r').length>0", timeout=15000)
        badge = p.locator("#results .r").nth(nth).locator(".rh u")
        badge_txt = badge.inner_text() if badge.count() else "-"
        p.locator("#results .r").nth(nth).click()
        p.wait_for_load_state()
        p.wait_for_function("window.IDX")
        p.wait_for_timeout(2200)
        v = p.evaluate(VIS)
        print(f"\n{query!r} -> result #{nth + 1} [{badge_txt}]  {p.url.split('#')[-1]}")
        print(f"   marks={v['marks']} primary={v['primary']} inView={v.get('inView')} top={v.get('top')}px word={v.get('word')!r}")
        print(f"   on screen: …{v.get('context', '')}…")
        p.screenshot(path=str(SITE.parent / f"scroll-{query.split()[0]}.png"))

    print("\n--- J/K keeps re-aiming ---")
    for _ in range(2):
        p.keyboard.press("j")
        p.wait_for_load_state()
        p.wait_for_function("window.IDX")
        p.wait_for_timeout(2200)
        v = p.evaluate(VIS)
        print(f"   j -> {p.url.split('#')[-1]:<8} primary={v['primary']} inView={v.get('inView')} word={v.get('word')!r}")

    print("\nJS errors:", errs[:4] if errs else "none")
    b.close()
