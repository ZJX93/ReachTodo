from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import Tag, Task, User, task_tags
from ..schemas import TagCreate, TagOut, TagUpdate

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """列出本人全部标签，附带「未删除任务」的引用计数。

    计数用一次 LEFT JOIN 聚合完成，避免前端为每个标签再发一次请求。
    """
    rows = await db.execute(
        select(Tag, func.count(Task.id).label("task_count"))
        .where(Tag.user_id == current.id)
        .join(task_tags, task_tags.c.tag_id == Tag.id, isouter=True)
        .join(
            Task,
            (Task.id == task_tags.c.task_id) & (Task.deleted_at.is_(None)),
            isouter=True,
        )
        .group_by(Tag.id)
        .order_by(func.count(Task.id).desc(), Tag.name)
    )
    out: list[TagOut] = []
    for tag, count in rows.all():
        item = TagOut.model_validate(tag)
        item.task_count = count or 0
        out.append(item)
    return out


@router.post("", response_model=TagOut, status_code=201)
async def create_tag(
    payload: TagCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")

    # 幂等：同名直接返回已有标签，而不是报 409。
    # 客户端「输入标签名 → 回车」这类交互重复提交很常见，报错只会制造无意义的失败态。
    existing = await db.scalar(
        select(Tag).where(Tag.user_id == current.id, Tag.name == name)
    )
    if existing:
        return TagOut.model_validate(existing)

    tag = Tag(user_id=current.id, name=name, color=payload.color)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        # 并发下唯一约束兜底
        await db.rollback()
        existing = await db.scalar(
            select(Tag).where(Tag.user_id == current.id, Tag.name == name)
        )
        if existing:
            return TagOut.model_validate(existing)
        raise HTTPException(status_code=400, detail="标签创建失败")
    await db.refresh(tag)
    return TagOut.model_validate(tag)


@router.put("/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    tag = await db.get(Tag, tag_id)
    if not tag or tag.user_id != current.id:
        raise HTTPException(status_code=404, detail="标签不存在")

    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields:
        new_name = (fields["name"] or "").strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="标签名不能为空")
        if new_name != tag.name:
            dup = await db.scalar(
                select(Tag.id).where(Tag.user_id == current.id, Tag.name == new_name)
            )
            if dup:
                raise HTTPException(status_code=409, detail="已存在同名标签")
        # 重命名只改这一行，所有引用它的任务自动生效——这正是用真表而非字符串的价值
        tag.name = new_name
    if "color" in fields and fields["color"]:
        tag.color = fields["color"]

    await db.commit()
    await db.refresh(tag)
    return TagOut.model_validate(tag)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """删除标签。关联行由 ``task_tags`` 的 ON DELETE CASCADE 清理，任务本身不受影响。

    SQLite 默认不开外键约束，因此这里显式删一次关联，保证两种数据库行为一致。
    """
    tag = await db.get(Tag, tag_id)
    if not tag or tag.user_id != current.id:
        raise HTTPException(status_code=404, detail="标签不存在")
    await db.execute(delete(task_tags).where(task_tags.c.tag_id == tag_id))
    await db.delete(tag)
    await db.commit()
