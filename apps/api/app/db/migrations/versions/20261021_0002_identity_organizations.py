"""Create identity and organization models with database-enforced scope rules.

Revision ID: 20261021_0002
Revises: 20261021_0001
Create Date: 2026-10-21 00:30:00+00:00
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_0002"
down_revision: str | None = "20261021_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SAMPLE_FACULTY_ID = UUID("10000000-0000-4000-8000-000000000001")
SAMPLE_DEPARTMENT_ID = UUID("10000000-0000-4000-8000-000000000002")


def upgrade() -> None:
    """Create identity tables, integrity triggers, indexes, and sample organizations."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    organizations = op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('faculty', 'department')",
            name="ck_organizations__kind",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organizations__status",
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_organizations__parent_not_self",
        ),
        sa.CheckConstraint(
            "(kind = 'faculty' AND parent_id IS NULL) "
            "OR (kind = 'department' AND parent_id IS NOT NULL)",
            name="ck_organizations__kind_parent_shape",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_organizations__name_not_blank",
        ),
        sa.CheckConstraint(
            "code IS NULL OR length(btrim(code)) > 0",
            name="ck_organizations__code_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["app.organizations.id"],
            name="fk_organizations__organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        schema="app",
    )
    op.create_index(
        "ix_organizations__parent_id",
        "organizations",
        ["parent_id"],
        schema="app",
    )
    op.create_index(
        "ix_organizations__kind",
        "organizations",
        ["kind"],
        schema="app",
    )
    op.create_index(
        "ix_organizations__status",
        "organizations",
        ["status"],
        schema="app",
    )
    op.create_index(
        "uq_organizations__parent_id_code",
        "organizations",
        ["parent_id", "code"],
        unique=True,
        schema="app",
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("code IS NOT NULL"),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("login_identifier", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "account_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("password_hash", sa.String(length=512), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "account_status IN ('pending', 'active', 'inactive', 'locked')",
            name="ck_users__account_status",
        ),
        sa.CheckConstraint(
            "length(btrim(login_identifier)) > 0",
            name="ck_users__login_identifier_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_users__name_not_blank",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        schema="app",
    )
    op.create_index(
        "uq_users__login_identifier_ci",
        "users",
        [sa.text("lower(login_identifier)")],
        unique=True,
        schema="app",
    )

    op.create_table(
        "role_grants",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('participant', 'mentor', 'lecturer', 'department_admin', 'faculty_admin')",
            name="ck_role_grants__role",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_role_grants__valid_period",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["app.organizations.id"],
            name="fk_role_grants__organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_role_grants__users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_role_grants"),
        schema="app",
    )
    op.create_index(
        "ix_role_grants__active_scope",
        "role_grants",
        ["user_id", "role", "organization_id", "valid_to"],
        schema="app",
    )
    op.execute(
        """
        ALTER TABLE app.role_grants
        ADD CONSTRAINT ex_role_grants__overlapping_scope
        EXCLUDE USING gist (
            user_id WITH =,
            role WITH =,
            organization_id WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        )
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.enforce_organization_hierarchy()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            parent_kind text;
            would_cycle boolean;
        BEGIN
            IF NEW.parent_id = NEW.id THEN
                RAISE EXCEPTION 'organization cannot be its own parent'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.kind = 'faculty' AND NEW.parent_id IS NOT NULL THEN
                RAISE EXCEPTION 'faculty organization cannot have a parent'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.kind = 'department' AND NEW.parent_id IS NULL THEN
                RAISE EXCEPTION 'department organization requires a faculty parent'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.parent_id IS NOT NULL THEN
                SELECT kind
                  INTO parent_kind
                  FROM app.organizations
                 WHERE id = NEW.parent_id;

                IF parent_kind IS NULL THEN
                    RAISE EXCEPTION 'parent organization does not exist'
                        USING ERRCODE = 'foreign_key_violation';
                END IF;

                IF parent_kind <> 'faculty' THEN
                    RAISE EXCEPTION 'department parent must be a faculty'
                        USING ERRCODE = 'check_violation';
                END IF;

                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id
                      FROM app.organizations
                     WHERE id = NEW.parent_id
                    UNION ALL
                    SELECT organization.id, organization.parent_id
                      FROM app.organizations AS organization
                      JOIN ancestors ON organization.id = ancestors.parent_id
                )
                SELECT EXISTS (SELECT 1 FROM ancestors WHERE id = NEW.id)
                  INTO would_cycle;

                IF would_cycle THEN
                    RAISE EXCEPTION 'organization hierarchy cannot contain a cycle'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            IF TG_OP = 'UPDATE' AND NEW.kind IS DISTINCT FROM OLD.kind THEN
                IF EXISTS (
                    SELECT 1 FROM app.organizations WHERE parent_id = NEW.id
                ) THEN
                    RAISE EXCEPTION 'organization kind cannot change while it has children'
                        USING ERRCODE = 'check_violation';
                END IF;

                IF EXISTS (
                    SELECT 1
                      FROM app.role_grants
                     WHERE organization_id = NEW.id
                       AND (
                           (role = 'faculty_admin' AND NEW.kind <> 'faculty')
                           OR (role = 'department_admin' AND NEW.kind <> 'department')
                       )
                ) THEN
                    RAISE EXCEPTION 'organization kind conflicts with an existing admin grant'
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
        CREATE TRIGGER trg_organizations_enforce_hierarchy
        BEFORE INSERT OR UPDATE OF id, parent_id, kind
        ON app.organizations
        FOR EACH ROW
        EXECUTE FUNCTION app.enforce_organization_hierarchy()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.enforce_admin_role_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            organization_kind text;
        BEGIN
            SELECT kind
              INTO organization_kind
              FROM app.organizations
             WHERE id = NEW.organization_id;

            IF organization_kind IS NULL THEN
                RAISE EXCEPTION 'role grant organization does not exist'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.role = 'faculty_admin' AND organization_kind <> 'faculty' THEN
                RAISE EXCEPTION 'faculty_admin requires a faculty organization'
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.role = 'department_admin' AND organization_kind <> 'department' THEN
                RAISE EXCEPTION 'department_admin requires a department organization'
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_role_grants_enforce_admin_scope
        BEFORE INSERT OR UPDATE OF organization_id, role
        ON app.role_grants
        FOR EACH ROW
        EXECUTE FUNCTION app.enforce_admin_role_scope()
        """
    )

    op.bulk_insert(
        organizations,
        [
            {
                "id": SAMPLE_FACULTY_ID,
                "parent_id": None,
                "kind": "faculty",
                "name": "Fakultas Contoh",
                "code": "FACULTY-SAMPLE",
                "status": "active",
            },
            {
                "id": SAMPLE_DEPARTMENT_ID,
                "parent_id": SAMPLE_FACULTY_ID,
                "kind": "department",
                "name": "Jurusan Contoh",
                "code": "DEPARTMENT-SAMPLE",
                "status": "active",
            },
        ],
    )


def downgrade() -> None:
    """Remove identity tables and their schema-local integrity functions."""
    op.execute("DROP TRIGGER IF EXISTS trg_role_grants_enforce_admin_scope ON app.role_grants")
    op.execute("DROP FUNCTION IF EXISTS app.enforce_admin_role_scope()")
    op.execute("DROP TRIGGER IF EXISTS trg_organizations_enforce_hierarchy ON app.organizations")
    op.execute("DROP FUNCTION IF EXISTS app.enforce_organization_hierarchy()")
    op.drop_table("role_grants", schema="app")
    op.drop_table("users", schema="app")
    op.drop_table("organizations", schema="app")
