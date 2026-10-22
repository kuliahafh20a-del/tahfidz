from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.assessments.models import AssessmentStatus, ThemeOutcome
from app.modules.assessments.router import get_theme_assessment_service
from app.modules.assessments.schemas import (
    MentorParticipantResponse,
    ThemeAssessmentDraftCreate,
    ThemeAssessmentDraftUpdate,
    ThemeAssessmentResponse,
)
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.mentoring.access import MentorActor, get_mentor_actor
from app.modules.mentoring.schemas import SessionParticipant, SessionThemeResponse
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store

PARTICIPANT = ParticipantActor(
    UUID("72000000-0000-4000-8000-000000000001"),
    UUID("72000000-0000-4000-8000-000000000002"),
)
MENTOR = MentorActor(
    UUID("72000000-0000-4000-8000-000000000003"),
    PARTICIPANT.organization_id,
)
SESSION_ID = UUID("72000000-0000-4000-8000-000000000004")
ASSESSMENT_ID = UUID("72000000-0000-4000-8000-000000000005")
ENROLLMENT_ID = UUID("72000000-0000-4000-8000-000000000006")
THEME_ID = UUID("72000000-0000-4000-8000-000000000007")
PART_ID = UUID("72000000-0000-4000-8000-000000000008")
POLICY_ID = UUID("72000000-0000-4000-8000-000000000009")
KEY = UUID("72000000-0000-4000-8000-000000000010")
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def assessment_response(
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
    version: int = 1,
) -> ThemeAssessmentResponse:
    return ThemeAssessmentResponse(
        assessment_id=ASSESSMENT_ID,
        session_id=SESSION_ID,
        session_theme_id=UUID("72000000-0000-4000-8000-000000000011"),
        participant=SessionParticipant(
            enrollment_id=ENROLLMENT_ID,
            user_id=PARTICIPANT.user_id,
            display_name="Peserta Contoh",
            nim="NIM-001",
        ),
        theme=SessionThemeResponse(
            id=UUID("72000000-0000-4000-8000-000000000011"),
            theme_id=THEME_ID,
            code="T01",
            name="An-Naba ayat 1-16",
            part_id=PART_ID,
            part_no=1,
            part_name="Bagian 1",
        ),
        status=assessment_status,
        attempt_no=1,
        outcome=ThemeOutcome.ENOUGH,
        manual_score=8,
        actual_at=NOW,
        finalized_at=NOW if assessment_status is AssessmentStatus.FINAL else None,
        mentor_note="Hafalan lancar",
        incidents=[],
        counted_incidents=0,
        policy_version_id=POLICY_ID,
        policy_version="2026.1",
        row_version=version,
        allowed_actions=[]
        if assessment_status is AssessmentStatus.FINAL
        else ["edit", "review", "finalize"],
    )


class StubAssessmentService:
    async def create_draft(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: ThemeAssessmentDraftCreate,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        del request_id
        assert actor == MENTOR and session_id == SESSION_ID and payload.manual_score == 8
        return assessment_response()

    async def update_draft(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        payload: ThemeAssessmentDraftUpdate,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        del request_id
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        assert payload.expected_version == 1
        return assessment_response(version=2)

    async def finalize(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        expected_version: int,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        del request_id
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        assert expected_version == 2
        return assessment_response(AssessmentStatus.FINAL, 3)

    async def get_for_mentor(
        self, actor: MentorActor, assessment_id: UUID
    ) -> ThemeAssessmentResponse:
        assert actor == MENTOR and assessment_id == ASSESSMENT_ID
        return assessment_response()

    async def list_for_session(
        self, actor: MentorActor, session_id: UUID
    ) -> list[ThemeAssessmentResponse]:
        assert actor == MENTOR and session_id == SESSION_ID
        return [assessment_response()]

    async def list_participant_results(
        self, actor: ParticipantActor
    ) -> list[ThemeAssessmentResponse]:
        assert actor == PARTICIPANT
        return [assessment_response(AssessmentStatus.FINAL, 3)]

    async def list_mentor_participants(self, actor: MentorActor) -> list[MentorParticipantResponse]:
        assert actor == MENTOR
        return [await self.get_mentor_participant(actor, ENROLLMENT_ID)]

    async def get_mentor_participant(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> MentorParticipantResponse:
        assert actor == MENTOR and enrollment_id == ENROLLMENT_ID
        return MentorParticipantResponse(
            enrollment_id=ENROLLMENT_ID,
            user_id=PARTICIPANT.user_id,
            display_name="Peserta Contoh",
            nim="NIM-001",
            final_assessments=1,
            enough_themes=1,
            follow_up_themes=0,
            allowed_actions=["view_assessment_history"],
        )

    async def assessment_history(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> list[ThemeAssessmentResponse]:
        assert actor == MENTOR and enrollment_id == ENROLLMENT_ID
        return [assessment_response(AssessmentStatus.FINAL, 3)]


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


def assessment_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: PARTICIPANT
    app.dependency_overrides[get_mentor_actor] = lambda: MENTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_theme_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    return TestClient(app)


def test_mentor_can_create_update_and_finalize_theme_assessment() -> None:
    base_payload = {
        "actual_at": NOW.isoformat(),
        "manual_score": 8,
        "outcome": "enough",
        "mentor_note": "Hafalan lancar",
        "incidents": [],
    }
    with assessment_client() as client:
        created = client.post(
            f"/api/v1/sessions/{SESSION_ID}/theme-assessments",
            headers={"Idempotency-Key": str(KEY)},
            json={"theme_id": str(THEME_ID), **base_payload},
        )
        updated = client.patch(
            f"/api/v1/theme-assessments/{ASSESSMENT_ID}",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={**base_payload, "expected_version": 1},
        )
        finalized = client.post(
            f"/api/v1/theme-assessments/{ASSESSMENT_ID}/finalize",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 2))},
            json={"expected_version": 2},
        )

    assert created.status_code == 201
    assert created.json()["data"]["attempt_no"] == 1
    assert updated.json()["version"] == 2
    assert finalized.json()["data"]["status"] == "final"


def test_participant_results_and_mentor_recap_are_scoped_contracts() -> None:
    with assessment_client() as client:
        participant_results = client.get("/api/v1/me/theme-results")
        participants = client.get("/api/v1/mentor/participants")
        history = client.get(f"/api/v1/enrollments/{ENROLLMENT_ID}/assessment-history")

    assert participant_results.status_code == 200
    assert participant_results.json()["data"]["items"][0]["manual_score"] == 8
    assert participants.json()["data"]["items"][0]["enough_themes"] == 1
    assert history.json()["data"]["items"][0]["policy_version"] == "2026.1"
