"""Participant targets and their effective calendar dates."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import Theme


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
