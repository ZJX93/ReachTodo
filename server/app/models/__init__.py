"""ORM 模型按领域拆分后的聚合出口。

所有子模块仅以字符串形式声明跨模型关系（如 ``Mapped[list["Category"]]``），
彼此之间无运行时 import 依赖，因此本 ``__init__`` 可以安全地把它们全部导入，
确保各自的表都注册到 ``Base.metadata``（Alembic / ``init_db`` 依赖这一点）。

对外保持与旧 ``app.models`` 模块完全一致的命名空间：
``from app.models import User`` 等既有导入语句无需改动。

例外：``models/task.py`` 需要 ``task_tags`` 这张关联表对象来声明 secondary，
因此它显式 ``from .tag import task_tags``（表对象而非模型类，无循环风险）。
"""

from .user import User, DeviceToken
from .category import Category
from .goal import Goal
from .tag import Tag, task_tags
from .task import Task
from .focus import FocusSession
from .record import Record, Template
from .setting import UserSetting, new_feed_token

__all__ = [
    "User",
    "DeviceToken",
    "Category",
    "Goal",
    "Tag",
    "task_tags",
    "Task",
    "FocusSession",
    "Record",
    "Template",
    "UserSetting",
    "new_feed_token",
]
