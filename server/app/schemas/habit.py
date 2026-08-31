"""习惯打卡的请求 / 响应模型。

字段命名与前端单文件原型（``docs/prototypes/habit-station.html``）保持
snake_case 一致，同步端点因此可以做零转换的字段映射。

对外暴露的 ``id`` 一律是 ``client_id``（字符串 uuid），不是数据库自增主键 ——
客户端全程只与 client_id 打交道，断网时也能自行生成 id。
"""

from datetime import date, datetime
from datetime import date as _Date  # 见 CheckinIn 的说明：规避类体字段名遮蔽
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_COLOR = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"
_TIME = r"^([01]\d|2[0-3]):[0-5]\d$"


def _norm_color(v: str, default: str) -> str:
    """颜色非法时回落到默认值而不是 422。

    同步场景下更要宽松：客户端可能来自旧版本、带了不被识别的色值，
    为此拒绝整包同步的代价远大于「颜色显示成默认色」。
    """
    import re

    s = (v or "").strip()
    return s if re.match(_COLOR, s) else default


def _norm_time(v: Optional[str]) -> Optional[str]:
    import re

    if v is None:
        return None
    s = str(v).strip()
    return s if re.match(_TIME, s) else None


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(default="smile", max_length=40)
    color: str = Field(default="#7C9A92")
    # type / frequency / size 用 str 而非 Literal：非法值在
    # _apply_habit_fields 里宽松回落为默认值，而不是在入口就 422。
    # 这样「显式创建」与「跨版本同步」两条写入路径行为完全一致。
    # （校验逻辑在 schema 的 field_validator 与 router 里双层兜底）
    type: str = Field(default="check", description="check|count|duration|timerange")
    target: int = Field(default=1, ge=1, le=9999)
    unit: str = Field(default="次", max_length=16)
    frequency: str = Field(default="daily", description="daily|weekday|weekend|custom")
    weekdays: list[int] = Field(default_factory=list)
    size: str = Field(default="md", description="sm|md|lg")
    category_id: Optional[str] = Field(default=None, max_length=40)
    goal_id: Optional[int] = None
    start_date: Optional[date] = None
    sort_order: int = 0
    # 客户端可自带 id（离线优先）；缺省时服务端生成 uuid4
    client_id: Optional[str] = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("习惯名称不能为空")
        return s

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        return _norm_color(v, "#7C9A92")

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v: list[int]) -> list[int]:
        return sorted({int(x) for x in (v or []) if 0 <= int(x) <= 6})


class HabitUpdate(BaseModel):
    """全量可选更新。只提交要改的字段（PATCH 语义）。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=40)
    color: Optional[str] = Field(default=None, max_length=9)
    type: Optional[str] = None  # 见 HabitCreate：宽松接收，router 清洗
    target: Optional[int] = Field(default=None, ge=1, le=9999)
    unit: Optional[str] = Field(default=None, max_length=16)
    frequency: Optional[str] = None
    weekdays: Optional[list[int]] = None
    size: Optional[str] = None
    category_id: Optional[str] = Field(default=None, max_length=40)
    goal_id: Optional[int] = None
    start_date: Optional[date] = None
    archived: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("习惯名称不能为空")
        return s


class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # = client_id
    name: str
    icon: str
    color: str
    type: str
    target: int
    unit: str
    frequency: str
    weekdays: list[int] = []
    size: str
    category_id: Optional[str] = None  # 维度字符串键（work/health/study/life）
    goal_id: Optional[int] = None
    start_date: date
    archived: bool = False
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # ---- 计算字段（列表接口一次带出，省掉前端 N 次请求）----
    streak: int = 0
    best_streak: int = 0
    done_today: bool = False
    value_today: int = 0


class CheckinIn(BaseModel):
    """打卡 / 取消打卡。

    - 不传 ``date`` 表示今天；传了即为**补卡**（回写历史某一天）。
    - ``value`` 语义随习惯类型而定；传 0 表示取消打卡。
    - ``timerange`` 类型改看 ``start_time`` / ``end_time``。

    注意：这里**不能**写 ``Optional[date]``。CPython 类体作用域有个知名坑：
    ``date: Optional[date] = None`` 中，注解里的 ``date`` 会被解析为
    当前类体中即将绑定的同名字段（求值结果是 ``None``，不是 ``datetime.date``），
    于是 Pydantic 生成的 schema 变成 ``type: null``，传任何日期都 422。
    规避手段是给类型起别名（模块顶部 ``date as _Date``），让注解里的名字
    与字段名不同 —— 与 ``from __future__ import annotations`` 无关。
    """

    date: Optional[_Date] = None
    value: Optional[int] = Field(default=None, ge=0, le=999999)
    start_time: Optional[str] = Field(default=None, max_length=5)
    end_time: Optional[str] = Field(default=None, max_length=5)
    note: Optional[str] = Field(default=None, max_length=300)

    @field_validator("start_time", "end_time")
    @classmethod
    def _t(cls, v: Optional[str]) -> Optional[str]:
        return _norm_time(v)


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # = client_id
    habit_id: str  # = 所属习惯的 client_id
    checkin_date: date
    value: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 该次打卡是否达成目标（由服务端按习惯类型判定，前端不必重复实现）
    done: bool = False


class MoodIn(BaseModel):
    date: Optional[_Date] = None
    score: int = Field(ge=1, le=5)
    note: Optional[str] = Field(default=None, max_length=300)


class MoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: _Date  # = mood_date
    score: int
    note: Optional[str] = None
    updated_at: Optional[datetime] = None


class HabitStatsOut(BaseModel):
    """单个习惯的战绩。"""

    habit_id: str
    streak: int = 0
    best_streak: int = 0
    total_checkins: int = 0
    rate_30: float = 0.0  # 近 30 天达成率 0~1
    rate_all: float = 0.0
    last_30: list[dict] = []  # [{date, value, done}]，供前端画小热力


class TodayOut(BaseModel):
    """今日聚合：一次请求满足首页全部渲染需求。"""

    date: str  # YYYY-MM-DD
    total: int = 0
    done: int = 0
    percent: int = 0  # 0~100
    streak: int = 0  # 全站连续全勤天数
    habits: list[dict] = []  # 今日待打卡的习惯 + 各自状态
    mood: Optional[int] = None


# ---------------------------------------------------------------------------
# 同步
# ---------------------------------------------------------------------------


class SyncPush(BaseModel):
    """推送上来的增量。

    刻意用宽松的 ``dict`` 而不是严格模型：同步是跨版本的，
    客户端多带一个字段（新版本加的）不该让整包同步失败。
    字段白名单提取与清洗在 router 里做（见 ``_apply_habit_fields``）。
    """

    habits: list[dict[str, Any]] = Field(default_factory=list)
    checkins: list[dict[str, Any]] = Field(default_factory=list)
    moods: list[dict[str, Any]] = Field(default_factory=list)
    client_time: Optional[str] = None


class SyncPull(BaseModel):
    """拉取下来的增量。``id`` 一律为 client_id，客户端可直接用于合并。"""

    habits: list[dict[str, Any]] = Field(default_factory=list)
    checkins: list[dict[str, Any]] = Field(default_factory=list)
    moods: list[dict[str, Any]] = Field(default_factory=list)
    server_time: str = ""
    applied: dict[str, int] = Field(default_factory=dict)  # 仅 POST 时有值
