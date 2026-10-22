from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.cohorts.access import DepartmentActor, get_department_actor
from app.modules.cohorts.models import AssignmentRole, CohortStatus, EnrollmentStatus
from app.modules.cohorts.router import get_department_program_service
from app.modules.cohorts.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    CohortCreate,
    CohortResponse,
    EnrollmentCreate,
    EnrollmentDetail,
    EnrollmentResponse,
    EnrollmentUpdate,
    UserReference,
)
from app.modules.cohorts.service import ResourceNotFoundError

ACTOR = DepartmentActor(
    user_id=UUID("40000000-0000-4000-8000-000000000001"),
    organization_id=UUID("40000000-0000-4000-8000-000000000002"),
)
COHORT_ID = UUID("40000000-0000-4000-8000-000000000003")
ENROLLMENT_ID = UUID("40000000-0000-4000-8000-000000000004")
PARTICIPANT_ID = UUID("40000000-0000-4000-8000-000000000005")
STAFF_ID = UUID("40000000-0000-4000-8000-000000000006")
ASSIGNMENT_ID = UUID("40000000-0000-4000-8000-000000000007")
REFERENCE_ID = UUID("40000000-0000-4000-8000-000000000008")
STARTED_AT = datetime(2027, 1, 1, tzinfo=UTC)


def participant() -> UserReference:
    return UserReference(
        id=PARTICIPANT_ID,
        name="Peserta Contoh",
        login_identifier="peserta@example.test",
    )


def staff() -> UserReference:
    return UserReference(
        id=STAFF_ID,
        name="Mentor Contoh",
        login_identifier="mentor@example.test",
    )


def enrollment() -> EnrollmentResponse:
    return EnrollmentResponse(
        id=ENROLLMENT_ID,
        cohort_id=COHORT_ID,
        user=participant(),
        nim_snapshot="NIM-001",
        status=EnrollmentStatus.ACTIVE,
        joined_at=STARTED_AT,
    )


def assignment() -> AssignmentResponse:
    return AssignmentResponse(
        id=ASSIGNMENT_ID,
        enrollment_id=ENROLLMENT_ID,
        staff=staff(),
        role=AssignmentRole.MENTOR,
        valid_from=STARTED_AT,
        valid_to=None,
        reason="Penugasan awal",
    )


class StubDepartmentProgramService:
    async def list_cohorts(self, actor: DepartmentActor) -> list[CohortResponse]:
        assert actor == ACTOR
        return [
            CohortResponse(
                id=COHORT_ID,
                organization_id=ACTOR.organization_id,
                curriculum_version_id=REFERENCE_ID,
                policy_version_id=REFERENCE_ID,
                name="Angkatan 2027",
                start_date=date(2027, 1, 1),
                close_date=None,
                status=CohortStatus.ACTIVE,
            )
        ]

    async def create_cohort(
        self,
        actor: DepartmentActor,
        payload: CohortCreate,
    ) -> CohortResponse:
        del payload
        return (await self.list_cohorts(actor))[0]

    async def list_enrollments(
        self,
        actor: DepartmentActor,
        cohort_id: UUID | None = None,
    ) -> list[EnrollmentResponse]:
        assert actor == ACTOR
        assert cohort_id in {None, COHORT_ID}
        return [enrollment()]

    async def get_enrollment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> EnrollmentDetail:
        assert actor == ACTOR
        if enrollment_id != ENROLLMENT_ID:
            raise ResourceNotFoundError
        return EnrollmentDetail(**enrollment().model_dump(), assignments=[assignment()])

    async def create_enrollment(
        self,
        actor: DepartmentActor,
        payload: EnrollmentCreate,
    ) -> EnrollmentResponse:
        del payload
        return (await self.list_enrollments(actor))[0]

    async def update_enrollment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
        payload: EnrollmentUpdate,
    ) -> EnrollmentResponse:
        del enrollment_id, payload
        return (await self.list_enrollments(actor))[0]

    async def list_assignments(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> list[AssignmentResponse]:
        assert actor == ACTOR
        assert enrollment_id == ENROLLMENT_ID
        return [assignment()]

    async def create_assignment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
        payload: AssignmentCreate,
    ) -> AssignmentResponse:
        del payload
        return (await self.list_assignments(actor, enrollment_id))[0]


def department_client() -> TestClient:
    application = create_app()
    service = StubDepartmentProgramService()
    application.dependency_overrides[get_department_actor] = lambda: ACTOR
    application.dependency_overrides[get_department_program_service] = lambda: service
    return TestClient(application)


def test_department_admin_can_list_enrollments_and_assignment_history() -> None:
    with department_client() as client:
        enrollments = client.get(f"/api/v1/department/enrollments?cohort_id={COHORT_ID}")
        detail = client.get(f"/api/v1/department/enrollments/{ENROLLMENT_ID}")

    assert enrollments.status_code == 200
    assert enrollments.json()[0]["nim_snapshot"] == "NIM-001"
    assert detail.status_code == 200
    assert detail.json()["assignments"][0]["staff"]["name"] == "Mentor Contoh"


def test_department_admin_can_create_assignment() -> None:
    with department_client() as client:
        response = client.post(
            f"/api/v1/department/enrollments/{ENROLLMENT_ID}/assignments",
            json={
                "role": "mentor",
                "assignee_user_id": str(STAFF_ID),
                "valid_from": STARTED_AT.isoformat(),
                "valid_to": None,
                "reason": "Penugasan awal",
            },
        )

    assert response.status_code == 201
    assert response.json()["role"] == "mentor"
    assert response.json()["valid_to"] is None


def test_out_of_scope_identifier_returns_stable_not_found() -> None:
    with department_client() as client:
        response = client.get("/api/v1/department/enrollments/40000000-0000-4000-8000-000000000099")

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "resource_not_found"}}
