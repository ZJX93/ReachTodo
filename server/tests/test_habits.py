"""习惯打卡（Habit）: CRUD / 四种打卡方式 / streak / 软删除墓碑 / 双向同步。

覆盖要点：
  - 四种打卡方式各自的达标判定（check / count / duration / timerange）
  - 同一 (habit, date) 重复写入走更新而非插入 —— 补卡与同步幂等的地基
  - streak 语义：今日未打卡不立刻断签；非排班日跳过不断签
  - 删除走墓碑，且墓碑能被另一台设备同步拉到（否则删不掉）
  - 同步合并：updated_at 后写覆盖，旧数据不覆盖新数据
  - 越权隔离：他人的习惯一律 404（不泄漏存在性）
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import httpx

from app.database import init_db
from app.main import app


def test_habits_crud_and_checkin():
    asyncio.run(_crud_and_checkin())


def test_habit_streak_semantics():
    asyncio.run(_streak_semantics())


def test_habit_tombstone_and_sync():
    asyncio.run(_tombstone_and_sync())


def test_habit_ownership_isolation():
    asyncio.run(_ownership_isolation())


def test_habit_sync_last_write_wins():
    asyncio.run(_sync_last_write_wins())


# --------------------------------------------------------------------------- #


async def _register(c) -> dict:
    user = "u_" + uuid.uuid4().hex[:10]
    r = await c.post(
        "/api/auth/register", json={"username": user, "password": "secret123"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _today(c, h) -> date:
    """以服务端认定的「今天」为基准，避免测试机与服务端时区不一致导致 flaky。"""
    r = await c.get("/api/habits/today", headers=h)
    assert r.status_code == 200, r.text
    return date.fromisoformat(r.json()["date"])


def _iso(d: date) -> str:
    return d.isoformat()


def _now_iso(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


async def _crud_and_checkin():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        today = await _today(c, h)

        # ---------- 创建四种打卡方式 ----------
        r = await c.post(
            "/api/habits",
            json={"name": "喝够水", "type": "count", "target": 8, "unit": "杯",
                  "frequency": "daily", "size": "lg", "category_id": "health",
                  "start_date": _iso(today - timedelta(days=10))},
            headers=h,
        )
        assert r.status_code == 201, r.text
        water = r.json()
        assert water["type"] == "count" and water["target"] == 8
        assert water["id"], "id 必须是 client_id(uuid)，不能是整数主键"
        assert not str(water["id"]).isdigit()

        r = await c.post(
            "/api/habits",
            json={"name": "读书", "type": "duration", "target": 30, "unit": "分钟"},
            headers=h,
        )
        read = r.json()
        r = await c.post("/api/habits", json={"name": "早睡", "type": "check"}, headers=h)
        sleep = r.json()
        r = await c.post(
            "/api/habits", json={"name": "写代码", "type": "timerange"}, headers=h
        )
        code = r.json()

        # ---------- 计数：未达标 / 达标 ----------
        r = await c.post(
            f"/api/habits/{water['id']}/checkin", json={"value": 3}, headers=h
        )
        assert r.status_code == 200, r.text
        assert r.json()["done"] is False, "3/8 不应算完成"

        r = await c.post(
            f"/api/habits/{water['id']}/checkin", json={"value": 8}, headers=h
        )
        assert r.json()["done"] is True, "8/8 应算完成"

        # 幂等：同一天再写一次，记录仍只有一条
        r = await c.get(f"/api/habits/{water['id']}/checkins", params={"days": 1}, headers=h)
        assert len(r.json()) == 1, f"同日重复打卡应只保留一条，实际 {len(r.json())}"

        # ---------- 时长 ----------
        r = await c.post(
            f"/api/habits/{read['id']}/checkin", json={"value": 29}, headers=h
        )
        assert r.json()["done"] is False, "29/30 分钟不应算完成"
        await c.post(
            f"/api/habits/{read['id']}/checkin", json={"value": 30}, headers=h
        )
        r = await c.get(f"/api/habits/{read['id']}", headers=h)
        assert r.json()["done_today"] is True

        # ---------- 打勾 / 取消 ----------
        await c.post(f"/api/habits/{sleep['id']}/checkin", json={"value": 1}, headers=h)
        r = await c.get(f"/api/habits/{sleep['id']}", headers=h)
        assert r.json()["done_today"] is True
        await c.post(f"/api/habits/{sleep['id']}/checkin", json={"value": 0}, headers=h)
        r = await c.get(f"/api/habits/{sleep['id']}", headers=h)
        assert r.json()["done_today"] is False, "value 归零应视为取消打卡"

        # ---------- 时间段：只填一端不算完成 ----------
        await c.post(
            f"/api/habits/{code['id']}/checkin", json={"start_time": "22:00"}, headers=h
        )
        r = await c.get(f"/api/habits/{code['id']}", headers=h)
        assert r.json()["done_today"] is False
        await c.post(
            f"/api/habits/{code['id']}/checkin", json={"end_time": "23:30"}, headers=h
        )
        r = await c.get(f"/api/habits/{code['id']}", headers=h)
        assert r.json()["done_today"] is True, "起止齐全应算完成"

        # ---------- 补卡：回写历史某一天 ----------
        past = today - timedelta(days=3)
        r = await c.post(
            f"/api/habits/{water['id']}/checkin",
            json={"value": 8, "date": _iso(past)},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["checkin_date"] == _iso(past)

        # ---------- 今日聚合 ----------
        r = await c.get("/api/habits/today", headers=h)
        assert r.status_code == 200, r.text
        tod = r.json()
        assert tod["total"] == 4, tod
        assert tod["done"] == 3, tod  # 水/读书/写代码 完成，早睡被取消
        assert tod["percent"] == 75, tod

        # ---------- 热力图 ----------
        r = await c.get("/api/habits/heatmap", params={"days": 7}, headers=h)
        assert r.status_code == 200, r.text
        heat = r.json()
        assert len(heat) == 7
        assert heat[-1]["date"] == _iso(today), "最后一项应为今天"
        assert 0.0 <= heat[-1]["rate"] <= 1.0

        # ---------- 心情 ----------
        r = await c.post("/api/habits/moods", json={"score": 4}, headers=h)
        assert r.status_code == 200, r.text
        r = await c.post("/api/habits/moods", json={"score": 5}, headers=h)
        assert r.json()["score"] == 5, "同日重复提交应覆盖而非新增"
        r = await c.get("/api/habits/moods", params={"days": 7}, headers=h)
        assert len(r.json()) == 1, "同一天只应有一条心情记录"

        # ---------- 非法枚举回落为默认值，而不是 422 / 500 ----------
        r = await c.post(
            "/api/habits",
            json={"name": "脏数据", "type": "not-a-type", "color": "not-a-color",
                  "frequency": "sometimes", "size": "xl"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["type"] == "check"
        assert r.json()["frequency"] == "daily"
        assert r.json()["size"] == "md"
        assert r.json()["color"] == "#7C9A92"


async def _streak_semantics():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        today = await _today(c, h)

        # 连续 3 天（昨天、前天、大前天），今天不打
        r = await c.post(
            "/api/habits",
            json={"name": "冥想", "type": "check",
                  "start_date": _iso(today - timedelta(days=10))},
            headers=h,
        )
        hid = r.json()["id"]
        for k in (3, 2, 1):
            await c.post(
                f"/api/habits/{hid}/checkin",
                json={"value": 1, "date": _iso(today - timedelta(days=k))},
                headers=h,
            )

        r = await c.get(f"/api/habits/{hid}/stats", headers=h)
        st = r.json()
        # 今日未打卡但昨日连续 —— 从昨天起算，保留 3 天而不是归零
        assert st["streak"] == 3, st
        assert st["best_streak"] == 3, st

        # 今日补上 → 变 4
        await c.post(f"/api/habits/{hid}/checkin", json={"value": 1}, headers=h)
        r = await c.get(f"/api/habits/{hid}/stats", headers=h)
        assert r.json()["streak"] == 4, r.json()

        # 非排班日跳过，不断签：custom 只在周一/三/五
        r = await c.post(
            "/api/habits",
            json={"name": "跑步", "type": "check", "frequency": "custom",
                  "weekdays": [1, 3, 5],
                  "start_date": _iso(today - timedelta(days=40))},
            headers=h,
        )
        assert r.json()["weekdays"] == [1, 3, 5], r.json()
        run_id = r.json()["id"]

        r = await c.get(f"/api/habits/{run_id}/stats", headers=h)
        custom_detail = r.json()["last_30"]

        r2 = await c.post(
            "/api/habits",
            json={"name": "喝水daily", "type": "check", "frequency": "daily",
                  "start_date": _iso(today - timedelta(days=40))},
            headers=h,
        )
        r3 = await c.get(f"/api/habits/{r2.json()['id']}/stats", headers=h)
        daily_detail = r3.json()["last_30"]
        # 两者都回溯 30 天，但 custom 只统计排班日
        assert len(custom_detail) < len(daily_detail), (
            f"custom 应只统计排班日: {len(custom_detail)} vs {len(daily_detail)}"
        )
        assert len(custom_detail) >= 8, f"30 天内周一/三/五至少应有 8 天，实际 {len(custom_detail)}"


async def _tombstone_and_sync():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        today = await _today(c, h)

        # ---- 设备 A：创建习惯并推送到服务端 ----
        cid = str(uuid.uuid4())
        payload = {
            "habits": [{
                "id": cid, "name": "喝水", "type": "count", "target": 8, "unit": "杯",
                "frequency": "daily", "size": "lg", "category_id": "health",
                "start_date": _iso(today - timedelta(days=5)),
                "updated_at": _now_iso(),
            }],
            "checkins": [],
            "moods": [],
        }
        r = await c.post("/api/habits/sync", json=payload, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["applied"]["habits"] == 1, r.json()

        # 对外契约名统一为 category_id（前端原型命名）；内部列名是 category_key
        r = await c.get("/api/habits", headers=h)
        got = [x for x in r.json() if x["id"] == cid]
        assert got and got[0]["category_id"] == "health", r.json()
        assert got[0]["size"] == "lg"

        # ---- 设备 B：拉取增量，应拿到同一条 ----
        r = await c.get(
            "/api/habits/sync", params={"since": "1970-01-01T00:00:00Z"}, headers=h
        )
        assert r.status_code == 200, r.text
        pulled = [x for x in r.json()["habits"] if x["id"] == cid]
        assert len(pulled) == 1, r.json()
        assert pulled[0]["name"] == "喝水"
        assert pulled[0]["deleted_at"] is None

        # ---- 设备 B：打卡后推送，服务端应记录 ----
        await c.post(
            "/api/habits/sync",
            json={
                "habits": [],
                "checkins": [{
                    "id": str(uuid.uuid4()), "habit_id": cid,
                    "checkin_date": _iso(today), "value": 8,
                    "updated_at": _now_iso(),
                }],
                "moods": [{"id": str(uuid.uuid4()), "date": _iso(today), "score": 5,
                           "updated_at": _now_iso()}],
            },
            headers=h,
        )
        r = await c.get("/api/habits/today", headers=h)
        assert r.json()["total"] == 1 and r.json()["done"] == 1, r.json()
        r = await c.get("/api/habits/moods", params={"days": 7}, headers=h)
        assert r.json()[0]["score"] == 5

        # ---- 设备 A：删除习惯（软删），墓碑必须能被拉到 ----
        r = await c.delete(f"/api/habits/{cid}", headers=h)
        assert r.status_code == 204, r.text
        r = await c.get("/api/habits", headers=h)
        assert [x for x in r.json() if x["id"] == cid] == [], "软删后不应出现在列表"

        r = await c.get(
            "/api/habits/sync", params={"since": "1970-01-01T00:00:00Z"}, headers=h
        )
        tomb = [x for x in r.json()["habits"] if x["id"] == cid]
        assert len(tomb) == 1 and tomb[0]["deleted_at"], (
            f"墓碑必须能传播，否则另一台设备上的数据会复活: {r.json()}"
        )

        # ---- 物理删除才是真的删 ----
        r = await c.delete(f"/api/habits/{cid}", params={"purge": "true"}, headers=h)
        assert r.status_code == 204, r.text
        r = await c.get(
            "/api/habits/sync", params={"since": "1970-01-01T00:00:00Z"}, headers=h
        )
        assert [x for x in r.json()["habits"] if x["id"] == cid] == []

        # ---- 孤儿打卡记录（习惯不存在）应被跳过而不是 500 ----
        r = await c.post(
            "/api/habits/sync",
            json={"checkins": [{"id": str(uuid.uuid4()), "habit_id": "ghost-uuid",
                                "checkin_date": _iso(today), "value": 1}]},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["applied"]["checkins"] == 0, r.json()


async def _sync_last_write_wins():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        h = await _register(c)
        today = await _today(c, h)
        cid = str(uuid.uuid4())

        base = {
            "id": cid, "name": "初始", "type": "check",
            "start_date": _iso(today - timedelta(days=3)),
        }
        # 第一次推送：t0
        t0 = _now_iso(-120)
        await c.post("/api/habits/sync", json={"habits": [{**base, "updated_at": t0}]}, headers=h)

        # 用更旧的时间戳推送改名 —— 不应覆盖
        t_old = _now_iso(-600)
        r = await c.post(
            "/api/habits/sync",
            json={"habits": [{**base, "name": "旧改名", "updated_at": t_old}]},
            headers=h,
        )
        assert r.json()["applied"]["habits"] == 0, r.json()
        r = await c.get("/api/habits", headers=h)
        assert [x for x in r.json() if x["id"] == cid][0]["name"] == "初始", r.json()

        # 用更新的时间戳推送改名 —— 应覆盖
        t_new = _now_iso(120)
        r = await c.post(
            "/api/habits/sync",
            json={"habits": [{**base, "name": "新改名", "updated_at": t_new}]},
            headers=h,
        )
        assert r.json()["applied"]["habits"] == 1, r.json()
        r = await c.get("/api/habits", headers=h)
        assert [x for x in r.json() if x["id"] == cid][0]["name"] == "新改名", r.json()

        # since 增量：只返回 updated_at 晚于该时刻的记录。
        # 注意 t_new 是「未来时间戳」(now+120)，所以这里的 since 必须比它更晚。
        r = await c.get("/api/habits/sync", params={"since": _now_iso(200)}, headers=h)
        assert [x for x in r.json()["habits"] if x["id"] == cid] == [], (
            "since 之后的增量应为空"
        )
        r = await c.get("/api/habits/sync", params={"since": t_old}, headers=h)
        assert len([x for x in r.json()["habits"] if x["id"] == cid]) == 1

        # 同步包里多余的未知字段不应导致整包失败
        r = await c.post(
            "/api/habits/sync",
            json={"habits": [{**base, "name": "带未知字段", "updated_at": _now_iso(300),
                              "some_future_field": {"a": 1}}],
                  "unknown_top_level": [1, 2, 3]},
            headers=h,
        )
        assert r.status_code == 200, r.text
        r = await c.get("/api/habits", headers=h)
        assert [x for x in r.json() if x["id"] == cid][0]["name"] == "带未知字段"


async def _ownership_isolation():
    await init_db()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        ha = await _register(c)
        hb = await _register(c)

        r = await c.post("/api/habits", json={"name": "A 的习惯"}, headers=ha)
        hid = r.json()["id"]

        # B 访问 A 的习惯：一律 404（不泄漏存在性）
        for method, url in (("GET", f"/api/habits/{hid}"),):
            r = await c.request(method, url, headers=hb)
            assert r.status_code == 404, r.text
        r = await c.put(f"/api/habits/{hid}", json={"name": "篡改"}, headers=hb)
        assert r.status_code == 404, r.text
        r = await c.delete(f"/api/habits/{hid}", headers=hb)
        assert r.status_code == 404, r.text
        r = await c.post(f"/api/habits/{hid}/checkin", json={"value": 1}, headers=hb)
        assert r.status_code == 404, r.text
        r = await c.get(f"/api/habits/{hid}/stats", headers=hb)
        assert r.status_code == 404, r.text

        # 列表互不可见
        assert len((await c.get("/api/habits", headers=hb)).json()) == 0
        assert len((await c.get("/api/habits", headers=ha)).json()) == 1

        # 未认证访问
        r = await c.get("/api/habits")
        assert r.status_code == 401, r.text
