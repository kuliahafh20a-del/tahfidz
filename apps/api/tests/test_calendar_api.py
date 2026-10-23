from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.calendar.models import TargetStatus
from app.modules.calendar.router import get_participant_target_service
from app.modules.calendar.schemas import (
    DashboardResponse,
    ParticipantSummary,
    PartProgress,
    ProgressResponse,
    TargetResponse,
    TargetTheme,
)
from app.modules.grading.schemas import (
    ActivityScoreResponse,
    ActivitySourceContext,
    ActivityThemeScore,
)

ACTOR = ParticipantActor(
    user_id=UUID("50000000-0000-4000-8000-000000000001"),
    organization_id=UUID("50000000-0000-4000-8000-000000000002"),
)
ENROLLMENT_ID = UUID("50000000-0000-4000-8000-000000000003")
TARGET_ID = UUID("50000000-0000-4000-8000-000000000004")
THEME_ID = UUID("50000000-0000-4000-8000-000000000005")
PART_ID = UUID("50000000-0000-4000-8000-000000000006")


def target() -> TargetResponse:
    return TargetResponse(
        id=TARGET_ID,
        theme=TargetTheme(
            id=THEME_ID,
            code="T01",
            name="An-Naba ayat 1-16",
            part_id=PART_ID,
            part_no=1,
            part_name="Bagian 1",
        ),
        initial_due_date=date(2027, 1, 1),
        effective_due_date=date(2027, 1, 1),
        status=TargetStatus.ACTIVE,
        allowed_actions=["request_session"],
    )


def progress() -> ProgressResponse:
    active_part = PartProgress(
        id=PART_ID,
        part_no=1,
        name="Bagian 1",
        total_targets=10,
        completed_targets=0,
        status="active",
    )
    return ProgressResponse(
        total_targets=44,
        completed_targets=0,
        overdue_targets=0,
        expected_completed_targets=0,
        completion_percentage=0,
        on_track=True,
        projected_completion_date=date(2027, 10, 29),
        active_part=active_part,
        parts=[active_part],
    )


class StubParticipantTargetService:
    async def list_targets(
        self, actor: ParticipantActor, **filters: object
    ) -> list[TargetResponse]:
        assert actor == ACTOR
        assert filters["part_id"] in {None, PART_ID}
        return [target()]

    async def progress(self, actor: ParticipantActor) -> ProgressResponse:
        assert actor == ACTOR
        return progress()

    async def dashboard(self, actor: ParticipantActor) -> DashboardResponse:
        assert actor == ACTOR
        return DashboardResponse(
            participant=ParticipantSummary(
                id=ACTOR.user_id,
                display_name="Peserta Contoh",
                enrollment_id=ENROLLMENT_ID,
                cohort_name="Angkatan 2027",
                cohort_start_date=date(2027, 1, 1),
                cohort_close_date=None,
            ),
            progress=progress(),
            next_target=target(),
            upcoming_targets=[target()],
        )

    async def activity_score(self, actor: ParticipantActor) -> ActivityScoreResponse:
        assert actor == ACTOR
        first_submission = datetime(2027, 1, 1, 2, tzinfo=UTC)
        return ActivityScoreResponse(
            value=Decimal("10.000"),
            is_final=False,
            source_context=ActivitySourceContext(
                cutoff_at=datetime(2027, 1, 2, tzinfo=UTC),
                total_target_count=44,
                scored_target_count=1,
                overdue_target_count=0,
                themes=[
                    ActivityThemeScore(
                        target_id=TARGET_ID,
                        theme_id=THEME_ID,
                        effective_due_date=date(2027, 1, 1),
                        first_valid_submission_at=first_submission,
                        days_late=0,
                        score=10,
                    )
                ],
            ),
        )


def participant_client() -> TestClient:
    application = create_app()
    application.dependency_overrides[get_participant_actor] = lambda: ACTOR
    application.dependency_overrides[get_participant_target_service] = lambda: (
        StubParticipantTargetService()
    )
    application.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    return TestClient(application)


def test_participant_dashboard_exposes_server_actions() -> None:
    with participant_client() as client:
        response = client.get("/api/v1/me/dashboard")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["data"]["next_target"]["allowed_actions"] == ["request_session"]


def test_participant_targets_are_paginated_and_filterable() -> None:
    with participant_client() as client:
        response = client.get(f"/api/v1/me/targets?part_id={PART_ID}&limit=10")

    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["theme"]["code"] == "T01"


def test_participant_progress_exposes_44_theme_projection() -> None:
    with participant_client() as client:
        response = client.get("/api/v1/me/progress")

    assert response.status_code == 200
    assert response.json()["data"]["total_targets"] == 44


def test_participant_activity_score_exposes_auditable_source_context() -> None:
    with participant_client() as client:
        response = client.get("/api/v1/me/activity-score")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["data"]["value"] == "10.000"
    context = response.json()["data"]["source_context"]
    assert context["timezone"] == "Asia/Jakarta"
    assert context["scored_target_count"] == 1
    assert context["themes"][0]["score"] == 10
