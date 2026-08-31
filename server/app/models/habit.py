"""习惯打卡（Habit）领域模型。

设计要点（与前端单文件原型 ``docs/prototypes/habit-station.html`` 及
``docs/competitive-analysis-and-roadmap.md`` 的 P1 规划保持一致）：

1. **为什么不能复用 ``Task.recurrence``**
   ``Task`` 的重复是「完成后顺延下一次」，库里永远只有当前这一条实例，
   查不到「上周三打没打卡」。而习惯的全部价值恰恰在于**历史轨迹**：
   streak、热力图、完成率、补卡。两者语义不同，必须分表。

2. **双 id 体系**
   - ``id``：内部自增整数主键，与其它表保持一致，用于外键与索引。
   - ``client_id``：对外的业务主键（客户端生成的 uuid）。
     所有 REST 路径参数与响应里的 ``id`` 一律用 ``client_id``，
     客户端永远不需要感知服务端自增 id —— 这正是离线优先架构的关键：
     客户端在断网时就能生成 id，联网后直接对齐，无需等服务端分配。

3. **打卡记录以 ``(habit_id, checkin_date)`` 为业务唯一键**
   这一条唯一约束是整个设计的地基：补卡、取消打卡、重复提交、多端同步
   的幂等性全靠它。「取消打卡」= 把 ``value`` 归零，记录仍然保留，
   因此不需要给 checkin 加软删除墓碑。

4. **日期口径**
   ``checkin_date`` 存**业务日期**（用户所在时区的那一天），不存 UTC 时间戳。
   打卡是「我的今天」，不是「UTC 的今天」。跨时区用户换设备时，
   服务端按请求头/偏好提供的时区解释「今天」，而不是强行按 UTC 切分。
   （对比：``routers/stats.py`` 统计任务完成数时用 UTC 比较时间戳，
   那是「事件发生了吗」的口径；这里是「这一天属于哪一天」的口径，不同。）

5. **删除用 ``deleted_at`` 墓碑**
   物理删除会导致另一台设备同步时不知道「有东西被删了」，
   于是已删数据会在下次推送时复活。墓碑是唯一可靠的传播方式。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Habit(Base):
    """习惯定义。"""

    __tablename__ = "habits"
    __table_args__ = (
        # 同一用户的 client_id 必须唯一 —— 同步时靠它定位行。
        UniqueConstraint("user_id", "client_id", name="uq_habits_user_client"),
        # 列表页最频繁的过滤组合：本人 + 未删除。
        Index("ix_habits_user_deleted", "user_id", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 对外业务主键（客户端 uuid）。见模块文档第 2 点。
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    goal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(100))
    # 前端图标集的 key（如 water / book / sleep），不存 emoji：
    # 三端字体覆盖不一致，emoji 在部分设备上会显示成豆腐块。
    icon: Mapped[str] = mapped_column(String(40), default="smile")
    color: Mapped[str] = mapped_column(String(9), default="#7C9A92")
    # check 打勾 | count 计数 | duration 时长(分钟) | timerange 时间段
    type: Mapped[str] = mapped_column(String(20), default="check")
    # 每日目标值。check/timerange 固定为 1，count/duration 由用户设定。
    target: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[str] = mapped_column(String(16), default="次")
    # daily 每天 | weekday 工作日 | weekend 周末 | custom 自选星期
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    # custom 时生效：JSON 数组文本，如 "[1,3,5]"（0=周日）。
    # 用文本列而非关联表：星期最多 7 个值，开表收益远不抵复杂度。
    weekdays: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 卡片尺寸 sm | md | lg（前端布局用，服务端只做透传与校验）
    size: Mapped[str] = mapped_column(String(10), default="md")
    # 维度标识（work / health / study / life）。
    # 注意与 Task.category_id 区分：那里是 Category 表的整数外键，
    # 这里存的是前端约定的维度字符串键，故命名为 category_key 以免混淆。
    category_key: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    owner: Mapped["User"] = relationship(back_populates="habits")
    checkins: Mapped[list["HabitCheckin"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------
    def weekdays_list(self) -> list[int]:
        """解析 weekdays 文本列。脏数据（手工改库/截断）退化为 [] 而不是 500。"""
        return parse_weekdays(self.weekdays)

    def set_weekdays(self, days: list[int] | None) -> None:
        self.weekdays = json.dumps(sorted({int(d) for d in (days or []) if 0 <= int(d) <= 6}))


class HabitCheckin(Base):
    """一次打卡记录。业务唯一键为 (habit_id, checkin_date)。"""

    __tablename__ = "habit_checkins"
    __table_args__ = (
        # 幂等的地基：同一习惯同一天只能有一条，重复提交走更新而非插入。
        UniqueConstraint("habit_id", "checkin_date", name="uq_checkin_habit_date"),
        UniqueConstraint("user_id", "client_id", name="uq_checkins_user_client"),
        # 热力图按「本人 + 日期区间」扫描，复合索引把它压成范围扫描。
        Index("ix_checkins_user_date", "user_id", "checkin_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(String(64), index=True)

    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # check: 0/1；count: 次数；duration: 分钟；timerange: 固定 1
    value: Mapped[int] = mapped_column(Integer, default=0)
    # timerange 专用，HH:MM
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    habit: Mapped["Habit"] = relationship(back_populates="checkins")


class HabitMood(Base):
    """每日心情。按 (user_id, mood_date) 唯一。"""

    __tablename__ = "habit_moods"
    __table_args__ = (
        UniqueConstraint("user_id", "mood_date", name="uq_mood_user_date"),
        UniqueConstraint("user_id", "client_id", name="uq_moods_user_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    mood_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=3)  # 1~5
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def parse_weekdays(raw: Optional[str]) -> list[int]:
    """把 weekdays 文本列解析为 0~6 的有序列表；脏数据返回空列表。"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    out: set[int] = set()
    for item in parsed:
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 6:
            out.add(n)
    return sorted(out)


def is_scheduled_on(habit: Habit, day: date) -> bool:
    """该习惯在指定日期是否需要执行。

    与前端 ``isScheduledOn`` 保持完全一致的语义，避免两端算出不同的 streak。
    """
    freq = habit.frequency or "daily"
    if freq == "daily":
        return True
    wd = (day.weekday() + 1) % 7  # Python: Mon=0..Sun=6 → 转成 Sun=0..Sat=6
    if freq == "weekday":
        return 1 <= wd <= 5
    if freq == "weekend":
        return wd in (0, 6)
    if freq == "custom":
        return wd in parse_weekdays(habit.weekdays)
    return True
