"""回收站：软删除的任务 / 记录的查看、恢复、彻底删除与自动清理。

为什么必须有：自托管工具的数据由用户自己兜底，一次误触即永久丢失是信任红线。
主流产品（滴答清单、Todoist）都有回收站，本项目改造前是硬删除。

保留期由 ``TRASH_RETENTION_DAYS`` 控制，过期项在调度器周期内自动物理删除。
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Record, Task, User

router = APIRouter(prefix="/api/trash", tags=["trash"])

_KINDS = ("task", "record")


def _expire_before() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=settings.trash_retention_days)


@router.get("")
async def list_trash(
    kind: str | None = Query(None, pattern="^(task|record)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """回收站列表。返回精简字段——回收站只需要「认出是哪条」，不需要完整正文。"""
    items: list[dict] = []

    if kind in (None, "task"):
        rows = (
            await db.scalars(
                select(Task)
                .where(Task.user_id == current.id, Task.deleted_at.isnot(None))
                .options(selectinload(Task.category))
                .order_by(Task.deleted_at.desc())
                .limit(limit)
            )
        ).unique().all()
        for t in rows:
            items.append(
                {
                    "kind": "task",
                    "id": t.id,
                    "title": t.title,
                    "subtitle": t.category.name if t.category else None,
                    "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
                }
            )

    if kind in (None, "record"):
        rows = (
            await db.scalars(
                select(Record)
                .where(Record.user_id == current.id, Record.deleted_at.isnot(None))
                .order_by(Record.deleted_at.desc())
                .limit(limit)
            )
        ).all()
        for r in rows:
            items.append(
                {
                    "kind": "record",
                    "id": r.id,
                    "title": r.title or r.record_date.isoformat(),
                    "subtitle": r.type,
                    "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                }
            )

    items.sort(key=lambda x: x["deleted_at"] or "", reverse=True)
    return {
        "items": items[:limit],
        "retention_days": settings.trash_retention_days,
    }


async def _fetch(db: AsyncSession, kind: str, item_id: int, user_id: int):
    model = Task if kind == "task" else Record
    obj = await db.get(model, item_id)
    if not obj or obj.user_id != user_id or obj.deleted_at is None:
        raise HTTPException(status_code=404, detail="回收站中没有该条目")
    return obj


@router.post("/{kind}/{item_id}/restore", status_code=200)
async def restore(
    kind: str,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if kind not in _KINDS:
        raise HTTPException(status_code=400, detail="类型不支持")
    obj = await _fetch(db, kind, item_id, current.id)
    obj.deleted_at = None
    await db.commit()
    return {"restored": True, "kind": kind, "id": item_id}


@router.delete("/{kind}/{item_id}", status_code=204)
async def purge_one(
    kind: str,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if kind not in _KINDS:
        raise HTTPException(status_code=400, detail="类型不支持")
    obj = await _fetch(db, kind, item_id, current.id)
    await db.delete(obj)
    await db.commit()


@router.delete("", status_code=200)
async def empty_trash(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """清空回收站（仅当前用户）。"""
    t = await db.execute(
        delete(Task).where(Task.user_id == current.id, Task.deleted_at.isnot(None))
    )
    r = await db.execute(
        delete(Record).where(Record.user_id == current.id, Record.deleted_at.isnot(None))
    )
    await db.commit()
    return {"purged_tasks": t.rowcount or 0, "purged_records": r.rowcount or 0}


async def purge_expired(db: AsyncSession) -> int:
    """物理删除超过保留期的软删除数据。由调度器周期调用（全局，不分用户）。"""
    cutoff = _expire_before()
    t = await db.execute(
        delete(Task).where(Task.deleted_at.isnot(None), Task.deleted_at < cutoff)
    )
    r = await db.execute(
        delete(Record).where(Record.deleted_at.isnot(None), Record.deleted_at < cutoff)
    )
    await db.commit()
    return (t.rowcount or 0) + (r.rowcount or 0)
