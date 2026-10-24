"""Realign simulated progress with the An-Nas-to-An-Naba theme order.

Revision ID: 20261024_0019
Revises: 20261024_0018
Create Date: 2026-10-24 18:30:00+07:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261024_0019"
down_revision: str | None = "20261024_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Preserve progress counts while moving simulated work onto the new order."""
    op.execute(
        """
        CREATE TEMP TABLE demo_theme_order ON COMMIT DROP AS
        SELECT
            theme.id AS theme_id,
            theme.part_id,
            row_number() OVER (
                ORDER BY max(theme_range.surah_no) DESC,
                         min(theme_range.surah_no) DESC,
                         min(theme_range.ayah_start) ASC
            )::integer AS ordinal
        FROM app.themes AS theme
        JOIN app.theme_ranges AS theme_range ON theme_range.theme_id = theme.id
        GROUP BY theme.id, theme.part_id;

        CREATE UNIQUE INDEX uq_demo_theme_order_ordinal
            ON demo_theme_order (ordinal);

        CREATE TEMP TABLE demo_enrollment_progress ON COMMIT DROP AS
        SELECT enrollment.id AS enrollment_id,
               count(target.id) FILTER (WHERE target.status = 'completed')::integer
                   AS completed_count,
               cohort.start_date
        FROM app.enrollments AS enrollment
        JOIN app.cohorts AS cohort ON cohort.id = enrollment.cohort_id
        JOIN app.targets AS target ON target.enrollment_id = enrollment.id
        GROUP BY enrollment.id, cohort.start_date;
        """
    )

    op.execute("ALTER TABLE app.targets DISABLE TRIGGER trg_targets_validate_curriculum")
    op.execute(
        "ALTER TABLE app.targets DISABLE TRIGGER trg_targets_require_approved_deadline_change"
    )
    op.execute(
        """
        UPDATE app.targets AS target
           SET initial_due_date = progress.start_date + ((theme_order.ordinal - 1) * 7),
               effective_due_date = progress.start_date + ((theme_order.ordinal - 1) * 7),
               status = CASE
                   WHEN theme_order.ordinal <= progress.completed_count THEN 'completed'
                   WHEN theme_order.ordinal = progress.completed_count + 1 THEN 'active'
                   ELSE 'scheduled'
               END
          FROM demo_theme_order AS theme_order,
               demo_enrollment_progress AS progress
         WHERE target.theme_id = theme_order.theme_id
           AND target.enrollment_id = progress.enrollment_id
        """
    )
    op.execute("ALTER TABLE app.targets ENABLE TRIGGER trg_targets_validate_curriculum")
    op.execute(
        "ALTER TABLE app.targets ENABLE TRIGGER trg_targets_require_approved_deadline_change"
    )

    op.execute(
        """
        CREATE TEMP TABLE demo_session_order ON COMMIT DROP AS
        SELECT
            session.id AS session_id,
            row_number() OVER (
                PARTITION BY session.enrollment_id
                ORDER BY
                    CASE session.status
                        WHEN 'completed' THEN 1
                        WHEN 'in_progress' THEN 2
                        WHEN 'scheduled' THEN 3
                        WHEN 'proposed' THEN 4
                        ELSE 5
                    END,
                    coalesce(session.actual_at, session.scheduled_at, session.proposed_at),
                    session.id
            )::integer AS ordinal
        FROM app.sessions AS session
        WHERE session.status IN ('completed', 'in_progress', 'scheduled', 'proposed');
        """
    )
    op.execute("ALTER TABLE app.sessions DISABLE TRIGGER USER")
    op.execute("ALTER TABLE app.session_themes DISABLE TRIGGER USER")
    op.execute(
        """
        UPDATE app.sessions AS session
           SET part_id = theme_order.part_id
          FROM demo_session_order AS session_order
          JOIN demo_theme_order AS theme_order
            ON theme_order.ordinal = session_order.ordinal
         WHERE session.id = session_order.session_id;

        UPDATE app.session_themes AS session_theme
           SET theme_id = theme_order.theme_id
          FROM demo_session_order AS session_order
          JOIN demo_theme_order AS theme_order
            ON theme_order.ordinal = session_order.ordinal
         WHERE session_theme.session_id = session_order.session_id;
        """
    )
    op.execute("ALTER TABLE app.session_themes ENABLE TRIGGER USER")
    op.execute("ALTER TABLE app.sessions ENABLE TRIGGER USER")


def downgrade() -> None:
    """Historical simulation assignments cannot be reconstructed safely."""
    raise RuntimeError("the demo-progress realignment is irreversible")
