"""偏好云同步 + ICS 日历订阅 + 数据导入/恢复 + /health 自省。"""
import asyncio
import uuid

import httpx

from app.database import init_db
from app.main import app


async def _register(c):
    user = "u_" + uuid.uuid4().hex[:10]
    r = await c.post(
        "/api/auth/register", json={"username": user, "password": "secret123"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_settings_sync():
    asyncio.run(_settings())


async def _settings():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)

        # 首次读取：懒创建 + 返回服务端权威默认值
        r = await c.get("/api/settings", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["settings"]["focusMinutes"] == 25
        assert body["settings"]["weekStart"] == "sun"
        assert len(body["feed_token"]) >= 8
        assert body["feed_path"].startswith("/api/calendar.ics?token=")
        token1 = body["feed_token"]

        # 增量更新：只提交要改的键
        r = await c.put(
            "/api/settings",
            json={"focusMinutes": 50, "weekStart": "mon", "theme": "dark"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        s = r.json()["settings"]
        assert s["focusMinutes"] == 50
        assert s["weekStart"] == "mon"
        assert s["theme"] == "dark"
        # 未提交的键保持默认
        assert s["focusBreakMinutes"] == 5

        # 再次单独改一个键，之前的改动不丢
        r = await c.put("/api/settings", json={"showCompleted": True}, headers=h)
        s = r.json()["settings"]
        assert s["focusMinutes"] == 50 and s["showCompleted"] is True

        # 越界值被拒
        assert (await c.put("/api/settings", json={"focusMinutes": 0}, headers=h)).status_code == 422
        assert (await c.put("/api/settings", json={"weekStart": "tue"}, headers=h)).status_code == 422
        # 白名单外的键被拒（extra="forbid"），防止当成免费 KV 存储
        assert (await c.put("/api/settings", json={"junk": 1}, headers=h)).status_code == 422

        # 重置订阅令牌
        r = await c.post("/api/settings/feed-token/reset", headers=h)
        assert r.status_code == 200
        assert r.json()["feed_token"] != token1

        # 每个用户的令牌互不相同
        h2 = await _register(c)
        token2 = (await c.get("/api/settings", headers=h2)).json()["feed_token"]
        assert token2 != token1


def test_ics_feed():
    asyncio.run(_ics())


async def _ics():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        cat_id = (await c.post("/api/categories", json={"name": "工作"}, headers=h)).json()["id"]
        token = (await c.get("/api/settings", headers=h)).json()["feed_token"]

        await c.post(
            "/api/tasks",
            json={
                # 标题里刻意放 ASCII 的 ; 与 , —— ICS 规范要求这两个字符必须转义
                "title": "季度汇报; 含分号,和逗号",
                "category_id": cat_id,
                "due_date": "2026-09-10",
                "due_time": "14:30",
                "remind_before_minutes": 45,
                "tags": ["重要"],
            },
            headers=h,
        )
        # 无到期日的任务不应出现在日历里
        await c.post("/api/tasks", json={"title": "没有排期", "category_id": cat_id}, headers=h)

        r = await c.get(f"/api/calendar.ics?token={token}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/calendar")
        text = r.text
        assert text.startswith("BEGIN:VCALENDAR\r\n")
        assert text.rstrip().endswith("END:VCALENDAR")
        # 每行必须用 CRLF
        assert "\r\n" in text
        assert text.count("BEGIN:VEVENT") == 1
        assert "没有排期" not in text
        # 分号 / 逗号必须被转义
        assert "\\;" in text and "\\," in text
        # 任务级提前量写进 VALARM
        assert "TRIGGER:-PT45M" in text
        # 折行的续行必须以单个空格开头
        for line in text.split("\r\n"):
            assert len(line.encode("utf-8")) <= 75, line

        # 无效令牌统一 404，不泄露格式信息
        assert (await c.get("/api/calendar.ics?token=" + "x" * 20)).status_code == 404


def test_export_import_roundtrip():
    asyncio.run(_roundtrip())


async def _roundtrip():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        cat_id = (await c.post("/api/categories", json={"name": "工作"}, headers=h)).json()["id"]
        goal_id = (
            await c.post("/api/goals", json={"title": "上线 v1"}, headers=h)
        ).json()["id"]

        parent = (
            await c.post(
                "/api/tasks",
                json={
                    "title": "父任务",
                    "category_id": cat_id,
                    "goal_id": goal_id,
                    "due_date": "2026-09-20",
                    "due_time": "09:00",
                    "priority": "urgent",
                    "importance": "high",
                    "recurrence": "biweekly",
                    "remind_before_minutes": 15,
                    "tags": ["A", "B"],
                },
                headers=h,
            )
        ).json()
        await c.post(
            "/api/tasks",
            json={"title": "子任务", "category_id": cat_id, "parent_id": parent["id"]},
            headers=h,
        )
        await c.post(
            "/api/records",
            json={
                "type": "note",
                "record_date": "2026-08-30",
                "title": "读书笔记",
                "content": "内容",
            },
            headers=h,
        )
        await c.put("/api/settings", json={"focusMinutes": 45}, headers=h)

        backup = (await c.get("/api/export?fmt=json", headers=h)).json()
        assert backup["version"] == 2
        assert backup["settings"]["focusMinutes"] == 45
        assert {t["name"] for t in backup["tags"]} == {"A", "B"}
        exported = next(t for t in backup["tasks"] if t["title"] == "父任务")
        assert sorted(exported["tags"]) == ["A", "B"]

        # ---- 导入到一个全新账号 ----
        h2 = await _register(c)
        r = await c.post("/api/import", json=backup, headers=h2)
        assert r.status_code == 200, r.text
        stats = r.json()["imported"]
        assert stats["tasks"] == 2
        assert stats["records"] == 1
        assert stats["goals"] == 1

        tasks = (await c.get("/api/tasks", headers=h2)).json()
        assert len(tasks) == 2
        p = next(t for t in tasks if t["title"] == "父任务")
        s = next(t for t in tasks if t["title"] == "子任务")
        # 字段完整还原
        assert p["priority"] == "urgent" and p["importance"] == "high"
        assert p["recurrence"] == "biweekly"
        assert p["due_date"] == "2026-09-20" and p["due_time"] == "09:00"
        assert p["remind_before_minutes"] == 15
        assert sorted(p["tags"]) == ["A", "B"]
        # 父子关系按名重建，且 id 是新账号自己的（不复用备份里的 id）
        assert s["parent_id"] == p["id"]
        assert p["id"] != parent["id"] or s["parent_id"] != parent["parent_id"]
        # 关联目标重新指向新账号的目标
        assert p["goal_title"] == "上线 v1"
        # 偏好一并恢复
        assert (await c.get("/api/settings", headers=h2)).json()["settings"]["focusMinutes"] == 45

        # ---- merge 幂等：记录去重，不翻倍 ----
        r = await c.post("/api/import", json=backup, headers=h2)
        assert r.json()["imported"]["records"] == 0
        assert len((await c.get("/api/records", headers=h2)).json()) == 1

        # ---- replace 策略：先清空再导入 ----
        r = await c.post("/api/import?strategy=replace", json=backup, headers=h2)
        assert r.status_code == 200
        assert len((await c.get("/api/tasks", headers=h2)).json()) == 2

        # ---- 非本应用备份被拒 ----
        assert (await c.post("/api/import", json={"app": "other"}, headers=h2)).status_code == 400


def test_health_introspection():
    asyncio.run(_health())


async def _health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["version"]
        assert "features" in body and "reminder" in body
        # 密钥必须脱敏
        assert "***" in body["secrets"]["jwt_secret"]
        assert isinstance(body["config_warnings"], list)

        # 深度探针会真正打一次库
        r = await c.get("/health?deep=1")
        assert r.status_code == 200
        assert r.json()["database_status"] == "ok"
