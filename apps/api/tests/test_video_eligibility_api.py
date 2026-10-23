from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.mentoring.access import MentorActor, get_mentor_actor
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store
from app.modules.video.models import (
    EligibilityDecision,
    EligibilityReviewStatus,
    VideoVersionStatus,
)
from app.modules.video.router import get_video_eligibility_service
from app.modules.video.schemas import (
    ChecklistCriterionResponse,
    EligibilityCheckResponse,
    EligibilityDraftUpdate,
    EligibilityFinalize,
    EligibilityReviewResponse,
    VideoEligibilityResponse,
)

ORGANIZATION_ID = UUID("75000000-0000-4000-8000-000000000001")
PARTICIPANT = ParticipantActor(UUID("75000000-0000-4000-8000-000000000002"), ORGANIZATION_ID)
MENTOR = MentorActor(UUID("75000000-0000-4000-8000-000000000003"), ORGANIZATION_ID)
VIDEO_VERSION_ID = UUID("75000000-0000-4000-8000-000000000004")
ATTEMPT_ID = UUID("75000000-0000-4000-8000-000000000005")
REVIEW_ID = UUID("75000000-0000-4000-8000-000000000006")
ENROLLMENT_ID = UUID("75000000-0000-4000-8000-000000000007")
PART_ID = UUID("75000000-0000-4000-8000-000000000008")
KEY = UUID("75000000-0000-4000-8000-000000000009")
NOW = datetime(2026, 10, 23, tzinfo=UTC)


def eligibility_response(*, final: bool = False) -> VideoEligibilityResponse:
    decision = EligibilityDecision.ELIGIBLE if final else None
    review = EligibilityReviewResponse(
        id=REVIEW_ID,
        reviewer_id=MENTOR.user_id,
        checklist_version="technical-v1",
        decision=decision,
        reason=None,
        status=EligibilityReviewStatus.FINAL if final else EligibilityReviewStatus.DRAFT,
        finalized_at=NOW if final else None,
        row_version=2 if final else 1,
        checks=[
            EligibilityCheckResponse(code=code, passed=True, note=None)
            for code in ("duration_ok", "audio_clear", "continuous_recording")
        ],
    )
    return VideoEligibilityResponse(
        video_version_id=VIDEO_VERSION_ID,
        attempt_id=ATTEMPT_ID,
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
        video_url="https://youtu.be/example",
        recorded_on=date(2026, 10, 20),
        submitted_at=NOW,
        video_status=VideoVersionStatus.AVAILABLE if final else VideoVersionStatus.SUBMITTED,
        checklist_version="technical-v1",
        criteria=[
            ChecklistCriterionResponse(code=code, label=code, required=True)
            for code in ("duration_ok", "audio_clear", "continuous_recording")
        ],
        review=review,
        allowed_actions=["start_academic_assessment"]
        if final
        else ["edit_eligibility", "finalize_eligibility"],
    )


class StubEligibilityService:
    async def list_for_mentor(self, actor: MentorActor) -> list[VideoEligibilityResponse]:
        assert actor == MENTOR
        return [eligibility_response()]

    async def list_for_participant(self, actor: ParticipantActor) -> list[VideoEligibilityResponse]:
        assert actor == PARTICIPANT
        return [eligibility_response(final=True)]

    async def get_for_mentor(
        self, actor: MentorActor, video_version_id: UUID
    ) -> VideoEligibilityResponse:
        assert actor == MENTOR and video_version_id == VIDEO_VERSION_ID
        return eligibility_response()

    async def save_draft(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: EligibilityDraftUpdate,
        request_id: UUID,
    ) -> VideoEligibilityResponse:
        del request_id
        assert actor == MENTOR and video_version_id == VIDEO_VERSION_ID
        assert len(payload.checks) == 3
        return eligibility_response()

    async def finalize(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: EligibilityFinalize,
        request_id: UUID,
    ) -> VideoEligibilityResponse:
        del request_id
        assert actor == MENTOR and video_version_id == VIDEO_VERSION_ID
        assert payload.decision is EligibilityDecision.ELIGIBLE
        return eligibility_response(final=True)


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


def eligibility_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: PARTICIPANT
    app.dependency_overrides[get_mentor_actor] = lambda: MENTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_video_eligibility_service] = lambda: StubEligibilityService()
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    return TestClient(app)


def checklist_payload(expected_version: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "checklist_version": "technical-v1",
        "decision": "eligible",
        "reason": None,
        "checks": [
            {"code": code, "passed": True, "note": None}
            for code in ("duration_ok", "audio_clear", "continuous_recording")
        ],
    }
    if expected_version is not None:
        payload["expected_version"] = expected_version
    return payload


def test_mentor_saves_and_finalizes_versioned_eligibility_review() -> None:
    with eligibility_client() as client:
        queue = client.get("/api/v1/mentor/video-versions")
        detail = client.get(f"/api/v1/video-versions/{VIDEO_VERSION_ID}")
        draft = client.put(
            f"/api/v1/video-versions/{VIDEO_VERSION_ID}/eligibility-draft",
            headers={"Idempotency-Key": str(KEY)},
            json=checklist_payload(),
        )
        final = client.post(
            f"/api/v1/video-versions/{VIDEO_VERSION_ID}/eligibility",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json=checklist_payload(expected_version=1),
        )

    assert queue.status_code == 200
    assert detail.status_code == 200
    assert draft.json()["data"]["review"]["status"] == "draft"
    assert final.json()["data"]["review"]["decision"] == "eligible"
    assert final.json()["data"]["video_status"] == "available"


def test_participant_projection_exposes_final_technical_result() -> None:
    with eligibility_client() as client:
        result = client.get("/api/v1/me/video-results")

    assert result.status_code == 200
    assert result.json()["data"][0]["review"]["status"] == "final"
