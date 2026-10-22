"""Persistent idempotency claims for critical commands."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class IdempotencyStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IdempotencyRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bind one UUID key to an actor, operation, and canonical request hash."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        CheckConstraint("length(request_hash) = 64", name="request_hash_length"),
        CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599", name="response_status"
        ),
        UniqueConstraint("actor_id", "idempotency_key", name="uq_idempotency_records__actor_key"),
        Index("ix_idempotency_records__expires_at", "expires_at"),
        {"schema": "app"},
    )

    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    normalized_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[IdempotencyStatus] = mapped_column(
        Enum(
            IdempotencyStatus,
            name="idempotency_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=IdempotencyStatus.PROCESSING,
        server_default=IdempotencyStatus.PROCESSING.value,
    )
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
