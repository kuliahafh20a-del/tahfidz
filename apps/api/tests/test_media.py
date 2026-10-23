import base64
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.media.models import MediaAsset, MediaAssetStatus, MediaPurpose
from app.modules.media.router import get_media_service
from app.modules.media.schemas import (
    AudioUploadIntentCreate,
    AudioUploadIntentResponse,
    MediaAssetResponse,
    PlaybackUrlResponse,
)
from app.modules.media.service import (
    MediaResourceNotFoundError,
    MediaService,
    MediaValidationWorker,
)
from app.modules.media.storage import (
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectStorageError,
    S3ObjectStorage,
)
from app.modules.mentoring.access import MentorActor, get_mentor_actor

ORGANIZATION_ID = UUID("76000000-0000-4000-8000-000000000001")
MENTOR = MentorActor(UUID("76000000-0000-4000-8000-000000000002"), ORGANIZATION_ID)
MEDIA_ID = UUID("76000000-0000-4000-8000-000000000003")
MISSING_MEDIA_ID = UUID("76000000-0000-4000-8000-000000000004")
NOW = datetime(2026, 10, 23, 4, 0, tzinfo=UTC)
CHECKSUM = "ab" * 32


def media_settings() -> Settings:
    return Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
            "OBJECT_STORAGE_ENDPOINT": "http://object-storage:9000",
            "OBJECT_STORAGE_PUBLIC_ENDPOINT": "https://media.example.test",
            "OBJECT_STORAGE_ACCESS_KEY": "test-access-key",
            "OBJECT_STORAGE_SECRET_KEY": "test-secret-key",
        }
    )


def asset(status: MediaAssetStatus = MediaAssetStatus.AVAILABLE) -> MediaAsset:
    return MediaAsset(
        id=MEDIA_ID,
        owner_id=MENTOR.user_id,
        organization_id=ORGANIZATION_ID,
        storage_key=f"audio/{ORGANIZATION_ID}/{MEDIA_ID}",
        original_file_name="umpan-balik.m4a",
        mime_type="audio/mp4",
        size_bytes=824_312,
        checksum=CHECKSUM,
        purpose=MediaPurpose.MENTOR_FEEDBACK,
        status=status,
        validation_attempts=1,
        created_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        validated_at=NOW if status is MediaAssetStatus.AVAILABLE else None,
        row_version=1,
    )


def media_response(status: MediaAssetStatus = MediaAssetStatus.AVAILABLE) -> MediaAssetResponse:
    return MediaService._response(asset(status))


def test_media_model_and_request_constraints() -> None:
    table = Base.metadata.tables["app.media_assets"]
    assert MediaAsset.__table__ is table
    assert any(index.name == "uq_media_assets__storage_key" for index in table.indexes)
    assert any(
        constraint.name == "ck_media_assets__checksum_sha256" for constraint in table.constraints
    )

    request = AudioUploadIntentCreate(
        file_name="umpan-balik.m4a",
        content_type="AUDIO/MP4",
        size_bytes=824_312,
        sha256=CHECKSUM.upper(),
    )
    assert request.content_type == "audio/mp4"
    assert request.sha256 == CHECKSUM

    with pytest.raises(ValidationError, match="must not contain a path"):
        AudioUploadIntentCreate(
            file_name="../secret.m4a",
            content_type="audio/mp4",
            size_bytes=1,
            sha256=CHECKSUM,
        )


def test_s3_signer_uses_short_lived_urls_without_exposing_secret() -> None:
    storage = S3ObjectStorage(media_settings())
    upload = storage.upload_request(f"audio/{MEDIA_ID}", "audio/mp4", CHECKSUM, now=NOW)
    query = parse_qs(urlsplit(upload.url).query)

    assert upload.url.startswith("https://media.example.test/yaqin-private/audio/")
    assert query["X-Amz-Expires"] == ["300"]
    assert query["X-Amz-SignedHeaders"] == ["content-type;host;x-amz-checksum-sha256"]
    assert "test-secret-key" not in upload.url
    assert (
        upload.required_headers["x-amz-checksum-sha256"]
        == base64.b64encode(bytes.fromhex(CHECKSUM)).decode()
    )


