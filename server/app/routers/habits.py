"""习惯打卡：CRUD + 打卡 + 今日聚合 + 统计 + 双向同步。

对外暴露的 ``id`` 一律是 ``client_id``（字符串 uuid），数据库自增主键只在
内部做外键关联。这样客户端断网时也能生成 id，联网后直接对齐，
不必等待服务端分配 —— 离线优先架构的关键一环。

同步协议（与前端 ``docs/prototypes/habit-station.html`` 的 Sync 模块对齐）：

    GET  /api/habits/sync?since=<ISO>&tz=<IANA>  拉取 updated_at 晚于 since 的增量
    POST /api/habits/sync?since=<ISO>&tz=<IANA>  推送增量，并回传 since 之后的增量

两个端点都接受可选的 ``tz``（IANA 时区名）来判定「今天」，不传则用服务端
配置时区。POST 的 ``since`` 默认为 epoch（等价回传全量快照，兼容早期客户端），
新客户端应传上次同步拿到的 ``server_time`` 以减小响应体。

合并策略：**last-write-wins**，按 client_id 定位、比 ``updated_at``。
删除通过 ``deleted_at`` 墓碑传播，绝不物理删除，否则已删数据会在另一台
设备下次推送时「复活」。

已知边界：
- ``updated_at`` 采用**客户端提供的时间戳**（客户端提供时），
  保证同一条记录在各端的时间戳一致；客户端未提供时才用服务端时间。
  因此客户端时钟严重偏移会影响合并结果 —— 响应里的 ``server_time``
  供客户端校准，建议用服务端时间作为下次 ``since`` 的基准。
- 「取消打卡」= 把 ``value`` 归零，记录仍保留；真正的删除只发生在
  删除习惯（走墓碑）。因此打卡记录不需要墓碑字段。
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Habit, HabitCheckin, HabitMood, User, is_scheduled_on
from ..schemas import (
    CheckinIn,
    CheckinOut,
    HabitCreate,
    HabitOut,
    HabitStatsOut,
    HabitUpdate,
    MoodIn,
    MoodOut,
    SyncPull,
    SyncPush,
    TodayOut,
)

router = APIRouter(prefix="/api/habits", tags=["habits"])

_TYPES = ("check", "count", "duration", "timerange")
_FREQS = ("daily", "weekday", "weekend", "custom")
_SIZES = ("sm", "md", "lg")
_DEFAULT_COLOR = "#7C9A92"
_MAX_SPAN_DAYS = 3650  # streak 回溯上限，防脏数据（start_date 极早）拖垮请求

# 客户端 updated_at 的容差区间。合并策略是 last-write-wins、完全信任客户端
# 时间戳，因此某端时钟严重超前（误设为 2099 年）时，那条记录会在所有设备上
# 「永远最新」，再也改不动 —— 必须对客户端时间戳做区间收敛。
_CLOCK_SKEW_FUTURE = timedelta(minutes=5)  # 允许的未来偏移（覆盖网络延迟与跨时区误差）
_CLOCK_SKEW_PAST = timedelta(days=365)  # 允许的回溯上限，超出即视为时钟异常


# =========================================================================
# 工具
# =========================================================================


def _tz(name: Optional[str] = None):
    """解析时区；非法或系统缺 tzdata 时回落到配置时区，再不行回落 UTC。

    Windows 上若未安装 ``tzdata``，``ZoneInfo`` 会抛异常；
    这里分级兜底，保证接口不会因时区库缺失而 500。
    """
    from zoneinfo import ZoneInfo

    candidates = [name, settings.timezone, "Asia/Shanghai", "UTC"]
    for cand in candidates:
        if not cand:
            continue
        try:
            return ZoneInfo(str(cand).strip())
        except Exception:  # noqa: BLE001
            continue
    return timezone.utc


def today_in(tz_name: Optional[str] = None) -> date:
    """业务意义上的「今天」。

    打卡是「我的今天」，必须按用户时区切分，不能一律用 UTC ——
    否则东八区用户在晚上 8 点打卡会被记到「明天」。
    """
    return datetime.now(_tz(tz_name)).date()


def _parse_dt(v: Any) -> Optional[datetime]:
    """把客户端时间字符串解析为 tz-aware datetime；脏数据返回 None。"""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _parse_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _dt_iso(v: Any) -> str:
    d = _parse_dt(v)
    return d.isoformat() if d else ""


def _is_done(habit: Habit, ci: Optional[HabitCheckin]) -> bool:
    """该次打卡是否达成目标。四种类型判定口径不同。"""
    if ci is None:
        return False
    if habit.type == "check":
        return ci.value >= 1
    if habit.type == "timerange":
        return bool(ci.start_time and ci.end_time)
    return ci.value >= max(1, habit.target)


def _progress(habit: Habit, ci: Optional[HabitCheckin]) -> float:
    """完成度 0~1，用于进度条与热力图色阶。"""
    if ci is None:
        return 0.0
    if habit.type == "check":
        return 1.0 if ci.value >= 1 else 0.0
    if habit.type == "timerange":
        return 1.0 if (ci.start_time and ci.end_time) else 0.0
    return min(1.0, ci.value / max(1, habit.target))


def _streak(habit: Habit, by_date: dict[date, HabitCheckin], today: date) -> int:
    """当前连续天数。

    今日尚未打卡时不立刻断签 —— 从昨天起算，给用户在当天结束前补救的机会。
    非排班日（如「工作日」习惯遇到周末）直接跳过，不计入也不断签。
    """
    start = _parse_date(habit.start_date) or today
    d = today if _is_done(habit, by_date.get(today)) else today - timedelta(days=1)
    n = 0
    guard = 0
    while d >= start and guard < _MAX_SPAN_DAYS:
        guard += 1
        if is_scheduled_on(habit, d):
            if _is_done(habit, by_date.get(d)):
                n += 1
                d -= timedelta(days=1)
                continue
            break
        d -= timedelta(days=1)
    return n


def _best_streak(habit: Habit, by_date: dict[date, HabitCheckin], today: date) -> int:
    """历史最长连续纪录。"""
    start = _parse_date(habit.start_date) or today
    best = 0
    cur = 0
    d = start
    guard = 0
    while d <= today and guard < _MAX_SPAN_DAYS:
        guard += 1
        if is_scheduled_on(habit, d):
            if _is_done(habit, by_date.get(d)):
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        d += timedelta(days=1)
    return best


def _habit_payload(
    habit: Habit,
    by_date: dict[date, HabitCheckin],
    today: date,
    with_stats: bool = True,
) -> dict[str, Any]:
    """把 ORM 对象序列化为对外契约（id 用 client_id）。

    with_stats=False 用于同步端点：同步只传原始字段，
    统计值各端本地算即可，没必要占用带宽，也避免快照与实时值打架。
    """
    out: dict[str, Any] = {
        "id": habit.client_id,
        "name": habit.name,
        "icon": habit.icon,
        "color": habit.color,
        "type": habit.type,
        "target": habit.target,
        "unit": habit.unit,
        "frequency": habit.frequency,
        "weekdays": habit.weekdays_list(),
        "size": habit.size,
        # 对外契约名跟随前端原型（category_id 是维度字符串键）。
        # 内部列名 category_key 是为了避免与 Task.category_id（整数外键）混淆。
        "category_id": habit.category_key,
        "goal_id": habit.goal_id,
        "start_date": _parse_date(habit.start_date) or today,
        "archived": bool(habit.archived),
        "sort_order": habit.sort_order,
        "created_at": _dt_iso(habit.created_at),
        "updated_at": _dt_iso(habit.updated_at),
        "deleted_at": _dt_iso(habit.deleted_at) or None,
    }
    if with_stats:
        ci = by_date.get(today)
        out["streak"] = _streak(habit, by_date, today)
        out["best_streak"] = _best_streak(habit, by_date, today)
        out["done_today"] = _is_done(habit, ci)
        out["value_today"] = ci.value if ci else 0
    return out


def _checkin_payload(ci: HabitCheckin, habit_client_id: str = "") -> dict[str, Any]:
    return {
        "id": ci.client_id,
        "habit_id": habit_client_id or "",
        "checkin_date": _parse_date(ci.checkin_date),
        "value": ci.value,
        "start_time": ci.start_time,
        "end_time": ci.end_time,
        "note": ci.note,
        "created_at": _dt_iso(ci.created_at),
        "updated_at": _dt_iso(ci.updated_at),
    }


def _mood_payload(m: HabitMood) -> dict[str, Any]:
    return {
        "id": m.client_id,
        "date": _parse_date(m.mood_date),
        "score": m.score,
        "note": m.note,
        "created_at": _dt_iso(m.created_at),
        "updated_at": _dt_iso(m.updated_at),
    }


async def _load_checkins(
    db: AsyncSession, user_id: int, since: Optional[date] = None
) -> dict[int, dict[date, HabitCheckin]]:
    """一次性加载该用户的打卡记录，按 habit 主键 → 日期 建索引。

    一次查询代替 N 次：streak / 热力图 / 今日态都需要历史数据，
    逐条查会退化成 N+1。个人场景下数据量在千级，全量加载完全可接受。
    """
    q = select(HabitCheckin).where(HabitCheckin.user_id == user_id)
    if since:
        q = q.where(HabitCheckin.checkin_date >= since)
    rows = (await db.execute(q)).scalars().all()
    out: dict[int, dict[date, HabitCheckin]] = defaultdict(dict)
    for r in rows:
        d = _parse_date(r.checkin_date)
        if d:
            out[r.habit_id][d] = r
    return out


async def _get_habit(
    db: AsyncSession, user_id: int, client_id: str, include_deleted: bool = False
) -> Optional[Habit]:
    q = select(Habit).where(Habit.user_id == user_id, Habit.client_id == client_id)
    if not include_deleted:
        q = q.where(Habit.deleted_at.is_(None))
    return await db.scalar(q)


# =========================================================================
# 具体路径（必须注册在 /{habit_id} 之前，否则会被路径参数吞掉）
# =========================================================================


@router.get("/today", response_model=TodayOut)
async def today(
    tz: Optional[str] = Query(default=None, description="IANA 时区，缺省用服务端配置"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """今日聚合：一次请求满足首页全部渲染需求。

    包含进度百分比、全站连续全勤天数、每个习惯的今日状态、今日心情。
    刻意做成聚合接口而不是让前端拼 N 个请求 —— 首页是打开频次最高的页面。
    """
    today = today_in(tz)
    habits = (
        await db.execute(
            select(Habit)
            .where(
                Habit.user_id == current.id,
                Habit.deleted_at.is_(None),
                Habit.archived.is_(False),
            )
            .order_by(Habit.sort_order, Habit.id)
        )
    ).scalars().all()

    by_date = await _load_checkins(db, current.id)

    items = []
    done_n = 0
    for h in habits:
        dates = by_date.get(h.id, {})
        # start_date 之后才开始计，避免把「未来才开始的习惯」算进今日待办
        if (_parse_date(h.start_date) or today) > today:
            continue
        if not is_scheduled_on(h, today):
            continue
        ci = dates.get(today)
        is_done = _is_done(h, ci)
        if is_done:
            done_n += 1
        items.append(
            {
                **_habit_payload(h, dates, today),
                "progress": round(_progress(h, ci), 3),
                "checkin": _checkin_payload(ci, h.client_id) if ci else None,
            }
        )

    total = len(items)
    mood = await db.scalar(
        select(HabitMood).where(
            HabitMood.user_id == current.id, HabitMood.mood_date == today
        )
    )

    # 全站连续全勤：连续几天「当天全部习惯都完成」
    streak = 0
    if total:
        d = today
        guard = 0
        while guard < _MAX_SPAN_DAYS:
            guard += 1
            scheduled = [
                h
                for h in habits
                if (_parse_date(h.start_date) or d) <= d and is_scheduled_on(h, d)
            ]
            if not scheduled:
                break
            if all(_is_done(h, by_date.get(h.id, {}).get(d)) for h in scheduled):
                streak += 1
                d -= timedelta(days=1)
                continue
            if d == today:
                # 今天还没做完很正常，从昨天起算（同单习惯 streak 的处理）
                d -= timedelta(days=1)
                continue
            break

    return TodayOut(
        date=today.isoformat(),
        total=total,
        done=done_n,
        percent=round(done_n / total * 100) if total else 0,
        streak=streak,
        habits=items,
        mood=mood.score if mood else None,
    )


@router.get("/heatmap")
async def heatmap(
    days: int = Query(default=30, ge=1, le=366),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """近 N 天每日完成度，供前端画热力图。

    返回 ``rate``（0~1）而不是布尔值：部分完成（如 8 杯水喝了 5 杯）
    也该在热力图上体现深浅，这正是一天一条记录的价值。
    """
    today = today_in(tz)
    start = today - timedelta(days=days - 1)

    habits = (
        await db.execute(
            select(Habit).where(
                Habit.user_id == current.id,
                Habit.deleted_at.is_(None),
                Habit.archived.is_(False),
            )
        )
    ).scalars().all()
    by_date = await _load_checkins(db, current.id, since=start)

    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        scheduled = [
            h
            for h in habits
            if (_parse_date(h.start_date) or d) <= d and is_scheduled_on(h, d)
        ]
        if not scheduled:
            out.append({"date": d.isoformat(), "total": 0, "done": 0, "rate": 0.0})
            continue
        done = sum(1 for h in scheduled if _is_done(h, by_date.get(h.id, {}).get(d)))
        acc = sum(_progress(h, by_date.get(h.id, {}).get(d)) for h in scheduled)
        out.append(
            {
                "date": d.isoformat(),
                "total": len(scheduled),
                "done": done,
                "rate": round(acc / len(scheduled), 3),
            }
        )
    return out


# ---------------------------------------------------------------- 心情


@router.get("/moods", response_model=list[MoodOut])
async def list_moods(
    days: int = Query(default=30, ge=1, le=366),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    today = today_in(tz)
    start = today - timedelta(days=days - 1)
    rows = (
        await db.execute(
            select(HabitMood)
            .where(
                HabitMood.user_id == current.id,
                HabitMood.mood_date >= start,
                HabitMood.mood_date <= today,
            )
            .order_by(HabitMood.mood_date)
        )
    ).scalars().all()
    return [MoodOut.model_validate(_mood_payload(m)) for m in rows]


@router.post("/moods", response_model=MoodOut)
async def upsert_mood(
    payload: MoodIn,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """记录今日（或补记某天）心情。同一天重复提交走更新。"""
    d = payload.date or today_in(tz)
    row = await db.scalar(
        select(HabitMood).where(
            HabitMood.user_id == current.id, HabitMood.mood_date == d
        )
    )
    if row is None:
        row = HabitMood(
            user_id=current.id,
            client_id=str(uuid.uuid4()),
            mood_date=d,
            score=payload.score,
            note=payload.note,
        )
        db.add(row)
    else:
        row.score = payload.score
        row.note = payload.note
    await db.commit()
    await db.refresh(row)
    return MoodOut.model_validate(_mood_payload(row))


# ---------------------------------------------------------------- 同步


@router.get("/sync", response_model=SyncPull)
async def sync_pull(
    since: str = Query(default="1970-01-01T00:00:00Z"),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """拉取增量。

    ``since`` 为 ISO 时间戳；返回所有 ``updated_at`` 晚于它的记录，
    **包含已删除的墓碑**（否则其它设备不知道有东西被删了）。
    """
    cutoff = _parse_dt(since) or datetime(1970, 1, 1, tzinfo=timezone.utc)
    today = today_in(tz)

    habits = (
        await db.execute(
            select(Habit).where(
                Habit.user_id == current.id, Habit.updated_at > cutoff
            )
        )
    ).scalars().all()
    checkins = (
        await db.execute(
            select(HabitCheckin).where(
                HabitCheckin.user_id == current.id, HabitCheckin.updated_at > cutoff
            )
        )
    ).scalars().all()
    moods = (
        await db.execute(
            select(HabitMood).where(
                HabitMood.user_id == current.id, HabitMood.updated_at > cutoff
            )
        )
    ).scalars().all()

    # checkin 需要带上所属习惯的 client_id，客户端才能把记录挂回去
    habit_ids = {c.habit_id for c in checkins}
    cid_map: dict[int, str] = {}
    if habit_ids:
        rows = (
            await db.execute(
                select(Habit.id, Habit.client_id).where(Habit.id.in_(habit_ids))
            )
        ).all()
        cid_map = {r[0]: r[1] for r in rows}

    return SyncPull(
        habits=[_habit_payload(h, {}, today, with_stats=False) for h in habits],
        checkins=[
            _checkin_payload(c, cid_map.get(c.habit_id, "")) for c in checkins
        ],
        moods=[_mood_payload(m) for m in moods],
        server_time=datetime.now(timezone.utc).isoformat(),
    )


_HABIT_FIELDS = (
    "name",
    "icon",
    "color",
    "type",
    "target",
    "unit",
    "frequency",
    "weekdays",
    "size",
    "category_key",
    "goal_id",
    "start_date",
    "archived",
    "sort_order",
)


def _apply_habit_fields(habit: Habit, item: dict[str, Any], today: date) -> None:
    """把客户端提交的字段白名单式地写进 ORM 对象。

    刻意「宽松清洗」而不是严格校验：客户端可能来自旧版本、多带字段、
    或带了不被识别的枚举值。为这种小问题拒绝整包同步的代价太大 ——
    非法值一律回落到默认值，保证数据能落库且页面不崩。
    """
    name = str(item.get("name") or "").strip()
    if name:
        habit.name = name[:100]

    if "icon" in item and str(item.get("icon") or "").strip():
        habit.icon = str(item["icon"]).strip()[:40]

    if "color" in item:
        import re

        c = str(item.get("color") or "").strip()
        habit.color = c if re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", c) else _DEFAULT_COLOR

    t = str(item.get("type") or "").strip()
    if t in _TYPES:
        habit.type = t

    if "target" in item:
        try:
            habit.target = max(1, min(9999, int(item.get("target") or 1)))
        except (TypeError, ValueError):
            pass

    if "unit" in item and str(item.get("unit") or "").strip():
        habit.unit = str(item["unit"]).strip()[:16]

    f = str(item.get("frequency") or "").strip()
    if f in _FREQS:
        habit.frequency = f

    if "weekdays" in item:
        raw = item.get("weekdays")
        if isinstance(raw, list):
            days = []
            for x in raw:
                try:
                    n = int(x)
                except (TypeError, ValueError):
                    continue
                if 0 <= n <= 6 and n not in days:
                    days.append(n)
            habit.weekdays = json.dumps(sorted(days))
        elif raw is None:
            habit.weekdays = json.dumps([])

    s = str(item.get("size") or "").strip()
    if s in _SIZES:
        habit.size = s

    # 前端契约字段名是 category_id（维度字符串键，如 work/health/study/life）；
    # 后端内部列名 category_key 以免与 Task.category_id（整数外键）混淆。
    # 顺带兼容早期推送方用 category_key 的情况。
    cat = item.get("category_id", item.get("category_key"))
    if cat is not None:
        habit.category_key = (str(cat).strip()[:40]) or None

    if "goal_id" in item:
        g = item.get("goal_id")
        try:
            habit.goal_id = int(g) if g not in (None, "", 0) else None
        except (TypeError, ValueError):
            habit.goal_id = None

    sd = _parse_date(item.get("start_date"))
    if sd:
        habit.start_date = sd
    elif habit.start_date is None:
        habit.start_date = today

    if "archived" in item:
        habit.archived = bool(item.get("archived"))

    if "sort_order" in item:
        try:
            habit.sort_order = int(item.get("sort_order") or 0)
        except (TypeError, ValueError):
            pass


def _newer_than(remote: Optional[datetime], local: Optional[datetime]) -> bool:
    """远端是否比本地新。任一端缺失时间戳时以「有值者」为新。"""
    if remote and local:
        return remote > local
    return remote is not None and local is None


def _sanitize_updated_at(remote: Optional[datetime]) -> Optional[datetime]:
    """把客户端提供的 updated_at 收敛到合理区间。

    LWW 的软肋是信任客户端时钟：一台时钟超前一天的设备推送后，它的数据
    在所有设备上都会「赢」，用户再怎么改都改不动。这里做双向夹紧：

    - 超前 → 夹到当前时刻（剥夺它不该有的优先权）；
    - 过分滞后 → 夹到回溯下限。**不能**退回 None：那样会触发列的
      ``onupdate`` 把时间戳刷成「现在」，反而让旧数据覆盖新数据。
    """
    if remote is None:
        return None
    now = datetime.now(timezone.utc)
    if remote > now + _CLOCK_SKEW_FUTURE:
        return now
    if remote < now - _CLOCK_SKEW_PAST:
        return now - _CLOCK_SKEW_PAST
    return remote


@router.post("/sync", response_model=SyncPull)
async def sync_push(
    payload: SyncPush,
    since: str = Query(
        default="1970-01-01T00:00:00Z",
        description="回传增量的起点；带上上次同步的 server_time 可显著减小响应体",
    ),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """推送增量，last-write-wins 合并，并返回本次写入计数。

    同时回传服务端增量，让客户端一次往返就能完成「推 + 拉」，省掉一次 GET。

    ``since`` 默认为 epoch（等价回传全量快照，兼容早期客户端）。新客户端应当
    带上上次同步拿到的 ``server_time``：习惯与打卡会随使用日积月累，每次同步
    都全量回传在数据量上来后会成为明显的带宽与延迟负担。
    """
    today = today_in(tz)
    applied = {"habits": 0, "checkins": 0, "moods": 0}

    # ---- 习惯 ----
    id_map: dict[str, int] = {}
    for item in payload.habits or []:
        cid = str(item.get("id") or "").strip()
        if not cid:
            continue
        remote_upd = _sanitize_updated_at(_parse_dt(item.get("updated_at")))
        row = await _get_habit(db, current.id, cid, include_deleted=True)
        if row is None:
            row = Habit(
                user_id=current.id,
                client_id=cid,
                name=str(item.get("name") or "未命名习惯")[:100],
                start_date=_parse_date(item.get("start_date")) or today,
            )
            db.add(row)
            await db.flush()
            _apply_habit_fields(row, item, today)
            if remote_upd:
                row.updated_at = remote_upd
            applied["habits"] += 1
        elif _newer_than(remote_upd, _parse_dt(row.updated_at)):
            _apply_habit_fields(row, item, today)
            if remote_upd:
                row.updated_at = remote_upd
            applied["habits"] += 1
        id_map[cid] = row.id

    await db.flush()

    # ---- 打卡记录 ----
    # 需要把客户端 habit_id（uuid）映射到内部主键；同步包里可能引用
    # 本次未提交的习惯，因此先按 uuid 批量查一次。
    habit_uuids = {
        str(i.get("habit_id") or "").strip()
        for i in (payload.checkins or [])
        if str(i.get("habit_id") or "").strip()
    }
    if habit_uuids:
        rows = (
            await db.execute(
                select(Habit.id, Habit.client_id).where(
                    Habit.user_id == current.id, Habit.client_id.in_(habit_uuids)
                )
            )
        ).all()
        for pk, cid in rows:
            id_map[cid] = pk

    # 先做一遍纯 CPU 的预解析，筛掉无效项与孤儿项；再用一条查询把已存在的
    # 记录批量取回 —— 避免原实现「每条一次 await」造成的 N+1。批量同步历史
    # 数据时，这里的查询次数从 O(n) 降到 O(1)。
    pending: list[tuple[dict[str, Any], int, date, Optional[datetime], str]] = []
    for item in payload.checkins or []:
        cid = str(item.get("id") or "").strip()
        habit_pk = id_map.get(str(item.get("habit_id") or "").strip())
        if not habit_pk:
            continue  # 孤儿打卡记录（习惯不存在/尚未同步）直接跳过
        d = _parse_date(item.get("checkin_date"))
        if not d:
            continue
        remote_upd = _sanitize_updated_at(_parse_dt(item.get("updated_at")))
        pending.append((item, habit_pk, d, remote_upd, cid))

    existing: dict[tuple[int, date], HabitCheckin] = {}
    if pending:
        # 这里刻意不用 tuple_().in_()：行值语法依赖较新的 SQLite，
        # 用 or_ 展开可保证在所有后端上都能跑（同步包通常几十到几百条）。
        conds = [
            and_(HabitCheckin.habit_id == pk, HabitCheckin.checkin_date == d)
            for pk, d in sorted({(pk, d) for _, pk, d, _, _ in pending})
        ]
        existing = {
            (r.habit_id, r.checkin_date): r
            for r in (
                await db.execute(
                    select(HabitCheckin).where(
                        HabitCheckin.user_id == current.id, or_(*conds)
                    )
                )
            )
            .scalars()
            .all()
        }

    import re as _re

    for item, habit_pk, d, remote_upd, cid in pending:
        row = existing.get((habit_pk, d))
        if row is None:
            # 同一 (habit, date) 可能已存在但 client_id 不同（两端各自生成）——
            # 此时按业务键合并，而不是报唯一约束冲突。
            row = HabitCheckin(
                user_id=current.id,
                habit_id=habit_pk,
                client_id=cid or str(uuid.uuid4()),
                checkin_date=d,
            )
            db.add(row)
            await db.flush()
            # 登记进索引：同一批次若还有相同业务键，复用它而不是再插一条
            existing[(habit_pk, d)] = row
            applied["checkins"] += 1
        elif not cid or row.client_id == cid:
            if not _newer_than(remote_upd, _parse_dt(row.updated_at)):
                continue
            applied["checkins"] += 1
        else:
            # 业务键命中但 client_id 不一致：以业务键为准，认作同一条
            if not _newer_than(remote_upd, _parse_dt(row.updated_at)):
                continue
            applied["checkins"] += 1

        try:
            row.value = max(0, min(999999, int(item.get("value") or 0)))
        except (TypeError, ValueError):
            row.value = 0
        st = item.get("start_time")
        et = item.get("end_time")
        import re as _re

        row.start_time = (
            str(st).strip()[:5]
            if st and _re.match(r"^([01]\d|2[0-3]):[0-5]\d$", str(st).strip())
            else None
        )
        row.end_time = (
            str(et).strip()[:5]
            if et and _re.match(r"^([01]\d|2[0-3]):[0-5]\d$", str(et).strip())
            else None
        )
        if "note" in item:
            row.note = (str(item.get("note") or "").strip()[:300]) or None
        if remote_upd:
            row.updated_at = remote_upd

    # ---- 心情 ----
    pending_moods: list[tuple[dict[str, Any], date, Optional[datetime]]] = []
    for item in payload.moods or []:
        d = _parse_date(item.get("date") or item.get("mood_date"))
        if not d:
            continue
        remote_upd = _sanitize_updated_at(_parse_dt(item.get("updated_at")))
        pending_moods.append((item, d, remote_upd))

    # 心情以 (user_id, mood_date) 唯一，一次 IN 查询即可批量取回
    existing_moods: dict[date, HabitMood] = {}
    if pending_moods:
        existing_moods = {
            r.mood_date: r
            for r in (
                await db.execute(
                    select(HabitMood).where(
                        HabitMood.user_id == current.id,
                        HabitMood.mood_date.in_({d for _, d, _ in pending_moods}),
                    )
                )
            )
            .scalars()
            .all()
        }

    for item, d, remote_upd in pending_moods:
        try:
            score = max(1, min(5, int(item.get("score") or 3)))
        except (TypeError, ValueError):
            score = 3
        row = existing_moods.get(d)
        if row is None:
            row = HabitMood(
                user_id=current.id,
                client_id=str(item.get("id") or uuid.uuid4()).strip()[:64]
                or str(uuid.uuid4()),
                mood_date=d,
                score=score,
            )
            db.add(row)
            await db.flush()
            existing_moods[d] = row
            applied["moods"] += 1
        elif _newer_than(remote_upd, _parse_dt(row.updated_at)):
            applied["moods"] += 1
        else:
            continue
        row.score = score
        if "note" in item:
            row.note = (str(item.get("note") or "").strip()[:300]) or None
        if remote_upd:
            row.updated_at = remote_upd

    await db.commit()

    # 回传服务端增量，客户端一次往返完成推 + 拉
    snapshot = await sync_pull(since=since, tz=tz, db=db, current=current)
    snapshot.applied = applied
    return snapshot


# =========================================================================
# 集合与单体 CRUD
# =========================================================================


@router.get("", response_model=list[HabitOut])
async def list_habits(
    include_archived: bool = Query(default=True),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """列出本人全部未删除习惯，附带 streak / 今日状态。"""
    today = today_in(tz)
    q = select(Habit).where(Habit.user_id == current.id, Habit.deleted_at.is_(None))
    if not include_archived:
        q = q.where(Habit.archived.is_(False))
    habits = (await db.execute(q.order_by(Habit.sort_order, Habit.id))).scalars().all()
    by_date = await _load_checkins(db, current.id)
    return [
        HabitOut.model_validate(_habit_payload(h, by_date.get(h.id, {}), today))
        for h in habits
    ]


@router.post("", response_model=HabitOut, status_code=201)
async def create_habit(
    payload: HabitCreate,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    today = today_in(tz)
    cid = (payload.client_id or "").strip() or str(uuid.uuid4())
    if await _get_habit(db, current.id, cid):
        raise HTTPException(status_code=409, detail="该 id 已存在")

    habit = Habit(
        user_id=current.id,
        client_id=cid,
        goal_id=payload.goal_id,
        name=payload.name,
        start_date=payload.start_date or today,
    )
    db.add(habit)
    await db.flush()
    # 复用同步的字段清洗逻辑，保证两条写入路径行为完全一致
    _apply_habit_fields(habit, payload.model_dump(), today)
    habit.name = payload.name  # model_dump 的 name 已 strip，这里再兜一次
    await db.commit()
    await db.refresh(habit)
    return HabitOut.model_validate(_habit_payload(habit, {}, today))


@router.get("/{habit_id}", response_model=HabitOut)
async def get_habit(
    habit_id: str,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    habit = await _get_habit(db, current.id, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")
    today = today_in(tz)
    by_date = await _load_checkins(db, current.id)
    return HabitOut.model_validate(
        _habit_payload(habit, by_date.get(habit.id, {}), today)
    )


@router.put("/{habit_id}", response_model=HabitOut)
async def update_habit(
    habit_id: str,
    payload: HabitUpdate,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    habit = await _get_habit(db, current.id, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")

    data = payload.model_dump(exclude_unset=True)
    _apply_habit_fields(habit, data, today_in(tz))
    await db.commit()
    await db.refresh(habit)

    today = today_in(tz)
    by_date = await _load_checkins(db, current.id)
    return HabitOut.model_validate(
        _habit_payload(habit, by_date.get(habit.id, {}), today)
    )


@router.delete("/{habit_id}", status_code=204)
async def delete_habit(
    habit_id: str,
    purge: bool = Query(default=False, description="true = 物理删除（含打卡记录）"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """删除习惯。默认软删除（写墓碑），``?purge=1`` 才物理删除。

    软删除是默认行为：物理删除后，另一台设备下次同步推送时
    这条数据会被当作「本地新增」重新写回服务端 —— 也就是删不掉。
    """
    # include_deleted=True：已软删的记录允许再次物理删除（purge）
    habit = await _get_habit(db, current.id, habit_id, include_deleted=True)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")

    if purge:
        await db.delete(habit)
    else:
        habit.deleted_at = datetime.now(timezone.utc)
        habit.updated_at = habit.deleted_at
    await db.commit()


@router.post("/{habit_id}/checkin", response_model=CheckinOut)
async def checkin(
    habit_id: str,
    payload: CheckinIn,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """打卡 / 取消打卡 / 补卡。同一天重复提交走更新（靠唯一约束幂等）。

    - 不传 ``date`` → 今天；传了 → 补写历史某一天。
    - ``value=0`` → 取消打卡。
    - ``timerange`` 类型以 ``start_time`` / ``end_time`` 是否齐全判定。
    """
    habit = await _get_habit(db, current.id, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")

    d = payload.date or today_in(tz)
    row = await db.scalar(
        select(HabitCheckin).where(
            HabitCheckin.habit_id == habit.id, HabitCheckin.checkin_date == d
        )
    )
    if row is None:
        row = HabitCheckin(
            user_id=current.id,
            habit_id=habit.id,
            client_id=str(uuid.uuid4()),
            checkin_date=d,
            value=0,
        )
        db.add(row)
        await db.flush()

    if payload.value is not None:
        row.value = max(0, min(999999, payload.value))
    if payload.start_time is not None:
        row.start_time = payload.start_time
    if payload.end_time is not None:
        row.end_time = payload.end_time
    if payload.note is not None:
        row.note = payload.note
    # timerange 两端齐全即视为完成
    if habit.type == "timerange" and row.start_time and row.end_time:
        row.value = max(row.value, 1)

    await db.commit()
    await db.refresh(row)
    return CheckinOut.model_validate(
        {**_checkin_payload(row, habit.client_id), "done": _is_done(habit, row)}
    )


@router.get("/{habit_id}/checkins", response_model=list[CheckinOut])
async def list_checkins(
    habit_id: str,
    days: int = Query(default=30, ge=1, le=366),
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    habit = await _get_habit(db, current.id, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")
    today = today_in(tz)
    start = today - timedelta(days=days - 1)
    rows = (
        await db.execute(
            select(HabitCheckin)
            .where(
                HabitCheckin.habit_id == habit.id,
                HabitCheckin.checkin_date >= start,
                HabitCheckin.checkin_date <= today,
            )
            .order_by(HabitCheckin.checkin_date)
        )
    ).scalars().all()
    return [
        CheckinOut.model_validate(
            {**_checkin_payload(r, habit.client_id), "done": _is_done(habit, r)}
        )
        for r in rows
    ]


@router.get("/{habit_id}/stats", response_model=HabitStatsOut)
async def habit_stats(
    habit_id: str,
    tz: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """单个习惯的战绩：当前连续、历史最长、累计次数、达成率、近 30 天明细。"""
    habit = await _get_habit(db, current.id, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="习惯不存在")

    today = today_in(tz)
    by_date = await _load_checkins(db, current.id)
    dates = by_date.get(habit.id, {})

    # 累计次数：只看真正生效的打卡（value>0 或 时间段齐全）
    total = sum(1 for ci in dates.values() if ci.value > 0 or (ci.start_time and ci.end_time))

    # 达成率：只统计「应当执行」的日子，否则低频习惯会被分母稀释
    def _rate(span: int) -> tuple[float, list[dict]]:
        start = today - timedelta(days=span - 1)
        scheduled = 0
        hit = 0
        detail = []
        for i in range(span):
            d = start + timedelta(days=i)
            if (_parse_date(habit.start_date) or d) > d:
                continue
            if not is_scheduled_on(habit, d):
                continue
            scheduled += 1
            ci = dates.get(d)
            ok = _is_done(habit, ci)
            if ok:
                hit += 1
            detail.append(
                {
                    "date": d.isoformat(),
                    "value": ci.value if ci else 0,
                    "done": ok,
                }
            )
        return (hit / scheduled if scheduled else 0.0), detail

    rate30, last30 = _rate(30)
    rate_all, _ = _rate((today - (_parse_date(habit.start_date) or today)).days + 1)

    return HabitStatsOut(
        habit_id=habit.client_id,
        streak=_streak(habit, dates, today),
        best_streak=_best_streak(habit, dates, today),
        total_checkins=total,
        rate_30=round(rate30, 3),
        rate_all=round(rate_all, 3),
        last_30=last30,
    )
