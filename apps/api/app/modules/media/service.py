"""Private media commands, object authorization, and worker validation."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.time import utc_now
from app.modules.audit.models import AuditEvent
from app.modules.media.models import MediaAsset, MediaAssetStatus
from app.modules.media.schemas import (
    AudioUploadIntentCreate,
    AudioUploadIntentResponse,
    MediaAssetResponse,
    PlaybackUrlResponse,
)
from app.modules.media.storage import (
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectStorageError,
    S3ObjectStorage,
)
from app.modules.mentoring.access import MentorActor


class MediaResourceNotFoundError(LookupError):
    pass


class MediaConflictError(ValueError):
    pass


class MediaInputError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


ACTIVE_UPLOAD_STATUSES = {
    MediaAssetStatus.UPLOADING,
    MediaAssetStatus.PENDING_VALIDATION,
    MediaAssetStatus.VALIDATING,
    MediaAssetStatus.AVAILABLE,
}


class MediaService:
    """Issue short-lived URLs while persisting only safe media metadata."""

    def __init__(
        self,
        session: AsyncSession,
        storage: S3ObjectStorage,
        settings: Settings,
    ) -> None:
        self.session = session
        self.storage = storage
        self.allowed_content_types = settings.audio_allowed_content_type_values
        self.max_size_bytes = settings.audio_max_size_bytes

    async def create_audio_upload_intent(
        self,
        actor: MentorActor,
        payload: AudioUploadIntentCreate,
        request_id: UUID,
    ) -> AudioUploadIntentResponse:
        self._validate_upload(payload)
        asset = await self.session.scalar(
            select(MediaAsset)
            .where(
                MediaAsset.owner_id == actor.user_id,
                MediaAsset.organization_id == actor.organization_id,
                MediaAsset.checksum == payload.sha256,
                MediaAsset.mime_type == payload.content_type,
                MediaAsset.size_bytes == payload.size_bytes,
                MediaAsset.purpose == payload.purpose,
                MediaAsset.status.in_(ACTIVE_UPLOAD_STATUSES),
            )
            .order_by(MediaAsset.created_at.desc())
            .limit(1)
        )
        if asset is None:
            media_id = uuid4()
            asset = MediaAsset(
                id=media_id,
                owner_id=actor.user_id,
                organization_id=actor.organization_id,
                storage_key=f"audio/{actor.organization_id}/{media_id}",
                original_file_name=payload.file_name,
                mime_type=payload.content_type,
                size_bytes=payload.size_bytes,
                checksum=payload.sha256,
                purpose=payload.purpose,
                status=MediaAssetStatus.UPLOADING,
            )
            self.session.add(asset)
            await self.session.flush()
            self.session.add(
                self._audit(
                    actor.user_id,
                    request_id,
                    "media.upload_intent_created",
                    asset,
                    after=self._state(asset),
                )
            )
            await self.session.commit()

        signed = self.storage.upload_request(
            asset.storage_key,
            asset.mime_type,
            asset.checksum,
        )
        return AudioUploadIntentResponse(
            media=self._response(asset),
            upload_url=signed.url,
            required_headers=signed.required_headers,
            expires_at=signed.expires_at,
        )

    async def complete_upload(
        self,
        actor: MentorActor,
        media_id: UUID,
        request_id: UUID,
    ) -> MediaAssetResponse:
        asset = await self._asset_for_actor(actor, media_id, lock=True)
        if asset.status is MediaAssetStatus.UPLOADING:
            asset.status = MediaAssetStatus.PENDING_VALIDATION
            asset.completed_at = utc_now()
            asset.validation_error_code = None
            await self.session.flush()
            self.session.add(
                self._audit(
                    actor.user_id,
                    request_id,
                    "media.upload_completed",
                    asset,
                    after=self._state(asset),
                )
            )
            await self.session.commit()
        elif asset.status not in {
            MediaAssetStatus.PENDING_VALIDATION,
            MediaAssetStatus.VALIDATING,
            MediaAssetStatus.AVAILABLE,
        }:
            raise MediaConflictError("this media upload can no longer be completed")
        return self._response(asset)

    async def get_asset(self, actor: MentorActor, media_id: UUID) -> MediaAssetResponse:
        return self._response(await self._asset_for_actor(actor, media_id))

    async def create_playback_url(
        self,
        actor: MentorActor,
        media_id: UUID,
        request_id: UUID,
    ) -> PlaybackUrlResponse:
        asset = await self._asset_for_actor(actor, media_id)
        if asset.status is not MediaAssetStatus.AVAILABLE:
            raise MediaConflictError("only validated media can be played")
        signed = self.storage.playback_request(asset.storage_key)
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "media.playback_url_issued",
                asset,
                after={"media_id": str(asset.id), "status": asset.status.value},
            )
        )
        await self.session.commit()
        return PlaybackUrlResponse(
            media_id=asset.id,
            playback_url=signed.url,
            expires_at=signed.expires_at,
        )

    def _validate_upload(self, payload: AudioUploadIntentCreate) -> None:
        if payload.content_type not in self.allowed_content_types:
            raise MediaInputError("content_type", "audio content type is not allowed")
        if payload.size_bytes > self.max_size_bytes:
            raise MediaInputError("size_bytes", "audio exceeds the configured size limit")

    async def _asset_for_actor(
        self,
        actor: MentorActor,
        media_id: UUID,
        *,
        lock: bool = False,
    ) -> MediaAsset:
        statement = select(MediaAsset).where(
            MediaAsset.id == media_id,
            MediaAsset.owner_id == actor.user_id,
            MediaAsset.organization_id == actor.organization_id,
        )
        if lock:
            statement = statement.with_for_update()
        asset = await self.session.scalar(statement)
        if asset is None:
            raise MediaResourceNotFoundError("media asset not found in the active scope")
        return asset

    @staticmethod
    def _response(asset: MediaAsset) -> MediaAssetResponse:
        return MediaAssetResponse(
            id=asset.id,
            file_name=asset.original_file_name,
            content_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            sha256=asset.checksum,
            purpose=asset.purpose,
            status=asset.status,
            validation_error_code=asset.validation_error_code,
            created_at=asset.created_at,
            completed_at=asset.completed_at,
            validated_at=asset.validated_at,
            row_version=asset.row_version,
        )

    @staticmethod
    def _state(asset: MediaAsset) -> dict[str, object]:
        return {
            "media_id": str(asset.id),
            "purpose": asset.purpose.value,
            "content_type": asset.mime_type,
            "size_bytes": asset.size_bytes,
            "status": asset.status.value,
        }

    @staticmethod
    def _audit(
        actor_id: UUID | None,
        request_id: UUID | None,
        action: str,
        asset: MediaAsset,
        *,
        after: dict[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="media_asset",
            object_reference=str(asset.id),
            request_id=request_id,
            before_data=None,
            after_data=after,
        )


@dataclass(frozen=True, slots=True)
class MediaValidationResult:
    status: MediaAssetStatus
    error_code: str | None


class MediaValidationWorker:
    """Claim and validate completed uploads without holding a DB lock over network I/O."""

    def __init__(
        self,
        session: AsyncSession,
        storage: S3ObjectStorage,
        settings: Settings,
    ) -> None:
        self.session = session
        self.storage = storage
        self.allowed_content_types = settings.audio_allowed_content_type_values
        self.max_attempts = settings.media_validation_max_attempts

    async def run_once(self) -> bool:
        asset = await self.session.scalar(
            select(MediaAsset)
            .where(MediaAsset.status == MediaAssetStatus.PENDING_VALIDATION)
            .order_by(MediaAsset.created_at, MediaAsset.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if asset is None:
            await self.session.rollback()
            return False
        asset.status = MediaAssetStatus.VALIDATING
        asset.validation_attempts += 1
        asset.validation_error_code = None
        media_id = asset.id
        storage_key = asset.storage_key
        await self.session.commit()

        try:
            metadata = await self.storage.inspect_object(storage_key)
        except ObjectStorageError as error:
            result = self.storage_error_result(error, asset.validation_attempts, self.max_attempts)
        else:
            result = self.classify(asset, metadata, self.allowed_content_types)

        claimed = await self.session.scalar(
            select(MediaAsset).where(MediaAsset.id == media_id).with_for_update()
        )
        if claimed is None or claimed.status is not MediaAssetStatus.VALIDATING:
            await self.session.rollback()
            return True
        if (
            result.status is MediaAssetStatus.PENDING_VALIDATION
            and claimed.validation_attempts >= self.max_attempts
        ):
            result = MediaValidationResult(MediaAssetStatus.FAILED, "storage_unavailable")
        claimed.status = result.status
        claimed.validation_error_code = result.error_code
        claimed.validated_at = (
            utc_now()
            if result.status
            in {
                MediaAssetStatus.AVAILABLE,
                MediaAssetStatus.FAILED,
                MediaAssetStatus.QUARANTINED,
            }
            else None
        )
        self.session.add(
            MediaService._audit(
                None,
                None,
                "media.validation_completed"
                if claimed.validated_at is not None
                else "media.validation_deferred",
                claimed,
                after={
                    "media_id": str(claimed.id),
                    "status": claimed.status.value,
                    "validation_error_code": claimed.validation_error_code,
                    "validation_attempts": claimed.validation_attempts,
                },
            )
        )
        await self.session.commit()
        return True

    @staticmethod
    def classify(
        asset: MediaAsset,
        metadata: ObjectMetadata,
        allowed_content_types: frozenset[str],
    ) -> MediaValidationResult:
        if (
            metadata.content_type not in allowed_content_types
            or metadata.content_type != asset.mime_type
        ):
            return MediaValidationResult(MediaAssetStatus.QUARANTINED, "content_type_mismatch")
        if metadata.size_bytes != asset.size_bytes:
            return MediaValidationResult(MediaAssetStatus.QUARANTINED, "size_mismatch")
        if metadata.checksum_sha256 is None:
            return MediaValidationResult(MediaAssetStatus.QUARANTINED, "checksum_missing")
        try:
            checksum_hex = base64.b64decode(metadata.checksum_sha256, validate=True).hex()
        except binascii.Error, ValueError:
            return MediaValidationResult(MediaAssetStatus.QUARANTINED, "checksum_invalid")
        if checksum_hex != asset.checksum:
            return MediaValidationResult(MediaAssetStatus.QUARANTINED, "checksum_mismatch")
        return MediaValidationResult(MediaAssetStatus.AVAILABLE, None)

    @staticmethod
    def storage_error_result(
        error: ObjectStorageError,
        attempts: int,
        max_attempts: int,
    ) -> MediaValidationResult:
        if isinstance(error, ObjectNotFoundError):
            return MediaValidationResult(MediaAssetStatus.FAILED, "object_not_found")
        if attempts >= max_attempts:
            return MediaValidationResult(MediaAssetStatus.FAILED, "storage_unavailable")
        return MediaValidationResult(MediaAssetStatus.PENDING_VALIDATION, "storage_unavailable")
