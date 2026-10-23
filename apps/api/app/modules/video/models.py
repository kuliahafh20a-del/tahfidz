"""Academic video slots and replaceable media versions."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import Part
    from app.modules.identity.models import User


class VideoAttemptStatus(StrEnum):
    OPEN = "open"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    FINALIZED = "finalized"
    CLOSED = "closed"


class VideoVersionStatus(StrEnum):
    SUBMITTED = "submitted"
    AVAILABLE = "available"
    FAILED = "failed"
    REPLACED = "replaced"


class EligibilityDecision(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class EligibilityReviewStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"


class VideoAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One server-allocated academic cycle/revision for a curriculum part."""

    __tablename__ = "video_attempts"
    __table_args__ = (
        CheckConstraint("cycle_no >= 1", name="cycle_positive"),
        CheckConstraint("revision_no BETWEEN 0 AND 3", name="revision_range"),
        UniqueConstraint(
            "enrollment_id",
            "part_id",
            "cycle_no",
            "revision_no",
            name="uq_video_attempts__enrollment_part_cycle_revision",
        ),
        Index(
            "ix_video_attempts__enrollment_id_part_id_status", "enrollment_id", "part_id", "status"
        ),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    part_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.parts.id", ondelete="RESTRICT"), nullable=False
    )
    cycle_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[VideoAttemptStatus] = mapped_column(
        Enum(
            VideoAttemptStatus,
            name="video_attempt_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=VideoAttemptStatus.OPEN,
        server_default=VideoAttemptStatus.OPEN.value,
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    __mapper_args__ = {"version_id_col": row_version}

    enrollment: Mapped[Enrollment] = relationship()
    part: Mapped[Part] = relationship()
    versions: Mapped[list[VideoVersion]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="VideoVersion.version_no",
    )


class VideoVersion(UUIDPrimaryKeyMixin, Base):
    """A media link version that never changes the academic revision slot."""

    __tablename__ = "video_versions"
    __table_args__ = (
        CheckConstraint("version_no >= 1", name="version_positive"),
        CheckConstraint("length(btrim(video_url)) > 0", name="url_not_blank"),
        UniqueConstraint(
            "attempt_id", "version_no", name="uq_video_versions__attempt_id_version_no"
        ),
        Index("ix_video_versions__attempt_id_version_no", "attempt_id", "version_no"),
        {"schema": "app"},
    )

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.video_attempts.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[VideoVersionStatus] = mapped_column(
        Enum(
            VideoVersionStatus,
            name="video_version_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=VideoVersionStatus.SUBMITTED,
        server_default=VideoVersionStatus.SUBMITTED.value,
    )

    attempt: Mapped[VideoAttempt] = relationship(back_populates="versions")
    eligibility_reviews: Mapped[list[EligibilityReview]] = relationship(
        back_populates="video_version",
        order_by="EligibilityReview.created_at",
    )


class EligibilityReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned technical decision that remains separate from academic grading."""

    __tablename__ = "eligibility_reviews"
    __table_args__ = (
        CheckConstraint("length(btrim(checklist_version)) > 0", name="checklist_version_not_blank"),
        CheckConstraint(
            "status <> 'final' OR decision <> 'ineligible' OR "
            "(reason IS NOT NULL AND length(btrim(reason)) > 0)",
            name="ineligible_reason_required",
        ),
        CheckConstraint(
            "status <> 'final' OR decision IS NOT NULL", name="final_decision_required"
        ),
        CheckConstraint(
            "(status = 'draft' AND finalized_at IS NULL) OR "
            "(status IN ('final', 'superseded') AND finalized_at IS NOT NULL)",
            name="status_finalized_at",
        ),
        Index(
            "ix_eligibility_reviews__video_version_id_status_finalized_at",
            "video_version_id",
            "status",
            "finalized_at",
        ),
        Index(
            "uq_eligibility_reviews__active_video_version",
            "video_version_id",
            unique=True,
            postgresql_where=text("status <> 'superseded'"),
        ),
        {"schema": "app"},
    )

    video_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.video_versions.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=False
    )
    checklist_version: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[EligibilityDecision | None] = mapped_column(
        Enum(
            EligibilityDecision,
            name="eligibility_decision",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EligibilityReviewStatus] = mapped_column(
        Enum(
            EligibilityReviewStatus,
            name="eligibility_review_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=EligibilityReviewStatus.DRAFT,
        server_default=EligibilityReviewStatus.DRAFT.value,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    __mapper_args__ = {"version_id_col": row_version}

    video_version: Mapped[VideoVersion] = relationship(back_populates="eligibility_reviews")
    reviewer: Mapped[User] = relationship()
    checks: Mapped[list[EligibilityCheck]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="EligibilityCheck.criterion_code",
    )


class EligibilityCheck(UUIDPrimaryKeyMixin, Base):
    """One stable criterion captured inside an eligibility review snapshot."""

    __tablename__ = "eligibility_checks"
    __table_args__ = (
        CheckConstraint("length(btrim(criterion_code)) > 0", name="criterion_code_not_blank"),
        CheckConstraint("notes IS NULL OR length(btrim(notes)) > 0", name="notes_not_blank"),
        UniqueConstraint(
            "review_id",
            "criterion_code",
            name="uq_eligibility_checks__review_id_criterion_code",
        ),
        {"schema": "app"},
    )

    review_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.eligibility_reviews.id", ondelete="CASCADE"), nullable=False
    )
    criterion_code: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    review: Mapped[EligibilityReview] = relationship(back_populates="checks")
