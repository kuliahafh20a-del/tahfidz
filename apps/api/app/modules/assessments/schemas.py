"""Request and response schemas for theme assessment workflows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.assessments.models import (
    AssessmentStatus,
    AssistanceType,
    ThemeOutcome,
)
from app.modules.mentoring.schemas import SessionParticipant, SessionThemeResponse


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone offset")
    return value


class IncidentInput(BaseModel):
    location_text: str = Field(min_length=1, max_length=500)
    video_second: int | None = Field(default=None, ge=0)
    primary_category: str = Field(min_length=1, max_length=64)
    context: str | None = Field(default=None, max_length=1000)
    assistance: AssistanceType = AssistanceType.NONE
    self_corrected: bool = False
    counted: bool = True
    counting_reason: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=2000)


class ThemeAssessmentDraftCreate(BaseModel):
    theme_id: UUID
    actual_at: datetime
    manual_score: int | None = Field(default=None, ge=1, le=10)
    outcome: ThemeOutcome | None = None
    mentor_note: str | None = Field(default=None, max_length=4000)
    incidents: list[IncidentInput] = Field(default_factory=list, max_length=100)

    _validate_actual_at = field_validator("actual_at")(_aware)


class ThemeAssessmentDraftUpdate(BaseModel):
    actual_at: datetime
    manual_score: int | None = Field(default=None, ge=1, le=10)
    outcome: ThemeOutcome | None = None
    mentor_note: str | None = Field(default=None, max_length=4000)
    incidents: list[IncidentInput] = Field(default_factory=list, max_length=100)
    expected_version: int = Field(ge=1)

    _validate_actual_at = field_validator("actual_at")(_aware)


class ThemeAssessmentFinalize(BaseModel):
    expected_version: int = Field(ge=1)


class IncidentResponse(BaseModel):
    id: UUID
    location_text: str
    video_second: int | None
    primary_category: str
    context: str | None
    assistance: AssistanceType
    self_corrected: bool
    counted: bool
    counting_reason: str | None
    note: str | None

    model_config = ConfigDict(from_attributes=True)


class ThemeAssessmentResponse(BaseModel):
    assessment_id: UUID
    session_id: UUID
    session_theme_id: UUID
    participant: SessionParticipant
    theme: SessionThemeResponse
    status: AssessmentStatus
    attempt_no: int
    outcome: ThemeOutcome | None
    manual_score: int | None
    actual_at: datetime
    finalized_at: datetime | None
    mentor_note: str | None
    incidents: list[IncidentResponse]
    counted_incidents: int
    policy_version_id: UUID
    policy_version: str
    row_version: int
    allowed_actions: list[str]


class MentorParticipantResponse(BaseModel):
    enrollment_id: UUID
    user_id: UUID
    display_name: str
    nim: str
    final_assessments: int
    enough_themes: int
    follow_up_themes: int
    allowed_actions: list[str]
