"""Mentoring sessions and their selected curriculum themes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import Part, Theme
    from app.modules.identity.models import User


class SessionMethod(StrEnum):
    IN_PERSON = "in_person"
    VIDEO_CALL = "video_call"


class SessionStatus(StrEnum):
    PROPOSED = "proposed"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class MentoringSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One participant proposal managed by the assigned mentor."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "(status = 'proposed' AND scheduled_at IS NULL AND actual_at IS NULL) OR "
            "(status = 'scheduled' AND scheduled_at IS NOT NULL AND actual_at IS NULL) OR "
            "(status IN ('in_progress', 'completed') AND scheduled_at IS NOT NULL "
            "AND actual_at IS NOT NULL) OR "
            "(status = 'no_show' AND scheduled_at IS NOT NULL AND actual_at IS NULL) OR "
            "(status = 'cancelled' AND actual_at IS NULL)",
            name="status_timestamps",
        ),
        CheckConstraint(
            "participant_note IS NULL OR length(btrim(participant_note)) > 0",
            name="participant_note_not_blank",
        ),
        CheckConstraint(
            "mentor_note IS NULL OR length(btrim(mentor_note)) > 0",
            name="mentor_note_not_blank",
        ),
        Index("ix_sessions__mentor_id_scheduled_at_status", "mentor_id", "scheduled_at", "status"),
        Index("ix_sessions__enrollment_id_actual_at", "enrollment_id", "actual_at"),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    part_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.parts.id", ondelete="RESTRICT"), nullable=False
    )
    mentor_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=False
    )
    proposed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    actual_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    method: Mapped[SessionMethod] = mapped_column(
        Enum(
            SessionMethod,
            name="session_method",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=SessionStatus.PROPOSED,
        server_default=SessionStatus.PROPOSED.value,
    )
    participant_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    mentor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    __mapper_args__ = {"version_id_col": row_version}

    enrollment: Mapped[Enrollment] = relationship()
    part: Mapped[Part] = relationship()
    mentor: Mapped[User] = relationship()
    session_themes: Mapped[list[SessionTheme]] = relationship(
        back_populates="session",
        order_by="SessionTheme.created_at",
    )


class SessionTheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A theme selected for one mentoring session."""

    __tablename__ = "session_themes"
    __table_args__ = (
        UniqueConstraint("session_id", "theme_id", name="uq_session_themes__session_id_theme_id"),
        Index("ix_session_themes__theme_id", "theme_id"),
        {"schema": "app"},
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.sessions.id", ondelete="RESTRICT"), nullable=False
    )
    theme_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.themes.id", ondelete="RESTRICT"), nullable=False
    )

    session: Mapped[MentoringSession] = relationship(back_populates="session_themes")
    theme: Mapped[Theme] = relationship()
