from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.main import create_app
from app.modules.assessments.models import (
    AssessmentStatus,
    VideoAssessment,
    VideoAssessmentOutcome,
)
from app.modules.assessments.schemas import IncidentInput
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.mentoring.access import MentorActor, get_mentor_actor
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store
from app.modules.video_assessments.router import get_video_assessment_service
from app.modules.video_assessments.schemas import (
    VideoAssessmentDraftCreate,
    VideoAssessmentDraftUpdate,
    VideoAssessmentPlayback,
    VideoAssessmentResponse,
)
from app.modules.video_assessments.service import (
    VideoAssessmentService,
    VideoAssessmentVersionConflictError,
)

PARTICIPANT = ParticipantActor(UUID(int=1), UUID(int=2))
MENTOR = MentorActor(UUID(int=3), PARTICIPANT.organization_id)
ASSESSMENT_ID = UUID(int=4)
VIDEO_VERSION_ID = UUID(int=5)
ENROLLMENT_ID = UUID(int=6)
PART_ID = UUID(int=7)
POLICY_ID = UUID(int=8)
REVIEW_ID = UUID(int=9)
KEY = UUID(int=10)
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def response(*, final: bool = False, version: int = 1) -> VideoAssessmentResponse:
    return VideoAssessmentResponse(
        assessment_id=ASSESSMENT_ID,
        video_version_id=VIDEO_VERSION_ID,
        eligibility_review_id=REVIEW_ID,
        participant=SessionParticipant(
            enrollment_id=ENROLLMENT_ID,
            user_id=PARTICIPANT.user_id,
            display_name="Peserta Contoh",
            nim="NIM-001",
        ),
        part_id=PART_ID,
        part_no=1,
        part_name="Bagian 1",
        cycle_no=1,
        revision_no=0,
        video_version_no=1,
        video_url="https://youtube.com/watch?v=contoh",
        status=AssessmentStatus.FINAL if final else AssessmentStatus.DRAFT,
        manual_score=8,
        mentor_note="Perbaiki panjang pendek.",
        counted_errors=4,
        outcome=VideoAssessmentOutcome.NOT_ENOUGH,
        incidents=[],
        feedback_audio=None,
        actual_at=NOW,
        finalized_at=NOW if final else None,
        policy_version_id=POLICY_ID,
        policy_version="2026.1",
        row_version=version,
        allowed_actions=["view_result"] if final else ["edit", "finalize"],
    )


class StubService:
    async def create_draft(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: VideoAssessmentDraftCreate,
        request_id: UUID,
    ) -> VideoAssessmentResponse:
        del request_id
        assert actor == MENTOR and video_version_id == VIDEO_VERSION_ID
        assert payload.manual_score == 8
        return response()

    async def update_draft(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        payload: VideoAssessmentDraftUpdate,
        request_id: UUID,
    ) -> VideoAssessmentResponse:
        del request_id
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        assert payload.expected_version == 1
        return response(version=2)

    async def finalize(
        self, actor: MentorActor, assessment_id: UUID, expected_version: int, request_id: UUID
    ) -> VideoAssessmentResponse:
        del request_id
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID and expected_version == 2
        return response(final=True, version=3)

    async def get_for_mentor(
        self, actor: MentorActor, assessment_id: UUID
    ) -> VideoAssessmentResponse:
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        return response()

    async def list_for_mentor(self, actor: MentorActor) -> list[VideoAssessmentResponse]:
        assert actor == MENTOR
        return [response()]

    async def list_for_participant(self, actor: ParticipantActor) -> list[VideoAssessmentResponse]:
        assert actor == PARTICIPANT
        return [response(final=True, version=3)]

    async def history_for_mentor(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> list[VideoAssessmentResponse]:
        assert actor == MENTOR and enrollment_id == ENROLLMENT_ID
        return [response(final=True, version=3)]

    async def playback_for_mentor(
        self, actor: MentorActor, assessment_id: UUID, request_id: UUID
    ) -> VideoAssessmentPlayback:
        del request_id
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        return VideoAssessmentPlayback(
            assessment_id=ASSESSMENT_ID,
            playback_url="https://storage.example/audio",
            expires_at=NOW,
        )

    async def playback_for_participant(
        self, actor: ParticipantActor, assessment_id: UUID, request_id: UUID
    ) -> VideoAssessmentPlayback:
        del request_id
        assert actor == PARTICIPANT and assessment_id == ASSESSMENT_ID
        return VideoAssessmentPlayback(
            assessment_id=ASSESSMENT_ID,
            playback_url="https://storage.example/audio",
            expires_at=NOW,
        )


class StubIdempotency:
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


class ReplayIdempotency(StubIdempotency):
    async def claim(self, **kwargs: object) -> IdempotencyClaim:
        claim = await super().claim(**kwargs)
        return IdempotencyClaim(
            record=claim.record,
            replay_body=response().model_dump(mode="json"),
        )

    async def complete(self, claim: IdempotencyClaim, **kwargs: object) -> None:
        del claim, kwargs
        raise AssertionError("an idempotency replay must not be completed twice")


def client(service: object | None = None, idempotency: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_mentor_actor] = lambda: MENTOR
    app.dependency_overrides[get_participant_actor] = lambda: PARTICIPANT
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_video_assessment_service] = lambda: service or StubService()
    app.dependency_overrides[get_idempotency_store] = lambda: idempotency or StubIdempotency()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost/test"}
    )
    return TestClient(app)


