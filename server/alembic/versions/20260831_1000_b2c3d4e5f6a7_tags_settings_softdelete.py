"""tags / user_settings / soft delete / per-task reminder lead

新增：
  - tags 表 + task_tags 关联表（标签体系）
  - user_settings 表（偏好跨端同步 + ICS 订阅令牌）
  - tasks.deleted_at / records.deleted_at（回收站软删除）
  - tasks.remind_before_minutes（每任务提醒提前量）
  - tasks 复合索引（提醒扫描 / 列表过滤）

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-31 10:00:00.000000

"""
import secrets

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- 标签 ----------------
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False, server_default="#64748B"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])

    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Integer(), primary_key=True),
        sa.Column("tag_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
    )
    # 反向查询（"这个标签下有哪些任务"）需要 tag_id 单列索引；
    # 复合主键 (task_id, tag_id) 只能加速正向查询。
    op.create_index("ix_task_tags_tag_id", "task_tags", ["tag_id"])

    # ---------------- 用户偏好 ----------------
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("feed_token", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=True)
    op.create_index(
        "ix_user_settings_feed_token", "user_settings", ["feed_token"], unique=True
    )

    # 为已有用户预生成偏好行与订阅令牌。
    # 令牌必须逐行生成随机值（不能用 server_default）——所有人共用同一个
    # feed_token 等于任何人都能读别人的日历。
    conn = op.get_bind()
    user_ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM users"))]
    for uid in user_ids:
        conn.execute(
            sa.text(
                "INSERT INTO user_settings (user_id, data, feed_token) "
                "VALUES (:uid, '{}', :tok)"
            ),
            {"uid": uid, "tok": secrets.token_urlsafe(24)},
        )

    # ---------------- 软删除 + 提醒提前量 ----------------
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("remind_before_minutes", sa.Integer(), nullable=True)
        )
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"])

    with op.batch_alter_table("records") as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    op.create_index("ix_records_deleted_at", "records", ["deleted_at"])

    # ---------------- 查询性能索引 ----------------
    # 提醒调度器每个周期都按这三列过滤，没有索引就是每分钟一次全表扫。
    op.create_index(
        "ix_tasks_reminder_scan",
        "tasks",
        ["status", "reminder_sent_at", "due_date"],
    )
    # 任务列表最常见的组合过滤。
    op.create_index(
        "ix_tasks_user_deleted_status",
        "tasks",
        ["user_id", "deleted_at", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_user_deleted_status", table_name="tasks")
    op.drop_index("ix_tasks_reminder_scan", table_name="tasks")

    op.drop_index("ix_records_deleted_at", table_name="records")
    with op.batch_alter_table("records") as batch_op:
        batch_op.drop_column("deleted_at")

    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("remind_before_minutes")
        batch_op.drop_column("deleted_at")

    op.drop_index("ix_user_settings_feed_token", table_name="user_settings")
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")

    op.drop_index("ix_task_tags_tag_id", table_name="task_tags")
    op.drop_table("task_tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")
