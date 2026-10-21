"""Faculty and department organization hierarchy."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.identity.models import RoleGrant


class OrganizationKind(StrEnum):
    """Organization levels supported by the initial YAQin deployment."""

    FACULTY = "faculty"
    DEPARTMENT = "department"


class OrganizationStatus(StrEnum):
    """Whether an organization may be used for new grants and assignments."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A faculty root or one of its direct department children."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="parent_not_self",
        ),
        CheckConstraint(
            "(kind = 'faculty' AND parent_id IS NULL) "
            "OR (kind = 'department' AND parent_id IS NOT NULL)",
            name="kind_parent_shape",
        ),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint(
            "code IS NULL OR length(btrim(code)) > 0",
            name="code_not_blank",
        ),
        Index("ix_organizations__parent_id", "parent_id"),
        Index("ix_organizations__kind", "kind"),
        Index("ix_organizations__status", "status"),
        Index(
            "uq_organizations__parent_id_code",
            "parent_id",
            "code",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("code IS NOT NULL"),
        ),
        {"schema": "app"},
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    kind: Mapped[OrganizationKind] = mapped_column(
        Enum(
            OrganizationKind,
            name="organization_kind",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(
            OrganizationStatus,
            name="organization_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
        server_default=OrganizationStatus.ACTIVE.value,
    )

    parent: Mapped[Organization | None] = relationship(
        back_populates="children",
        remote_side="Organization.id",
    )
    children: Mapped[list[Organization]] = relationship(back_populates="parent")
    role_grants: Mapped[list[RoleGrant]] = relationship(back_populates="organization")

    @validates("name")
    def normalize_name(self, _key: str, value: str) -> str:
        """Strip display names while preserving intentional internal spacing."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("organization name must not be blank")
        return normalized

    @validates("code")
    def normalize_code(self, _key: str, value: str | None) -> str | None:
        """Store optional organization codes in a stable canonical form."""
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("organization code must not be blank")
        return normalized
