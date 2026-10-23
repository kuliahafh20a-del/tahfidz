from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.main import create_app
from app.modules.auth.access import require_csrf
from app.modules.exams.access import LecturerActor, get_lecturer_actor
from app.modules.exams.models import (
    Exam,
    ExamItem,
    ExamStatus,
    QuestionKind,
    QuestionSource,
    QuestionStatus,
    QuestionVersion,
)
from app.modules.exams.router import get_exam_package_service
from app.modules.exams.schemas import (
    ExamAssessmentDraft,
    ExamCreate,
    ExamFinalize,
    ExamItemsReplace,
    ExamQueueItemResponse,
    ExamResponse,
    ExamStart,
    ExamSummaryResponse,
    ExamUpdate,
    PackagePolicyResponse,
    QuestionVersionCreate,
    QuestionVersionResponse,
)
from app.modules.exams.service import ExamPolicyNotApprovedError, ExamVersionConflictError
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.operations.models import IdempotencyRecord
from app.modules.operations.service import IdempotencyClaim, get_idempotency_store

LECTURER = LecturerActor(UUID(int=1), UUID(int=2))
ENROLLMENT_ID = UUID(int=3)
PARTICIPANT_ID = UUID(int=4)
EXAM_ID = UUID(int=5)
QUESTION_ID = UUID(int=6)
QUESTION_KEY = UUID(int=7)
POLICY_ID = UUID(int=8)
KEY = UUID(int=9)
NOW = datetime(2027, 1, 1, tzinfo=UTC)


def question_response() -> QuestionVersionResponse:
    return QuestionVersionResponse(
        id=QUESTION_ID,
        question_key=QUESTION_KEY,
        author_id=LECTURER.user_id,
        source=QuestionSource.LECTURER,
        kind=QuestionKind.CONTINUE_VERSES,
        stimulus="Lanjutkan tiga ayat berikutnya.",
        answer_reference={"surah_no": 78, "ayah_start": 2, "ayah_end": 4},
        scope={"surah_no": 78, "ayah": 1},
        version_no=1,
        status=QuestionStatus.DRAFT,
    )


def exam_response(version: int = 1) -> ExamResponse:
    return ExamResponse(
        id=EXAM_ID,
        participant=SessionParticipant(
            enrollment_id=ENROLLMENT_ID,
            user_id=PARTICIPANT_ID,
            display_name="Peserta Siap",
            nim="NIM-001",
        ),
        lecturer_id=LECTURER.user_id,
        policy_version_id=POLICY_ID,
        policy_version="2026.1",
        scheduled_at=NOW,
        actual_at=None,
        lecturer_note=None,
        status=ExamStatus.DRAFT,
        items=[],
        package_policy=PackagePolicyResponse(
            approved=False,
            required_item_count=None,
            expected_total_weight=None,
            aggregation_method=None,
            blockers=["exam_package_policy_not_approved"],
        ),
        row_version=version,
        finalized_at=None,
        allowed_actions=["edit_exam", "edit_items"],
    )


