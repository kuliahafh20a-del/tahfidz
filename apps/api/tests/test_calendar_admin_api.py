from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.calendar.admin_router import get_deadline_change_service
from app.modules.calendar.admin_schemas import (
    CalendarParticipant,
    CalendarTheme,
    DeadlineChangeBatchResponse,
    DeadlineChangePreview,
    DeadlineChangeRequest,
    DeadlineChangeResponse,
    DeadlineDecisionRequest,
    DeadlineImpactItem,
)
from app.modules.calendar.models import DeadlineChangeStatus
from app.modules.cohorts.access import DepartmentActor, get_department_actor
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store

ACTOR = DepartmentActor(
    user_id=UUID("60000000-0000-4000-8000-000000000001"),
    organization_id=UUID("60000000-0000-4000-8000-000000000002"),
)
COHORT_ID = UUID("60000000-0000-4000-8000-000000000003")
TARGET_ID = UUID("60000000-0000-4000-8000-000000000004")
CHANGE_ID = UUID("60000000-0000-4000-8000-000000000005")
KEY = UUID("60000000-0000-4000-8000-000000000006")
APPROVAL_KEY = UUID("60000000-0000-4000-8000-000000000010")
REJECTION_KEY = UUID("60000000-0000-4000-8000-000000000011")
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def change(status: DeadlineChangeStatus = DeadlineChangeStatus.PENDING) -> DeadlineChangeResponse:
    decided = NOW if status is not DeadlineChangeStatus.PENDING else None
    return DeadlineChangeResponse(
        id=CHANGE_ID,
        target_id=TARGET_ID,
        requested_by=ACTOR.user_id,
        approved_by=ACTOR.user_id if decided else None,
        old_date=date(2027, 1, 1),
        new_date=date(2027, 1, 8),
        reason="Penyesuaian kalender",
        impact_note="Bergeser tujuh hari",
        decision_note=None,
        status=status,
        decided_at=decided,
        row_version=2 if decided else 1,
        created_at=NOW,
    )


class StubDeadlineChangeService:
    async def preview(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        payload: DeadlineChangeRequest,
    ) -> DeadlineChangePreview:
        assert actor == ACTOR and cohort_id == COHORT_ID and payload.expected_version == 1
        participant = CalendarParticipant(
            enrollment_id=UUID("60000000-0000-4000-8000-000000000007"),
            user_id=UUID("60000000-0000-4000-8000-000000000008"),
            display_name="Peserta Contoh",
            nim="NIM-001",
        )
        theme = CalendarTheme(
            id=UUID("60000000-0000-4000-8000-000000000009"),
            code="T01",
            name="An-Naba ayat 1-16",
            part_no=1,
            part_name="Bagian 1",
        )
        return DeadlineChangePreview(
            cohort_id=COHORT_ID,
            calendar_version=1,
            affected_count=1,
            earliest_old_date=date(2027, 1, 1),
            latest_old_date=date(2027, 1, 1),
            new_due_date=payload.new_due_date,
            impacts=[
                DeadlineImpactItem(
                    target_id=TARGET_ID,
                    participant=participant,
                    theme=theme,
                    old_date=date(2027, 1, 1),
                    new_date=payload.new_due_date,
                    shift_days=7,
                )
            ],
        )

    async def propose(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        payload: DeadlineChangeRequest,
        request_id: UUID,
    ) -> DeadlineChangeBatchResponse:
        del payload, request_id
        assert actor == ACTOR and cohort_id == COHORT_ID
        return DeadlineChangeBatchResponse(
            cohort_id=COHORT_ID,
            calendar_version=2,
            changes=[change()],
        )

    async def decide(
        self,
        actor: DepartmentActor,
        change_id: UUID,
        payload: DeadlineDecisionRequest,
        request_id: UUID,
        *,
        approve: bool,
    ) -> DeadlineChangeBatchResponse:
        del payload, request_id
        assert actor == ACTOR and change_id == CHANGE_ID
        return DeadlineChangeBatchResponse(
            cohort_id=COHORT_ID,
            calendar_version=3,
            changes=[
                change(DeadlineChangeStatus.APPROVED if approve else DeadlineChangeStatus.REJECTED)
            ],
        )

    async def calendar(self, actor: DepartmentActor, cohort_id: UUID) -> object:
        del actor, cohort_id
        raise AssertionError("not used by these tests")


class StubIdempotencyStore:
    async def claim(self, **kwargs: object) -> IdempotencyClaim:
        return IdempotencyClaim(
            record=IdempotencyRecord(
                actor_id=ACTOR.user_id,
                idempotency_key=UUID(str(kwargs["idempotency_key"])),
                method="POST",
                normalized_path=str(kwargs["normalized_path"]),
                request_hash="0" * 64,
                request_id=UUID(str(kwargs["request_id"])),
                expires_at=NOW,
            )
        )

    async def complete(self, claim: IdempotencyClaim, **kwargs: object) -> None:
        del claim, kwargs


def calendar_client() -> TestClient:
    application = create_app()
    application.dependency_overrides[get_department_actor] = lambda: ACTOR
    application.dependency_overrides[require_csrf] = lambda: None
    application.dependency_overrides[get_deadline_change_service] = lambda: (
        StubDeadlineChangeService()
    )
    application.dependency_overrides[get_idempotency_store] = lambda: StubIdempotencyStore()
    application.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    return TestClient(application)


def request_body() -> dict[str, object]:
    return {
        "target_ids": [str(TARGET_ID)],
        "new_due_date": "2027-01-08",
        "reason": "Penyesuaian kalender",
        "impact_note": "Bergeser tujuh hari",
        "expected_version": 1,
    }


def test_department_admin_previews_deadline_impact() -> None:
    with calendar_client() as client:
        response = client.post(
            f"/api/v1/department/cohorts/{COHORT_ID}/deadline-changes/preview",
            json=request_body(),
        )

    assert response.status_code == 200
    assert response.json()["data"]["impacts"][0]["shift_days"] == 7


def test_proposal_and_approval_use_idempotency_contract() -> None:
    with calendar_client() as client:
        proposed = client.post(
            f"/api/v1/department/cohorts/{COHORT_ID}/deadline-changes",
            headers={"Idempotency-Key": str(KEY)},
            json=request_body(),
        )
        approved = client.post(
            f"/api/v1/department/deadline-changes/{CHANGE_ID}/approve",
            headers={"Idempotency-Key": str(APPROVAL_KEY)},
            json={"expected_version": 1, "decision_note": "Disetujui"},
        )

    assert proposed.status_code == 201
    assert proposed.json()["data"]["changes"][0]["status"] == "pending"
    assert approved.status_code == 200
    assert approved.json()["data"]["changes"][0]["status"] == "approved"


def test_rejection_endpoint_records_decision() -> None:
    with calendar_client() as client:
        rejected = client.post(
            f"/api/v1/department/deadline-changes/{CHANGE_ID}/reject",
            headers={"Idempotency-Key": str(REJECTION_KEY)},
            json={"expected_version": 1, "decision_note": "Dampak terlalu besar"},
        )

    assert rejected.status_code == 200
    assert rejected.json()["data"]["changes"][0]["status"] == "rejected"
