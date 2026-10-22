"""Request and response contracts for participant video submissions."""

from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.video.models import VideoAttemptStatus, VideoVersionStatus


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
