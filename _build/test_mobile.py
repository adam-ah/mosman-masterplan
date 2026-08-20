import pathlib

from playwright.sync_api import sync_playwright

SITE = pathlib.Path("/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/site")

AUDIT = """
() => {
  const de = document.documentElement, o = {vw: innerWidth};
  o.hScroll = de.scrollWidth - innerWidth;
  const side = document.getElementById('side');
  const cs = getComputedStyle(side);
  const r = side.getBoundingClientRect();
  o.drawerOpen = document.body.classList.contains('side-open');
  o.sideOnScreen = r.right > 1;                 // is the drawer covering content?
  o.sideW = Math.round(r.width);
  const bar = document.querySelector('.mbar');
  o.barVisible = bar ? getComputedStyle(bar).display !== 'none' : false;
  const small = [];
  document.querySelectorAll('a, button, input').forEach(e => {
    const b = e.getBoundingClientRect();
    if (b.width > 0 && b.height > 0 && b.height < 40 && e.offsetParent !== null) {
      small.push((e.tagName + '.' + (e.className || '')).slice(0, 26) + ':' + Math.round(b.height));
    }
  });
  o.smallTargets = small.length; o.smallSample = small.slice(0, 5);
  const wide = [];
  document.querySelectorAll('.doc *, .home-main *').forEach(e => {
    if (e.getBoundingClientRect().width > innerWidth + 2) wide.push(e.tagName);
  });
  o.overflowing = wide.length;
  const mc = document.getElementById('mcount');
  o.counter = mc ? mc.textContent : null;
  const mn = document.getElementById('mnext');
  o.nextEnabled = mn ? !mn.disabled : null;
  return o;
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for name in ["iPhone 13", "iPhone SE", "Pixel 5"]:
        dev = pw.devices.get(name)
        ctx = b.new_context(**dev)
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        tag = name.replace(" ", "")

        p.goto((SITE / "index.html").as_uri())
        p.wait_for_function("window.IDX && window.IDX.V.length>0", timeout=60000)
        a = p.evaluate(AUDIT)
        print(f"\n=== {name} ({a['vw']}px) ===")
        print(f"  landing:  drawerOpen={a['drawerOpen']} sideOnScreen={a['sideOnScreen']} "
              f"bar={a['barVisible']} hScroll={a['hScroll']} overflow={a['overflowing']} small={a['smallTargets']}")
        if a["smallTargets"]:
            print(f"            {a['smallSample']}")
        p.screenshot(path=str(SITE.parent / f"mob2-{tag}-home.png"))

        # open drawer via the search pill, run a query
        p.tap("#msearch")
        p.wait_for_timeout(400)
        p.fill("#q", "flood risk")
        p.wait_for_function("()=>sessionStorage.getItem('mmp.query')==='flood risk'", timeout=20000)
        p.wait_for_function("()=>document.querySelectorAll('#results .r').length>0", timeout=20000)
        a2 = p.evaluate(AUDIT)
        print(f"  searching: drawerOpen={a2['drawerOpen']} results={p.locator('#results .r').count()} counter={a2['counter']!r}")
        p.screenshot(path=str(SITE.parent / f"mob2-{tag}-search.png"))

        # tap a result: drawer must close so the document is visible
        p.locator("#results .r").first.tap()
        p.wait_for_load_state()
        p.wait_for_function("window.IDX", timeout=60000)
        p.wait_for_timeout(2600)
        a3 = p.evaluate(AUDIT)
        hit = p.evaluate("()=>{const m=document.querySelector('mark.hit.primary');if(!m)return null;"
                         "const r=m.getBoundingClientRect();"
                         "return {inView:r.top>=0&&r.bottom<=innerHeight,top:Math.round(r.top),w:m.textContent};}")
        print(f"  after tap: drawerOpen={a3['drawerOpen']} sideOnScreen={a3['sideOnScreen']} "
              f"counter={a3['counter']!r} nextEnabled={a3['nextEnabled']} hit={hit}")
        print(f"             hScroll={a3['hScroll']} overflow={a3['overflowing']} small={a3['smallTargets']}")
        p.screenshot(path=str(SITE.parent / f"mob2-{tag}-section.png"))

        # step to next hit using the bar button only (drawer stays shut)
        p.tap("#mnext")
        p.wait_for_load_state()
        p.wait_for_function("window.IDX", timeout=60000)
        p.wait_for_timeout(2200)
        a4 = p.evaluate(AUDIT)
        hit2 = p.evaluate("()=>{const m=document.querySelector('mark.hit.primary');if(!m)return null;"
                          "const r=m.getBoundingClientRect();return {inView:r.top>=0&&r.bottom<=innerHeight};}")
        print(f"  mnext ->   {p.url.split('#')[-1]:<7} counter={a4['counter']!r} drawerOpen={a4['drawerOpen']} hit={hit2}")
        print(f"  JS errors: {errs[:2] if errs else 'none'}")
        ctx.close()
    b.close()
