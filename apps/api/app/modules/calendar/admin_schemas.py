"""Department calendar and deadline approval contracts."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.api.contracts import ExpectedVersion
from app.modules.calendar.models import DeadlineChangeStatus, TargetStatus
from app.modules.cohorts.models import CohortStatus


class DeadlineChangeRequest(ExpectedVersion):
    target_ids: list[UUID] = Field(min_length=1, max_length=500)
    new_due_date: date
    reason: str = Field(min_length=1, max_length=2_000)
    impact_note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def unique_targets(self) -> Self:
        if len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError("target_ids must not contain duplicates")
        return self


class DeadlineDecisionRequest(ExpectedVersion):
    decision_note: str | None = Field(default=None, max_length=2_000)


class CalendarParticipant(BaseModel):
    enrollment_id: UUID
    user_id: UUID
    display_name: str
    nim: str


class CalendarTheme(BaseModel):
    id: UUID
    code: str
    name: str
    part_no: int
    part_name: str


class DeadlineChangeResponse(BaseModel):
    id: UUID
    target_id: UUID
    requested_by: UUID
    approved_by: UUID | None
    old_date: date
    new_date: date
    reason: str
    impact_note: str | None
    decision_note: str | None
    status: DeadlineChangeStatus
    decided_at: datetime | None
    row_version: int
    created_at: datetime


class CalendarTargetResponse(BaseModel):
    id: UUID
    participant: CalendarParticipant
    theme: CalendarTheme
    initial_due_date: date
    effective_due_date: date
    status: TargetStatus
    pending_change: DeadlineChangeResponse | None
    allowed_actions: list[str]


class CohortCalendarSummary(BaseModel):
    id: UUID
    name: str
    start_date: date
    close_date: date | None
    status: CohortStatus


class CohortCalendarResponse(BaseModel):
    cohort: CohortCalendarSummary
    calendar_version: int
    targets: list[CalendarTargetResponse]
    history: list[DeadlineChangeResponse]
    allowed_actions: list[str]


class DeadlineImpactItem(BaseModel):
    target_id: UUID
    participant: CalendarParticipant
    theme: CalendarTheme
    old_date: date
    new_date: date
    shift_days: int


class DeadlineChangePreview(BaseModel):
    cohort_id: UUID
    calendar_version: int
    affected_count: int
    earliest_old_date: date
    latest_old_date: date
    new_due_date: date
    requires_approval: bool = True
    impacts: list[DeadlineImpactItem]


class DeadlineChangeBatchResponse(BaseModel):
    cohort_id: UUID
    calendar_version: int
    changes: list[DeadlineChangeResponse]
