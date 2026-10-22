"""Create department cohorts, enrollments, and assignment history.

Revision ID: 20261022_0004
Revises: 20261021_0003
Create Date: 2026-10-22 02:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_0004"
down_revision: str | None = "20261021_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def create_program_tables() -> None:
    """Create program ownership and non-destructive assignment records."""
    op.create_table(
        "cohorts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'closed', 'archived')",
            name="ck_cohorts__status",
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_cohorts__name_not_blank"),
        sa.CheckConstraint(
            "close_date IS NULL OR close_date >= start_date",
            name="ck_cohorts__date_order",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["app.organizations.id"],
            name="fk_cohorts__organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["app.curriculum_versions.id"],
            name="fk_cohorts__curriculum_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["app.policy_versions.id"],
            name="fk_cohorts__policy_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cohorts"),
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="uq_cohorts__organization_id_name",
        ),
        schema="app",
    )
    op.create_index(
        "ix_cohorts__organization_id_status",
        "cohorts",
        ["organization_id", "status"],
        schema="app",
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.Column("nim_snapshot", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            "status IN ('active', 'completed', 'withdrawn', 'inactive')",
            name="ck_enrollments__status",
        ),
        sa.CheckConstraint(
            "length(btrim(nim_snapshot)) > 0",
            name="ck_enrollments__nim_not_blank",
        ),
        sa.CheckConstraint(
            "nim_snapshot = upper(btrim(nim_snapshot))",
            name="ck_enrollments__nim_canonical",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_enrollments__users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"],
            ["app.cohorts.id"],
            name="fk_enrollments__cohorts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_enrollments"),
        sa.UniqueConstraint(
            "user_id",
            "cohort_id",
            name="uq_enrollments__user_id_cohort_id",
        ),
        sa.UniqueConstraint(
            "cohort_id",
            "nim_snapshot",
            name="uq_enrollments__cohort_id_nim_snapshot",
        ),
        schema="app",
    )
    op.create_index(
        "ix_enrollments__cohort_id_status",
        "enrollments",
        ["cohort_id", "status"],
        schema="app",
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("staff_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
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
            "role IN ('mentor', 'lecturer')",
            name="ck_assignments__role",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_assignments__valid_period",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["app.enrollments.id"],
            name="fk_assignments__enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["app.users.id"],
            name="fk_assignments__users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assignments"),
        schema="app",
    )
    op.create_index(
        "ix_assignments__enrollment_id_role_valid_to",
        "assignments",
        ["enrollment_id", "role", "valid_to"],
        schema="app",
    )
    op.execute(
        """
        ALTER TABLE app.assignments
        ADD CONSTRAINT ex_assignments__overlapping_role
        EXCLUDE USING gist (
            enrollment_id WITH =,
            role WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        )
        """
    )


def create_program_triggers() -> None:
    """Enforce department ownership, publish readiness, and staff capacity."""
    op.execute(
        """
        CREATE FUNCTION app.enforce_cohort_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            organization_kind text;
            organization_status text;
            curriculum_status text;
            policy_status text;
        BEGIN
            SELECT kind, status
              INTO organization_kind, organization_status
              FROM app.organizations
             WHERE id = NEW.organization_id;

            IF organization_kind IS NULL THEN
                RAISE EXCEPTION 'cohort organization does not exist'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
            IF organization_kind <> 'department' THEN
                RAISE EXCEPTION 'cohort organization must be a department'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.status = 'active' THEN
                IF organization_status <> 'active' THEN
                    RAISE EXCEPTION 'active cohort requires an active department'
                        USING ERRCODE = 'check_violation';
                END IF;

                SELECT status INTO curriculum_status
                  FROM app.curriculum_versions
                 WHERE id = NEW.curriculum_version_id;
                SELECT status INTO policy_status
                  FROM app.policy_versions
                 WHERE id = NEW.policy_version_id;

                IF curriculum_status IS DISTINCT FROM 'published'
                   OR policy_status IS DISTINCT FROM 'published' THEN
                    RAISE EXCEPTION 'active cohort requires published curriculum and policy'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_cohorts_enforce_scope
        BEFORE INSERT OR UPDATE OF organization_id, curriculum_version_id, policy_version_id, status
        ON app.cohorts
        FOR EACH ROW EXECUTE FUNCTION app.enforce_cohort_scope()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.prevent_cohort_organization_kind_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.kind IS DISTINCT FROM OLD.kind
               AND EXISTS (SELECT 1 FROM app.cohorts WHERE organization_id = NEW.id) THEN
                RAISE EXCEPTION 'organization kind cannot change while cohorts reference it'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_organizations_protect_cohort_scope
        BEFORE UPDATE OF kind ON app.organizations
        FOR EACH ROW EXECUTE FUNCTION app.prevent_cohort_organization_kind_change()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.enforce_assignment_role_grant()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            department_id uuid;
            participant_id uuid;
        BEGIN
            SELECT cohort.organization_id, enrollment.user_id
              INTO department_id, participant_id
              FROM app.enrollments AS enrollment
              JOIN app.cohorts AS cohort ON cohort.id = enrollment.cohort_id
             WHERE enrollment.id = NEW.enrollment_id;

            IF department_id IS NULL THEN
                RAISE EXCEPTION 'assignment enrollment does not exist'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
            IF participant_id = NEW.staff_id THEN
                RAISE EXCEPTION 'participant cannot be assigned to themselves'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                  FROM app.role_grants AS role_grant
                 WHERE role_grant.user_id = NEW.staff_id
                   AND role_grant.organization_id = department_id
                   AND role_grant.role = NEW.role
                   AND role_grant.valid_from <= NEW.valid_from
                   AND (
                        role_grant.valid_to IS NULL
                        OR (
                            NEW.valid_to IS NOT NULL
                            AND role_grant.valid_to >= NEW.valid_to
                        )
                   )
            ) THEN
                RAISE EXCEPTION 'staff role grant does not cover assignment scope and interval'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_assignments_enforce_role_grant
        BEFORE INSERT OR UPDATE OF enrollment_id, staff_id, role, valid_from, valid_to
        ON app.assignments
        FOR EACH ROW EXECUTE FUNCTION app.enforce_assignment_role_grant()
        """
    )


def upgrade() -> None:
    """Create cohort, enrollment, and assignment storage and safeguards."""
    create_program_tables()
    create_program_triggers()


def downgrade() -> None:
    """Remove program records and schema-local validation functions."""
    op.execute("DROP TRIGGER IF EXISTS trg_assignments_enforce_role_grant ON app.assignments")
    op.execute("DROP FUNCTION IF EXISTS app.enforce_assignment_role_grant()")
    op.execute("DROP TRIGGER IF EXISTS trg_organizations_protect_cohort_scope ON app.organizations")
    op.execute("DROP FUNCTION IF EXISTS app.prevent_cohort_organization_kind_change()")
    op.execute("DROP TRIGGER IF EXISTS trg_cohorts_enforce_scope ON app.cohorts")
    op.execute("DROP FUNCTION IF EXISTS app.enforce_cohort_scope()")
    op.drop_table("assignments", schema="app")
    op.drop_table("enrollments", schema="app")
    op.drop_table("cohorts", schema="app")
