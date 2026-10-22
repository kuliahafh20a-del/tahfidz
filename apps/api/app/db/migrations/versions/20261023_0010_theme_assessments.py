"""Add end-to-end theme assessment records.

Revision ID: 20261023_0010
Revises: 20261023_0009
Create Date: 2026-10-23 06:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0010"
down_revision: str | None = "20261023_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_records",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("assessor_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("actual_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("manual_score", sa.Numeric(precision=4, scale=2), nullable=True),
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
            "kind IN ('theme', 'video', 'exam')", name="ck_assessment_records__kind"
        ),
        sa.CheckConstraint(
            "manual_score IS NULL OR (manual_score BETWEEN 1 AND 10 "
            "AND manual_score = trunc(manual_score))",
            name="ck_assessment_records__manual_score_integer_range",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'final', 'superseded', 'needs_review')",
            name="ck_assessment_records__status",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND finalized_at IS NULL) OR "
            "(status IN ('final', 'superseded', 'needs_review') AND finalized_at IS NOT NULL)",
            name="ck_assessment_records__status_finalized_at",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_assessment_records__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assessor_id"],
            ["app.users.id"],
            name="fk_assessment_records__users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["app.policy_versions.id"],
            name="fk_assessment_records__policy_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_records"),
        schema="app",
    )
    op.create_index(
        "ix_assessment_records__enrollment_id_kind_status_finalized_at",
        "assessment_records",
        ["enrollment_id", "kind", "status", "finalized_at"],
        schema="app",
    )

    op.create_table(
        "theme_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_theme_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_no", sa.SmallInteger(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "attempt_no BETWEEN 1 AND 5", name="ck_theme_assessments__attempt_range"
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('enough', 'repeat', 'follow_up')",
            name="ck_theme_assessments__outcome",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_theme_assessments__notes_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["app.assessment_records.id"],
            name="fk_theme_assessments__assessment_records",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_theme_id"],
            ["app.session_themes.id"],
            name="fk_theme_assessments__session_themes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_theme_assessments"),
        sa.UniqueConstraint("session_theme_id", name="uq_theme_assessments__session_theme_id"),
        schema="app",
    )
    op.create_index(
        "ix_theme_assessments__session_theme_id_attempt_no",
        "theme_assessments",
        ["session_theme_id", "attempt_no"],
        schema="app",
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("location_text", sa.Text(), nullable=False),
        sa.Column("video_second", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("assistance_type", sa.String(length=16), server_default="none", nullable=False),
        sa.Column("self_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("counted", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("count_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "assistance_type IN ('none', 'cue', 'answer')",
            name="ck_incidents__assistance_type",
        ),
        sa.CheckConstraint("length(btrim(category)) > 0", name="ck_incidents__category_not_blank"),
        sa.CheckConstraint(
            "length(btrim(location_text)) > 0", name="ck_incidents__location_not_blank"
        ),
        sa.CheckConstraint(
            "context IS NULL OR length(btrim(context)) > 0",
            name="ck_incidents__context_not_blank",
        ),
        sa.CheckConstraint(
            "video_second IS NULL OR video_second >= 0",
            name="ck_incidents__video_second_nonnegative",
        ),
        sa.CheckConstraint(
            "count_reason IS NULL OR length(btrim(count_reason)) > 0",
            name="ck_incidents__count_reason_not_blank",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_incidents__notes_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["app.assessment_records.id"],
            name="fk_incidents__assessment_records",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        schema="app",
    )
    op.create_index(
        "ix_incidents__assessment_id_counted",
        "incidents",
        ["assessment_id", "counted"],
        schema="app",
    )

    op.execute(
        """
        CREATE FUNCTION app.require_theme_assessment_subtype()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
          IF NEW.kind = 'theme' AND (
            SELECT count(*) FROM app.theme_assessments WHERE id = NEW.id
          ) <> 1 THEN
            RAISE EXCEPTION 'theme assessment % must have exactly one theme subtype', NEW.id;
          END IF;
          RETURN NEW;
        END
        $function$;

        CREATE CONSTRAINT TRIGGER assessment_records_require_theme_subtype
        AFTER INSERT OR UPDATE OF kind ON app.assessment_records
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION app.require_theme_assessment_subtype();

        CREATE FUNCTION app.validate_theme_assessment_subtype()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
          parent_kind text;
          parent_enrollment uuid;
          session_enrollment uuid;
          subtype_id uuid := COALESCE(NEW.id, OLD.id);
        BEGIN
          SELECT kind, enrollment_id
          INTO parent_kind, parent_enrollment
          FROM app.assessment_records
          WHERE id = subtype_id;

          IF parent_kind IS NULL THEN
            RETURN COALESCE(NEW, OLD);
          END IF;
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'theme assessment % must retain its theme subtype', subtype_id;
          END IF;
          IF parent_kind <> 'theme' THEN
            RAISE EXCEPTION 'theme subtype % requires kind theme', subtype_id;
          END IF;

          SELECT s.enrollment_id
          INTO session_enrollment
          FROM app.session_themes st
          JOIN app.sessions s ON s.id = st.session_id
          WHERE st.id = NEW.session_theme_id;
          IF session_enrollment IS DISTINCT FROM parent_enrollment THEN
            RAISE EXCEPTION 'assessment enrollment must match session enrollment';
          END IF;
          RETURN NEW;
        END
        $function$;

        CREATE CONSTRAINT TRIGGER theme_assessments_validate_subtype
        AFTER INSERT OR UPDATE OR DELETE ON app.theme_assessments
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION app.validate_theme_assessment_subtype();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS theme_assessments_validate_subtype ON app.theme_assessments")
    op.execute("DROP FUNCTION IF EXISTS app.validate_theme_assessment_subtype()")
    op.execute(
        "DROP TRIGGER IF EXISTS assessment_records_require_theme_subtype ON app.assessment_records"
    )
    op.execute("DROP FUNCTION IF EXISTS app.require_theme_assessment_subtype()")
    op.drop_index("ix_incidents__assessment_id_counted", table_name="incidents", schema="app")
    op.drop_table("incidents", schema="app")
    op.drop_index(
        "ix_theme_assessments__session_theme_id_attempt_no",
        table_name="theme_assessments",
        schema="app",
    )
    op.drop_table("theme_assessments", schema="app")
    op.drop_index(
        "ix_assessment_records__enrollment_id_kind_status_finalized_at",
        table_name="assessment_records",
        schema="app",
    )
    op.drop_table("assessment_records", schema="app")
