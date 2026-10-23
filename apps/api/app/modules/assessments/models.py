"""Shared assessment records, incidents, and the theme-assessment subtype."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import PolicyVersion
    from app.modules.identity.models import User
    from app.modules.media.models import MediaAsset
    from app.modules.mentoring.models import SessionTheme
    from app.modules.video.models import EligibilityReview, VideoVersion


class AssessmentKind(StrEnum):
    THEME = "theme"
    VIDEO = "video"
    EXAM = "exam"


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"
    NEEDS_REVIEW = "needs_review"


class AssistanceType(StrEnum):
    NONE = "none"
    CUE = "cue"
    ANSWER = "answer"


class ThemeOutcome(StrEnum):
    ENOUGH = "enough"
    REPEAT = "repeat"
    FOLLOW_UP = "follow_up"


class VideoAssessmentOutcome(StrEnum):
    ENOUGH = "enough"
    NOT_ENOUGH = "not_enough"


class AssessmentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable-after-finalization parent for every academic assessment."""

    __tablename__ = "assessment_records"
    __table_args__ = (
        CheckConstraint(
            "manual_score IS NULL OR (manual_score BETWEEN 1 AND 10 "
            "AND manual_score = trunc(manual_score))",
            name="manual_score_integer_range",
        ),
        CheckConstraint(
            "(status = 'draft' AND finalized_at IS NULL) OR "
            "(status IN ('final', 'superseded', 'needs_review') AND finalized_at IS NOT NULL)",
            name="status_finalized_at",
        ),
        Index(
            "ix_assessment_records__enrollment_id_kind_status_finalized_at",
            "enrollment_id",
            "kind",
            "status",
            "finalized_at",
        ),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    assessor_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=False
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.policy_versions.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[AssessmentKind] = mapped_column(
        Enum(
            AssessmentKind,
            name="assessment_kind",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
    )
    actual_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    manual_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(
            AssessmentStatus,
            name="assessment_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=AssessmentStatus.DRAFT,
        server_default=AssessmentStatus.DRAFT.value,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    __mapper_args__ = {"version_id_col": row_version}

    enrollment: Mapped[Enrollment] = relationship()
    assessor: Mapped[User] = relationship()
    policy_version: Mapped[PolicyVersion] = relationship()
    theme_assessment: Mapped[ThemeAssessment | None] = relationship(
        back_populates="assessment", uselist=False
    )
    video_assessment: Mapped[VideoAssessment | None] = relationship(
        back_populates="assessment", uselist=False
    )
    incidents: Mapped[list[Incident]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="Incident.created_at, Incident.id",
    )


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One categorized observation supporting an assessment decision."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("length(btrim(category)) > 0", name="category_not_blank"),
        CheckConstraint("length(btrim(location_text)) > 0", name="location_not_blank"),
        CheckConstraint("context IS NULL OR length(btrim(context)) > 0", name="context_not_blank"),
        CheckConstraint(
            "video_second IS NULL OR video_second >= 0", name="video_second_nonnegative"
        ),
        CheckConstraint(
            "count_reason IS NULL OR length(btrim(count_reason)) > 0",
            name="count_reason_not_blank",
        ),
        CheckConstraint("notes IS NULL OR length(btrim(notes)) > 0", name="notes_not_blank"),
        Index("ix_incidents__assessment_id_counted", "assessment_id", "counted"),
        {"schema": "app"},
    )

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.assessment_records.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    location_text: Mapped[str] = mapped_column(Text, nullable=False)
    video_second: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistance_type: Mapped[AssistanceType] = mapped_column(
        Enum(
            AssistanceType,
            name="assistance_type",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=AssistanceType.NONE,
        server_default=AssistanceType.NONE.value,
    )
    self_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    counted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    count_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[AssessmentRecord] = relationship(back_populates="incidents")


class ThemeAssessment(Base):
    """Theme-specific one-to-one subtype of an assessment record."""

    __tablename__ = "theme_assessments"
    __table_args__ = (
        CheckConstraint("attempt_no BETWEEN 1 AND 5", name="attempt_range"),
        CheckConstraint("notes IS NULL OR length(btrim(notes)) > 0", name="notes_not_blank"),
        UniqueConstraint("session_theme_id", name="uq_theme_assessments__session_theme_id"),
        Index(
            "ix_theme_assessments__session_theme_id_attempt_no", "session_theme_id", "attempt_no"
        ),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(
        ForeignKey("app.assessment_records.id", ondelete="RESTRICT"), primary_key=True
    )
    session_theme_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.session_themes.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    outcome: Mapped[ThemeOutcome | None] = mapped_column(
        Enum(
            ThemeOutcome,
            name="theme_outcome",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[AssessmentRecord] = relationship(back_populates="theme_assessment")
    session_theme: Mapped[SessionTheme] = relationship()


class VideoAssessment(Base):
    """Video-specific academic result authorized by a final eligibility review."""

    __tablename__ = "video_assessments"
    __table_args__ = (
        CheckConstraint("counted_errors >= 0", name="counted_errors_nonnegative"),
        CheckConstraint("notes IS NULL OR length(btrim(notes)) > 0", name="notes_not_blank"),
        Index("ix_video_assessments__video_version_id", "video_version_id"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(
        ForeignKey("app.assessment_records.id", ondelete="RESTRICT"), primary_key=True
    )
    video_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.video_versions.id", ondelete="RESTRICT"), nullable=False
    )
    eligibility_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.eligibility_reviews.id", ondelete="RESTRICT"), nullable=False
    )
    audio_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.media_assets.id", ondelete="RESTRICT"), nullable=True
    )
    counted_errors: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    outcome: Mapped[VideoAssessmentOutcome | None] = mapped_column(
        Enum(
            VideoAssessmentOutcome,
            name="video_assessment_outcome",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[AssessmentRecord] = relationship(back_populates="video_assessment")
    video_version: Mapped[VideoVersion] = relationship()
    eligibility_review: Mapped[EligibilityReview] = relationship()
    audio_asset: Mapped[MediaAsset | None] = relationship()
