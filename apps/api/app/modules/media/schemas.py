"""Safe API contracts for private audio uploads and playback."""

from datetime import datetime
from pathlib import PurePath
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.media.models import MediaAssetStatus, MediaPurpose


class AudioUploadIntentCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    purpose: MediaPurpose = MediaPurpose.MENTOR_FEEDBACK

    @field_validator("file_name")
    @classmethod
    def normalize_file_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or PurePath(normalized).name != normalized or "\\" in normalized:
            raise ValueError("file_name must not contain a path")
        return normalized

    @field_validator("content_type")
    @classmethod
    def normalize_content_type(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("sha256")
    @classmethod
    def normalize_sha256(cls, value: str) -> str:
        return value.lower()


class MediaAssetResponse(BaseModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    purpose: MediaPurpose
    status: MediaAssetStatus
    validation_error_code: str | None
    created_at: datetime
    completed_at: datetime | None
    validated_at: datetime | None
    row_version: int


class AudioUploadIntentResponse(BaseModel):
    media: MediaAssetResponse
    upload_url: str
    upload_method: str = "PUT"
    required_headers: dict[str, str]
    expires_at: datetime


class PlaybackUrlResponse(BaseModel):
    media_id: UUID
    playback_url: str
    expires_at: datetime
