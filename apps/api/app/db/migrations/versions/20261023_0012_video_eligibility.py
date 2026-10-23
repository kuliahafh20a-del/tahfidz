"""Add versioned technical video eligibility reviews.

Revision ID: 20261023_0012
Revises: 20261023_0011
Create Date: 2026-10-23 09:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0012"
down_revision: str | None = "20261023_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eligibility_reviews",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("video_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_version", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "length(btrim(checklist_version)) > 0",
            name="ck_eligibility_reviews__checklist_version_not_blank",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('eligible', 'ineligible')",
            name="ck_eligibility_reviews__decision",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'final', 'superseded')",
            name="ck_eligibility_reviews__status",
        ),
        sa.CheckConstraint(
            "status <> 'final' OR decision <> 'ineligible' OR "
            "(reason IS NOT NULL AND length(btrim(reason)) > 0)",
            name="ck_eligibility_reviews__ineligible_reason_required",
        ),
        sa.CheckConstraint(
            "status <> 'final' OR decision IS NOT NULL",
            name="ck_eligibility_reviews__final_decision_required",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND finalized_at IS NULL) OR "
            "(status IN ('final', 'superseded') AND finalized_at IS NOT NULL)",
            name="ck_eligibility_reviews__status_finalized_at",
        ),
        sa.ForeignKeyConstraint(
            ["video_version_id"],
            ["app.video_versions.id"],
            name="fk_eligibility_reviews__video_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["app.users.id"],
            name="fk_eligibility_reviews__users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eligibility_reviews"),
        schema="app",
    )
    op.create_index(
        "ix_eligibility_reviews__video_version_id_status_finalized_at",
        "eligibility_reviews",
        ["video_version_id", "status", "finalized_at"],
        schema="app",
    )
    op.create_index(
        "uq_eligibility_reviews__active_video_version",
        "eligibility_reviews",
        ["video_version_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("status <> 'superseded'"),
    )

    op.create_table(
        "eligibility_checks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_code", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "length(btrim(criterion_code)) > 0",
            name="ck_eligibility_checks__criterion_code_not_blank",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_eligibility_checks__notes_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["app.eligibility_reviews.id"],
            name="fk_eligibility_checks__eligibility_reviews",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eligibility_checks"),
        sa.UniqueConstraint(
            "review_id",
            "criterion_code",
            name="uq_eligibility_checks__review_id_criterion_code",
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("eligibility_checks", schema="app")
    op.drop_index(
        "uq_eligibility_reviews__active_video_version",
        table_name="eligibility_reviews",
        schema="app",
    )
    op.drop_index(
        "ix_eligibility_reviews__video_version_id_status_finalized_at",
        table_name="eligibility_reviews",
        schema="app",
    )
    op.drop_table("eligibility_reviews", schema="app")
