from datetime import datetime, timezone, date, timedelta
import calendar

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import Task, Category, Goal, Tag, User
from ..schemas import (
    TaskCreate,
    TaskUpdate,
    TaskOut,
    TaskBulkRequest,
    TaskBulkResult,
)
from ..deps import get_current_user
from ..tagging import resolve_tags

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# 重复规则
# ---------------------------------------------------------------------------
def _month_last_day(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def _next_month(y: int, m: int) -> tuple[int, int]:
    return (y + 1, 1) if m == 12 else (y, m + 1)


def next_occurrence(d: date | None, recurrence: str) -> date:
    """根据重复规则计算下一次到期日（以原到期日、缺省则今天为基准）。

    各规则语义：
    - ``daily``    +1 天
    - ``weekday``  下一个工作日（周五 → 下周一，跳过周末）
    - ``weekly``   +7 天
    - ``biweekly`` +14 天
    - ``monthly``  下个月同一天，钳制到该月最后一天（1/31 → 2/28、12/31 → 次年 1/31）
    - ``monthend`` 下个月的最后一天
    未知规则原样返回基准日，绝不抛异常——否则一条脏数据能让「完成任务」直接 500。
    """
    base = d or date.today()
    if recurrence == "daily":
        return base + timedelta(days=1)
    if recurrence == "weekday":
        nxt = base + timedelta(days=1)
        while nxt.weekday() >= 5:  # 5=周六, 6=周日
            nxt += timedelta(days=1)
        return nxt
    if recurrence == "weekly":
        return base + timedelta(days=7)
    if recurrence == "biweekly":
        return base + timedelta(days=14)
    if recurrence == "monthly":
        y, m = _next_month(base.year, base.month)
        last_day = calendar.monthrange(y, m)[1]
        return date(y, m, min(base.day, last_day))
    if recurrence == "monthend":
        # 若基准日本身还没到本月最后一天，则下一次就是本月末；否则是下个月末。
        this_end = _month_last_day(base.year, base.month)
        if base < this_end:
            return this_end
        y, m = _next_month(base.year, base.month)
        return _month_last_day(y, m)
    return base


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------
def _to_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.category_name = task.category.name if task.category else None
    out.category_color = task.category.color if task.category else None
    out.category_icon = task.category.icon if task.category else None
    out.goal_title = task.goal.title if task.goal else None
    # tags 由 TaskOut 的 before-validator 从 ORM 实体摊平成名称数组；
    # Task.tags 声明为 lazy="selectin"，查询与新建路径下都已装载。
    return out


def _base_query(user_id: int, *, include_deleted: bool = False):
    q = (
        select(Task)
        .where(Task.user_id == user_id)
        .join(Category, Task.category_id == Category.id, isouter=True)
        .join(Goal, Task.goal_id == Goal.id, isouter=True)
        .options(selectinload(Task.category), selectinload(Task.goal))
    )
    if not include_deleted:
        q = q.where(Task.deleted_at.is_(None))
    return q


async def _refresh_out(db: AsyncSession, task: Task) -> TaskOut:
    """提交后重新装载展示所需的关联，再序列化。

    必须显式列出 ``tags``：异步会话下访问未装载的关系会抛 MissingGreenlet，
    这在「更新任务后返回」路径上是必然踩到的。
    """
    await db.refresh(task, attribute_names=["category", "goal", "tags"])
    return _to_out(task)


# ---------------------------------------------------------------------------
# 列表 / 搜索
# ---------------------------------------------------------------------------
@router.get("", response_model=list[TaskOut])
async def list_tasks(
    category_id: int | None = None,
    goal_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    importance: str | None = None,
    q: str | None = Query(None, max_length=100, description="标题 / 备注模糊搜索"),
    tag: list[str] | None = Query(
        None, description="按标签名过滤，可重复传参；多个标签取「同时含有」"
    ),
    due_from: date | None = Query(None, description="到期日下界（含）"),
    due_to: date | None = Query(None, description="到期日上界（含）"),
    overdue: bool | None = Query(None, description="true=仅逾期未完成"),
    parent_id: int | None = Query(None, description="仅取某任务的子任务"),
    top_level: bool | None = Query(None, description="true=仅取顶层任务"),
    sort: str = Query(
        "default",
        pattern="^(default|due|priority|created|title)$",
        description="default=维度+手工排序；due=按到期日；priority=按紧急度",
    ),
    limit: int = Query(settings.page_size_default, ge=1, le=settings.page_size_max),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    qry = _base_query(current.id)

    if category_id is not None:
        qry = qry.where(Task.category_id == category_id)
    if goal_id is not None:
        qry = qry.where(Task.goal_id == goal_id)
    if status:
        qry = qry.where(Task.status == status)
    if priority:
        qry = qry.where(Task.priority == priority)
    if importance:
        qry = qry.where(Task.importance == importance)
    if parent_id is not None:
        qry = qry.where(Task.parent_id == parent_id)
    elif top_level:
        qry = qry.where(Task.parent_id.is_(None))
    if q:
        # 转义 LIKE 元字符，否则用户搜 "50%" 会变成通配匹配全部
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        qry = qry.where(
            or_(
                Task.title.ilike(like, escape="\\"),
                Task.note.ilike(like, escape="\\"),
            )
        )
    if due_from is not None:
        qry = qry.where(Task.due_date >= due_from)
    if due_to is not None:
        qry = qry.where(Task.due_date <= due_to)
    if overdue:
        qry = qry.where(
            Task.status == "todo",
            Task.due_date.isnot(None),
            Task.due_date < date.today(),
        )
    if tag:
        # 「同时含有全部指定标签」用 EXISTS 逐个叠加，而不是 IN + GROUP BY HAVING：
        # 前者语义直观、不影响外层排序与分页，也不会因 join 放大行数。
        for name in [t.strip() for t in tag if t and t.strip()]:
            qry = qry.where(
                Task.tags.any(and_(Tag.user_id == current.id, Tag.name == name))
            )

    if sort == "due":
        # 未排期的排最后：先按「是否为空」再按日期，跨方言都成立
        qry = qry.order_by(
            Task.due_date.is_(None), Task.due_date, Task.due_time, Task.sort_order
        )
    elif sort == "priority":
        # SQL 层没有枚举序（字符串排序会得到 high < low < normal < urgent），
        # 必须用 CASE 显式给权重。
        qry = qry.order_by(
            case(
                {"urgent": 0, "high": 1, "normal": 2, "low": 3},
                value=func.coalesce(Task.priority, "normal"),
                else_=9,
            ),
            Task.due_date.is_(None),
            Task.due_date,
        )
    elif sort == "created":
        qry = qry.order_by(Task.created_at.desc())
    elif sort == "title":
        qry = qry.order_by(Task.title)
    else:
        qry = qry.order_by(Category.sort_order, Task.sort_order, Task.created_at)

    qry = qry.limit(limit).offset(offset)
    res = await db.scalars(qry)
    return [_to_out(t) for t in res.unique()]


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """看板统计：每个维度的待办/已完成数量 + 总览"""
    not_deleted = Task.deleted_at.is_(None)
    rows = await db.execute(
        select(
            Category.id,
            Category.name,
            Category.color,
            Category.icon,
            Category.sort_order,
            func.count(Task.id).filter(Task.status == "todo", not_deleted).label("todo"),
            func.count(Task.id).filter(Task.status == "done", not_deleted).label("done"),
        )
        .where(Category.user_id == current.id)
        .join(Task, Task.category_id == Category.id, isouter=True)
        .group_by(Category.id)
        .order_by(Category.sort_order)
    )
    categories = [
        {
            "category_id": r.id,
            "name": r.name,
            "color": r.color,
            "icon": r.icon,
            "todo": r.todo,
            "done": r.done,
        }
        for r in rows.all()
    ]
    total_todo = await db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == current.id, Task.status == "todo", not_deleted
        )
    )
    total_done = await db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == current.id, Task.status == "done", not_deleted
        )
    )
    # 今日待办：未完成的、且未排期或到期日为今天及以后（不含逾期）
    today = date.today()
    today_todo = await db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == current.id,
            Task.status == "todo",
            not_deleted,
            or_(Task.due_date.is_(None), Task.due_date >= today),
        )
    )
    overdue = await db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == current.id,
            Task.status == "todo",
            not_deleted,
            Task.due_date.isnot(None),
            Task.due_date < today,
        )
    )
    return {
        "categories": categories,
        "total_todo": total_todo or 0,
        "today_todo": today_todo or 0,
        "total_done": total_done or 0,
        "overdue": overdue or 0,
    }


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------
@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    cat = await db.get(Category, payload.category_id)
    if not cat or cat.user_id != current.id:
        raise HTTPException(status_code=400, detail="维度不存在")
    if payload.goal_id is not None:
        g = await db.get(Goal, payload.goal_id)
        if not g or g.user_id != current.id:
            raise HTTPException(status_code=400, detail="目标不存在")

    data = payload.model_dump()
    tag_names = data.pop("tags", None) or []
    # 子任务：校验父任务归属，并将其归入父任务同维度
    if data.get("parent_id") is not None:
        p = await db.get(Task, data["parent_id"])
        if not p or p.user_id != current.id:
            raise HTTPException(status_code=400, detail="父任务不存在")
        data["category_id"] = p.category_id

    data["user_id"] = current.id
    t = Task(**data)
    if tag_names:
        t.tags = await resolve_tags(db, current.id, tag_names)
    db.add(t)
    await db.commit()
    return await _refresh_out(db, t)