def test_worker_classifies_valid_failed_and_quarantined_media() -> None:
    record = asset(MediaAssetStatus.VALIDATING)
    valid = ObjectMetadata(
        "audio/mp4", record.size_bytes, base64.b64encode(bytes.fromhex(CHECKSUM)).decode()
    )
    wrong_size = ObjectMetadata("audio/mp4", record.size_bytes + 1, valid.checksum_sha256)

    assert (
        MediaValidationWorker.classify(record, valid, frozenset({"audio/mp4"})).status
        is MediaAssetStatus.AVAILABLE
    )
    quarantined = MediaValidationWorker.classify(record, wrong_size, frozenset({"audio/mp4"}))
    assert quarantined.status is MediaAssetStatus.QUARANTINED
    assert quarantined.error_code == "size_mismatch"
    assert (
        MediaValidationWorker.storage_error_result(ObjectNotFoundError("missing"), 1, 5).status
        is MediaAssetStatus.FAILED
    )
    assert (
        MediaValidationWorker.storage_error_result(ObjectStorageError("unavailable"), 1, 5).status
        is MediaAssetStatus.PENDING_VALIDATION
    )
    assert (
        MediaValidationWorker.storage_error_result(ObjectStorageError("unavailable"), 5, 5).status
        is MediaAssetStatus.FAILED
    )


def test_audit_state_excludes_storage_location_checksum_and_signed_urls() -> None:
    state = MediaService._state(asset())
    assert set(state) == {"media_id", "purpose", "content_type", "size_bytes", "status"}


class StubMediaService:
    async def create_audio_upload_intent(
        self,
        actor: MentorActor,
        payload: AudioUploadIntentCreate,
        request_id: UUID,
    ) -> AudioUploadIntentResponse:
        del request_id
        assert actor == MENTOR
        assert payload.sha256 == CHECKSUM
        return AudioUploadIntentResponse(
            media=media_response(MediaAssetStatus.UPLOADING),
            upload_url="https://media.example.test/signed-upload",
            required_headers={"Content-Type": "audio/mp4"},
            expires_at=NOW,
        )

    async def complete_upload(
        self, actor: MentorActor, media_id: UUID, request_id: UUID
    ) -> MediaAssetResponse:
        del request_id
        assert actor == MENTOR and media_id == MEDIA_ID
        return media_response(MediaAssetStatus.PENDING_VALIDATION)

    async def get_asset(self, actor: MentorActor, media_id: UUID) -> MediaAssetResponse:
        assert actor == MENTOR
        if media_id == MISSING_MEDIA_ID:
            raise MediaResourceNotFoundError("not found")
        assert media_id == MEDIA_ID
        return media_response()

    async def create_playback_url(
        self, actor: MentorActor, media_id: UUID, request_id: UUID
    ) -> PlaybackUrlResponse:
        del request_id
        assert actor == MENTOR and media_id == MEDIA_ID
        return PlaybackUrlResponse(
            media_id=MEDIA_ID,
            playback_url="https://media.example.test/signed-playback",
            expires_at=NOW,
        )


def media_client() -> TestClient:
    application = create_app()
    application.dependency_overrides[get_mentor_actor] = lambda: MENTOR
    application.dependency_overrides[require_csrf] = lambda: None
    application.dependency_overrides[get_media_service] = lambda: StubMediaService()
    return TestClient(application)


def test_private_audio_upload_metadata_and_playback_endpoints() -> None:
    payload = {
        "file_name": "umpan-balik.m4a",
        "content_type": "audio/mp4",
        "size_bytes": 824_312,
        "sha256": CHECKSUM,
        "purpose": "mentor_feedback",
    }
    with media_client() as client:
        intent = client.post("/api/v1/media/audio/upload-intents", json=payload)
        completed = client.post(f"/api/v1/media/{MEDIA_ID}/complete")
        metadata = client.get(f"/api/v1/media/{MEDIA_ID}")
        playback = client.post(f"/api/v1/media/{MEDIA_ID}/playback-url")
        hidden = client.get(f"/api/v1/media/{MISSING_MEDIA_ID}")

    assert intent.status_code == 201
    assert intent.json()["data"]["media"]["status"] == "uploading"
    assert completed.json()["data"]["status"] == "pending_validation"
    assert metadata.json()["data"]["status"] == "available"
    assert playback.json()["data"]["playback_url"].endswith("signed-playback")
    assert playback.headers["cache-control"] == "no-store"
    assert hidden.status_code == 404
