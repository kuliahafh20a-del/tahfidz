"""Request and response contracts for participant video submissions."""

from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.mentoring.schemas import SessionParticipant
from app.modules.video.models import (
    EligibilityDecision,
    EligibilityReviewStatus,
    VideoAttemptStatus,
    VideoVersionStatus,
)


def normalize_https_url(value: str) -> str:
    """Normalize only URL syntax; the configured host allowlist is checked by the service."""
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("video_url must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("video_url must not contain credentials")
    if parsed.port not in {None, 443}:
        raise ValueError("video_url must use the standard HTTPS port")
    return urlunsplit(("https", parsed.netloc.lower(), parsed.path, parsed.query, ""))


class VideoAttemptCreate(BaseModel):
    part_id: UUID


class VideoVersionCreate(BaseModel):
    video_url: str = Field(min_length=1, max_length=2048)
    recorded_on: date
    completeness_declared: bool
    expected_version: int = Field(ge=1)

    _normalize_video_url = field_validator("video_url")(normalize_https_url)


class VideoVersionResponse(BaseModel):
    id: UUID
    version_no: int
    video_url: str
    recorded_on: date
    submitted_at: datetime
    status: VideoVersionStatus


class VideoAttemptResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    part_id: UUID
    part_no: int
    part_name: str
    cycle_no: int
    revision_no: int
    status: VideoAttemptStatus
    row_version: int
    versions: list[VideoVersionResponse]
    allowed_actions: list[str]


class EligibilityCheckInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    passed: bool
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().lower()


class EligibilityDraftUpdate(BaseModel):
    checklist_version: str = Field(default="technical-v1", min_length=1, max_length=64)
    decision: EligibilityDecision | None = None
    reason: str | None = Field(default=None, max_length=4000)
    checks: list[EligibilityCheckInput] = Field(default_factory=list, max_length=50)
    expected_version: int | None = Field(default=None, ge=1)


class EligibilityFinalize(BaseModel):
    checklist_version: str = Field(default="technical-v1", min_length=1, max_length=64)
    decision: EligibilityDecision
    reason: str | None = Field(default=None, max_length=4000)
    checks: list[EligibilityCheckInput] = Field(min_length=1, max_length=50)
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def require_ineligible_reason(self) -> EligibilityFinalize:
        if self.decision is EligibilityDecision.INELIGIBLE and not (
            self.reason and self.reason.strip()
        ):
            raise ValueError("reason is required for an ineligible decision")
        return self


class ChecklistCriterionResponse(BaseModel):
    code: str
    label: str
    required: bool


class EligibilityCheckResponse(BaseModel):
    code: str
    passed: bool
    note: str | None


class EligibilityReviewResponse(BaseModel):
    id: UUID
    reviewer_id: UUID
    checklist_version: str
    decision: EligibilityDecision | None
    reason: str | None
    status: EligibilityReviewStatus
    finalized_at: datetime | None
    row_version: int
    checks: list[EligibilityCheckResponse]


class VideoEligibilityResponse(BaseModel):
    video_version_id: UUID
    attempt_id: UUID
    participant: SessionParticipant
    part_id: UUID
    part_no: int
    part_name: str
    cycle_no: int
    revision_no: int
    video_version_no: int
    video_url: str
    recorded_on: date
    submitted_at: datetime
    video_status: VideoVersionStatus
    checklist_version: str
    criteria: list[ChecklistCriterionResponse]
    review: EligibilityReviewResponse | None
    allowed_actions: list[str]
