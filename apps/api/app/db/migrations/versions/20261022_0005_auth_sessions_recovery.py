"""Create server-side sessions, recovery capabilities, and auth rate-limit events.

Revision ID: 20261022_0005
Revises: 20261022_0004
Create Date: 2026-10-22 08:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_0005"
down_revision: str | None = "20261022_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist only hashed auth capabilities and privacy-preserving rate events."""
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("active_role", sa.String(length=32), nullable=True),
        sa.Column("active_organization_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_id", sa.Uuid(), nullable=True),
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
            "active_role IS NULL OR active_role IN "
            "('participant', 'mentor', 'lecturer', 'department_admin', 'faculty_admin')",
            name="ck_auth_sessions__active_role",
        ),
        sa.CheckConstraint(
            "(active_role IS NULL) = (active_organization_id IS NULL)",
            name="ck_auth_sessions__active_context_complete",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_sessions__expires_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_auth_sessions__users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["active_organization_id"],
            ["app.organizations.id"],
            name="fk_auth_sessions__organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rotated_from_id"],
            ["app.auth_sessions.id"],
            name="fk_auth_sessions__auth_sessions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions__token_hash"),
        schema="app",
    )
    op.create_index(
        "ix_auth_sessions__user_id_expires_at",
        "auth_sessions",
        ["user_id", "expires_at"],
        schema="app",
    )
    op.create_index(
        "ix_auth_sessions__active_token",
        "auth_sessions",
        ["token_hash", "revoked_at", "expires_at"],
        schema="app",
    )

    op.create_table(
        "password_recovery_tokens",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
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
            "expires_at > created_at",
            name="ck_password_recovery_tokens__expires_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_password_recovery_tokens__users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_recovery_tokens"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_password_recovery_tokens__token_hash",
        ),
        schema="app",
    )
    op.create_index(
        "ix_password_recovery_tokens__user_id_expires_at",
        "password_recovery_tokens",
        ["user_id", "expires_at"],
        schema="app",
    )

    op.create_table(
        "auth_rate_limit_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("identity_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("client_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('login', 'recovery', 'reset')",
            name="ck_auth_rate_limit_events__action",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_rate_limit_events"),
        schema="app",
    )
    op.create_index(
        "ix_auth_rate_limit_events__identity_window",
        "auth_rate_limit_events",
        ["action", "identity_fingerprint", "occurred_at"],
        schema="app",
    )
    op.create_index(
        "ix_auth_rate_limit_events__client_window",
        "auth_rate_limit_events",
        ["action", "client_fingerprint", "occurred_at"],
        schema="app",
    )
    op.execute(
        """
        CREATE FUNCTION app.revoke_sessions_for_inactive_user()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.account_status <> 'active'
               AND NEW.account_status IS DISTINCT FROM OLD.account_status THEN
                UPDATE app.auth_sessions
                   SET revoked_at = COALESCE(revoked_at, now()),
                       updated_at = now()
                 WHERE user_id = NEW.id
                   AND revoked_at IS NULL;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_users_revoke_sessions_on_inactive
        AFTER UPDATE OF account_status ON app.users
        FOR EACH ROW EXECUTE FUNCTION app.revoke_sessions_for_inactive_user()
        """
    )


def downgrade() -> None:
    """Remove authentication state while preserving user identities."""
    op.execute("DROP TRIGGER IF EXISTS trg_users_revoke_sessions_on_inactive ON app.users")
    op.execute("DROP FUNCTION IF EXISTS app.revoke_sessions_for_inactive_user()")
    op.drop_table("auth_rate_limit_events", schema="app")
    op.drop_table("password_recovery_tokens", schema="app")
    op.drop_table("auth_sessions", schema="app")
