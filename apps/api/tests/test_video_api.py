from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store
from app.modules.video.models import VideoAttemptStatus, VideoVersionStatus
from app.modules.video.router import get_video_submission_service
from app.modules.video.schemas import VideoAttemptResponse, VideoVersionCreate, VideoVersionResponse
from app.modules.video.service import VideoVersionConflictError

ACTOR = ParticipantActor(
    UUID("74000000-0000-4000-8000-000000000001"),
    UUID("74000000-0000-4000-8000-000000000002"),
)
ATTEMPT_ID = UUID("74000000-0000-4000-8000-000000000003")
ENROLLMENT_ID = UUID("74000000-0000-4000-8000-000000000004")
PART_ID = UUID("74000000-0000-4000-8000-000000000005")
KEY = UUID("74000000-0000-4000-8000-000000000006")
NOW = datetime(2026, 10, 23, tzinfo=UTC)


def response(*, submitted: bool = False) -> VideoAttemptResponse:
    return VideoAttemptResponse(
        id=ATTEMPT_ID,
        enrollment_id=ENROLLMENT_ID,
        part_id=PART_ID,
        part_no=1,
        part_name="Bagian 1",
        cycle_no=1,
        revision_no=0,
        status=VideoAttemptStatus.SUBMITTED if submitted else VideoAttemptStatus.OPEN,
        row_version=2 if submitted else 1,
        versions=[
            VideoVersionResponse(
                id=UUID("74000000-0000-4000-8000-000000000007"),
                version_no=1,
                video_url="https://youtu.be/example",
                recorded_on=date(2026, 10, 20),
                submitted_at=NOW,
                status=VideoVersionStatus.SUBMITTED,
            )
        ]
        if submitted
        else [],
        allowed_actions=["submit_version"],
    )


class StubVideoService:
    async def create_attempt(
        self, actor: ParticipantActor, part_id: UUID, request_id: UUID
    ) -> VideoAttemptResponse:
        del request_id
        assert actor == ACTOR and part_id == PART_ID
        return response()

    async def submit_version(
        self,
        actor: ParticipantActor,
        attempt_id: UUID,
        payload: VideoVersionCreate,
        request_id: UUID,
    ) -> VideoAttemptResponse:
        del request_id
        assert actor == ACTOR and attempt_id == ATTEMPT_ID
        assert payload.expected_version == 1 and payload.completeness_declared
        return response(submitted=True)

    async def get_attempt(self, actor: ParticipantActor, attempt_id: UUID) -> VideoAttemptResponse:
        assert actor == ACTOR and attempt_id == ATTEMPT_ID
        return response(submitted=True)


class ConcurrentConflictVideoService(StubVideoService):
    async def submit_version(
        self,
        actor: ParticipantActor,
        attempt_id: UUID,
        payload: VideoVersionCreate,
        request_id: UUID,
    ) -> VideoAttemptResponse:
        del actor, attempt_id, payload, request_id
        raise VideoVersionConflictError(current_version=2)


class StubIdempotencyStore:
    async def claim(self, **kwargs: object) -> IdempotencyClaim:
        return IdempotencyClaim(
            record=IdempotencyRecord(
                actor_id=UUID(str(kwargs["actor_id"])),
                idempotency_key=UUID(str(kwargs["idempotency_key"])),
                method=str(kwargs["method"]),
                normalized_path=str(kwargs["normalized_path"]),
                request_hash="0" * 64,
                request_id=UUID(str(kwargs["request_id"])),
                expires_at=NOW,
            )
        )

    async def complete(self, claim: IdempotencyClaim, **kwargs: object) -> None:
        del claim, kwargs


def video_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: ACTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_video_submission_service] = lambda: StubVideoService()
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    return TestClient(app)


def test_participant_creates_attempt_and_submits_media_version() -> None:
    with video_client() as client:
        created = client.post(
            "/api/v1/video-attempts",
            headers={"Idempotency-Key": str(KEY)},
            json={"part_id": str(PART_ID)},
        )
        submitted = client.post(
            f"/api/v1/video-attempts/{ATTEMPT_ID}/versions",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={
                "video_url": "https://youtu.be/example",
                "recorded_on": "2026-10-20",
                "completeness_declared": True,
                "expected_version": 1,
            },
        )
        loaded = client.get(f"/api/v1/video-attempts/{ATTEMPT_ID}")

    assert created.status_code == 201
    assert created.json()["data"]["cycle_no"] == 1
    assert created.json()["data"]["revision_no"] == 0
    assert submitted.status_code == 201
    assert submitted.json()["data"]["versions"][0]["version_no"] == 1
    assert loaded.status_code == 200


def test_stale_concurrent_version_request_is_rejected() -> None:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: ACTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_video_submission_service] = lambda: (
        ConcurrentConflictVideoService()
    )
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )

    with TestClient(app) as client:
        result = client.post(
            f"/api/v1/video-attempts/{ATTEMPT_ID}/versions",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "video_url": "https://youtu.be/example",
                "recorded_on": "2026-10-20",
                "completeness_declared": True,
                "expected_version": 1,
            },
        )

    assert result.status_code == 409
    assert result.json()["code"] == "VIDEO_VERSION_CONFLICT"
    assert result.json()["details"]["current_version"] == 2
