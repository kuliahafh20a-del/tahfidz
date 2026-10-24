from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.curriculum.router import get_reference_service
from app.modules.curriculum.schemas import (
    AssessmentRubricResponse,
    CurriculumResponse,
    PolicySummary,
)

POLICY_ID = UUID("30000000-0000-4000-8000-000000000001")
CURRICULUM_ID = UUID("30000000-0000-4000-8000-000000000002")
PUBLISHED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class StubReferenceService:
    async def assessment_rubric(self) -> AssessmentRubricResponse:
        return AssessmentRubricResponse.model_validate(
            {
                "policy_id": POLICY_ID,
                "policy_version": "2026.1",
                "score": {
                    "minimum": 1,
                    "maximum": 10,
                    "step": 1,
                    "allow_fractional": False,
                    "display_decimals": 0,
                    "bands": [
                        {"minimum": 1, "maximum": 4, "description": "Perlu perbaikan."},
                        {"minimum": 5, "maximum": 7, "description": "Cukup."},
                        {"minimum": 8, "maximum": 10, "description": "Baik."},
                    ],
                },
            }
        )

    async def current_policy(self) -> PolicySummary:
        return PolicySummary(
            id=POLICY_ID,
            version="2026.1",
            status="published",
            effective_from=PUBLISHED_AT,
        )

    async def current_curriculum(self) -> CurriculumResponse:
        return CurriculumResponse.model_validate(
            {
                "id": CURRICULUM_ID,
                "version": "juz30-2026.1",
                "title": "Kurikulum Juz 30 - 40 Tema",
                "published_at": PUBLISHED_AT,
                "parts": [
                    {
                        "sequence_no": 1,
                        "title": "Bagian 1",
                        "themes": [
                            {
                                "sequence_no": 1,
                                "title": "An-Naba 1-16",
                                "description": None,
                                "ranges": [
                                    {
                                        "sequence_no": 1,
                                        "surah_no": 78,
                                        "ayah_start": 1,
                                        "ayah_end": 16,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )


class MissingReferenceService(StubReferenceService):
    async def current_curriculum(self) -> CurriculumResponse:
        raise LookupError("missing")


def client_for(service: StubReferenceService) -> TestClient:
    application = create_app()
    application.dependency_overrides[get_reference_service] = lambda: service
    return TestClient(application)


def test_reference_endpoints_expose_effective_versions() -> None:
    with client_for(StubReferenceService()) as client:
        rubric = client.get("/api/v1/reference/assessment-rubric")
        policy = client.get("/api/v1/reference/policies/current")
        curriculum = client.get("/api/v1/reference/curriculum")

    assert rubric.status_code == 200
    assert rubric.json()["data"]["score"] == {
        "minimum": 1,
        "maximum": 10,
        "step": 1,
        "allow_fractional": False,
        "display_decimals": 0,
        "bands": [
            {"minimum": 1, "maximum": 4, "description": "Perlu perbaikan."},
            {"minimum": 5, "maximum": 7, "description": "Cukup."},
            {"minimum": 8, "maximum": 10, "description": "Baik."},
        ],
    }
    assert policy.status_code == 200
    assert policy.json()["data"]["version"] == "2026.1"
    assert curriculum.status_code == 200
    assert curriculum.json()["data"]["parts"][0]["themes"][0]["ranges"][0] == {
        "sequence_no": 1,
        "surah_no": 78,
        "ayah_start": 1,
        "ayah_end": 16,
    }


def test_reference_endpoint_returns_stable_not_found_error() -> None:
    with client_for(MissingReferenceService()) as client:
        response = client.get("/api/v1/reference/curriculum")

    assert response.status_code == 404
    assert response.json()["code"] == "REFERENCE_NOT_AVAILABLE"
    assert response.json()["request_id"] == response.headers["x-request-id"]
