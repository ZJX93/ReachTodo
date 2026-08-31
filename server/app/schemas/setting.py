"""用户偏好 schema。

服务端对偏好做的是「白名单 + 类型收敛」而不是完整业务校验：
- **白名单**防止客户端把偏好当成免费 KV 存储，塞进几 MB 垃圾；
- **类型收敛**保证 web / Android / 鸿蒙读到的值形态一致（比如 focusMinutes
  永远是 int，不会一个端存 "25" 另一个端存 25 导致比较失败）。

键名统一用 camelCase，与三端客户端字段一一对应，减少映射心智负担。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

WeekStart = Literal["sun", "mon"]
ThemeMode = Literal["system", "light", "dark"]
LunarSource = Literal["backend", "custom"]
DefaultView = Literal["dashboard", "tasks", "matrix", "calendar", "goals"]


class SettingsPatch(BaseModel):
    """PUT /api/settings 的请求体。所有字段可选，只提交要改的键。"""

    model_config = ConfigDict(extra="forbid")

    # 番茄钟默认时长（分钟）
    focusMinutes: Optional[int] = Field(default=None, ge=1, le=240)
    # 番茄钟休息时长
    focusBreakMinutes: Optional[int] = Field(default=None, ge=1, le=120)
    # 日历 / 周回顾的周起始日
    weekStart: Optional[WeekStart] = None
    # IANA 时区名，空串 = 跟随设备
    timezone: Optional[str] = Field(default=None, max_length=64)
    # 主题模式
    theme: Optional[ThemeMode] = None
    # 主题强调色
    accentColor: Optional[str] = Field(
        default=None, pattern=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"
    )
    # 农历 / 节假日数据源
    lunarSource: Optional[LunarSource] = None
    lunarApiBase: Optional[str] = Field(default=None, max_length=300)
    holidayApiBase: Optional[str] = Field(default=None, max_length=300)
    # 自定义数据源密钥。注意：这属于用户自己的第三方 key，不是本系统凭证。
    lunarApiKey: Optional[str] = Field(default=None, max_length=200)
    # 默认提醒提前量（分钟），新建任务时客户端用它预填
    defaultRemindBeforeMinutes: Optional[int] = Field(
        default=None, ge=0, le=60 * 24 * 7
    )
    # 是否在移动端启用本机本地提醒（无 GMS / 无网络时的兜底通道）
    localReminderEnabled: Optional[bool] = None
    # 列表里是否显示已完成任务
    showCompleted: Optional[bool] = None
    # 启动后默认落地页
    defaultView: Optional[DefaultView] = None

    @field_validator("timezone")
    @classmethod
    def _trim_tz(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class SettingsOut(BaseModel):
    """GET/PUT 的响应体。

    ``settings`` 是合并后的完整偏好（服务端默认值 ⊕ 用户已存值），
    客户端直接整份采纳即可，无需自己再兜一层默认。
    """

    settings: dict[str, Any]
    # ICS 订阅地址所需的令牌与完整 URL 路径（不含域名，客户端自行拼接 baseUrl）
    feed_token: str
    feed_path: str
    updated_at: Optional[str] = None


# 服务端权威默认值。新增偏好时只需在这里加一行 + 在 SettingsPatch 加字段。
DEFAULT_SETTINGS: dict[str, Any] = {
    "focusMinutes": 25,
    "focusBreakMinutes": 5,
    "weekStart": "sun",
    "timezone": "",
    "theme": "system",
    "accentColor": "#3B82F6",
    "lunarSource": "backend",
    "lunarApiBase": "",
    "holidayApiBase": "",
    "lunarApiKey": "",
    "defaultRemindBeforeMinutes": 10,
    "localReminderEnabled": True,
    "showCompleted": False,
    "defaultView": "dashboard",
}
