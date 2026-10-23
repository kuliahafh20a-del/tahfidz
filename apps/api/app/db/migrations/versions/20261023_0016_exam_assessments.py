"""Add per-item exam assessments and final exam evidence.

Revision ID: 20261023_0016
Revises: 20261023_0015
Create Date: 2026-10-23 17:00:00+07:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261023_0016"
down_revision: str | None = "20261023_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("d_score", sa.Numeric(6, 3), nullable=True), schema="app")
    op.add_column(
        "exams",
        sa.Column(
            "evidence_media_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema="app",
    )
    op.create_check_constraint(
        "d_score_range",
        "exams",
        "d_score IS NULL OR d_score BETWEEN 1 AND 10",
        schema="app",
    )
    op.create_check_constraint(
        "evidence_media_ids_array",
        "exams",
        "jsonb_typeof(evidence_media_ids) = 'array'",
        schema="app",
    )
    op.create_table(
        "exam_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_item_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_exam_assessments__notes_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["app.assessment_records.id"],
            name="fk_exam_assessments__assessment_records",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exam_item_id"],
            ["app.exam_items.id"],
            name="fk_exam_assessments__exam_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_exam_assessments"),
        sa.UniqueConstraint("exam_item_id", name="uq_exam_assessments__exam_item_id"),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("exam_assessments", schema="app")
    op.drop_constraint("ck_exams__evidence_media_ids_array", "exams", schema="app")
    op.drop_constraint("ck_exams__d_score_range", "exams", schema="app")
    op.drop_column("exams", "evidence_media_ids", schema="app")
    op.drop_column("exams", "d_score", schema="app")
