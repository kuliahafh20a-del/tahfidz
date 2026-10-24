"""Validated mentoring session request and response contracts."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.contracts import ExpectedVersion
from app.modules.mentoring.models import SessionMethod, SessionStatus


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone offset is required")
    return value


class SessionCreate(BaseModel):
    theme_ids: list[UUID] = Field(min_length=1, max_length=40)
    method: SessionMethod
    proposed_at: datetime
    participant_note: str | None = Field(default=None, max_length=2_000)

    _validate_time = field_validator("proposed_at")(_aware)

    @model_validator(mode="after")
    def unique_themes(self) -> Self:
        if len(set(self.theme_ids)) != len(self.theme_ids):
            raise ValueError("theme_ids must not contain duplicates")
        return self


class SessionSchedule(ExpectedVersion):
    scheduled_at: datetime
    method: SessionMethod
    mentor_note: str | None = Field(default=None, max_length=2_000)

    _validate_time = field_validator("scheduled_at")(_aware)


class SessionTransition(ExpectedVersion):
    note: str | None = Field(default=None, max_length=2_000)


class SessionParticipant(BaseModel):
    enrollment_id: UUID
    user_id: UUID
    display_name: str
    nim: str


class SessionMentor(BaseModel):
    user_id: UUID
    display_name: str


class SessionThemeResponse(BaseModel):
    id: UUID
    theme_id: UUID
    code: str
    name: str
    part_id: UUID
    part_no: int
    part_name: str


class SessionResponse(BaseModel):
    id: UUID
    participant: SessionParticipant
    part_id: UUID
    mentor: SessionMentor
    proposed_at: datetime
    scheduled_at: datetime | None
    actual_at: datetime | None
    method: SessionMethod
    status: SessionStatus
    participant_note: str | None
    mentor_note: str | None
    row_version: int = Field(ge=1)
    created_at: datetime
    themes: list[SessionThemeResponse]
    allowed_actions: list[str]