class StubExamService:
    async def list_queue(self, actor: LecturerActor) -> list[ExamQueueItemResponse]:
        assert actor == LECTURER
        return [
            ExamQueueItemResponse(
                participant=exam_response().participant,
                completed_parts=5,
                required_parts=5,
                latest_exam_id=None,
                latest_exam_status=None,
                allowed_actions=["create_exam"],
            )
        ]

    async def list_exams(self, actor: LecturerActor) -> list[ExamResponse]:
        assert actor == LECTURER
        return [exam_response()]

    async def create_exam(
        self, actor: LecturerActor, payload: ExamCreate, request_id: UUID
    ) -> ExamResponse:
        del request_id
        assert actor == LECTURER and payload.enrollment_id == ENROLLMENT_ID
        return exam_response()

    async def update_exam(
        self, actor: LecturerActor, exam_id: UUID, payload: ExamUpdate, request_id: UUID
    ) -> ExamResponse:
        del request_id
        assert actor == LECTURER and exam_id == EXAM_ID and payload.expected_version == 1
        return exam_response(2)

    async def replace_items(
        self,
        actor: LecturerActor,
        exam_id: UUID,
        payload: ExamItemsReplace,
        request_id: UUID,
    ) -> ExamResponse:
        del request_id
        assert actor == LECTURER and exam_id == EXAM_ID
        assert payload.items[0].question_version_id == QUESTION_ID
        return exam_response(2)

    async def get_exam(self, actor: LecturerActor, exam_id: UUID) -> ExamResponse:
        assert actor == LECTURER and exam_id == EXAM_ID
        return exam_response()

    async def start_exam(
        self, actor: LecturerActor, exam_id: UUID, payload: ExamStart, request_id: UUID
    ) -> ExamResponse:
        del request_id
        assert actor == LECTURER and exam_id == EXAM_ID and payload.expected_version == 1
        return exam_response(2)

    async def save_assessment_draft(
        self,
        actor: LecturerActor,
        exam_id: UUID,
        payload: ExamAssessmentDraft,
        request_id: UUID,
    ) -> ExamResponse:
        del request_id
        assert actor == LECTURER and exam_id == EXAM_ID
        assert payload.items[0].manual_score == 8
        return exam_response(2)

    async def finalize_exam(
        self, actor: LecturerActor, exam_id: UUID, payload: ExamFinalize, request_id: UUID
    ) -> ExamResponse:
        del actor, exam_id, payload, request_id
        raise ExamPolicyNotApprovedError("exam_package_policy_not_approved")

    async def exam_summary(self, actor: LecturerActor, exam_id: UUID) -> ExamSummaryResponse:
        assert actor == LECTURER and exam_id == EXAM_ID
        return ExamSummaryResponse(
            exam=exam_response(),
            assessed_item_count=0,
            total_item_count=0,
            d_status="policy_pending",
            missing_requirements=["exam_package_policy_not_approved"],
        )

    async def list_questions(self, actor: LecturerActor) -> list[QuestionVersionResponse]:
        assert actor == LECTURER
        return [question_response()]

    async def create_question(
        self, actor: LecturerActor, payload: QuestionVersionCreate, request_id: UUID
    ) -> QuestionVersionResponse:
        del request_id
        assert actor == LECTURER and payload.kind is QuestionKind.CONTINUE_VERSES
        return question_response()


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


def client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_lecturer_actor] = lambda: LECTURER
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_exam_package_service] = lambda: service or StubExamService()
    app.dependency_overrides[get_idempotency_store] = lambda: StubIdempotency()
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost/test"}
    )
    return TestClient(app)


def test_exam_models_register_snapshot_and_version_constraints() -> None:
    questions = Base.metadata.tables["app.question_versions"]
    exams = Base.metadata.tables["app.exams"]
    items = Base.metadata.tables["app.exam_items"]
    assessments = Base.metadata.tables["app.exam_assessments"]

    assert QuestionVersion.__table__ is questions
    assert Exam.__table__ is exams
    assert ExamItem.__table__ is items
    assert any(
        constraint.name == "uq_exam_assessments__exam_item_id"
        for constraint in assessments.constraints
    )
    assert any(
        constraint.name == "uq_question_versions__question_key_version_no"
        for constraint in questions.constraints
    )
    assert any(
        constraint.name == "uq_exam_items__exam_id_sequence_no" for constraint in items.constraints
    )


def test_lecturer_queue_question_and_package_contracts() -> None:
    with client() as test_client:
        queue = test_client.get("/api/v1/lecturer/exam-queue")
        created = test_client.post(
            "/api/v1/exams",
            headers={"Idempotency-Key": str(KEY)},
            json={"enrollment_id": str(ENROLLMENT_ID), "scheduled_at": NOW.isoformat()},
        )
        question = test_client.post(
            "/api/v1/lecturer/questions",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={
                "kind": "continue_verses",
                "stimulus": "Lanjutkan tiga ayat berikutnya.",
                "answer_reference": {"surah_no": 78, "ayah_start": 2, "ayah_end": 4},
                "scope": {"surah_no": 78, "ayah": 1},
            },
        )
        items = test_client.put(
            f"/api/v1/exams/{EXAM_ID}/items",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 2))},
            json={
                "items": [{"question_version_id": str(QUESTION_ID), "weight": None}],
                "expected_version": 1,
            },
        )

    assert queue.json()["data"][0]["completed_parts"] == 5
    assert created.status_code == 201
    assert created.json()["data"]["package_policy"]["approved"] is False
    assert question.json()["data"]["answer_reference"]["ayah_end"] == 4
    assert items.json()["version"] == 2


