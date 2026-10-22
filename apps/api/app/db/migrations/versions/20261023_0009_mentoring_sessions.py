"""Add participant proposals and mentor-managed sessions.

Revision ID: 20261023_0009
Revises: 20261023_0008
Create Date: 2026-10-23 15:00:00+07:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0009"
down_revision: str | None = "20261023_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("mentor_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="proposed", nullable=False),
        sa.Column("participant_note", sa.Text(), nullable=True),
        sa.Column("mentor_note", sa.Text(), nullable=True),
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
            "method IN ('in_person', 'video_call')",
            name="ck_sessions__method",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'scheduled', 'in_progress', 'completed', "
            "'no_show', 'cancelled')",
            name="ck_sessions__status",
        ),
        sa.CheckConstraint(
            "(status = 'proposed' AND scheduled_at IS NULL AND actual_at IS NULL) OR "
            "(status = 'scheduled' AND scheduled_at IS NOT NULL AND actual_at IS NULL) OR "
            "(status IN ('in_progress', 'completed') AND scheduled_at IS NOT NULL "
            "AND actual_at IS NOT NULL) OR "
            "(status = 'no_show' AND scheduled_at IS NOT NULL AND actual_at IS NULL) OR "
            "(status = 'cancelled' AND actual_at IS NULL)",
            name="ck_sessions__status_timestamps",
        ),
        sa.CheckConstraint(
            "participant_note IS NULL OR length(btrim(participant_note)) > 0",
            name="ck_sessions__participant_note_not_blank",
        ),
        sa.CheckConstraint(
            "mentor_note IS NULL OR length(btrim(mentor_note)) > 0",
            name="ck_sessions__mentor_note_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_sessions__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["app.parts.id"],
            name="fk_sessions__parts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["app.users.id"],
            name="fk_sessions__users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        schema="app",
    )
    op.create_index(
        "ix_sessions__mentor_id_scheduled_at_status",
        "sessions",
        ["mentor_id", "scheduled_at", "status"],
        schema="app",
    )
    op.create_index(
        "ix_sessions__enrollment_id_actual_at",
        "sessions",
        ["enrollment_id", "actual_at"],
        schema="app",
    )
    op.create_table(
        "session_themes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("theme_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["app.sessions.id"],
            name="fk_session_themes__sessions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["app.themes.id"],
            name="fk_session_themes__themes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_session_themes"),
        sa.UniqueConstraint(
            "session_id",
            "theme_id",
            name="uq_session_themes__session_id_theme_id",
        ),
        schema="app",
    )
    op.create_index(
        "ix_session_themes__theme_id",
        "session_themes",
        ["theme_id"],
        schema="app",
    )
    op.execute(
        """
        CREATE FUNCTION app.validate_session_theme()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            session_enrollment uuid;
            session_part uuid;
            theme_part uuid;
        BEGIN
            SELECT enrollment_id, part_id
              INTO session_enrollment, session_part
              FROM app.sessions
             WHERE id = NEW.session_id;
            SELECT part_id INTO theme_part FROM app.themes WHERE id = NEW.theme_id;
            IF session_part IS DISTINCT FROM theme_part THEN
                RAISE EXCEPTION 'session theme must belong to the session part'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF NOT EXISTS (
                SELECT 1
                  FROM app.targets
                 WHERE enrollment_id = session_enrollment
                   AND theme_id = NEW.theme_id
                   AND status = 'active'
            ) THEN
                RAISE EXCEPTION 'session theme must be an active participant target'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_session_themes_validate_scope
        BEFORE INSERT OR UPDATE ON app.session_themes
        FOR EACH ROW EXECUTE FUNCTION app.validate_session_theme()
        """
    )
    op.execute(
        """
        CREATE FUNCTION app.require_session_theme()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM app.session_themes WHERE session_id = NEW.id
            ) THEN
                RAISE EXCEPTION 'session must contain at least one theme'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_sessions_require_theme
        AFTER INSERT OR UPDATE ON app.sessions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION app.require_session_theme()
        """
    )
    op.execute(
        """
        CREATE FUNCTION app.keep_session_theme()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM app.sessions WHERE id = OLD.session_id)
               AND NOT EXISTS (
                   SELECT 1 FROM app.session_themes WHERE session_id = OLD.session_id
               ) THEN
                RAISE EXCEPTION 'session must contain at least one theme'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN OLD;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_session_themes_keep_one
        AFTER DELETE ON app.session_themes
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION app.keep_session_theme()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_session_themes_keep_one ON app.session_themes")
    op.execute("DROP TRIGGER IF EXISTS trg_sessions_require_theme ON app.sessions")
    op.execute("DROP TRIGGER IF EXISTS trg_session_themes_validate_scope ON app.session_themes")
    op.execute("DROP FUNCTION IF EXISTS app.keep_session_theme()")
    op.execute("DROP FUNCTION IF EXISTS app.require_session_theme()")
    op.execute("DROP FUNCTION IF EXISTS app.validate_session_theme()")
    op.drop_table("session_themes", schema="app")
    op.drop_table("sessions", schema="app")
