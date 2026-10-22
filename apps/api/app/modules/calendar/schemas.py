"""Public participant dashboard, target, and progress contracts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.calendar.models import TargetStatus


class TargetTheme(BaseModel):
    id: UUID
    code: str
    name: str
    part_id: UUID
    part_no: int
    part_name: str


class TargetResponse(BaseModel):
    id: UUID
    theme: TargetTheme
    initial_due_date: date
    effective_due_date: date
    status: TargetStatus
    first_valid_submission_at: datetime | None = None
    activity_score: int | None = None
    locked_reason: str | None = None
    allowed_actions: list[str]


class PartProgress(BaseModel):
    id: UUID
    part_no: int
    name: str
    total_targets: int
    completed_targets: int
    status: str
    locked_reason: str | None = None


class ProgressResponse(BaseModel):
    total_targets: int
    completed_targets: int
    overdue_targets: int
    expected_completed_targets: int
    completion_percentage: float
    on_track: bool
    projected_completion_date: date | None
    active_part: PartProgress | None
    parts: list[PartProgress]


class ParticipantSummary(BaseModel):
    id: UUID
    display_name: str
    enrollment_id: UUID
    cohort_name: str
    cohort_start_date: date
    cohort_close_date: date | None


class DashboardResponse(BaseModel):
    participant: ParticipantSummary
    progress: ProgressResponse
    next_target: TargetResponse | None
    upcoming_targets: list[TargetResponse]
