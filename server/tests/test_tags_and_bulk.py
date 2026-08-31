"""标签体系 + 任务搜索/筛选 + 批量操作。"""
import asyncio
import uuid

import httpx

from app.database import init_db
from app.main import app


def test_tags_search_and_bulk():
    asyncio.run(_run())


async def _register(c):
    user = "u_" + uuid.uuid4().hex[:10]
    r = await c.post(
        "/api/auth/register", json={"username": user, "password": "secret123"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _run():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        cat_id = (await c.post("/api/categories", json={"name": "work"}, headers=h)).json()["id"]

        # ---- 创建任务时按名自动建标签 ----
        r = await c.post(
            "/api/tasks",
            json={
                "title": "写季度复盘",
                "category_id": cat_id,
                "tags": ["工作", "深度", "工作", "  "],  # 含重复与空白，应被归一化
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        t1 = r.json()
        assert t1["tags"] == ["工作", "深度"], t1["tags"]

        r = await c.post(
            "/api/tasks",
            json={"title": "打电话给客户", "category_id": cat_id, "tags": ["电话"]},
            headers=h,
        )
        t2 = r.json()

        # ---- 标签列表带引用计数 ----
        r = await c.get("/api/tags", headers=h)
        assert r.status_code == 200
        tags = {x["name"]: x for x in r.json()}
        assert set(tags) == {"工作", "深度", "电话"}
        assert tags["工作"]["task_count"] == 1

        # ---- 按标签过滤 ----
        r = await c.get("/api/tasks", params={"tag": "工作"}, headers=h)
        assert [x["id"] for x in r.json()] == [t1["id"]]

        # 多标签 = 同时含有
        r = await c.get("/api/tasks", params=[("tag", "工作"), ("tag", "深度")], headers=h)
        assert [x["id"] for x in r.json()] == [t1["id"]]
        r = await c.get("/api/tasks", params=[("tag", "工作"), ("tag", "电话")], headers=h)
        assert r.json() == []

        # ---- 全文搜索 ----
        r = await c.get("/api/tasks", params={"q": "复盘"}, headers=h)
        assert [x["id"] for x in r.json()] == [t1["id"]]
        # LIKE 元字符必须被转义，否则 "%" 会匹配到全部
        r = await c.get("/api/tasks", params={"q": "%"}, headers=h)
        assert r.json() == []

        # ---- 更新标签：传 [] 清空 ----
        r = await c.put(f"/api/tasks/{t1['id']}", json={"tags": []}, headers=h)
        assert r.status_code == 200
        assert r.json()["tags"] == []
        # 不传 tags 则保持不变
        r = await c.put(f"/api/tasks/{t2['id']}", json={"title": "打电话"}, headers=h)
        assert r.json()["tags"] == ["电话"]

        # ---- 标签重命名全局生效 ----
        tag_id = tags["电话"]["id"]
        r = await c.put(f"/api/tags/{tag_id}", json={"name": "联络"}, headers=h)
        assert r.status_code == 200
        r = await c.get("/api/tasks", params={"tag": "联络"}, headers=h)
        assert [x["id"] for x in r.json()] == [t2["id"]]

        # 同名冲突 -> 409
        r = await c.put(f"/api/tags/{tags['工作']['id']}", json={"name": "联络"}, headers=h)
        assert r.status_code == 409

        # ---- 批量：加标签 ----
        r = await c.post(
            "/api/tasks/bulk",
            json={"ids": [t1["id"], t2["id"]], "action": "add_tags", "tags": ["本周"]},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["affected"] == 2
        r = await c.get("/api/tasks", params={"tag": "本周"}, headers=h)
        assert len(r.json()) == 2

        # 幂等：重复加同一标签不再计入 affected
        r = await c.post(
            "/api/tasks/bulk",
            json={"ids": [t1["id"], t2["id"]], "action": "add_tags", "tags": ["本周"]},
            headers=h,
        )
        assert r.json()["affected"] == 0

        # ---- 批量：完成 ----
        r = await c.post(
            "/api/tasks/bulk",
            json={"ids": [t1["id"], t2["id"]], "action": "complete"},
            headers=h,
        )
        assert r.json()["affected"] == 2
        r = await c.get("/api/tasks", params={"status": "done"}, headers=h)
        assert len(r.json()) == 2

        # ---- 跨账号隔离：他人 id 计入 skipped，不报错也不生效 ----
        h2 = await _register(c)
        r = await c.post(
            "/api/tasks/bulk",
            json={"ids": [t1["id"], t2["id"]], "action": "delete"},
            headers=h2,
        )
        assert r.status_code == 200
        assert r.json() == {
            "action": "delete",
            "requested": 2,
            "affected": 0,
            "skipped": 2,
        }
        # 原用户的数据没被动
        r = await c.get("/api/tasks", headers=h)
        assert len(r.json()) == 2

        # 他人标签也不可见
        r = await c.get("/api/tags", headers=h2)
        assert r.json() == []
