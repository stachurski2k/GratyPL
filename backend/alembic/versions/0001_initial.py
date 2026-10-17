"""initial schema: reports, report_photos, weekly_summaries

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text()),
        sa.Column("has_plates", sa.Boolean()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("source IN ('web', 'seed')", name="ck_reports_source"),
    )
    op.create_index("ix_reports_location", "reports", ["location"], postgresql_using="gist")
    op.create_index("ix_reports_created_at_id", "reports", ["created_at", "id"])

    op.create_table(
        "report_photos",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "report_id",
            sa.UUID(),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("thumb_path", sa.Text(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_report_photos_report_id", "report_photos", ["report_id"])

    op.create_table(
        "weekly_summaries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False, unique=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("report_count", sa.Integer(), nullable=False),
        sa.Column("bbox", postgresql.JSONB()),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_weekly_summaries_generated_at_id", "weekly_summaries", ["generated_at", "id"]
    )


def downgrade() -> None:
    op.drop_table("weekly_summaries")
    op.drop_table("report_photos")
    op.drop_table("reports")
