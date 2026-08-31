from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Task, Category, Goal, FocusSession, User
from ..deps import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """周回顾 / 数据看板：本周完成、连续天数、专注时长、各维度与目标进展。

    全部用 SQL 聚合（GROUP BY / COUNT），不再把全表拉回内存计数；
    时间统一在 UTC 下计算（入库即 UTC），避免本地时区比较造成 streak 断签。
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today = now.date()

    # 所有统计都必须排除回收站数据：软删除后仍计入「已完成数 / streak」
    # 会让用户看到自相矛盾的数字（列表里没有，统计里还在）。
    base = and_(Task.user_id == current.id, Task.deleted_at.is_(None))

    # 待办 / 已完成总数
    status_counts = dict(
        (
            await db.execute(
                select(Task.status, func.count(Task.id)).where(base).group_by(Task.status)
            )
        ).all()
    )
    total_todo = status_counts.get("todo", 0)
    total_done = status_counts.get("done", 0)

    # 本周完成数
    week_completed = await db.scalar(
        select(func.count(Task.id)).where(
            base,
            Task.status == "done",
            Task.completed_at >= week_ago,
        )
    ) or 0

    # 连续完成天数（streak）：从今天往前逐日查。
    # 只统计 done 的 completed_at 日期集合，最坏逐天回溯，量级小；
    # 相比全表加载仍显著更优。
    # 注意：不要在 SQL 里 CAST(... AS DATE) 取日期——SQLite 的 DATE 是
    # NUMERIC 亲和，会把 '2026-08-18 09:20:00' 转成整数 2026 而不是日期，
    # 结果处理器 fromisoformat 直接炸（见 #stats-sqlite-cast）。这里拉回
    # 时间戳后在 Python 侧取 .date()，双数据库通用。
    done_dates = {
        row[0].date()
        for row in (
            await db.execute(
                select(Task.completed_at).where(
                    base, Task.status == "done", Task.completed_at.is_not(None)
                ).distinct()
            )
        ).all()
    }
    streak = 0
    cur = today
    while cur in done_dates:
        streak += 1
        cur -= timedelta(days=1)

    # 各维度统计：按 category 聚合 todo/done
    cat_rows = (
        await db.execute(
            select(
                Category.id,
                Category.name,
                Category.color,
                Category.icon,
                func.count(Task.id).filter(Task.status == "todo").label("todo"),
                func.count(Task.id).filter(Task.status == "done").label("done"),
            )
            .where(Category.user_id == current.id)
            .join(Task, Task.category_id == Category.id, isouter=True)
            .group_by(Category.id)
            .order_by(Category.sort_order)
        )
    ).all()
    per_category = [
        {
            "name": r.name,
            "color": r.color,
            "icon": r.icon,
            "todo": r.todo,
            "done": r.done,
        }
        for r in cat_rows
    ]

    # 目标进展：按 goal 聚合
    goal_rows = (
        await db.execute(
            select(
                Goal.id,
                Goal.title,
                func.count(Task.id).label("total"),
                func.count(Task.id).filter(Task.status == "done").label("done"),
            )
            .where(Goal.user_id == current.id)
            .join(Task, Task.goal_id == Goal.id, isouter=True)
            .group_by(Goal.id)
        )
    ).all()
    goals_progress = [
        {
            "id": r.id,
            "title": r.title,
            "total": r.total,
            "done": r.done,
            "progress": round(r.done / r.total * 100) if r.total else 0,
        }
        for r in goal_rows
    ]

    # 专注时长：今日 / 本周
    # 今日用 [今天 00:00, 明天 00:00) 区间判断，避免 SQLite 下
    # CAST(... AS DATE) 返回整数导致 fromisoformat 崩溃（同 streak 处的坑）。
    today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    focus_minutes_today = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.minutes), 0)).where(
            FocusSession.user_id == current.id,
            FocusSession.started_at >= today_start,
            FocusSession.started_at < today_start + timedelta(days=1),
        )
    ) or 0
    focus_minutes_week = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.minutes), 0)).where(
            FocusSession.user_id == current.id,
            FocusSession.started_at >= week_ago,
        )
    ) or 0

    return {
        "total_todo": total_todo,
        "total_done": total_done,
        "week_completed": week_completed,
        "streak": streak,
        "per_category": per_category,
        "goals_progress": goals_progress,
        "focus_minutes_today": int(focus_minutes_today),
        "focus_minutes_week": int(focus_minutes_week),
    }
