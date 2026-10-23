"""Contracts for lecturer question banks, exam queues, and draft packages."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.exams.models import ExamStatus, QuestionKind, QuestionSource, QuestionStatus
from app.modules.mentoring.schemas import SessionParticipant


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone offset")
    return value


class QuestionVersionCreate(BaseModel):
    kind: QuestionKind
    stimulus: str = Field(min_length=1, max_length=4000)
    answer_reference: dict[str, object]
    scope: dict[str, object]
    previous_version_id: UUID | None = None


class QuestionVersionResponse(BaseModel):
    id: UUID
    question_key: UUID
    author_id: UUID | None
    source: QuestionSource
    kind: QuestionKind
    stimulus: str
    answer_reference: dict[str, object]
    scope: dict[str, object]
    version_no: int
    status: QuestionStatus


class ExamCreate(BaseModel):
    enrollment_id: UUID
    scheduled_at: datetime

    _validate_scheduled_at = field_validator("scheduled_at")(_aware)


class ExamUpdate(BaseModel):
    scheduled_at: datetime
    lecturer_note: str | None = Field(default=None, max_length=4000)
    expected_version: int = Field(ge=1)

    _validate_scheduled_at = field_validator("scheduled_at")(_aware)


class ExamItemInput(BaseModel):
    question_version_id: UUID
    weight: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=3)


class ExamItemsReplace(BaseModel):
    items: list[ExamItemInput] = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=1)


class PackagePolicyResponse(BaseModel):
    approved: bool
    required_item_count: int | None
    expected_total_weight: Decimal | None
    blockers: list[str]


class ExamItemResponse(BaseModel):
    id: UUID
    sequence_no: int
    question_version_id: UUID
    source: QuestionSource
    kind: QuestionKind
    stimulus: str
    scope: dict[str, object]
    answer_reference: dict[str, object]
    question_version_no: int
    weight: Decimal | None


class ExamResponse(BaseModel):
    id: UUID
    participant: SessionParticipant
    lecturer_id: UUID
    policy_version_id: UUID
    policy_version: str
    scheduled_at: datetime
    actual_at: datetime | None
    lecturer_note: str | None
    status: ExamStatus
    items: list[ExamItemResponse]
    package_policy: PackagePolicyResponse
    row_version: int
    finalized_at: datetime | None
    allowed_actions: list[str]


class ExamQueueItemResponse(BaseModel):
    participant: SessionParticipant
    completed_parts: int
    required_parts: int
    latest_exam_id: UUID | None
    latest_exam_status: ExamStatus | None
    allowed_actions: list[str]
