from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select

from ..database import get_db
from ..models import Category, Goal, Tag, Task, Record, User
from ..deps import get_current_user
from ..schemas import CategoryOut, GoalOut, TagOut, TaskOut, RecordOut
from ..sanitize import sanitize_csv_cell
from .settings import get_or_create as get_or_create_settings

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("")
async def export_data(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    db=Depends(get_db),
    current: User = Depends(get_current_user),
):
    """导出当前用户的全部数据，用于备份 / 迁移。

    - fmt=json：全量结构化备份（categories / goals / tasks / records），可再导入。
    - fmt=csv：仅导出 tasks 为表格（带 BOM 便于 Excel 打开中文）。
    """
    cats = (
        await db.scalars(select(Category).where(Category.user_id == current.id))
    ).all()
    goals = (
        await db.scalars(select(Goal).where(Goal.user_id == current.id))
    ).all()
    tags = (
        await db.scalars(select(Tag).where(Tag.user_id == current.id).order_by(Tag.name))
    ).all()
    # 备份不包含回收站内容：用户导出的是「当前有效数据」，
    # 把待清理的垃圾一起带走只会在导入时复活已删除的条目。
    tasks = (
        await db.scalars(
            select(Task)
            .where(Task.user_id == current.id, Task.deleted_at.is_(None))
            .order_by(Task.sort_order, Task.created_at)
        )
    ).unique().all()
    records = (
        await db.scalars(
            select(Record)
            .where(Record.user_id == current.id, Record.deleted_at.is_(None))
            .order_by(Record.record_date)
        )
    ).all()

    if fmt == "csv":
        import csv
        import io

        buf = io.StringIO()
        buf.write("\ufeff")  # BOM，Excel 正确识别 UTF-8 中文
        w = csv.writer(buf)
        w.writerow(
            [
                "id",
                "title",
                "category",
                "goal",
                "priority",
                "importance",
                "recurrence",
                "status",
                "due_date",
                "due_time",
                "tags",
                "note",
                "created_at",
                "completed_at",
            ]
        )
        cat_name = {c.id: c.name for c in cats}
        goal_title = {g.id: g.title for g in goals}
        for t in tasks:
            # 逐单元格中和公式注入风险（= + - @ 开头加单引号前缀，Excel 呈现为文本）
            w.writerow(
                [
                    sanitize_csv_cell(v)
                    for v in [
                        t.id,
                        t.title,
                        cat_name.get(t.category_id, ""),
                        goal_title.get(t.goal_id, ""),
                        t.priority,
                        t.importance,
                        t.recurrence,
                        t.status,
                        t.due_date or "",
                        t.due_time or "",
                        " ".join(tag.name for tag in (t.tags or [])),
                        (t.note or "").replace("\r", " ").replace("\n", " "),
                        t.created_at,
                        t.completed_at or "",
                    ]
                ]
            )
        return Response(
            content=buf.getvalue().encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=reach-tasks.csv"
            },
        )

    def task_dump(t: Task) -> dict:
        d = TaskOut.model_validate(t).model_dump(mode="json")
        # TaskOut.tags 默认空列表；这里显式回填，保证导入端能还原标签绑定
        d["tags"] = [tag.name for tag in (t.tags or [])]
        return d

    setting_row = await get_or_create_settings(db, current.id)

    payload = {
        "app": "Reach-Todo",
        # version 2 起包含 tags / settings，且不再包含回收站数据。
        # 导入端按 version 做兼容分支，v1 备份仍可导入。
        "version": 2,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "settings": setting_row.as_dict(),
        "categories": [
            CategoryOut.model_validate(c).model_dump(mode="json") for c in cats
        ],
        "goals": [GoalOut.model_validate(g).model_dump(mode="json") for g in goals],
        "tags": [TagOut.model_validate(t).model_dump(mode="json") for t in tags],
        "tasks": [task_dump(t) for t in tasks],
        "records": [
            RecordOut.model_validate(r).model_dump(mode="json") for r in records
        ],
    }
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": "attachment; filename=reach-backup.json"
        },
    )
