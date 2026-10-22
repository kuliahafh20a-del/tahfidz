"""Add academic video attempts and replaceable media versions.

Revision ID: 20261023_0011
Revises: 20261023_0010
Create Date: 2026-10-23 08:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0011"
down_revision: str | None = "20261023_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_attempts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_no", sa.Integer(), nullable=False),
        sa.Column("revision_no", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("cycle_no >= 1", name="ck_video_attempts__cycle_positive"),
        sa.CheckConstraint("revision_no BETWEEN 0 AND 3", name="ck_video_attempts__revision_range"),
        sa.CheckConstraint(
            "status IN ('open', 'submitted', 'under_review', 'finalized', 'closed')",
            name="ck_video_attempts__status",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_video_attempts__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["app.parts.id"],
            name="fk_video_attempts__parts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_video_attempts"),
        sa.UniqueConstraint(
            "enrollment_id",
            "part_id",
            "cycle_no",
            "revision_no",
            name="uq_video_attempts__enrollment_part_cycle_revision",
        ),
        schema="app",
    )
    op.create_index(
        "ix_video_attempts__enrollment_id_part_id_status",
        "video_attempts",
        ["enrollment_id", "part_id", "status"],
        schema="app",
    )

    op.create_table(
        "video_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=False),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="submitted", nullable=False),
        sa.CheckConstraint("version_no >= 1", name="ck_video_versions__version_positive"),
        sa.CheckConstraint("length(btrim(video_url)) > 0", name="ck_video_versions__url_not_blank"),
        sa.CheckConstraint(
            "status IN ('submitted', 'available', 'failed', 'replaced')",
            name="ck_video_versions__status",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["app.video_attempts.id"],
            name="fk_video_versions__video_attempts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_video_versions"),
        sa.UniqueConstraint(
            "attempt_id", "version_no", name="uq_video_versions__attempt_id_version_no"
        ),
        schema="app",
    )
    op.create_index(
        "ix_video_versions__attempt_id_version_no",
        "video_versions",
        ["attempt_id", "version_no"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_video_versions__attempt_id_version_no", table_name="video_versions", schema="app"
    )
    op.drop_table("video_versions", schema="app")
    op.drop_index(
        "ix_video_attempts__enrollment_id_part_id_status",
        table_name="video_attempts",
        schema="app",
    )
    op.drop_table("video_attempts", schema="app")
