"""Persistent authentication state; raw security tokens are never stored."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.modules.identity.models import Role, User
from app.modules.organizations.models import Organization


class AuthSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A revocable opaque browser session with one optional active role context."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    active_role: Mapped[Role | None] = mapped_column(
        Enum(
            Role,
            name="session_active_role",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=32,
        ),
        nullable=True,
    )
    active_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped[User] = relationship()
    active_organization: Mapped[Organization | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(active_role IS NULL) = (active_organization_id IS NULL)",
            name="active_context_complete",
        ),
        CheckConstraint("expires_at > created_at", name="expires_after_creation"),
        Index("ix_auth_sessions__user_id_expires_at", "user_id", "expires_at"),
        Index("ix_auth_sessions__active_token", "token_hash", "revoked_at", "expires_at"),
        {"schema": "app"},
    )


class PasswordRecoveryToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A short-lived, single-use password recovery capability."""

    __tablename__ = "password_recovery_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user: Mapped[User] = relationship()

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expires_after_creation"),
        Index(
            "ix_password_recovery_tokens__user_id_expires_at",
            "user_id",
            "expires_at",
        ),
        {"schema": "app"},
    )


class AuthRateLimitEvent(UUIDPrimaryKeyMixin, Base):
    """A privacy-preserving login/recovery attempt used for database rate limits."""

    __tablename__ = "auth_rate_limit_events"

    action: Mapped[str] = mapped_column(String(16), nullable=False)
    identity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    client_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "action IN ('login', 'recovery', 'reset')",
            name="action",
        ),
        Index(
            "ix_auth_rate_limit_events__identity_window",
            "action",
            "identity_fingerprint",
            "occurred_at",
        ),
        Index(
            "ix_auth_rate_limit_events__client_window",
            "action",
            "client_fingerprint",
            "occurred_at",
        ),
        {"schema": "app"},
    )
