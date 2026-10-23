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
