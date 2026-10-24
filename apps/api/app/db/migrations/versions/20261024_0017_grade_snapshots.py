"""Add immutable grade snapshots and assessment provenance.

Revision ID: 20261024_0017
Revises: 20261023_0016
Create Date: 2026-10-24 09:00:00+07:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261024_0017"
down_revision: str | None = "20261023_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grade_snapshots",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("k_value", sa.Numeric(6, 3), nullable=True),
        sa.Column("m_value", sa.Numeric(6, 3), nullable=True),
        sa.Column("d_value", sa.Numeric(6, 3), nullable=True),
        sa.Column("n_value", sa.Numeric(6, 3), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "k_value IS NULL OR k_value BETWEEN 1 AND 10", name="ck_grade_snapshots__k_range"
        ),
        sa.CheckConstraint(
            "m_value IS NULL OR m_value BETWEEN 1 AND 10", name="ck_grade_snapshots__m_range"
        ),
        sa.CheckConstraint(
            "d_value IS NULL OR d_value BETWEEN 1 AND 10", name="ck_grade_snapshots__d_range"
        ),
        sa.CheckConstraint(
            "n_value IS NULL OR n_value BETWEEN 1 AND 10", name="ck_grade_snapshots__n_range"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_context) = 'object'",
            name="ck_grade_snapshots__source_context_object",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_grade_snapshots__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["app.policy_versions.id"],
            name="fk_grade_snapshots__policy_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["app.grade_snapshots.id"],
            name="fk_grade_snapshots__grade_snapshots",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grade_snapshots"),
        schema="app",
    )
    op.create_index(
        "ix_grade_snapshots__enrollment_id_calculated_at",
        "grade_snapshots",
        ["enrollment_id", "calculated_at"],
        schema="app",
    )
    op.create_table(
        "grade_sources",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("grade_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("component", sa.String(length=1), nullable=False),
        sa.Column("contribution", sa.Numeric(8, 4), nullable=True),
        sa.CheckConstraint("component IN ('M', 'D')", name="ck_grade_sources__component"),
        sa.CheckConstraint(
            "contribution IS NULL OR contribution BETWEEN 0 AND 10",
            name="ck_grade_sources__contribution_range",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["app.assessment_records.id"],
            name="fk_grade_sources__assessment_records",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["grade_snapshot_id"],
            ["app.grade_snapshots.id"],
            name="fk_grade_sources__grade_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grade_sources"),
        sa.UniqueConstraint(
            "grade_snapshot_id",
            "assessment_id",
            "component",
            name="uq_grade_sources__snapshot_assessment_component",
        ),
        schema="app",
    )
    op.execute("""
        CREATE FUNCTION app.validate_grade_source() RETURNS trigger AS $$
        DECLARE source_enrollment uuid; snapshot_enrollment uuid; source_status text;
        BEGIN
          SELECT enrollment_id, status INTO source_enrollment, source_status
            FROM app.assessment_records WHERE id = NEW.assessment_id;
          SELECT enrollment_id INTO snapshot_enrollment
            FROM app.grade_snapshots WHERE id = NEW.grade_snapshot_id;
          IF source_enrollment IS DISTINCT FROM snapshot_enrollment OR source_status <> 'final' THEN
            RAISE EXCEPTION 'grade source must be final and belong to snapshot enrollment';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        CREATE CONSTRAINT TRIGGER trg_grade_sources_validate
          AFTER INSERT OR UPDATE ON app.grade_sources DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION app.validate_grade_source();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_grade_sources_validate ON app.grade_sources")
    op.execute("DROP FUNCTION IF EXISTS app.validate_grade_source()")
    op.drop_table("grade_sources", schema="app")
    op.drop_index(
        "ix_grade_snapshots__enrollment_id_calculated_at",
        table_name="grade_snapshots",
        schema="app",
    )
    op.drop_table("grade_snapshots", schema="app")
