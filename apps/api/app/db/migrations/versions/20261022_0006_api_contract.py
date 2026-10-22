"""Add durable idempotency storage for critical commands.

Revision ID: 20261022_0006
Revises: 20261022_0005
Create Date: 2026-10-22 16:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261022_0006"
down_revision: str | None = "20261022_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist command identity and safe replay responses without raw request bodies."""
    op.add_column(
        "enrollments",
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        schema="app",
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("normalized_path", sa.String(length=500), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="processing", nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
            "length(request_hash) = 64", name="ck_idempotency_records__request_hash_length"
        ),
        sa.CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599",
            name="ck_idempotency_records__response_status",
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_idempotency_records__status",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["app.users.id"],
            name="fk_idempotency_records__users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
        sa.UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_idempotency_records__actor_key",
        ),
        schema="app",
    )
    op.create_index(
        "ix_idempotency_records__expires_at",
        "idempotency_records",
        ["expires_at"],
        schema="app",
    )


def downgrade() -> None:
    """Remove idempotency claims."""
    op.drop_table("idempotency_records", schema="app")
    op.drop_column("enrollments", "row_version", schema="app")
