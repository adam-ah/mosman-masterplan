import pathlib

from playwright.sync_api import sync_playwright

SITE = pathlib.Path("/tmp/claude-1000/-mnt-c-Users-Adam-Downloads-masterplan/5af5b2c6-473f-4ba8-b26e-58a9d3dd1994/scratchpad/site")
QUERIES = ["heritage conservation", "biodivrsity", "spit junction", "contamination",
           "flood risk", "affordable housing", "stormwater", "hertiage", "military road"]

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto((SITE / "index.html").as_uri())
    page.wait_for_function("window.IDX")
    print("sidebar nav items:", page.locator(".navitem").count())
    print("cards:", page.locator(".card").count())

    for q in QUERIES:
        page.evaluate("document.getElementById('results').innerHTML=''")
        page.fill("#q", "")
        page.fill("#q", q)
        page.wait_for_function("()=>document.querySelectorAll('#results .r, #results .empty').length>0", timeout=8000)
        n = page.locator("#results .r").count()
        top = page.locator("#results .r").first.locator(".rh").inner_text().replace("\n", " ") if n else "-"
        ms = page.locator(".rcount").inner_text().split("·")[-1].strip()
        print(f"  {q!r:24} n={n:<4} {ms:<7} -> {top[:46]}")

    print("\n--- persistence across navigation ---")
    page.fill("#q", "")
    page.fill("#q", "flood risk")
    page.wait_for_function("()=>sessionStorage.getItem('mmp.query')==='flood risk'", timeout=8000)
    page.wait_for_function("()=>document.querySelectorAll('#results .r').length>0")
    before = page.locator("#results .r").count()
    hrefs = page.eval_on_selector_all("#results .r", "els=>els.slice(0,4).map(e=>e.getAttribute('href'))")

    for i, h in enumerate(hrefs):
        page.locator("#results .r").nth(i).click()
        page.wait_for_load_state()
        page.wait_for_function("window.IDX")
        page.wait_for_function("()=>document.querySelectorAll('#results .r').length>0", timeout=8000)
        after = page.locator("#results .r").count()
        qval = page.input_value("#q")
        active = page.locator("#results .r.on").count()
        tgt = page.locator(".pg.target").count()
        print(f"  click {i + 1}: results kept={after}/{before} q={qval!r} active={active} target_page={tgt} url=…{page.url.split('/')[-1][:38]}")

    print("\n--- J/K stepping through hits ---")
    for _ in range(3):
        page.keyboard.press("j")
        page.wait_for_load_state()
        page.wait_for_function("()=>document.querySelectorAll('#results .r').length>0", timeout=8000)
        on = page.locator("#results .r.on")
        lbl = on.first.locator(".rh").inner_text().replace("\n", " ") if on.count() else "-"
        print(f"  j -> {page.url.split('#')[-1]:<8} {lbl[:44]}")

    print("\n--- sidebar toggle ---")
    page.keyboard.press("\\")
    page.wait_for_timeout(200)
    print("  hidden:", page.evaluate("document.body.classList.contains('nosidebar')"),
          "| side visible:", page.locator(".side").is_visible())
    page.keyboard.press("\\")
    page.wait_for_timeout(200)
    print("  restored, side visible:", page.locator(".side").is_visible())

    img = page.locator("figure img").first
    if img.count():
        print("\nfirst figure natural:", page.evaluate(
            "()=>{const i=document.querySelector('figure img');return i?i.naturalWidth+'x'+i.naturalHeight:'none'}"))
    page.screenshot(path=str(SITE.parent / "shot-sidebar.png"))
    print("JS errors:", errors[:4] if errors else "none")
    browser.close()
