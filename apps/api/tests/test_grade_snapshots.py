from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.calendar.access import ParticipantActor, get_participant_actor
from app.modules.grading.models import GradeSnapshot, GradeSource
from app.modules.grading.router import get_grade_snapshot_service
from app.modules.grading.schemas import (
    GradeComponentResponse,
    GradeHistoryResponse,
    GradeSnapshotResponse,
)
from app.modules.grading.service import GradeSnapshotNotFoundError, GradeSnapshotService

ACTOR = ParticipantActor(UUID(int=1), UUID(int=2))
SNAPSHOT_ID = UUID(int=3)
ENROLLMENT_ID = UUID(int=4)
POLICY_ID = UUID(int=5)
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def snapshot(*, previous: UUID | None = None) -> GradeSnapshotResponse:
    return GradeSnapshotResponse(
        id=SNAPSHOT_ID,
        enrollment_id=ENROLLMENT_ID,
        status="awaiting_components",
        exam_readiness="ready_for_exam",
        components={
            "k": GradeComponentResponse(
                value=Decimal("8.250"), weight=Decimal("0.200"), status="available"
            ),
            "m": GradeComponentResponse(
                value=None, weight=Decimal("0.500"), status="policy_pending"
            ),
            "d": GradeComponentResponse(value=None, weight=Decimal("0.300"), status="not_assessed"),
        },
        final_score=None,
        graduation_status=None,
        policy_version_id=POLICY_ID,
        policy_version="2026.1",
        calculated_at=NOW,
        supersedes_id=previous,
        missing_requirements=["mentor_aggregation_policy", "final_exam"],
        source_context={"activity_is_final": True},
        sources=[],
    )


class StubGradeService:
    async def latest_for_participant(self, actor: ParticipantActor) -> GradeSnapshotResponse:
        assert actor == ACTOR
        return snapshot()

    async def history_for_participant(self, actor: ParticipantActor) -> GradeHistoryResponse:
        assert actor == ACTOR
        return GradeHistoryResponse(items=[snapshot(previous=UUID(int=9))])

    async def publish_for_participant(
        self, actor: ParticipantActor, *, request_id: UUID
    ) -> GradeSnapshotResponse:
        assert actor == ACTOR and isinstance(request_id, UUID)
        return snapshot()


def client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_participant_actor] = lambda: ACTOR
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_grade_snapshot_service] = lambda: service or StubGradeService()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost/test"}
    )
    return TestClient(app)


def test_grade_models_register_history_and_source_constraints() -> None:
    snapshots = Base.metadata.tables["app.grade_snapshots"]
    sources = Base.metadata.tables["app.grade_sources"]

    assert GradeSnapshot.__table__ is snapshots
    assert GradeSource.__table__ is sources
    assert any(
        constraint.name == "uq_grade_sources__snapshot_assessment_component"
        for constraint in sources.constraints
    )


def test_final_score_uses_decimal_formula_without_float_rounding() -> None:
    assert GradeSnapshotService.final_score(Decimal("10"), Decimal("10"), Decimal("1")) == Decimal(
        "7.300"
    )
    assert GradeSnapshotService.final_score(Decimal("8"), Decimal("8"), Decimal("3")) == Decimal(
        "6.500"
    )


def test_grade_recap_keeps_unavailable_components_null() -> None:
    with client() as test_client:
        result = test_client.get("/api/v1/me/grades")

    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    data = result.json()["data"]
    assert data["components"]["k"]["value"] == "8.250"
    assert data["components"]["m"]["value"] is None
    assert data["components"]["d"]["value"] is None
    assert data["final_score"] is None


def test_grade_history_preserves_superseded_snapshot_link() -> None:
    with client() as test_client:
        result = test_client.get("/api/v1/me/grades/history")

    assert result.status_code == 200
    assert result.json()["data"]["items"][0]["supersedes_id"] == str(UUID(int=9))


def test_publish_grade_snapshot_is_csrf_protected_command() -> None:
    with client() as test_client:
        result = test_client.post("/api/v1/me/grades/publish")

    assert result.status_code == 201
    assert result.json()["data"]["status"] == "awaiting_components"


def test_missing_latest_snapshot_returns_domain_not_found() -> None:
    class MissingService(StubGradeService):
        async def latest_for_participant(self, actor: ParticipantActor) -> GradeSnapshotResponse:
            del actor
            raise GradeSnapshotNotFoundError("missing")

    with client(MissingService()) as test_client:
        result = test_client.get("/api/v1/me/grades")

    assert result.status_code == 404
    assert result.json()["code"] == "GRADE_SNAPSHOT_NOT_FOUND"
