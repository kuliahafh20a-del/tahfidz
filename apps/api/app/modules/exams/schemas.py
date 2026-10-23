"""Contracts for lecturer question banks, exam queues, and draft packages."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.assessments.models import AssessmentStatus
from app.modules.assessments.schemas import IncidentInput, IncidentResponse
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
    aggregation_method: str | None = None
    blockers: list[str]


class ExamStart(BaseModel):
    actual_at: datetime
    expected_version: int = Field(ge=1)

    _validate_actual_at = field_validator("actual_at")(_aware)


class ExamAssessmentItemDraft(BaseModel):
    exam_item_id: UUID
    manual_score: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=4000)
    incidents: list[IncidentInput] = Field(default_factory=list, max_length=100)


class ExamAssessmentDraft(BaseModel):
    items: list[ExamAssessmentItemDraft] = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=1)


class ExamFinalize(BaseModel):
    actual_at: datetime
    manual_score: Decimal | None = Field(default=None, ge=1, le=10, decimal_places=3)
    examiner_note: str | None = Field(default=None, max_length=4000)
    evidence_media_ids: list[UUID] = Field(min_length=1, max_length=20)
    expected_version: int = Field(ge=1)

    _validate_actual_at = field_validator("actual_at")(_aware)


class ExamAssessmentResponse(BaseModel):
    assessment_id: UUID
    exam_item_id: UUID
    sequence_no: int
    status: AssessmentStatus
    manual_score: int | None
    notes: str | None
    incidents: list[IncidentResponse]
    row_version: int


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
    assessments: list[ExamAssessmentResponse] = Field(default_factory=list)
    d_score: Decimal | None = None
    evidence_media_ids: list[UUID] = Field(default_factory=list)
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


class ExamSummaryResponse(BaseModel):
    exam: ExamResponse
    assessed_item_count: int
    total_item_count: int
    d_status: str
    missing_requirements: list[str]
