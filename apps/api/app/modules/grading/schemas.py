"""Auditable contracts for the activity component (K)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ActivityThemeScore(BaseModel):
    target_id: UUID
    theme_id: UUID
    effective_due_date: date
    first_valid_submission_at: datetime | None
    days_late: int | None
    score: int | None


class ActivitySourceContext(BaseModel):
    cutoff_at: datetime
    timezone: Literal["Asia/Jakarta"] = "Asia/Jakarta"
    total_target_count: int
    scored_target_count: int
    overdue_target_count: int
    themes: list[ActivityThemeScore]


class ActivityScoreResponse(BaseModel):
    value: Decimal | None
    is_final: bool
    source_context: ActivitySourceContext


class GradeComponentResponse(BaseModel):
    value: Decimal | None
    weight: Decimal
    status: Literal["available", "not_assessed", "policy_pending", "incomplete"]


class GradeSourceResponse(BaseModel):
    assessment_id: UUID
    component: Literal["M", "D"]
    contribution: Decimal | None


class GradeSnapshotResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    status: str
    exam_readiness: Literal["not_ready", "ready_for_exam", "exam_in_progress", "exam_final"]
    components: dict[Literal["k", "m", "d"], GradeComponentResponse]
    final_score: Decimal | None
    graduation_status: Literal["graduated", "not_graduated"] | None
    policy_version_id: UUID
    policy_version: str
    calculated_at: datetime
    supersedes_id: UUID | None
    missing_requirements: list[str]
    source_context: dict[str, object]
    sources: list[GradeSourceResponse]


class GradeHistoryResponse(BaseModel):
    items: list[GradeSnapshotResponse]
