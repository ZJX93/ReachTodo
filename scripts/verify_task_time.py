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
        await pg.goto(URL + "/", wait_until="networkidle")
        await pg.wait_for_timeout(1000)

        # open task form
        await pg.click("text=+ 新建")
        await pg.wait_for_timeout(400)
        form = pg.locator('div.fixed.inset-0.z-50')
        await form.locator('input[placeholder="要做什么？"]').fill("带时分截止任务")
        # due date + time (use TODAY so it shows in 今日待办)
        await form.locator('input[type="date"]').fill("2026-08-05")
        await form.locator('input[type="time"]').fill("14:30")
        await form.locator('button:has-text("创建")').click()
        await pg.wait_for_timeout(1200)

        page_txt = await pg.locator("main").inner_text()
        print("LIST_SHOWS_TIME", "📅 2026-08-05 14:30" in page_txt)

        # verify via API
        token = await pg.evaluate("() => localStorage.getItem('token') || ''")
        import httpx
        r = await httpx.AsyncClient().get(
            URL + "/api/tasks?status=todo",
            headers={"Authorization": f"Bearer {token}"},
        )
        tasks = r.json()
        found = [t for t in tasks if t.get("title") == "带时分截止任务"]
        if found:
            t = found[0]
            print("API_DUE_DATE", t["due_date"], "API_DUE_TIME", t["due_time"], "HAS_FIELD", "due_time" in t)
        else:
            print("API_TASK_NOT_FOUND")
        await b.close()


asyncio.run(main())
