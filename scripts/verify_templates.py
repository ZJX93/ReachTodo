import asyncio
from playwright.async_api import async_playwright

URL = "https://a6b47180c33600087.bj6.agentos-app.net"

EXPECT = {
    "diary": {
        "每日心情日记": "明天换个做法",
        "感恩日记": "小确幸",
        "自由书写": "写满就好",
    },
    "worklog": {
        "每日工作日报": "今日收获",
        "周报": "本周复盘",
        "会议纪要": "核心决议",
    },
    "note": {
        "读书卡片": "可以如何应用",
        "金句摘抄": "可迁移到",
        "读后感": "我的行动",
    },
}
TYPE_LABEL = {"diary": "个人日记", "worklog": "工作日志", "note": "读书笔记"}


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

        all_ok = True
        for ttype, names in EXPECT.items():
            await pg.click("text=+ 新建")
            await pg.wait_for_timeout(400)
            modal = pg.locator('div.fixed.inset-0.z-50')
            await modal.get_by_text(TYPE_LABEL[ttype]).click()
            await pg.wait_for_timeout(500)
            overlay = pg.locator('div.fixed.inset-0.z-50')
            for name, marker in names.items():
                await overlay.locator(f'button:has-text("{name}")').click()
                await pg.wait_for_timeout(250)
                txt = await overlay.locator('.rich-editor').inner_text()
                ok = marker in txt
                all_ok = all_ok and ok
                print(f"[{ttype}] {name}: marker '{marker}' -> {ok}")
            await overlay.locator('button:has-text("‹ 返回")').click()
            await pg.wait_for_timeout(400)

        print("ALL_OK", all_ok)
        await b.close()


asyncio.run(main())
