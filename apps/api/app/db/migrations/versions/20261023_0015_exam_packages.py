"""Add versioned questions and lecturer exam packages.

Revision ID: 20261023_0015
Revises: 20261023_0014
Create Date: 2026-10-23 13:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261023_0015"
down_revision: str | None = "20261023_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("question_key", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("stimulus", sa.Text(), nullable=False),
        sa.Column("answer_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
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
        sa.CheckConstraint("version_no > 0", name="ck_question_versions__version_positive"),
        sa.CheckConstraint(
            "length(btrim(stimulus)) > 0", name="ck_question_versions__stimulus_not_blank"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(answer_reference) = 'object'", name="ck_question_versions__answer_object"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(scope) = 'object'", name="ck_question_versions__scope_object"
        ),
        sa.CheckConstraint(
            "source IN ('application', 'lecturer')", name="ck_question_versions__source"
        ),
        sa.CheckConstraint(
            "kind IN ('continue_verses', 'surah_order', 'recitation')",
            name="ck_question_versions__kind",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'verified', 'inactive')", name="ck_question_versions__status"
        ),
        sa.CheckConstraint(
            "(source = 'application' AND author_id IS NULL) OR "
            "(source = 'lecturer' AND author_id IS NOT NULL)",
            name="ck_question_versions__source_author",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["app.users.id"], name="fk_question_versions__users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_question_versions"),
        sa.UniqueConstraint(
            "question_key", "version_no", name="uq_question_versions__question_key_version_no"
        ),
        schema="app",
    )
    op.create_index(
        "ix_question_versions__source_status_kind",
        "question_versions",
        ["source", "status", "kind"],
        schema="app",
    )
    op.create_table(
        "exams",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("lecturer_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
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
            "notes IS NULL OR length(btrim(notes)) > 0", name="ck_exams__notes_not_blank"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'scheduled', 'in_progress', 'final', 'cancelled')",
            name="ck_exams__status",
        ),
        sa.CheckConstraint(
            "(status = 'final' AND finalized_at IS NOT NULL) OR "
            "(status <> 'final' AND finalized_at IS NULL)",
            name="ck_exams__status_finalized_at",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_exams__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lecturer_id"], ["app.users.id"], name="fk_exams__users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["app.policy_versions.id"],
            name="fk_exams__policy_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_exams"),
        schema="app",
    )
    op.create_index(
        "ix_exams__enrollment_id_status_created_at",
        "exams",
        ["enrollment_id", "status", "created_at"],
        schema="app",
    )
    op.create_table(
        "exam_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("question_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weight", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.CheckConstraint("sequence_no > 0", name="ck_exam_items__sequence_positive"),
        sa.CheckConstraint("weight IS NULL OR weight > 0", name="ck_exam_items__weight_positive"),
        sa.CheckConstraint(
            "jsonb_typeof(question_snapshot) = 'object'", name="ck_exam_items__snapshot_object"
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["app.exams.id"], name="fk_exam_items__exams", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["app.question_versions.id"],
            name="fk_exam_items__question_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_exam_items"),
        sa.UniqueConstraint("exam_id", "sequence_no", name="uq_exam_items__exam_id_sequence_no"),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("exam_items", schema="app")
    op.drop_table("exams", schema="app")
    op.drop_table("question_versions", schema="app")
