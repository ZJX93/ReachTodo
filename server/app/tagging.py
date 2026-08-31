"""标签解析：把「客户端传来的标签名数组」映射成本用户的 ``Tag`` 实体。

单独成模块的原因：``routers/tasks.py``（创建/更新/批量）与 ``routers/import_data.py``
都需要「按名取标签，没有就建」这套逻辑，放在任一 router 里都会造成反向依赖。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Tag

# 预置调色板：新标签按创建顺序轮换取色，避免全是灰色一片、
# 也避免让用户在创建任务时被迫先选颜色。
_PALETTE = [
    "#3B82F6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#06B6D4",
    "#EC4899",
    "#64748B",
]


async def resolve_tags(
    db: AsyncSession, user_id: int, names: list[str]
) -> list[Tag]:
    """按名取本用户标签，缺失的自动创建。返回顺序与 ``names`` 一致。

    注意：这里 ``flush`` 而不 ``commit``——调用方（router）负责事务边界，
    否则批量操作里每个标签一次提交会把一个逻辑操作拆成几十个事务。
    """
    if not names:
        return []

    existing = (
        await db.scalars(
            select(Tag).where(Tag.user_id == user_id, Tag.name.in_(names))
        )
    ).all()
    by_name = {t.name: t for t in existing}

    missing = [n for n in names if n not in by_name]
    if missing:
        # 取当前标签总数作为调色板起点，让同一用户的标签颜色尽量分散
        total = len(
            (await db.scalars(select(Tag.id).where(Tag.user_id == user_id))).all()
        )
        for i, name in enumerate(missing):
            tag = Tag(
                user_id=user_id,
                name=name,
                color=_PALETTE[(total + i) % len(_PALETTE)],
            )
            db.add(tag)
            by_name[name] = tag
        await db.flush()

    return [by_name[n] for n in names if n in by_name]
