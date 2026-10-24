"""Immutable grade snapshots and their assessment provenance."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.assessments.models import AssessmentRecord
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import PolicyVersion


class GradeStatus(StrEnum):
    INCOMPLETE = "incomplete"
    READY_FOR_EXAM = "ready_for_exam"
    AWAITING_EXAM = "awaiting_exam"
    AWAITING_COMPONENTS = "awaiting_components"
    GRADUATED = "graduated"
    NOT_GRADUATED = "not_graduated"
    NEEDS_REVIEW = "needs_review"


class GradeComponent(StrEnum):
    M = "M"
    D = "D"


class GradeSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "grade_snapshots"
    __table_args__ = (
        CheckConstraint("k_value IS NULL OR k_value BETWEEN 1 AND 10", name="k_range"),
        CheckConstraint("m_value IS NULL OR m_value BETWEEN 1 AND 10", name="m_range"),
        CheckConstraint("d_value IS NULL OR d_value BETWEEN 1 AND 10", name="d_range"),
        CheckConstraint("n_value IS NULL OR n_value BETWEEN 1 AND 10", name="n_range"),
        CheckConstraint("jsonb_typeof(source_context) = 'object'", name="source_context_object"),
        Index("ix_grade_snapshots__enrollment_id_calculated_at", "enrollment_id", "calculated_at"),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.policy_versions.id", ondelete="RESTRICT"), nullable=False
    )
    k_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    m_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    d_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    n_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    status: Mapped[GradeStatus] = mapped_column(
        Enum(
            GradeStatus,
            name="grade_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=24,
        ),
        nullable=False,
    )
    source_context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.now()
    )
    supersedes_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.grade_snapshots.id", ondelete="RESTRICT"), nullable=True
    )

    enrollment: Mapped[Enrollment] = relationship()
    policy_version: Mapped[PolicyVersion] = relationship()
    supersedes: Mapped[GradeSnapshot | None] = relationship(remote_side="GradeSnapshot.id")
    sources: Mapped[list[GradeSource]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class GradeSource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "grade_sources"
    __table_args__ = (
        CheckConstraint(
            "contribution IS NULL OR contribution BETWEEN 0 AND 10",
            name="contribution_range",
        ),
        UniqueConstraint(
            "grade_snapshot_id",
            "assessment_id",
            "component",
            name="uq_grade_sources__snapshot_assessment_component",
        ),
        {"schema": "app"},
    )

    grade_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.grade_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.assessment_records.id", ondelete="RESTRICT"), nullable=False
    )
    component: Mapped[GradeComponent] = mapped_column(
        Enum(
            GradeComponent,
            name="grade_component",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=1,
        ),
        nullable=False,
    )
    contribution: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    snapshot: Mapped[GradeSnapshot] = relationship(back_populates="sources")
    assessment: Mapped[AssessmentRecord] = relationship()
