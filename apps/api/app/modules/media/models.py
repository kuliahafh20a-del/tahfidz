"""Private object-storage media metadata and validation lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.identity.models import User
    from app.modules.organizations.models import Organization


class MediaPurpose(StrEnum):
    MENTOR_FEEDBACK = "mentor_feedback"


class MediaAssetStatus(StrEnum):
    UPLOADING = "uploading"
    PENDING_VALIDATION = "pending_validation"
    VALIDATING = "validating"
    AVAILABLE = "available"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata for a private object; signed URLs are deliberately never persisted."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("length(btrim(storage_key)) > 0", name="storage_key_not_blank"),
        CheckConstraint("length(btrim(original_file_name)) > 0", name="file_name_not_blank"),
        CheckConstraint("mime_type LIKE 'audio/%'", name="audio_mime_type"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("checksum ~ '^[0-9a-f]{64}$'", name="checksum_sha256"),
        CheckConstraint("validation_attempts >= 0", name="validation_attempts_nonnegative"),
        Index("uq_media_assets__storage_key", "storage_key", unique=True),
        Index(
            "ix_media_assets__owner_id_status_created_at",
            "owner_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_media_assets__validation_queue",
            "status",
            "created_at",
        ),
        {"schema": "app"},
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.organizations.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[MediaPurpose] = mapped_column(
        Enum(
            MediaPurpose,
            name="media_purpose",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=32,
        ),
        nullable=False,
    )
    status: Mapped[MediaAssetStatus] = mapped_column(
        Enum(
            MediaAssetStatus,
            name="media_asset_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=24,
        ),
        nullable=False,
        default=MediaAssetStatus.UPLOADING,
        server_default=MediaAssetStatus.UPLOADING.value,
    )
    validation_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    validation_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    __mapper_args__ = {"version_id_col": row_version}

    owner: Mapped[User] = relationship()
    organization: Mapped[Organization] = relationship()
