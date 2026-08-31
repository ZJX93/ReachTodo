"""用户偏好同步接口。

三端（web / Android / 鸿蒙）启动时 GET 一次覆盖本地，用户改动后 PUT 回写，
从而让「番茄钟时长、周起始日、时区、主题」等偏好跨设备一致。

服务端不解释偏好语义，只做白名单与类型校验（见 ``schemas/setting.py``），
这样新端新增自己的偏好键时无需改动后端。
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserSetting, new_feed_token
from ..schemas import DEFAULT_SETTINGS, SettingsOut, SettingsPatch

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def get_or_create(db: AsyncSession, user_id: int) -> UserSetting:
    """懒创建：老用户第一次访问时补一行，无需数据迁移回填。"""
    row = await db.scalar(select(UserSetting).where(UserSetting.user_id == user_id))
    if row:
        return row
    row = UserSetting(user_id=user_id, data="{}", feed_token=new_feed_token())
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # 两个端同时首启会撞 unique(user_id)，回滚后重取即可
        await db.rollback()
        row = await db.scalar(
            select(UserSetting).where(UserSetting.user_id == user_id)
        )
        if row is None:
            raise
        return row
    await db.refresh(row)
    return row


def _compose(row: UserSetting) -> SettingsOut:
    merged = {**DEFAULT_SETTINGS, **row.as_dict()}
    return SettingsOut(
        settings=merged,
        feed_token=row.feed_token,
        feed_path=f"/api/calendar.ics?token={row.feed_token}",
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.get("", response_model=SettingsOut)
async def read_settings(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return _compose(await get_or_create(db, current.id))


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsPatch,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """增量更新：只提交要改的键，未提交的键保持原值。

    用 PUT 而非 PATCH 是为了兼容部分 HTTP 客户端（含鸿蒙早期 http 模块）
    对 PATCH 支持不完整的问题；语义上等价于 PATCH。
    """
    row = await get_or_create(db, current.id)
    patch = payload.model_dump(exclude_unset=True)
    if patch:
        row.merge(patch)
        await db.commit()
        await db.refresh(row)
    return _compose(row)


@router.post("/feed-token/reset", response_model=SettingsOut)
async def reset_feed_token(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """重置日历订阅令牌。订阅链接一旦外泄（例如贴到聊天群），用它作废旧链接。"""
    row = await get_or_create(db, current.id)
    row.feed_token = new_feed_token()
    await db.commit()
    await db.refresh(row)
    return _compose(row)
