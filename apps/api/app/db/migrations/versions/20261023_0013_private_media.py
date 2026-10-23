"""Add private media metadata and validation queue.

Revision ID: 20261023_0013
Revises: 20261023_0012
Create Date: 2026-10-23 11:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0013"
down_revision: str | None = "20261023_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="uploading", nullable=False),
        sa.Column("validation_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("validation_error_code", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
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
            "length(btrim(storage_key)) > 0",
            name="ck_media_assets__storage_key_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(original_file_name)) > 0",
            name="ck_media_assets__file_name_not_blank",
        ),
        sa.CheckConstraint("mime_type LIKE 'audio/%'", name="ck_media_assets__audio_mime_type"),
        sa.CheckConstraint("size_bytes > 0", name="ck_media_assets__size_positive"),
        sa.CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$'",
            name="ck_media_assets__checksum_sha256",
        ),
        sa.CheckConstraint(
            "purpose IN ('mentor_feedback')",
            name="ck_media_assets__purpose",
        ),
        sa.CheckConstraint(
            "status IN ('uploading', 'pending_validation', 'validating', "
            "'available', 'failed', 'quarantined', 'deleted')",
            name="ck_media_assets__status",
        ),
        sa.CheckConstraint(
            "validation_attempts >= 0",
            name="ck_media_assets__validation_attempts_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["app.users.id"],
            name="fk_media_assets__users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["app.organizations.id"],
            name="fk_media_assets__organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
        schema="app",
    )
    op.create_index(
        "uq_media_assets__storage_key",
        "media_assets",
        ["storage_key"],
        unique=True,
        schema="app",
    )
    op.create_index(
        "ix_media_assets__owner_id_status_created_at",
        "media_assets",
        ["owner_id", "status", "created_at"],
        schema="app",
    )
    op.create_index(
        "ix_media_assets__validation_queue",
        "media_assets",
        ["status", "created_at"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("media_assets", schema="app")
