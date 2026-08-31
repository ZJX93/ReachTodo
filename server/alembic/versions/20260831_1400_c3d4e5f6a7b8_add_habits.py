"""habits / habit_checkins / habit_moods（习惯打卡）

补齐路线图 P1 第一项「习惯打卡」。三张表：

  - habits          习惯定义（含 client_id 业务主键、软删除墓碑）
  - habit_checkins  打卡记录，业务唯一键 (habit_id, checkin_date)
  - habit_moods     每日心情，业务唯一键 (user_id, mood_date)

为什么新建三张表而不是复用 tasks：
  Task 的重复是「完成后顺延下一次」，库里永远只有当前一条实例，
  查不到历史轨迹；而习惯的全部价值正在于 streak / 热力图 / 完成率 / 补卡。
  两者语义不同，强行复用会让所有统计功能无法实现。

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-31 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- 习惯定义 ----------------
    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # 对外业务主键（客户端 uuid）。离线优先架构下客户端断网即可生成 id，
        # 联网后靠它对齐，无需等待服务端分配自增 id。
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=40), nullable=False, server_default="smile"),
        sa.Column("color", sa.String(length=9), nullable=False, server_default="#7C9A92"),
        # check 打勾 | count 计数 | duration 时长 | timerange 时间段
        sa.Column("type", sa.String(length=20), nullable=False, server_default="check"),
        sa.Column("target", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=16), nullable=False, server_default="次"),
        # daily | weekday | weekend | custom
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="daily"),
        sa.Column("weekdays", sa.Text(), nullable=True),
        sa.Column("size", sa.String(length=10), nullable=False, server_default="md"),
        sa.Column("category_key", sa.String(length=40), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        # 软删除墓碑：物理删除会让已删数据在另一台设备下次推送时「复活」
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_habits_user_client"),
    )
    op.create_index("ix_habits_user_id", "habits", ["user_id"])
    op.create_index("ix_habits_client_id", "habits", ["client_id"])
    op.create_index("ix_habits_goal_id", "habits", ["goal_id"])
    op.create_index("ix_habits_deleted_at", "habits", ["deleted_at"])
    op.create_index("ix_habits_user_deleted", "habits", ["user_id", "deleted_at"])

    # ---------------- 打卡记录 ----------------
    op.create_table(
        "habit_checkins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("habit_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        # 业务日期（用户所在时区的那一天），不是 UTC 时间戳
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_time", sa.String(length=5), nullable=True),
        sa.Column("end_time", sa.String(length=5), nullable=True),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        # 幂等的地基：补卡 / 取消打卡 / 重复提交 / 多端同步全靠这条唯一约束
        sa.UniqueConstraint("habit_id", "checkin_date", name="uq_checkin_habit_date"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_checkins_user_client"),
    )
    op.create_index("ix_habit_checkins_user_id", "habit_checkins", ["user_id"])
    op.create_index("ix_habit_checkins_habit_id", "habit_checkins", ["habit_id"])
    op.create_index("ix_habit_checkins_client_id", "habit_checkins", ["client_id"])
    op.create_index("ix_habit_checkins_checkin_date", "habit_checkins", ["checkin_date"])
    # 热力图按「本人 + 日期区间」扫描，复合索引压成范围扫描
    op.create_index("ix_checkins_user_date", "habit_checkins", ["user_id", "checkin_date"])

    # ---------------- 每日心情 ----------------
    op.create_table(
        "habit_moods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("mood_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "mood_date", name="uq_mood_user_date"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_moods_user_client"),
    )
    op.create_index("ix_habit_moods_user_id", "habit_moods", ["user_id"])
    op.create_index("ix_habit_moods_client_id", "habit_moods", ["client_id"])
    op.create_index("ix_habit_moods_mood_date", "habit_moods", ["mood_date"])


def downgrade() -> None:
    op.drop_table("habit_moods")
    op.drop_table("habit_checkins")
    op.drop_table("habits")