# ---------------------------------------------------------------------------
# 排序 / 批量
# ---------------------------------------------------------------------------
class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderPayload(BaseModel):
    items: list[ReorderItem]


@router.put("/reorder", status_code=200)
async def reorder_tasks(
    payload: ReorderPayload,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """批量更新任务排序（拖拽后调用）。仅接受属于当前用户且存在的任务。"""
    ids = [it.id for it in payload.items]
    if not ids:
        return {"updated": 0}
    tasks = (
        await db.scalars(select(Task).where(Task.id.in_(ids), Task.user_id == current.id))
    ).all()
    by_id = {t.id: t for t in tasks}
    updated = 0
    for it in payload.items:
        t = by_id.get(it.id)
        if t is None:
            continue
        if t.sort_order != it.sort_order:
            t.sort_order = it.sort_order
            updated += 1
    if updated:
        await db.commit()
    return {"updated": updated}


@router.post("/bulk", response_model=TaskBulkResult)
async def bulk_tasks(
    payload: TaskBulkRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """批量操作：一次请求处理多条任务，避免前端 N 次串行请求。

    归属校验仍逐条执行（``user_id == current.id`` 直接写进 WHERE），
    传入他人 id 会被静默计入 ``skipped``，不泄露「该 id 是否存在」。
    """
    action = payload.action
    # purge / restore 需要能看到回收站里的行，其余动作只作用于未删除的任务
    include_deleted = action in ("purge", "restore")
    q = select(Task).where(Task.id.in_(payload.ids), Task.user_id == current.id)
    if not include_deleted:
        q = q.where(Task.deleted_at.is_(None))
    if action == "restore":
        q = q.where(Task.deleted_at.isnot(None))
    q = q.options(selectinload(Task.tags))
    tasks = (await db.scalars(q)).unique().all()

    now = datetime.now(timezone.utc)
    affected = 0

    if action in ("add_tags", "remove_tags"):
        names = payload.tags or []
        if not names:
            raise HTTPException(status_code=400, detail="请提供标签名")
        if action == "add_tags":
            wanted = await resolve_tags(db, current.id, names)
            for t in tasks:
                have = {x.id for x in t.tags}
                added = [x for x in wanted if x.id not in have]
                if added:
                    t.tags.extend(added)
                    affected += 1
        else:
            drop = set(names)
            for t in tasks:
                keep = [x for x in t.tags if x.name not in drop]
                if len(keep) != len(t.tags):
                    t.tags = keep
                    affected += 1
    elif action == "set_category":
        if payload.category_id is None:
            raise HTTPException(status_code=400, detail="请提供 category_id")
        cat = await db.get(Category, payload.category_id)
        if not cat or cat.user_id != current.id:
            raise HTTPException(status_code=400, detail="维度不存在")
        for t in tasks:
            if t.category_id != cat.id:
                t.category_id = cat.id
                affected += 1
    elif action == "set_goal":
        if payload.goal_id is not None:
            g = await db.get(Goal, payload.goal_id)
            if not g or g.user_id != current.id:
                raise HTTPException(status_code=400, detail="目标不存在")
        for t in tasks:
            if t.goal_id != payload.goal_id:
                t.goal_id = payload.goal_id
                affected += 1
    elif action == "set_priority":
        if payload.priority is None:
            raise HTTPException(status_code=400, detail="请提供 priority")
        for t in tasks:
            if t.priority != payload.priority:
                t.priority = payload.priority
                affected += 1
    elif action == "set_importance":
        if payload.importance is None:
            raise HTTPException(status_code=400, detail="请提供 importance")
        for t in tasks:
            if t.importance != payload.importance:
                t.importance = payload.importance
                affected += 1
    elif action == "complete":
        for t in tasks:
            if t.status != "done":
                _mark_done(db, t, now)
                affected += 1
    elif action == "uncomplete":
        for t in tasks:
            if t.status != "todo":
                t.status = "todo"
                t.completed_at = None
                affected += 1
    elif action == "delete":
        for t in tasks:
            t.deleted_at = now
            affected += 1
    elif action == "restore":
        for t in tasks:
            t.deleted_at = None
            affected += 1
    elif action == "purge":
        for t in tasks:
            await db.delete(t)
            affected += 1

    await db.commit()
    return TaskBulkResult(
        action=action,
        requested=len(payload.ids),
        affected=affected,
        skipped=len(payload.ids) - affected,
    )


def _mark_done(db: AsyncSession, t: Task, now: datetime) -> None:
    """标记完成；重复任务额外生成下一次实例（保留本次为 done 以计入统计）。"""
    t.status = "done"
    t.completed_at = now
    if t.recurrence and t.recurrence != "none":
        db.add(
            Task(
                user_id=t.user_id,
                category_id=t.category_id,
                goal_id=t.goal_id,
                parent_id=t.parent_id,
                title=t.title,
                note=t.note,
                priority=t.priority,
                importance=t.importance,
                recurrence=t.recurrence,
                due_date=next_occurrence(t.due_date, t.recurrence),
                due_time=t.due_time,
                remind_before_minutes=t.remind_before_minutes,
                sort_order=t.sort_order,
            )
        )


# ---------------------------------------------------------------------------
# 四象限
# ---------------------------------------------------------------------------
QUADRANTS = [
    {"key": "q1", "title": "重要且紧急", "sub": "立即做", "importance": "high", "urgent": True},
    {"key": "q2", "title": "重要不紧急", "sub": "计划做", "importance": "high", "urgent": False},
    {"key": "q3", "title": "紧急不重要", "sub": "授权/尽快", "importance": "low", "urgent": True},
    {"key": "q4", "title": "不紧急不重要", "sub": "少做/删除", "importance": "low", "urgent": False},
]


@router.get("/matrix")
async def matrix(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """返回四个象限的任务列表（仅未完成、未删除）。"""
    urgent_vals = ["high", "urgent"]
    res = await db.scalars(
        _base_query(current.id)
        .where(Task.status == "todo")
        .order_by(Category.sort_order, Task.sort_order)
    )
    tasks = res.unique().all()
    out = []
    for qd in QUADRANTS:
        items = [
            _to_out(t)
            for t in tasks
            if t.importance == qd["importance"]
            and (t.priority in urgent_vals) == qd["urgent"]
        ]
        out.append(
            {"key": qd["key"], "title": qd["title"], "sub": qd["sub"], "tasks": items}
        )
    return out


# ---------------------------------------------------------------------------
# 更新 / 删除
# ---------------------------------------------------------------------------
@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    t = await db.get(Task, task_id, options=[selectinload(Task.tags)])
    if not t or t.user_id != current.id or t.deleted_at is not None:
        raise HTTPException(status_code=404, detail="任务不存在")

    fields = payload.model_dump(exclude_unset=True)

    # 标签独立处理：tags 是关系而非标量列，不能走 setattr 循环
    if "tags" in fields:
        names = fields.pop("tags") or []
        t.tags = await resolve_tags(db, current.id, names)

    if fields.get("category_id") is not None and fields["category_id"] != t.category_id:
        cat = await db.get(Category, fields["category_id"])
        if not cat or cat.user_id != current.id:
            raise HTTPException(status_code=400, detail="维度不存在")
    if fields.get("goal_id") is not None and fields["goal_id"] != t.goal_id:
        g = await db.get(Goal, fields["goal_id"])
        if not g or g.user_id != current.id:
            raise HTTPException(status_code=400, detail="目标不存在")

    now = datetime.now(timezone.utc)
    for k, v in fields.items():
        if k == "status":
            if v == "done" and t.status != "done":
                _mark_done(db, t, now)
                continue  # _mark_done 已写入 status/completed_at
            if v == "todo":
                t.completed_at = None
        setattr(t, k, v)

    # 到期时间 / 重复规则 / 提前量变更：重置提醒标记，允许重新提醒
    if any(
        k in fields
        for k in ("due_date", "due_time", "recurrence", "remind_before_minutes")
    ):
        t.reminder_sent_at = None

    await db.commit()
    return await _refresh_out(db, t)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    purge: bool = Query(
        False, description="true=跳过回收站直接彻底删除（不可恢复）"
    ),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """删除任务。

    默认**软删除**（移入回收站，可在 `/api/trash` 恢复）；
    传 `?purge=1` 或关闭 `FEATURE_TRASH` 时才真正物理删除。
    """
    t = await db.get(Task, task_id)
    if not t or t.user_id != current.id:
        raise HTTPException(status_code=404, detail="任务不存在")

    if purge or not settings.feature_trash:
        await db.delete(t)
    else:
        t.deleted_at = datetime.now(timezone.utc)
    await db.commit()
