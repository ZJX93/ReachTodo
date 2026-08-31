import asyncio
from playwright.async_api import async_playwright

URL = "https://a6b47180c33600087.bj6.agentos-app.net"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width": 1280, "height": 800})
        await pg.goto(URL + "/login", wait_until="networkidle")
        # login — first input is username, second is password
        await pg.locator("input").nth(0).fill("demo")
        await pg.fill('input[type="password"]', "reach2026")
        await pg.click('button[type="submit"]')
        await pg.wait_for_timeout(1500)
        await pg.goto(URL + "/records", wait_until="networkidle")
        await pg.wait_for_timeout(1200)
        # open new record editor
        await pg.click("text=+ 新建")
        await pg.wait_for_timeout(800)

        vp = pg.viewport_size
        # the editor overlay is the fixed inset-0 element
        boxes = await pg.evaluate(
            """() => {
                const els = [...document.querySelectorAll('div')];
                const ed = els.find(e => getComputedStyle(e).position === 'fixed'
                                          && e.className.includes('inset-0'));
                if (!ed) return null;
                const r = ed.getBoundingClientRect();
                const bodyChild = ed.parentElement === document.body;
                // inner editing column: the mx-auto container with max-w
                const col = els.find(e => e.className.includes('max-w-4xl')
                                          && e.className.includes('mx-auto'));
                const cr = col ? col.getBoundingClientRect() : null;
                return {top:r.top,left:r.left,width:r.width,height:r.height,
                        parentIsBody:bodyChild,
                        colWidth: cr ? cr.width : null,
                        colLeft: cr ? cr.left : null};
            }"""
        )
        print("VIEWPORT", vp)
        print("EDITOR_BOX", boxes)
        if boxes:
            full = abs(boxes["top"]) < 1 and abs(boxes["left"]) < 1 and \
                   abs(boxes["width"] - vp["width"]) < 2 and abs(boxes["height"] - vp["height"]) < 2
            print("FULLSCREEN_OK", full, "PARENT_BODY", boxes["parentIsBody"])
            if boxes["colWidth"]:
                gutter = (vp["width"] - boxes["colWidth"]) / 2
                print("COL_WIDTH", round(boxes["colWidth"]), "SIDE_GUTTER", round(gutter))
        await pg.screenshot(path="/workspace/editor_fullscreen.png")
        await b.close()

asyncio.run(main())
