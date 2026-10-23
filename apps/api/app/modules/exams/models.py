"""Versioned question bank and lecturer exam packages."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.cohorts.models import Enrollment
    from app.modules.curriculum.models import PolicyVersion
    from app.modules.identity.models import User


class QuestionSource(StrEnum):
    APPLICATION = "application"
    LECTURER = "lecturer"


class QuestionKind(StrEnum):
    CONTINUE_VERSES = "continue_verses"
    SURAH_ORDER = "surah_order"
    RECITATION = "recitation"


class QuestionStatus(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    INACTIVE = "inactive"


class ExamStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    CANCELLED = "cancelled"


class QuestionVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable question content in one explicit version lineage."""

    __tablename__ = "question_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_positive"),
        CheckConstraint("length(btrim(stimulus)) > 0", name="stimulus_not_blank"),
        CheckConstraint("jsonb_typeof(answer_reference) = 'object'", name="answer_object"),
        CheckConstraint("jsonb_typeof(scope) = 'object'", name="scope_object"),
        CheckConstraint(
            "(source = 'application' AND author_id IS NULL) OR "
            "(source = 'lecturer' AND author_id IS NOT NULL)",
            name="source_author",
        ),
        UniqueConstraint(
            "question_key", "version_no", name="uq_question_versions__question_key_version_no"
        ),
        Index("ix_question_versions__source_status_kind", "source", "status", "kind"),
        {"schema": "app"},
    )

    question_key: Mapped[UUID] = mapped_column(default=uuid4, nullable=False)
    author_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=True
    )
    source: Mapped[QuestionSource] = mapped_column(
        Enum(
            QuestionSource,
            name="question_source",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
    )
    kind: Mapped[QuestionKind] = mapped_column(
        Enum(
            QuestionKind,
            name="question_kind",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=32,
        ),
        nullable=False,
    )
    stimulus: Mapped[str] = mapped_column(Text, nullable=False)
    answer_reference: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(
            QuestionStatus,
            name="question_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=QuestionStatus.DRAFT,
        server_default=QuestionStatus.DRAFT.value,
    )

    author: Mapped[User | None] = relationship()


class Exam(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A lecturer-scoped exam package for one eligible enrollment."""

    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("notes IS NULL OR length(btrim(notes)) > 0", name="notes_not_blank"),
        CheckConstraint(
            "(status = 'final' AND finalized_at IS NOT NULL) OR "
            "(status <> 'final' AND finalized_at IS NULL)",
            name="status_finalized_at",
        ),
        Index("ix_exams__enrollment_id_status_created_at", "enrollment_id", "status", "created_at"),
        {"schema": "app"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    lecturer_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"), nullable=False
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.policy_versions.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    actual_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(
            ExamStatus,
            name="exam_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=ExamStatus.DRAFT,
        server_default=ExamStatus.DRAFT.value,
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    finalized_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    __mapper_args__ = {"version_id_col": row_version}

    enrollment: Mapped[Enrollment] = relationship()
    lecturer: Mapped[User] = relationship()
    policy_version: Mapped[PolicyVersion] = relationship()
    items: Mapped[list[ExamItem]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamItem.sequence_no",
    )


class ExamItem(UUIDPrimaryKeyMixin, Base):
    """Immutable question snapshot in the ordered exam package."""

    __tablename__ = "exam_items"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="sequence_positive"),
        CheckConstraint("weight IS NULL OR weight > 0", name="weight_positive"),
        CheckConstraint("jsonb_typeof(question_snapshot) = 'object'", name="snapshot_object"),
        UniqueConstraint("exam_id", "sequence_no", name="uq_exam_items__exam_id_sequence_no"),
        {"schema": "app"},
    )

    exam_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.exams.id", ondelete="CASCADE"), nullable=False
    )
    question_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.question_versions.id", ondelete="RESTRICT"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)

    exam: Mapped[Exam] = relationship(back_populates="items")
    question_version: Mapped[QuestionVersion] = relationship()
