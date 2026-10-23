"""Request and response contracts for academic video assessments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.assessments.models import AssessmentStatus, VideoAssessmentOutcome
from app.modules.assessments.schemas import IncidentInput, IncidentResponse
from app.modules.media.models import MediaAssetStatus
from app.modules.mentoring.schemas import SessionParticipant


class VideoAssessmentDraftCreate(BaseModel):
    manual_score: int | None = Field(default=None, ge=1, le=10)
    mentor_note: str | None = Field(default=None, max_length=4000)
    feedback_audio_id: UUID | None = None
    incidents: list[IncidentInput] = Field(default_factory=list, max_length=100)


class VideoAssessmentDraftUpdate(VideoAssessmentDraftCreate):
    expected_version: int = Field(ge=1)


class VideoAssessmentFinalize(BaseModel):
    expected_version: int = Field(ge=1)


class VideoAssessmentAudio(BaseModel):
    id: UUID
    file_name: str
    status: MediaAssetStatus


class VideoAssessmentResponse(BaseModel):
    assessment_id: UUID
    video_version_id: UUID
    eligibility_review_id: UUID
    participant: SessionParticipant
    part_id: UUID
    part_no: int
    part_name: str
    cycle_no: int
    revision_no: int
    video_version_no: int
    video_url: str
    status: AssessmentStatus
    manual_score: int | None
    mentor_note: str | None
    counted_errors: int
    outcome: VideoAssessmentOutcome | None
    incidents: list[IncidentResponse]
    feedback_audio: VideoAssessmentAudio | None
    actual_at: datetime
    finalized_at: datetime | None
    policy_version_id: UUID
    policy_version: str
    row_version: int
    allowed_actions: list[str]


class VideoAssessmentPlayback(BaseModel):
    assessment_id: UUID
    playback_url: str
    expires_at: datetime
