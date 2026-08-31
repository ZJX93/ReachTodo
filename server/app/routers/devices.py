from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import DeviceToken, User
from ..schemas import DevicePlatform

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceRegister(BaseModel):
    # token 长度上限按 FCM/Push Kit 实际取值放宽，同时防止超长串灌库
    token: str = Field(min_length=8, max_length=1024)
    # 用 Literal 而非裸 str：平台值决定推送走哪条通道（harmony → 华为 Push Kit，
    # 其余 → FCM），一个拼错的平台名会让该设备永远收不到推送且毫无报错。
    platform: DevicePlatform = "android"
    device_name: Optional[str] = Field(default=None, max_length=100)


@router.post("/register")
async def register_device(
    body: DeviceRegister,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """注册/更新当前用户的设备推送令牌（幂等：同一 token 重复上报只更新）。"""
    existing = await db.scalar(
        select(DeviceToken).where(
            DeviceToken.user_id == current.id, DeviceToken.token == body.token
        )
    )
    now = datetime.now(timezone.utc)
    if existing:
        existing.platform = body.platform
        existing.device_name = body.device_name
        existing.last_used_at = now
    else:
        db.add(
            DeviceToken(
                user_id=current.id,
                token=body.token,
                platform=body.platform,
                device_name=body.device_name,
                last_used_at=now,
            )
        )
    await db.commit()
    return {"ok": True}


@router.post("/unregister")
async def unregister_device(
    body: DeviceRegister,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """注销设备令牌（退出登录 / 卸载时调用）。"""
    await db.execute(
        delete(DeviceToken).where(
            DeviceToken.user_id == current.id, DeviceToken.token == body.token
        )
    )
    await db.commit()
    return {"ok": True}


@router.get("")
async def list_devices(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """列出当前用户已注册的设备（用于设置页管理）。"""
    rows = (
        await db.execute(
            select(DeviceToken)
            .where(DeviceToken.user_id == current.id)
            .order_by(DeviceToken.id.desc())
        )
    ).scalars().all()
    return [
        {
            "id": d.id,
            "platform": d.platform,
            "device_name": d.device_name,
            "last_used_at": d.last_used_at.isoformat() if d.last_used_at else None,
        }
        for d in rows
    ]
