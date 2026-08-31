from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Goal, User, Task
from ..schemas import GoalCreate, GoalUpdate, GoalOut, GoalBoardItem
from ..deps import get_current_user

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
async def list_goals(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = select(Goal).where(Goal.user_id == current.id)
    if status:
        q = q.where(Goal.status == status)
    q = q.order_by(Goal.created_at.desc())
    res = await db.scalars(q)
    return [GoalOut.model_validate(g) for g in res]


@router.get("/board", response_model=list[GoalBoardItem])
async def board(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """目标进度看板：每个目标的关联任务总数/完成数/逾期数/完成率。

    优化：原先每个目标各发 3 次 count 查询（N+1）。改为一次 GROUP BY 聚合，
    再用结果补齐未关联任何任务的目标（total=0）。
    """
    from datetime import date

    agg = (
        await db.execute(
            select(
                Task.goal_id,
                func.count(Task.id).label("total"),
                func.count(Task.id).filter(Task.status == "done").label("done"),
                func.count(Task.id)
                .filter(Task.status == "todo", Task.due_date < date.today())
                .label("overdue"),
            )
            # 只统计本人且未在回收站的任务：
            # 缺少 user_id 条件会跨账号聚合，缺少 deleted_at 条件会让
            # 目标进度把已删任务算进分母。
            .where(
                Task.goal_id.isnot(None),
                Task.user_id == current.id,
                Task.deleted_at.is_(None),
            )
            .group_by(Task.goal_id)
        )
    ).all()
    by_goal = {row.goal_id: row for row in agg}

    goals = (await db.scalars(select(Goal).where(Goal.user_id == current.id))).all()
    out = []
    for g in goals:
        row = by_goal.get(g.id)
        total = row.total if row else 0
        done = row.done if row else 0
        overdue = row.overdue if row else 0
        progress = round(done / total * 100) if total else 0
        item = GoalBoardItem.model_validate(g)
        item.total = total
        item.done = done
        item.overdue = overdue
        item.progress = progress
        out.append(item)
    return out


@router.post("", response_model=GoalOut, status_code=201)
async def create_goal(
    payload: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    g = Goal(user_id=current.id, **payload.model_dump())
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return GoalOut.model_validate(g)


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    g = await db.get(Goal, goal_id)
    if not g or g.user_id != current.id:
        raise HTTPException(status_code=404, detail="目标不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    await db.commit()
    await db.refresh(g)
    return GoalOut.model_validate(g)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    g = await db.get(Goal, goal_id)
    if not g or g.user_id != current.id:
        raise HTTPException(status_code=404, detail="目标不存在")
    await db.delete(g)
    await db.commit()
