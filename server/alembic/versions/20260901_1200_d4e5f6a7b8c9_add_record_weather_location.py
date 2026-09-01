"""records.weather / records.location（日记天气与位置）

为日记类记录补充天气与位置上下文，让记录更贴近 Day One / Journey
等成熟日记应用的「时间 + 地点 + 氛围」元信息结构。

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-01 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "records", sa.Column("weather", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "records", sa.Column("location", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("records", "location")
    op.drop_column("records", "weather")