def test_exam_execution_and_summary_contracts() -> None:
    with client() as test_client:
        exams = test_client.get("/api/v1/lecturer/exams")
        started = test_client.post(
            f"/api/v1/exams/{EXAM_ID}/start",
            headers={"Idempotency-Key": str(KEY)},
            json={"actual_at": NOW.isoformat(), "expected_version": 1},
        )
        draft = test_client.put(
            f"/api/v1/exams/{EXAM_ID}/assessment-draft",
            headers={"Idempotency-Key": str(UUID(int=KEY.int + 1))},
            json={
                "items": [
                    {
                        "exam_item_id": str(QUESTION_ID),
                        "manual_score": 8,
                        "notes": "Lancar",
                        "incidents": [],
                    }
                ],
                "expected_version": 1,
            },
        )
        summary = test_client.get(f"/api/v1/exams/{EXAM_ID}/summary")

    assert exams.status_code == 200
    assert started.json()["version"] == 2
    assert draft.status_code == 200
    assert summary.json()["data"]["d_status"] == "policy_pending"


def test_exam_scores_must_be_integer_and_within_scale() -> None:
    with client() as test_client:
        fractional = test_client.put(
            f"/api/v1/exams/{EXAM_ID}/assessment-draft",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "items": [
                    {
                        "exam_item_id": str(QUESTION_ID),
                        "manual_score": 7.5,
                        "incidents": [],
                    }
                ],
                "expected_version": 1,
            },
        )

    assert fractional.status_code == 422


def test_exam_finalization_reports_unapproved_policy() -> None:
    with client() as test_client:
        result = test_client.post(
            f"/api/v1/exams/{EXAM_ID}/finalize",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "actual_at": NOW.isoformat(),
                "manual_score": None,
                "examiner_note": None,
                "evidence_media_ids": [str(UUID(int=10))],
                "expected_version": 1,
            },
        )

    assert result.status_code == 409
    assert result.json()["code"] == "POLICY_NOT_APPROVED"
    assert result.json()["details"]["blockers"] == ["exam_package_policy_not_approved"]


def test_assessment_draft_version_conflict_exposes_current_version() -> None:
    class StaleService(StubExamService):
        async def save_assessment_draft(
            self,
            actor: LecturerActor,
            exam_id: UUID,
            payload: ExamAssessmentDraft,
            request_id: UUID,
        ) -> ExamResponse:
            del actor, exam_id, payload, request_id
            raise ExamVersionConflictError(3)

    with client(StaleService()) as test_client:
        result = test_client.put(
            f"/api/v1/exams/{EXAM_ID}/assessment-draft",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "items": [
                    {
                        "exam_item_id": str(QUESTION_ID),
                        "manual_score": 8,
                        "incidents": [],
                    }
                ],
                "expected_version": 1,
            },
        )

    assert result.status_code == 409
    assert result.json()["code"] == "EXAM_VERSION_CONFLICT"
    assert result.json()["details"]["current_version"] == 3


def test_exam_version_conflict_exposes_current_version() -> None:
    class StaleService(StubExamService):
        async def update_exam(
            self,
            actor: LecturerActor,
            exam_id: UUID,
            payload: ExamUpdate,
            request_id: UUID,
        ) -> ExamResponse:
            del actor, exam_id, payload, request_id
            raise ExamVersionConflictError(4)

    with client(StaleService()) as test_client:
        result = test_client.patch(
            f"/api/v1/exams/{EXAM_ID}",
            headers={"Idempotency-Key": str(KEY)},
            json={
                "scheduled_at": NOW.isoformat(),
                "lecturer_note": None,
                "expected_version": 1,
            },
        )

    assert result.status_code == 409
    assert result.json()["code"] == "EXAM_VERSION_CONFLICT"
    assert result.json()["details"]["current_version"] == 4


def test_unapproved_package_contract_keeps_weights_empty() -> None:
    response = exam_response()
    assert response.package_policy.blockers == ["exam_package_policy_not_approved"]
    assert response.package_policy.expected_total_weight is None
