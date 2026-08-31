"""回收站（软删除）+ 扩展重复规则。"""
import asyncio
import uuid
from datetime import date

import httpx

from app.database import init_db
from app.main import app
from app.routers.tasks import next_occurrence


def test_recurrence_rules():
    """扩展重复规则是纯函数，直接单测，无需起服务。"""
    # weekday：周五(2026-09-04) → 下周一(09-07)
    assert next_occurrence(date(2026, 9, 4), "weekday") == date(2026, 9, 7)
    # weekday：周六 → 下周一
    assert next_occurrence(date(2026, 9, 5), "weekday") == date(2026, 9, 7)
    # weekday：周一 → 周二
    assert next_occurrence(date(2026, 9, 7), "weekday") == date(2026, 9, 8)

    assert next_occurrence(date(2026, 9, 1), "biweekly") == date(2026, 9, 15)

    # monthly 需钳制到目标月最后一天：1/31 → 2/28（2026 非闰年）
    assert next_occurrence(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
    # 跨年
    assert next_occurrence(date(2026, 12, 15), "monthly") == date(2027, 1, 15)

    # monthend：月中 → 本月末；月末 → 下月末
    assert next_occurrence(date(2026, 9, 10), "monthend") == date(2026, 9, 30)
    assert next_occurrence(date(2026, 9, 30), "monthend") == date(2026, 10, 31)
    # 跨年月末
    assert next_occurrence(date(2026, 12, 31), "monthend") == date(2027, 1, 31)

    # 旧规则语义不变
    assert next_occurrence(date(2026, 9, 1), "daily") == date(2026, 9, 2)
    assert next_occurrence(date(2026, 9, 1), "weekly") == date(2026, 9, 8)
    # 未知规则不抛异常，原样返回
    assert next_occurrence(date(2026, 9, 1), "garbage") == date(2026, 9, 1)


def test_trash_flow():
    asyncio.run(_run())


async def _run():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        user = "u_" + uuid.uuid4().hex[:10]
        r = await c.post(
            "/api/auth/register", json={"username": user, "password": "secret123"}
        )
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        cat_id = (await c.post("/api/categories", json={"name": "life"}, headers=h)).json()["id"]

        task_id = (
            await c.post(
                "/api/tasks", json={"title": "会被误删的任务", "category_id": cat_id}, headers=h
            )
        ).json()["id"]
        rec_id = (
            await c.post(
                "/api/records",
                json={
                    "type": "diary",
                    "record_date": "2026-08-31",
                    "title": "会被误删的日记",
                    "content": "正文",
                },
                headers=h,
            )
        ).json()["id"]

        # ---- 删除 → 进回收站，列表不再可见 ----
        assert (await c.delete(f"/api/tasks/{task_id}", headers=h)).status_code == 204
        assert (await c.delete(f"/api/records/{rec_id}", headers=h)).status_code == 204
        assert (await c.get("/api/tasks", headers=h)).json() == []
        assert (await c.get("/api/records", headers=h)).json() == []

        # 统计也不应再包含它
        s = (await c.get("/api/tasks/summary", headers=h)).json()
        assert s["total_todo"] == 0

        # ---- 回收站可见 ----
        r = await c.get("/api/trash", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        kinds = {(x["kind"], x["id"]) for x in body["items"]}
        assert ("task", task_id) in kinds
        assert ("record", rec_id) in kinds
        assert body["retention_days"] >= 1

        # ---- 恢复 ----
        assert (
            await c.post(f"/api/trash/task/{task_id}/restore", headers=h)
        ).status_code == 200
        assert len((await c.get("/api/tasks", headers=h)).json()) == 1
        # 恢复过的条目不再在回收站里
        r = await c.post(f"/api/trash/task/{task_id}/restore", headers=h)
        assert r.status_code == 404

        # ---- 彻底删除 ----
        assert (await c.delete(f"/api/trash/record/{rec_id}", headers=h)).status_code == 204
        assert (await c.get("/api/trash", headers=h)).json()["items"] == []

        # ---- purge=1 跳过回收站 ----
        assert (
            await c.delete(f"/api/tasks/{task_id}?purge=1", headers=h)
        ).status_code == 204
        assert (await c.get("/api/trash", headers=h)).json()["items"] == []
        assert (await c.get("/api/tasks", headers=h)).json() == []

        # ---- 清空回收站 ----
        t2 = (
            await c.post("/api/tasks", json={"title": "T2", "category_id": cat_id}, headers=h)
        ).json()["id"]
        await c.delete(f"/api/tasks/{t2}", headers=h)
        r = await c.delete("/api/trash", headers=h)
        assert r.status_code == 200
        assert r.json()["purged_tasks"] == 1
        assert (await c.get("/api/trash", headers=h)).json()["items"] == []


def test_recurring_task_spawns_next():
    asyncio.run(_spawn())


async def _spawn():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        user = "u_" + uuid.uuid4().hex[:10]
        r = await c.post(
            "/api/auth/register", json={"username": user, "password": "secret123"}
        )
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        cat_id = (await c.post("/api/categories", json={"name": "w"}, headers=h)).json()["id"]

        # 完成「工作日重复」任务应生成下一个工作日的实例，并继承标签与提前量
        r = await c.post(
            "/api/tasks",
            json={
                "title": "写日报",
                "category_id": cat_id,
                "recurrence": "weekday",
                "due_date": "2026-09-04",  # 周五
                "due_time": "18:00",
                "remind_before_minutes": 30,
                "tags": ["日常"],
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        assert r.json()["remind_before_minutes"] == 30

        await c.put(f"/api/tasks/{tid}", json={"status": "done"}, headers=h)

        todos = (await c.get("/api/tasks", params={"status": "todo"}, headers=h)).json()
        assert len(todos) == 1
        nxt = todos[0]
        assert nxt["due_date"] == "2026-09-07"  # 周五 → 下周一
        assert nxt["due_time"] == "18:00"
        assert nxt["remind_before_minutes"] == 30
