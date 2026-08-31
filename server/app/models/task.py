from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Date,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
from .tag import task_tags


class Task(Base):
    """待办事项"""

    __tablename__ = "tasks"
    __table_args__ = (
        # 提醒调度器每个周期都按 (status, reminder_sent_at, due_date) 过滤，
        # 没有索引就是每分钟一次全表扫。复合索引把它压成范围扫描。
        Index(
            "ix_tasks_reminder_scan",
            "status",
            "reminder_sent_at",
            "due_date",
        ),
        # 列表页最常见的组合过滤：本人 + 未删除 + 状态。
        Index("ix_tasks_user_deleted_status", "user_id", "deleted_at", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    goal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20), default="normal"
    )  # low | normal | high | urgent（紧急度）
    importance: Mapped[str] = mapped_column(
        String(20), default="normal"
    )  # low | normal | high（重要度，用于艾森豪威尔矩阵）
    recurrence: Mapped[str] = mapped_column(
        String(20), default="none"
    )  # none | daily | weekday | weekly | biweekly | monthly | monthend
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo | done
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_time: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True
    )  # HH:MM，截止时间精确到分；为空表示仅日期
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 最近一次到期提醒已推送的时间；为空表示尚未推送。调度器据此去重，
    # 重复任务顺延后（新任务 reminder_sent_at 默认空）会重新触发。
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 本任务的提醒提前量（分钟）。为空 = 沿用全局 REMINDER_LEAD_MINUTES。
    # 「重要会议提前 60 分钟、顺手买瓶水提前 0 分钟」是真实需求，
    # 全局单值满足不了，所以下沉到任务粒度。
    remind_before_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    # 软删除时间戳。非空 = 在回收站中，所有常规查询都必须排除。
    # 自托管工具没有回收站等于误删不可恢复，是信任红线。
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    owner: Mapped["User"] = relationship(back_populates="tasks")
    category: Mapped["Category"] = relationship(back_populates="tasks")
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="tasks")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=task_tags, back_populates="tasks", lazy="selectin"
    )

    # 子任务：自引用的父子关系（parent_id 为 NULL 表示顶层任务）
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    parent: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent", cascade="all, delete-orphan"
    )