def test_video_assessment_policy_ignores_manual_score() -> None:
    rules = {
        "schema_version": 1,
        "score": {
            "minimum": 1,
            "maximum": 10,
            "step": 1,
            "allow_fractional": False,
            "display_decimals": 0,
            "bands": [
                {"minimum": 1, "maximum": 4, "description": "Dasar"},
                {"minimum": 5, "maximum": 7, "description": "Baik"},
                {"minimum": 8, "maximum": 10, "description": "Sangat baik"},
            ],
        },
        "video_assessment": {"maximum_errors_for_enough": 3},
    }
    assert VideoAssessmentService.outcome_for(0, rules) is VideoAssessmentOutcome.ENOUGH
    assert VideoAssessmentService.outcome_for(3, rules) is VideoAssessmentOutcome.ENOUGH
    assert VideoAssessmentService.outcome_for(4, rules) is VideoAssessmentOutcome.NOT_ENOUGH
    assert (
        VideoAssessmentService.counted_errors(
            [
                IncidentInput(
                    location_text="Ayat 1",
                    video_second=10,
                    primary_category="word_choice",
                    counted=True,
                ),
                IncidentInput(
                    location_text="Ayat 2",
                    video_second=20,
                    primary_category="pause",
                    counted=False,
                    self_corrected=True,
                ),
            ]
        )
        == 1
    )


def test_video_assessment_model_is_registered() -> None:
    table = Base.metadata.tables["app.video_assessments"]
    assert VideoAssessment.__table__ is table
    assert table.fullname == "app.video_assessments"
    assert any(
        constraint.name == "ck_video_assessments__counted_errors_nonnegative"
        for constraint in table.constraints
    )


def test_video_assessment_mutations_and_scoped_results() -> None:
    payload = {
        "manual_score": 8,
        "mentor_note": "Perbaiki panjang pendek.",
        "feedback_audio_id": None,
        "incidents": [],
    }
    with client() as test_client:
        created = test_client.post(
            f"/api/v1/video-versions/{VIDEO_VERSION_ID}/assessment",
            headers={"Idempotency-Key": str(KEY)},
            json=payload,
        )
        updated = test_client.patch(
            f"/api/v1/video-assessments/{ASSESSMENT_ID}",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={**payload, "expected_version": 1},
        )
        finalized = test_client.post(
            f"/api/v1/video-assessments/{ASSESSMENT_ID}/finalize",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 2))},
            json={"expected_version": 2},
        )
        participant_results = test_client.get("/api/v1/me/video-assessment-results")
        mentor_history = test_client.get(
            f"/api/v1/enrollments/{ENROLLMENT_ID}/video-assessment-history"
        )

    assert created.status_code == 201
    assert updated.json()["version"] == 2
    assert finalized.json()["data"]["outcome"] == "not_enough"
    assert participant_results.json()["data"][0]["manual_score"] == 8
    assert mentor_history.json()["data"][0]["counted_errors"] == 4


def test_stale_video_assessment_update_reports_current_version() -> None:
    class StaleService(StubService):
        async def update_draft(
            self,
            actor: MentorActor,
            assessment_id: UUID,
            payload: VideoAssessmentDraftUpdate,
            request_id: UUID,
        ) -> VideoAssessmentResponse:
            del actor, assessment_id, payload, request_id
            raise VideoAssessmentVersionConflictError(4)

    with client(StaleService()) as test_client:
        result = test_client.patch(
            f"/api/v1/video-assessments/{ASSESSMENT_ID}",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "manual_score": 8,
                "mentor_note": None,
                "feedback_audio_id": None,
                "incidents": [],
                "expected_version": 1,
            },
        )

    assert result.status_code == 409
    assert result.json()["code"] == "ASSESSMENT_VERSION_CONFLICT"
    assert result.json()["details"]["current_version"] == 4


def test_video_assessment_create_replays_an_idempotent_response() -> None:
    class ExplodingService(StubService):
        async def create_draft(
            self,
            actor: MentorActor,
            video_version_id: UUID,
            payload: VideoAssessmentDraftCreate,
            request_id: UUID,
        ) -> VideoAssessmentResponse:
            del actor, video_version_id, payload, request_id
            raise AssertionError("service must not run for a completed idempotency key")

    with client(ExplodingService(), ReplayIdempotency()) as test_client:
        result = test_client.post(
            f"/api/v1/video-versions/{VIDEO_VERSION_ID}/assessment",
            headers={"Idempotency-Key": str(KEY)},
            json={"manual_score": 8, "incidents": []},
        )

    assert result.status_code == 201
    assert result.json()["data"]["assessment_id"] == str(ASSESSMENT_ID)
