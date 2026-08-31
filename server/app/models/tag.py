"""标签模型（任务多对多）。

同类产品（滴答清单 / Todoist / Vikunja）都把「标签」作为与清单正交的第二筛选维度：
维度回答「这属于我人生的哪一块」，标签回答「这件事的形态是什么」（#电话 #外出 #5分钟）。
任务量上百之后，没有标签就只能靠肉眼翻列表。

设计取舍：
- 采用真表 + 关联表而非 ``Record.tags`` 那样的逗号分隔字符串——只有真表才能
  做「按标签过滤 + 统计计数 + 重命名后全局生效」。
- 标签按用户隔离，``(user_id, name)`` 唯一，写入时按名 upsert，前端只传名字数组。
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# 任务 ↔ 标签 关联表。两端都 CASCADE：删任务或删标签都自动清理关联行。
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column(
        "task_id",
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base):
    """用户自定义标签。"""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(20), default="#64748B")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", secondary=task_tags, back_populates="tags"
    )
