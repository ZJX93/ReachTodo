import asyncio, re
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
        await pg.wait_for_timeout(1000)

        # open editor
        await pg.click("text=+ 新建")
        await pg.wait_for_timeout(400)
        modal = pg.locator('div.fixed.inset-0.z-50')
        await modal.get_by_text("工作日志").click()
        await pg.wait_for_timeout(500)
        overlay = pg.locator('div.fixed.inset-0.z-50')

        # time input present + default HH:MM
        time_val = await overlay.locator('input[type="time"]').input_value()
        print("TIME_INPUT_DEFAULT", time_val, "MATCH", bool(re.match(r"^\d{2}:\d{2}$", time_val)))

        # pick a template then set title and save
        await overlay.locator('button:has-text("每日工作日报")').click()
        await pg.wait_for_timeout(200)
        await overlay.locator('input[placeholder="无标题文档"]').fill("时间精度测试记录")
        await overlay.locator('button:has-text("保存")').click()
        await pg.wait_for_timeout(1200)

        # back on list: new card should show 🕒 time
        main_txt = await pg.locator("main").inner_text()
        print("LIST_HAS_CLOCK", "🕒" in main_txt)

        # confirm via API
        token = await pg.evaluate("() => localStorage.getItem('token') || ''")
        import httpx
        headers = {"Authorization": f"Bearer {token}"}
        r = await httpx.AsyncClient().get(URL + "/api/records?type=worklog", headers=headers)
        recs = r.json()
        found = [x for x in recs if x.get("title") == "时间精度测试记录"]
        print("API_RECORD_TIME", found[0]["record_time"] if found else "NOT_FOUND",
              "HAS_FIELD", "record_time" in (found[0] if found else {}))
        await b.close()


asyncio.run(main())
