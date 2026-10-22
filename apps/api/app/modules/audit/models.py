"""Append-only audit events for security-sensitive domain actions."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "ix_audit_events__object_type_reference_occurred_at",
            "object_type",
            "object_reference",
            "occurred_at",
        ),
        Index("ix_audit_events__actor_id_occurred_at", "actor_id", "occurred_at"),
        {"schema": "app"},
    )

    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(nullable=True)
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
