"""Participant targets and their effective calendar dates."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import Theme
    from app.modules.identity.models import User


class TargetStatus(StrEnum):
    """Lifecycle states for one participant-theme target."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CLOSED = "closed"


class Target(UUIDPrimaryKeyMixin, Base):
    """A stable participant-theme deadline derived from a cohort calendar."""

    __tablename__ = "targets"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id",
            "theme_id",
            name="uq_targets__enrollment_id_theme_id",
        ),
        Index(
            "ix_targets__enrollment_id_effective_due_date_status",
            "enrollment_id",
            "effective_due_date",
            "status",
        ),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="CASCADE"),
        nullable=False,
    )
    theme_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.themes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    initial_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TargetStatus] = mapped_column(
        Enum(
            TargetStatus,
            name="target_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=TargetStatus.SCHEDULED,
        server_default=TargetStatus.SCHEDULED.value,
    )

    enrollment: Mapped[Enrollment] = relationship()
    theme: Mapped[Theme] = relationship()


class DeadlineChangeStatus(StrEnum):
    """Review lifecycle for a proposed effective deadline."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DeadlineChange(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only proposal and decision history for one target deadline."""

    __tablename__ = "deadline_changes"
    __table_args__ = (
        CheckConstraint("new_date <> old_date", name="date_changed"),
        CheckConstraint("length(btrim(reason)) > 0", name="reason_not_blank"),
        CheckConstraint(
            "(status = 'pending' AND approved_by IS NULL AND decided_at IS NULL) OR "
            "(status IN ('approved', 'rejected') AND approved_by IS NOT NULL "
            "AND decided_at IS NOT NULL) OR status = 'cancelled'",
            name="decision_complete",
        ),
        Index("ix_deadline_changes__target_id_status", "target_id", "status"),
        {"schema": "app"},
    )

    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.targets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    old_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    impact_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DeadlineChangeStatus] = mapped_column(
        Enum(
            DeadlineChangeStatus,
            name="deadline_change_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=DeadlineChangeStatus.PENDING,
        server_default=DeadlineChangeStatus.PENDING.value,
    )
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    __mapper_args__ = {"version_id_col": row_version}

    target: Mapped[Target] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requested_by])
    approver: Mapped[User | None] = relationship(foreign_keys=[approved_by])
