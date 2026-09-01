from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, Text, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Record(Base):
    """记录：个人日记 / 工作日志 / 读书笔记（统一模型，按 type 区分）"""

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(
        String(20), default="diary"
    )  # diary | worklog | note
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 日记心情
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 逗号分隔
    book_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 读书笔记
    book_author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    project: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 工作日志项目
    weather: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # 天气（emoji 或文字）
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 位置
    record_date: Mapped[date] = mapped_column(Date, index=True, default=date.today)
    record_time: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True
    )  # HH:MM，精确到分；为空表示仅记录日期
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # 软删除时间戳，与 Task 一致：删除先进回收站，可恢复 / 可彻底清除。
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    owner: Mapped["User"] = relationship("User")


class Template(Base):
    """记录模板：内置预设（user_id 为 NULL）与用户自定义（user_id 有值）"""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(
        String(20), default="diary"
    )  # diary | worklog | note | all
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(20), default="📄")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_preset: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
