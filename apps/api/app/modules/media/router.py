"""Mentor-authorized private audio upload and playback endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import SuccessEnvelope, request_id, success
from app.api.pagination import require_query_allowlist
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.media.schemas import (
    AudioUploadIntentCreate,
    AudioUploadIntentResponse,
    MediaAssetResponse,
    PlaybackUrlResponse,
)
from app.modules.media.service import (
    MediaConflictError,
    MediaInputError,
    MediaResourceNotFoundError,
    MediaService,
)
from app.modules.media.storage import S3ObjectStorage
from app.modules.mentoring.access import MentorActorDependency

router = APIRouter(prefix="/media", tags=["private media"])


def get_media_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MediaService:
    return MediaService(session, S3ObjectStorage(settings), settings)


MediaServiceDependency = Annotated[MediaService, Depends(get_media_service)]


def raise_media_error(error: Exception) -> NoReturn:
    if isinstance(error, MediaResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, MediaInputError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "MEDIA_VALIDATION_FAILED",
                "message": str(error),
                "field_errors": {error.field: [str(error)]},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "MEDIA_STATE_CONFLICT", "message": str(error)},
    ) from error


@router.post(
    "/audio/upload-intents",
    response_model=SuccessEnvelope[AudioUploadIntentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_audio_upload_intent(
    payload: AudioUploadIntentCreate,
    request: Request,
    actor: MentorActorDependency,
    service: MediaServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[AudioUploadIntentResponse]:
    try:
        result = await service.create_audio_upload_intent(actor, payload, request_id(request))
    except MediaInputError as error:
        raise_media_error(error)
    return success(request, result, version=result.media.row_version)


@router.post(
    "/{media_id}/complete",
    response_model=SuccessEnvelope[MediaAssetResponse],
)
async def complete_media_upload(
    media_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: MediaServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[MediaAssetResponse]:
    try:
        result = await service.complete_upload(actor, media_id, request_id(request))
    except (MediaResourceNotFoundError, MediaConflictError) as error:
        raise_media_error(error)
    return success(request, result, version=result.row_version)


@router.get("/{media_id}", response_model=SuccessEnvelope[MediaAssetResponse])
async def read_media_asset(
    media_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[MediaAssetResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_asset(actor, media_id)
    except MediaResourceNotFoundError as error:
        raise_media_error(error)
    return success(request, result, version=result.row_version)


@router.post(
    "/{media_id}/playback-url",
    response_model=SuccessEnvelope[PlaybackUrlResponse],
)
async def create_media_playback_url(
    media_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: MediaServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[PlaybackUrlResponse]:
    try:
        result = await service.create_playback_url(actor, media_id, request_id(request))
    except (MediaResourceNotFoundError, MediaConflictError) as error:
        raise_media_error(error)
    return success(request, result)
