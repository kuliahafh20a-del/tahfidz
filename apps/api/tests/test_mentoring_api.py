from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.mentoring.access import MentorActor, get_mentor_actor
from app.modules.mentoring.models import SessionMethod, SessionStatus
from app.modules.mentoring.router import get_mentoring_session_service
from app.modules.mentoring.schemas import (
    SessionCreate,
    SessionMentor,
    SessionParticipant,
    SessionResponse,
    SessionSchedule,
    SessionThemeResponse,
    SessionTransition,
)
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store

PARTICIPANT = ParticipantActor(
    UUID("70000000-0000-4000-8000-000000000001"),
    UUID("70000000-0000-4000-8000-000000000002"),
)
MENTOR = MentorActor(
    UUID("70000000-0000-4000-8000-000000000003"),
    PARTICIPANT.organization_id,
)
SESSION_ID = UUID("70000000-0000-4000-8000-000000000004")
THEME_ID = UUID("70000000-0000-4000-8000-000000000005")
PART_ID = UUID("70000000-0000-4000-8000-000000000006")
KEY = UUID("70000000-0000-4000-8000-000000000007")
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def response(
    session_status: SessionStatus = SessionStatus.PROPOSED,
    version: int = 1,
) -> SessionResponse:
    scheduled_at = NOW if session_status is not SessionStatus.PROPOSED else None
    actual_at = (
        NOW if session_status in {SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED} else None
    )
    return SessionResponse(
        id=SESSION_ID,
        participant=SessionParticipant(
            enrollment_id=UUID("70000000-0000-4000-8000-000000000008"),
            user_id=PARTICIPANT.user_id,
            display_name="Peserta Contoh",
            nim="NIM-001",
        ),
        part_id=PART_ID,
        mentor=SessionMentor(user_id=MENTOR.user_id, display_name="Mentor Contoh"),
        proposed_at=NOW,
        scheduled_at=scheduled_at,
        actual_at=actual_at,
        method=SessionMethod.VIDEO_CALL,
        status=session_status,
        participant_note="Fokus kelancaran",
        mentor_note=None,
        row_version=version,
        created_at=NOW,
        themes=[
            SessionThemeResponse(
                id=UUID("70000000-0000-4000-8000-000000000009"),
                theme_id=THEME_ID,
                code="T01",
                name="An-Naba ayat 1-16",
                part_id=PART_ID,
                part_no=1,
                part_name="Bagian 1",
            )
        ],
        allowed_actions=["schedule"],
    )


class StubSessionService:
    async def create(
        self, actor: ParticipantActor, payload: SessionCreate, request_id: UUID
    ) -> SessionResponse:
        del request_id
        assert actor == PARTICIPANT and payload.theme_ids == [THEME_ID]
        return response()

    async def list_participant(self, actor: ParticipantActor) -> list[SessionResponse]:
        assert actor == PARTICIPANT
        return [response()]

    async def get_for_participant(
        self, actor: ParticipantActor, session_id: UUID
    ) -> SessionResponse:
        assert actor == PARTICIPANT and session_id == SESSION_ID
        return response()

    async def cancel(
        self,
        actor: ParticipantActor,
        session_id: UUID,
        payload: SessionTransition,
        request_id: UUID,
    ) -> SessionResponse:
        del payload, request_id
        assert actor == PARTICIPANT and session_id == SESSION_ID
        return response(SessionStatus.CANCELLED, 2)

    async def mentor_queue(self, actor: MentorActor, **kwargs: object) -> list[SessionResponse]:
        assert actor == MENTOR and kwargs["session_status"] is None
        return [response()]

    async def schedule(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: SessionSchedule,
        request_id: UUID,
    ) -> SessionResponse:
        del payload, request_id
        assert actor == MENTOR and session_id == SESSION_ID
        return response(SessionStatus.SCHEDULED, 2)

    async def transition(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: SessionTransition,
        request_id: UUID,
        *,
        action: str,
    ) -> SessionResponse:
        del payload, request_id
        assert actor == MENTOR and session_id == SESSION_ID
        status = {
            "start": SessionStatus.IN_PROGRESS,
            "complete": SessionStatus.COMPLETED,
            "no-show": SessionStatus.NO_SHOW,
        }[action]
        return response(status, 2)


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


def mentoring_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: PARTICIPANT
    app.dependency_overrides[get_mentor_actor] = lambda: MENTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_mentoring_session_service] = lambda: StubSessionService()
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    return TestClient(app)


def test_participant_can_propose_and_cancel_session() -> None:
    with mentoring_client() as client:
        created = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "theme_ids": [str(THEME_ID)],
                "method": "video_call",
                "proposed_at": NOW.isoformat(),
                "participant_note": "Fokus kelancaran",
            },
        )
        cancelled = client.post(
            f"/api/v1/sessions/{SESSION_ID}/cancel",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={"expected_version": 1, "note": "Berhalangan"},
        )

    assert created.status_code == 201
    assert created.json()["data"]["status"] == "proposed"
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"


def test_mentor_queue_schedule_and_start_contracts() -> None:
    with mentoring_client() as client:
        queue = client.get("/api/v1/mentor/queue?work_type=session")
        scheduled = client.patch(
            f"/api/v1/sessions/{SESSION_ID}",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 2))},
            json={
                "scheduled_at": NOW.isoformat(),
                "method": "video_call",
                "mentor_note": "Tautan terpisah",
                "expected_version": 1,
            },
        )
        started = client.post(
            f"/api/v1/sessions/{SESSION_ID}/start",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 3))},
            json={"expected_version": 2, "note": "Dimulai"},
        )

    assert queue.status_code == 200
    assert queue.json()["data"]["items"][0]["participant"]["nim"] == "NIM-001"
    assert scheduled.json()["data"]["status"] == "scheduled"
    assert started.json()["data"]["status"] == "in_progress"


def test_mentor_complete_and_no_show_contracts() -> None:
    with mentoring_client() as client:
        no_show = client.post(
            f"/api/v1/sessions/{SESSION_ID}/no-show",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 4))},
            json={"expected_version": 2, "note": "Tidak hadir"},
        )
        completed = client.post(
            f"/api/v1/sessions/{SESSION_ID}/complete",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 5))},
            json={"expected_version": 3, "note": "Selesai"},
        )

    assert no_show.status_code == 200
    assert no_show.json()["data"]["status"] == "no_show"
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "completed"
