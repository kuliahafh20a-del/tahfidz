"""User accounts and time-bounded organization role grants."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.time import ensure_utc
from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.modules.organizations.models import Organization


class AccountStatus(StrEnum):
    """Account lifecycle states that authentication must honor."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class Role(StrEnum):
    """Organization-scoped capacities supported by the product."""

    PARTICIPANT = "participant"
    MENTOR = "mentor"
    LECTURER = "lecturer"
    DEPARTMENT_ADMIN = "department_admin"
    FACULTY_ADMIN = "faculty_admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A login account identified independently from academic identifiers."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(login_identifier)) > 0",
            name="login_identifier_not_blank",
        ),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        Index(
            "uq_users__login_identifier_ci",
            text("lower(login_identifier)"),
            unique=True,
        ),
        {"schema": "app"},
    )

    login_identifier: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_status: Mapped[AccountStatus] = mapped_column(
        Enum(
            AccountStatus,
            name="account_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=AccountStatus.PENDING,
        server_default=AccountStatus.PENDING.value,
    )
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    role_grants: Mapped[list[RoleGrant]] = relationship(back_populates="user")

    @validates("login_identifier")
    def normalize_login_identifier(self, _key: str, value: str) -> str:
        """Normalize identifiers before the case-insensitive database guard."""
        normalized = value.strip().casefold()
        if not normalized:
            raise ValueError("login identifier must not be blank")
        return normalized

    @validates("name")
    def normalize_name(self, _key: str, value: str) -> str:
        """Reject empty display names and remove accidental edge whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("user name must not be blank")
        return normalized


class RoleGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A time-bounded role capacity within one organization."""

    __tablename__ = "role_grants"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="role",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=32,
        ),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user: Mapped[User] = relationship(back_populates="role_grants")
    organization: Mapped[Organization] = relationship(back_populates="role_grants")

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="valid_period",
        ),
        ExcludeConstraint(
            (user_id, "="),
            (role, "="),
            (organization_id, "="),
            (func.tstzrange(valid_from, valid_to, "[)"), "&&"),
            name="ex_role_grants__overlapping_scope",
            using="gist",
        ),
        Index(
            "ix_role_grants__active_scope",
            "user_id",
            "role",
            "organization_id",
            "valid_to",
        ),
        {"schema": "app"},
    )

    def is_active_at(self, moment: datetime) -> bool:
        """Return whether the grant covers the supplied absolute instant."""
        instant = ensure_utc(moment)
        starts_at = ensure_utc(self.valid_from)
        ends_at = ensure_utc(self.valid_to) if self.valid_to is not None else None
        return starts_at <= instant and (ends_at is None or instant < ends_at)

    def applies_to(self, organization_id: UUID, moment: datetime) -> bool:
        """Check both organization scope and validity at an instant."""
        return self.organization_id == organization_id and self.is_active_at(moment)
