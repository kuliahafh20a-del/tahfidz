"""Add participant targets and the 44-theme cohort calendar.

Revision ID: 20261023_0007
Revises: 20261022_0006
Create Date: 2026-10-23 09:00:00+07:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0007"
down_revision: str | None = "20261022_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create target constraints, validation triggers, and backfill current enrollments."""
    op.create_table(
        "targets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("theme_id", sa.Uuid(), nullable=False),
        sa.Column("initial_due_date", sa.Date(), nullable=False),
        sa.Column("effective_due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="scheduled", nullable=False),
        sa.CheckConstraint(
            "status IN ('scheduled', 'active', 'completed', 'closed')",
            name="ck_targets__status",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_targets__enrollments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["app.themes.id"],
            name="fk_targets__themes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_targets"),
        sa.UniqueConstraint(
            "enrollment_id",
            "theme_id",
            name="uq_targets__enrollment_id_theme_id",
        ),
        schema="app",
    )
    op.create_index(
        "ix_targets__enrollment_id_effective_due_date_status",
        "targets",
        ["enrollment_id", "effective_due_date", "status"],
        schema="app",
    )
    op.execute(
        """
        CREATE FUNCTION app.validate_target_curriculum()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            enrollment_curriculum uuid;
            theme_curriculum uuid;
        BEGIN
            SELECT cohort.curriculum_version_id
              INTO enrollment_curriculum
              FROM app.enrollments AS enrollment
              JOIN app.cohorts AS cohort ON cohort.id = enrollment.cohort_id
             WHERE enrollment.id = NEW.enrollment_id;

            SELECT part.curriculum_version_id
              INTO theme_curriculum
              FROM app.themes AS theme
              JOIN app.parts AS part ON part.id = theme.part_id
             WHERE theme.id = NEW.theme_id;

            IF enrollment_curriculum IS DISTINCT FROM theme_curriculum THEN
                RAISE EXCEPTION 'target theme must belong to the enrollment curriculum'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.initial_due_date IS DISTINCT FROM OLD.initial_due_date THEN
                RAISE EXCEPTION 'target initial due date is immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_targets_validate_curriculum
        BEFORE INSERT OR UPDATE OF enrollment_id, theme_id, initial_due_date ON app.targets
        FOR EACH ROW EXECUTE FUNCTION app.validate_target_curriculum()
        """
    )
    op.execute(
        """
        INSERT INTO app.targets (
            id, enrollment_id, theme_id, initial_due_date, effective_due_date, status
        )
        SELECT
            gen_random_uuid(),
            enrollment.id,
            theme.id,
            cohort.start_date + (
                (row_number() OVER (
                    PARTITION BY enrollment.id
                    ORDER BY part.sequence_no, theme.sequence_no
                ) - 1)::integer * 7
            ),
            cohort.start_date + (
                (row_number() OVER (
                    PARTITION BY enrollment.id
                    ORDER BY part.sequence_no, theme.sequence_no
                ) - 1)::integer * 7
            ),
            CASE WHEN part.sequence_no = 1 THEN 'active' ELSE 'scheduled' END
          FROM app.enrollments AS enrollment
          JOIN app.cohorts AS cohort ON cohort.id = enrollment.cohort_id
          JOIN app.parts AS part
            ON part.curriculum_version_id = cohort.curriculum_version_id
          JOIN app.themes AS theme ON theme.part_id = part.id
        ON CONFLICT (enrollment_id, theme_id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove participant target data and validation."""
    op.execute("DROP TRIGGER IF EXISTS trg_targets_validate_curriculum ON app.targets")
    op.execute("DROP FUNCTION IF EXISTS app.validate_target_curriculum()")
    op.drop_table("targets", schema="app")
