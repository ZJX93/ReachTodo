"""用户偏好（跨设备同步）+ 日历订阅令牌。

背景：改造前 web 把偏好存 ``localStorage``、Android 存 DataStore、鸿蒙存
``PersistentStorage``，同一个人换端后「番茄钟时长 / 周起始日 / 时区 / 农历数据源」
全部要重设一遍——这是三端体验割裂最明显的地方。

实现取舍：
- 偏好用**一个 JSON 文本列**存，而不是给每个偏好开一列。偏好属于「客户端自定义、
  增删频繁、无需服务端按字段查询」的数据，开列意味着每加一个偏好就要一次迁移。
- 服务端只做白名单校验与类型收敛（见 ``schemas/setting.py``），不理解业务含义，
  这样新端要加自己的偏好键时无需改后端。
- ``feed_token`` 承载 ICS 日历订阅的免登录访问：日历客户端（系统日历 / Outlook）
  无法带 Bearer 头，只能用 URL 里的长随机令牌；它与 JWT 完全隔离，
  泄露也只暴露「任务标题 + 到期时间」，且可一键重置。
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def new_feed_token() -> str:
    return secrets.token_urlsafe(24)


class UserSetting(Base):
    """一个用户一行。首次访问 /api/settings 时懒创建。"""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    # 偏好 JSON（UTF-8 文本）。空串视为 {}。
    data: Mapped[str] = mapped_column(Text, default="{}")
    # ICS 订阅令牌（URL 内传递，不可猜测）
    feed_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_feed_token
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User")

    # ------------------------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        """安全解析 JSON；脏数据（手工改库 / 截断）时退化为空字典而不是 500。"""
        if not self.data:
            return {}
        try:
            parsed = json.loads(self.data)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def merge(self, patch: dict[str, Any]) -> dict[str, Any]:
        """浅合并写入：客户端只需提交变更的键，未提交的键保持原值。"""
        merged = {**self.as_dict(), **patch}
        self.data = json.dumps(merged, ensure_ascii=False)
        return merged
