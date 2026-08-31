from datetime import datetime, date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import Priority, Importance, Recurrence, TaskStatus

# 标签名：去掉首尾空白后不得为空，最长 40 字符（与 models.Tag.name 一致）
TagName = str


def _norm_tags(values: Optional[list[str]]) -> Optional[list[str]]:
    """标签名归一化：去空白、丢弃空串、去重且保持首次出现顺序、截断超长。

    去重必须保序——用户输入 ["工作","电话","工作"] 时期望看到 ["工作","电话"]，
    用 set() 会让顺序随哈希抖动，前端展示每次刷新都在跳。
    """
    if values is None:
        return None
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        name = (raw or "").strip()[:40]
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out[:20]  # 单任务标签上限，防滥用


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category_id: int = Field(ge=1)
    goal_id: Optional[int] = Field(default=None, ge=1)
    parent_id: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    priority: Priority = "normal"
    importance: Importance = "normal"
    recurrence: Recurrence = "none"
    due_date: Optional[date] = None
    due_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # 提醒提前量（分钟），None = 用服务端全局默认；上限 7 天
    remind_before_minutes: Optional[int] = Field(default=None, ge=0, le=60 * 24 * 7)
    tags: Optional[list[TagName]] = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _norm_tags(v)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    category_id: Optional[int] = Field(default=None, ge=1)
    goal_id: Optional[int] = Field(default=None, ge=1)
    parent_id: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    priority: Optional[Priority] = None
    importance: Optional[Importance] = None
    recurrence: Optional[Recurrence] = None
    status: Optional[TaskStatus] = None  # todo | done
    due_date: Optional[date] = None
    due_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    remind_before_minutes: Optional[int] = Field(default=None, ge=0, le=60 * 24 * 7)
    # 传 [] 表示清空全部标签；不传（unset）表示不动标签。
    tags: Optional[list[TagName]] = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _norm_tags(v)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    goal_id: Optional[int]
    parent_id: Optional[int] = None
    title: str
    note: Optional[str]
    priority: str
    importance: str
    recurrence: str
    status: str
    due_date: Optional[date]
    due_time: Optional[str] = None
    sort_order: int
    created_at: datetime
    completed_at: Optional[datetime]
    remind_before_minutes: Optional[int] = None
    deleted_at: Optional[datetime] = None

    # 关联信息（供前端展示蓝色目标文字、维度色块）
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    category_icon: Optional[str] = None
    goal_title: Optional[str] = None
    # 标签名数组（客户端只关心名字；颜色由 /api/tags 一次性拉取后本地映射）
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _tags_to_names(cls, v):
        """把 ORM 的 ``list[Tag]`` 摊平成 ``list[str]``。

        ``model_validate(task)`` 在 ``from_attributes`` 模式下会直接读到 Tag 实体，
        没有这个前置转换就会报 string_type 校验错误。放在 schema 里而不是
        每个路由手工赋值，可保证所有返回 TaskOut 的地方行为一致。
        """
        if v is None:
            return []
        return [x if isinstance(x, str) else getattr(x, "name", str(x)) for x in v]


# ---------------------------------------------------------------------------
# 批量操作
# ---------------------------------------------------------------------------
BulkAction = Literal[
    "complete",      # 标记完成
    "uncomplete",    # 取消完成
    "delete",        # 移入回收站
    "restore",       # 从回收站恢复
    "purge",         # 彻底删除
    "set_category",  # 改维度
    "set_goal",      # 改关联目标（goal_id=null 解除关联）
    "set_priority",  # 改紧急度
    "set_importance",# 改重要度
    "add_tags",      # 追加标签
    "remove_tags",   # 移除标签
]


class TaskBulkRequest(BaseModel):
    """批量操作请求。

    一次只做一件事（``action``），避免「批量改维度顺便还把标签清空了」这类
    意图不明的复合语义；需要连做两件事就发两次请求。
    """

    ids: list[int] = Field(min_length=1, max_length=500)
    action: BulkAction
    category_id: Optional[int] = Field(default=None, ge=1)
    goal_id: Optional[int] = Field(default=None, ge=1)
    priority: Optional[Priority] = None
    importance: Optional[Importance] = None
    tags: Optional[list[TagName]] = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _norm_tags(v)


class TaskBulkResult(BaseModel):
    action: str
    requested: int
    affected: int
    skipped: int
