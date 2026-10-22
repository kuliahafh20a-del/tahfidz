"""Persistent program cohorts, enrollments, and assignment history."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.time import ensure_utc
from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.curriculum.models import CurriculumVersion, PolicyVersion
    from app.modules.identity.models import User
    from app.modules.organizations.models import Organization


class CohortStatus(StrEnum):
    """Lifecycle states for one department program cohort."""

    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EnrollmentStatus(StrEnum):
    """Participant membership states within a cohort."""

    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"
    INACTIVE = "inactive"


class AssignmentRole(StrEnum):
    """Staff capacities that may be assigned to an enrollment."""

    MENTOR = "mentor"
    LECTURER = "lecturer"


class Cohort(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A department-owned delivery of one curriculum and policy version."""

    __tablename__ = "cohorts"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint(
            "close_date IS NULL OR close_date >= start_date",
            name="date_order",
        ),
        UniqueConstraint("organization_id", "name", name="uq_cohorts__organization_id_name"),
        Index("ix_cohorts__organization_id_status", "organization_id", "status"),
        {"schema": "app"},
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    curriculum_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.curriculum_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CohortStatus] = mapped_column(
        Enum(
            CohortStatus,
            name="cohort_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=CohortStatus.DRAFT,
        server_default=CohortStatus.DRAFT.value,
    )

    organization: Mapped[Organization] = relationship()
    curriculum_version: Mapped[CurriculumVersion] = relationship()
    policy_version: Mapped[PolicyVersion] = relationship()
    enrollments: Mapped[list[Enrollment]] = relationship(
        back_populates="cohort",
    )

    @validates("name")
    def normalize_name(self, _key: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("cohort name must not be blank")
        return normalized


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A participant's durable membership in one cohort."""

    __tablename__ = "enrollments"
    __table_args__ = (
        CheckConstraint("length(btrim(nim_snapshot)) > 0", name="nim_not_blank"),
        CheckConstraint(
            "nim_snapshot = upper(btrim(nim_snapshot))",
            name="nim_canonical",
        ),
        UniqueConstraint(
            "user_id",
            "cohort_id",
            name="uq_enrollments__user_id_cohort_id",
        ),
        UniqueConstraint(
            "cohort_id",
            "nim_snapshot",
            name="uq_enrollments__cohort_id_nim_snapshot",
        ),
        Index("ix_enrollments__cohort_id_status", "cohort_id", "status"),
        {"schema": "app"},
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.cohorts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nim_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(
            EnrollmentStatus,
            name="enrollment_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
        server_default=EnrollmentStatus.ACTIVE.value,
    )
    joined_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship()
    cohort: Mapped[Cohort] = relationship(back_populates="enrollments")
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="enrollment",
        order_by="Assignment.valid_from.desc()",
    )

    @validates("nim_snapshot")
    def normalize_nim(self, _key: str, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("NIM must not be blank")
        return normalized


class Assignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A non-destructive Mentor or Lecturer assignment interval."""

    __tablename__ = "assignments"

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    staff_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[AssignmentRole] = mapped_column(
        Enum(
            AssignmentRole,
            name="assignment_role",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    enrollment: Mapped[Enrollment] = relationship(back_populates="assignments")
    staff: Mapped[User] = relationship()

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="valid_period",
        ),
        ExcludeConstraint(
            (enrollment_id, "="),
            (role, "="),
            (func.tstzrange(valid_from, valid_to, "[)"), "&&"),
            name="ex_assignments__overlapping_role",
            using="gist",
        ),
        Index(
            "ix_assignments__enrollment_id_role_valid_to",
            "enrollment_id",
            "role",
            "valid_to",
        ),
        {"schema": "app"},
    )

    @validates("valid_from", "valid_to")
    def normalize_time(self, _key: str, value: datetime | None) -> datetime | None:
        return ensure_utc(value) if value is not None else None

    @validates("reason")
    def normalize_reason(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
