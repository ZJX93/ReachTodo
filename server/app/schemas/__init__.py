"""Pydantic schema 按领域拆分后的聚合出口。

与旧 ``app.schemas`` 模块保持完全一致的命名空间：
``from app.schemas import TaskCreate`` 等既有导入语句无需改动。

``common`` 中的 Literal 枚举类型也在此重新导出，便于路由层集中引用。
"""

from .common import (
    Priority,
    Importance,
    Recurrence,
    TaskStatus,
    RecordType,
    TemplateType,
    GoalStatus,
    DevicePlatform,
)
from .user import UserCreate, UserUpdate, PasswordChange, UserOut, TokenOut
from .category import CategoryCreate, CategoryUpdate, CategoryOut
from .goal import GoalCreate, GoalUpdate, GoalOut, GoalBoardItem
from .tag import TagCreate, TagUpdate, TagOut
from .task import (
    TaskCreate,
    TaskUpdate,
    TaskOut,
    TaskBulkRequest,
    TaskBulkResult,
    BulkAction,
)
from .focus import FocusSessionCreate, FocusSessionOut
from .record import (
    RecordCreate,
    RecordUpdate,
    RecordOut,
    CalendarDay,
    TemplateCreate,
    TemplateUpdate,
    TemplateOut,
)
from .setting import SettingsPatch, SettingsOut, DEFAULT_SETTINGS

__all__ = [
    # enums
    "Priority",
    "Importance",
    "Recurrence",
    "TaskStatus",
    "RecordType",
    "TemplateType",
    "GoalStatus",
    "DevicePlatform",
    "BulkAction",
    # user
    "UserCreate",
    "UserUpdate",
    "PasswordChange",
    "UserOut",
    "TokenOut",
    # category
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryOut",
    # goal
    "GoalCreate",
    "GoalUpdate",
    "GoalOut",
    "GoalBoardItem",
    # tag
    "TagCreate",
    "TagUpdate",
    "TagOut",
    # task
    "TaskCreate",
    "TaskUpdate",
    "TaskOut",
    "TaskBulkRequest",
    "TaskBulkResult",
    # focus
    "FocusSessionCreate",
    "FocusSessionOut",
    # record
    "RecordCreate",
    "RecordUpdate",
    "RecordOut",
    "CalendarDay",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateOut",
    # settings
    "SettingsPatch",
    "SettingsOut",
    "DEFAULT_SETTINGS",
]
