"""数据导入 / 备份恢复。

改造前项目只能导出不能导入——备份文件无法回灌，等于备份只有一半价值，
换机 / 重装 / 误清库时依然抓瞎。本接口消费 ``GET /api/export?fmt=json`` 的产物。

两种策略：
- ``merge``（默认）：维度/目标/标签按名称对齐已有数据，任务与记录追加。安全，可重复执行。
- ``replace``：先清空当前用户的全部业务数据再导入，用于「把这台机器恢复成备份那一刻」。

关键设计：备份里的主键 id **一律不信任**，全部按「名称」重新建立引用关系。
直接沿用 id 会与目标库现有数据撞主键，也会在跨账号迁移时产生越权引用。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings as app_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Category, Goal, Record, Tag, Task, User, task_tags
from ..schemas import DEFAULT_SETTINGS
from ..tagging import resolve_tags
from .settings import get_or_create as get_or_create_settings

router = APIRouter(prefix="/api/import", tags=["import"])

_PRIORITIES = {"low", "normal", "high", "urgent"}
_IMPORTANCES = {"low", "normal", "high"}
_RECURRENCES = {"none", "daily", "weekday", "weekly", "biweekly", "monthly", "monthend"}
_RECORD_TYPES = {"diary", "worklog", "note"}
_MAX_ROWS = 20000


def _s(v: Any, limit: int) -> str:
    return str(v).strip()[:limit] if v is not None else ""


def _pick(v: Any, allowed: set[str], default: str) -> str:
    s = str(v).strip().lower() if v is not None else ""
    return s if s in allowed else default


def _parse_date(v: Any) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _parse_dt(v: Any) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_time(v: Any) -> str | None:
    """校验 HH:MM。脏值丢弃而不是报错——导入应尽最大努力成功。"""
    s = _s(v, 5)
    if len(s) == 5 and s[2] == ":" and s[:2].isdigit() and s[3:].isdigit():
        if 0 <= int(s[:2]) <= 23 and 0 <= int(s[3:]) <= 59:
            return s
    return None


@router.post("")
async def import_data(
    payload: dict = Body(..., description="GET /api/export?fmt=json 的完整内容"),
    strategy: str = Query("merge", pattern="^(merge|replace)$"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not app_settings.feature_import:
        raise HTTPException(status_code=403, detail="导入功能已关闭")
    if payload.get("app") != "Reach-Todo":
        raise HTTPException(
            status_code=400, detail="不是「抵达 Reach」的备份文件（app 字段不匹配）"
        )

    cats_in = payload.get("categories") or []
    goals_in = payload.get("goals") or []
    tags_in = payload.get("tags") or []
    tasks_in = payload.get("tasks") or []
    records_in = payload.get("records") or []
    for name, rows in (
        ("categories", cats_in),
        ("goals", goals_in),
        ("tasks", tasks_in),
        ("records", records_in),
    ):
        if not isinstance(rows, list):
            raise HTTPException(status_code=400, detail=f"{name} 字段格式错误")
        if len(rows) > _MAX_ROWS:
            raise HTTPException(
                status_code=413, detail=f"{name} 超过 {_MAX_ROWS} 条上限"
            )

    stats = {
        "categories": 0,
        "goals": 0,
        "tags": 0,
        "tasks": 0,
        "records": 0,
        "settings": 0,
    }

    if strategy == "replace":
        # 顺序：任务标签关联 → 任务 → 目标 → 维度 → 记录。
        # 先删关联再删主体，避免 SQLite 未开外键时留下孤儿行。
        own_task_ids = select(Task.id).where(Task.user_id == current.id)
        await db.execute(
            delete(task_tags).where(task_tags.c.task_id.in_(own_task_ids))
        )
        await db.execute(delete(Task).where(Task.user_id == current.id))
        await db.execute(delete(Goal).where(Goal.user_id == current.id))
        await db.execute(delete(Category).where(Category.user_id == current.id))
        await db.execute(delete(Record).where(Record.user_id == current.id))
        await db.flush()

    # ---------- 维度：按名称对齐 ----------
    existing_cats = {
        c.name: c
        for c in (
            await db.scalars(select(Category).where(Category.user_id == current.id))
        ).all()
    }
    cat_by_old_id: dict[Any, Category] = {}
    for row in cats_in:
        if not isinstance(row, dict):
            continue
        name = _s(row.get("name"), 50)
        if not name:
            continue
        cat = existing_cats.get(name)
        if cat is None:
            cat = Category(
                user_id=current.id,
                name=name,
                color=_s(row.get("color"), 20) or "#3B82F6",
                icon=_s(row.get("icon"), 20) or "📁",
                sort_order=int(row.get("sort_order") or 0),
            )
            db.add(cat)
            existing_cats[name] = cat
            stats["categories"] += 1
        cat_by_old_id[row.get("id")] = cat
    await db.flush()

    # 至少要有一个维度可落任务，否则整个导入无意义
    if not existing_cats:
        fallback = Category(
            user_id=current.id, name="导入", color="#3B82F6", icon="📥", sort_order=99
        )
        db.add(fallback)
        existing_cats["导入"] = fallback
        stats["categories"] += 1
        await db.flush()
    default_cat = next(iter(existing_cats.values()))

    # ---------- 目标：按标题对齐 ----------
    existing_goals = {
        g.title: g
        for g in (
            await db.scalars(select(Goal).where(Goal.user_id == current.id))
        ).all()
    }
    goal_by_old_id: dict[Any, Goal] = {}
    for row in goals_in:
        if not isinstance(row, dict):
            continue
        title = _s(row.get("title"), 200)
        if not title:
            continue
        g = existing_goals.get(title)
        if g is None:
            g = Goal(
                user_id=current.id,
                title=title,
                description=row.get("description") or None,
                status="done" if _s(row.get("status"), 10) == "done" else "active",
                deadline=_parse_date(row.get("deadline")),
            )
            db.add(g)
            existing_goals[title] = g
            stats["goals"] += 1
        goal_by_old_id[row.get("id")] = g
    await db.flush()

    # ---------- 标签：先建定义，保住颜色 ----------
    for row in tags_in:
        if not isinstance(row, dict):
            continue
        name = _s(row.get("name"), 40)
        if not name:
            continue
        exists = await db.scalar(
            select(Tag.id).where(Tag.user_id == current.id, Tag.name == name)
        )
        if not exists:
            db.add(
                Tag(
                    user_id=current.id,
                    name=name,
                    color=_s(row.get("color"), 20) or "#64748B",
                )
            )
            stats["tags"] += 1
    await db.flush()

    # ---------- 任务 ----------
    # 两遍导入：第一遍建所有任务（parent_id 留空），第二遍再接父子关系。
    # 备份里子任务可能出现在父任务之前，单遍处理会丢失层级。
    created_by_old_id: dict[Any, Task] = {}
    pending_parent: list[tuple[Task, Any]] = []
    for row in tasks_in:
        if not isinstance(row, dict):
            continue
        title = _s(row.get("title"), 300)
        if not title:
            continue
        cat_ref = cat_by_old_id.get(row.get("category_id")) or default_cat
        goal_ref = goal_by_old_id.get(row.get("goal_id"))
        status = "done" if _s(row.get("status"), 10) == "done" else "todo"
        t = Task(
            user_id=current.id,
            category_id=cat_ref.id,
            goal_id=goal_ref.id if goal_ref else None,
            title=title,
            note=row.get("note") or None,
            priority=_pick(row.get("priority"), _PRIORITIES, "normal"),
            importance=_pick(row.get("importance"), _IMPORTANCES, "normal"),
            recurrence=_pick(row.get("recurrence"), _RECURRENCES, "none"),
            status=status,
            due_date=_parse_date(row.get("due_date")),
            due_time=_parse_time(row.get("due_time")),
            sort_order=int(row.get("sort_order") or 0),
            completed_at=_parse_dt(row.get("completed_at")) if status == "done" else None,
        )
        rbm = row.get("remind_before_minutes")
        if isinstance(rbm, int) and 0 <= rbm <= 60 * 24 * 7:
            t.remind_before_minutes = rbm

        raw_tags = row.get("tags")
        if isinstance(raw_tags, list):
            names = [_s(x, 40) for x in raw_tags if _s(x, 40)][:20]
            if names:
                t.tags = await resolve_tags(db, current.id, names)

        db.add(t)
        stats["tasks"] += 1
        if row.get("id") is not None:
            created_by_old_id[row["id"]] = t
        if row.get("parent_id") is not None:
            pending_parent.append((t, row["parent_id"]))
    await db.flush()

    for child, old_parent_id in pending_parent:
        parent = created_by_old_id.get(old_parent_id)
        # 父任务必须同属本次导入且不能自引用，否则宁可保留为顶层任务
        if parent is not None and parent.id != child.id:
            child.parent_id = parent.id
            child.category_id = parent.category_id

    # ---------- 记录 ----------
    existing_records = {
        (r.type, r.record_date, r.title or "")
        for r in (
            await db.scalars(select(Record).where(Record.user_id == current.id))
        ).all()
    }
    for row in records_in:
        if not isinstance(row, dict):
            continue
        rtype = _pick(row.get("type"), _RECORD_TYPES, "diary")
        rdate = _parse_date(row.get("record_date")) or _parse_date(row.get("date"))
        if rdate is None:
            continue
        # Record.title 非空列：备份里缺标题时用日期兜底，避免 NOT NULL 失败
        title = _s(row.get("title"), 200) or rdate.isoformat()
        key = (rtype, rdate, title)
        # 幂等去重：同类型 + 同日期 + 同标题视为同一条，重复导入不会翻倍
        if key in existing_records:
            continue
        db.add(
            Record(
                user_id=current.id,
                type=rtype,
                record_date=rdate,
                record_time=_parse_time(row.get("record_time")),
                title=title,
                content=row.get("content") or None,
                mood=_s(row.get("mood"), 20) or None,
                tags=_s(row.get("tags"), 200) or None,
                book_title=_s(row.get("book_title"), 200) or None,
                book_author=_s(row.get("book_author"), 100) or None,
                project=_s(row.get("project"), 100) or None,
            )
        )
        existing_records.add(key)
        stats["records"] += 1

    # ---------- 偏好 ----------
    raw_settings = payload.get("settings")
    if isinstance(raw_settings, dict) and raw_settings:
        row = await get_or_create_settings(db, current.id)
        # 只接受白名单里的键，防止备份文件被手工塞入垃圾键
        clean = {k: v for k, v in raw_settings.items() if k in DEFAULT_SETTINGS}
        if clean:
            row.merge(clean)
            stats["settings"] = len(clean)

    await db.commit()
    return {"strategy": strategy, "imported": stats}
