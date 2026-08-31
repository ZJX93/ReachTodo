import asyncio
from playwright.async_api import async_playwright

URL = "https://a6b47180c33600087.bj6.agentos-app.net"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width": 1280, "height": 800})
        await pg.goto(URL + "/login", wait_until="networkidle")
        await pg.locator("input").nth(0).fill("demo")
        await pg.fill('input[type="password"]', "reach2026")
        await pg.click('button[type="submit"]')
        await pg.wait_for_timeout(1500)
        await pg.goto(URL + "/records", wait_until="networkidle")
        await pg.wait_for_timeout(1200)

        # 1) click 新建 -> type picker appears
        await pg.click("text=+ 新建")
        await pg.wait_for_timeout(500)
        picker_txt = await pg.evaluate(
            """() => { const el=[...document.querySelectorAll('div')].find(e=>e.textContent.includes('选择记录类型')); return el?el.textContent.slice(0,40):null }"""
        )
        print("PICKER_SHOWN", picker_txt is not None, "->", picker_txt)

        # 2) pick 工作日志 (scope to the picker modal)
        modal = pg.locator('div.fixed.inset-0.z-50')
        await modal.get_by_text('工作日志').click()
        await pg.wait_for_timeout(600)

        info = await pg.evaluate(
            """() => {
                const overlay=[...document.querySelectorAll('div')].find(e=>getComputedStyle(e).position==='fixed'&&e.className.includes('inset-0'));
                if(!overlay) return null;
                const r=overlay.getBoundingClientRect();
                const scroll=overlay.querySelector('div.flex-1.overflow-y-auto');
                const col=scroll?scroll.firstElementChild:null;
                const cr=col?col.getBoundingClientRect():null;
                const rich=overlay.querySelector('.rich-editor');
                const rr=rich?rich.getBoundingClientRect():null;
                const title=overlay.querySelector('input[placeholder="无标题文档"]');
                const chip=[...overlay.querySelectorAll('span')].find(s=>s.textContent.includes('工作日志'));
                return {vw:r.width, vh:r.height,
                        colW: cr?Math.round(cr.width):null,
                        colLeft: cr?Math.round(cr.left):null,
                        richH: rr?Math.round(rr.height):null,
                        titlePH: title?title.placeholder:null,
                        chip: chip?chip.textContent.trim():null};
            }"""
        )
        print("EDITOR", info)

        # template switching test
        overlay = pg.locator('div.fixed.inset-0.z-50')
        await overlay.locator('button:has-text("每日工作日报")').click()
        await pg.wait_for_timeout(300)
        c1 = await overlay.locator('.rich-editor').inner_text()
        print("AFTER_TPL_A", "今日完成" in c1, "本周成果" in c1)
        await overlay.locator('button:has-text("周报")').click()
        await pg.wait_for_timeout(300)
        c2 = await overlay.locator('.rich-editor').inner_text()
        print("AFTER_TPL_B", "今日完成" in c2, "本周成果" in c2)
        await pg.screenshot(path="/workspace/editor_word.png")
        await b.close()

asyncio.run(main())
