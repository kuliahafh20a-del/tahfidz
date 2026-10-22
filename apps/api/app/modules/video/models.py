"""Academic video slots and replaceable media versions."""

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
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import Part


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
