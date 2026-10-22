"""Add controlled deadline changes and audit history.

Revision ID: 20261023_0008
Revises: 20261023_0007
Create Date: 2026-10-23 12:00:00+07:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261023_0008"
down_revision: str | None = "20261023_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cohorts",
        sa.Column("calendar_version", sa.Integer(), server_default="1", nullable=False),
        schema="app",
    )
    op.create_table(
        "deadline_changes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("old_date", sa.Date(), nullable=False),
        sa.Column("new_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("impact_note", sa.Text(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("new_date <> old_date", name="ck_deadline_changes__date_changed"),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0", name="ck_deadline_changes__reason_not_blank"
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND approved_by IS NULL AND decided_at IS NULL) OR "
            "(status IN ('approved', 'rejected') AND approved_by IS NOT NULL "
            "AND decided_at IS NOT NULL) OR status = 'cancelled'",
            name="ck_deadline_changes__decision_complete",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_deadline_changes__status",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["app.targets.id"],
            name="fk_deadline_changes__targets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["app.users.id"],
            name="fk_deadline_changes__requesters",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["app.users.id"],
            name="fk_deadline_changes__approvers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deadline_changes"),
        schema="app",
    )
    op.create_index(
        "ix_deadline_changes__target_id_status",
        "deadline_changes",
        ["target_id", "status"],
        schema="app",
    )
    op.create_index(
        "uq_deadline_changes__pending_target",
        "deadline_changes",
        ["target_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_reference", sa.String(length=200), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["app.users.id"], name="fk_audit_events__users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        schema="app",
    )
    op.create_index(
        "ix_audit_events__object_type_reference_occurred_at",
        "audit_events",
        ["object_type", "object_reference", "occurred_at"],
        schema="app",
    )
    op.create_index(
        "ix_audit_events__actor_id_occurred_at",
        "audit_events",
        ["actor_id", "occurred_at"],
        schema="app",
    )
    op.execute(
        """
        CREATE FUNCTION app.require_approved_deadline_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            change_id uuid;
            valid_change boolean;
        BEGIN
            IF NEW.effective_due_date IS NOT DISTINCT FROM OLD.effective_due_date THEN
                RETURN NEW;
            END IF;
            change_id := nullif(current_setting('app.deadline_change_id', true), '')::uuid;
            SELECT EXISTS (
                SELECT 1 FROM app.deadline_changes AS change
                 WHERE change.id = change_id
                   AND change.target_id = NEW.id
                   AND change.old_date = OLD.effective_due_date
                   AND change.new_date = NEW.effective_due_date
                   AND change.status = 'approved'
            ) INTO valid_change;
            IF valid_change IS NOT TRUE THEN
                RAISE EXCEPTION 'effective deadline requires an approved deadline change'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_targets_require_approved_deadline_change
        BEFORE UPDATE OF effective_due_date ON app.targets
        FOR EACH ROW EXECUTE FUNCTION app.require_approved_deadline_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_targets_require_approved_deadline_change ON app.targets")
    op.execute("DROP FUNCTION IF EXISTS app.require_approved_deadline_change()")
    op.drop_table("audit_events", schema="app")
    op.drop_table("deadline_changes", schema="app")
    op.drop_column("cohorts", "calendar_version", schema="app")
