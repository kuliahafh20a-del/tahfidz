"""Lecturer-scoped queue, versioned questions, and exam package drafts."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Select, distinct, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.time import ensure_utc, utc_now
from app.modules.assessments.models import (
    AssessmentRecord,
    AssessmentStatus,
    VideoAssessment,
    VideoAssessmentOutcome,
)
from app.modules.audit.models import AuditEvent
from app.modules.cohorts.models import (
    Assignment,
    AssignmentRole,
    Cohort,
    Enrollment,
    EnrollmentStatus,
)
from app.modules.curriculum.models import PolicyStatus
from app.modules.curriculum.schemas import PolicyRules
from app.modules.exams.access import LecturerActor
from app.modules.exams.models import (
    Exam,
    ExamItem,
    ExamStatus,
    QuestionKind,
    QuestionSource,
    QuestionStatus,
    QuestionVersion,
)
from app.modules.exams.schemas import (
    ExamCreate,
    ExamItemResponse,
    ExamItemsReplace,
    ExamQueueItemResponse,
    ExamResponse,
    ExamUpdate,
    PackagePolicyResponse,
    QuestionVersionCreate,
    QuestionVersionResponse,
)
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.video.models import VideoAttempt, VideoVersion


class ExamNotFoundError(LookupError):
    pass


class ExamConflictError(ValueError):
    pass


class ExamVersionConflictError(ExamConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("exam was updated by another request")
        self.current_version = current_version


class ExamPackageService:
    REQUIRED_PARTS = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_queue(self, actor: LecturerActor) -> list[ExamQueueItemResponse]:
        now = utc_now()
        enrollments = list(
            await self.session.scalars(
                select(Enrollment)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .where(
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                    Cohort.organization_id == actor.organization_id,
                    self._active_assignment(actor.user_id, Enrollment.id, now),
                )
                .options(selectinload(Enrollment.user))
                .order_by(Enrollment.nim_snapshot)
            )
        )
        result: list[ExamQueueItemResponse] = []
        for enrollment in enrollments:
            completed = await self._completed_parts(enrollment.id)
            if completed != self.REQUIRED_PARTS:
                continue
            latest = await self.session.scalar(
                select(Exam)
                .where(Exam.enrollment_id == enrollment.id)
                .order_by(Exam.created_at.desc(), Exam.id.desc())
                .limit(1)
            )
            result.append(
                ExamQueueItemResponse(
                    participant=self._participant(enrollment),
                    completed_parts=completed,
                    required_parts=self.REQUIRED_PARTS,
                    latest_exam_id=latest.id if latest else None,
                    latest_exam_status=latest.status if latest else None,
                    allowed_actions=(
                        ["open_exam"]
                        if latest and latest.status is not ExamStatus.CANCELLED
                        else ["create_exam"]
                    ),
                )
            )
        return result

    async def create_exam(
        self, actor: LecturerActor, payload: ExamCreate, request_id: UUID
    ) -> ExamResponse:
        enrollment = await self._lecturer_enrollment(actor, payload.enrollment_id, lock=True)
        if await self._completed_parts(enrollment.id) != self.REQUIRED_PARTS:
            raise ExamConflictError("participant must have five enough video parts")
        existing = await self.session.scalar(
            select(Exam.id).where(
                Exam.enrollment_id == enrollment.id,
                Exam.status != ExamStatus.CANCELLED,
            )
        )
        if existing is not None:
            raise ExamConflictError("participant already has an active exam")
        scheduled_at = ensure_utc(payload.scheduled_at)
        if scheduled_at < utc_now() - timedelta(minutes=5):
            raise ExamConflictError("scheduled_at cannot be in the past")
        policy = enrollment.cohort.policy_version
        if policy.status is not PolicyStatus.PUBLISHED:
            raise ExamConflictError("the cohort policy version is not published")
        exam = Exam(
            enrollment_id=enrollment.id,
            lecturer_id=actor.user_id,
            policy_version_id=policy.id,
            scheduled_at=scheduled_at,
            status=ExamStatus.DRAFT,
            items=[],
        )
        self.session.add(exam)
        await self.session.flush()
        self.session.add(self._audit(actor.user_id, request_id, "exam.draft_created", exam))
        await self.session.flush()
        return self._response(await self._load(exam.id))

    async def update_exam(
        self, actor: LecturerActor, exam_id: UUID, payload: ExamUpdate, request_id: UUID
    ) -> ExamResponse:
        exam = await self._lecturer_exam(actor, exam_id, lock=True, author=True)
        self._require_version(exam, payload.expected_version)
        self._require_draft(exam)
        scheduled_at = ensure_utc(payload.scheduled_at)
        if scheduled_at < utc_now() - timedelta(minutes=5):
            raise ExamConflictError("scheduled_at cannot be in the past")
        exam.scheduled_at = scheduled_at
        exam.notes = self._note(payload.lecturer_note)
        await self.session.flush()
        self.session.add(self._audit(actor.user_id, request_id, "exam.draft_updated", exam))
        await self.session.flush()
        return self._response(await self._load(exam.id))

    async def replace_items(
        self, actor: LecturerActor, exam_id: UUID, payload: ExamItemsReplace, request_id: UUID
    ) -> ExamResponse:
        exam = await self._lecturer_exam(actor, exam_id, lock=True, author=True)
        self._require_version(exam, payload.expected_version)
        self._require_draft(exam)
        ids = [item.question_version_id for item in payload.items]
        if len(ids) != len(set(ids)):
            raise ExamConflictError("an exam package cannot contain a question twice")
        questions = list(
            await self.session.scalars(select(QuestionVersion).where(QuestionVersion.id.in_(ids)))
        )
        indexed = {item.id: item for item in questions}
        if len(indexed) != len(ids) or any(
            not self._question_allowed(actor, indexed.get(question_id)) for question_id in ids
        ):
            raise ExamNotFoundError("question version not found in lecturer scope")
        policy = PolicyRules.model_validate(exam.policy_version.rules).exam_package
        if not policy.approved and any(item.weight is not None for item in payload.items):
            raise ExamConflictError("question weights require an approved exam package policy")
        exam.items.clear()
        await self.session.flush()
        exam.items.extend(
            ExamItem(
                question_version_id=question.id,
                sequence_no=index,
                question_snapshot=self._snapshot(question),
                weight=item.weight,
            )
            for index, item in enumerate(payload.items, start=1)
            for question in [indexed[item.question_version_id]]
        )
        exam.row_version += 1
        await self.session.flush()
        self.session.add(self._audit(actor.user_id, request_id, "exam.items_replaced", exam))
        await self.session.flush()
        return self._response(await self._load(exam.id))

    async def get_exam(self, actor: LecturerActor, exam_id: UUID) -> ExamResponse:
        return self._response(await self._lecturer_exam(actor, exam_id))

    async def list_questions(self, actor: LecturerActor) -> list[QuestionVersionResponse]:
        questions = list(
            await self.session.scalars(
                select(QuestionVersion)
                .where(
                    or_(
                        (QuestionVersion.source == QuestionSource.APPLICATION)
                        & (QuestionVersion.status == QuestionStatus.VERIFIED),
                        (QuestionVersion.source == QuestionSource.LECTURER)
                        & (QuestionVersion.author_id == actor.user_id)
                        & (QuestionVersion.status != QuestionStatus.INACTIVE),
                    )
                )
                .order_by(QuestionVersion.source, QuestionVersion.kind, QuestionVersion.created_at)
            )
        )
        return [self._question_response(item) for item in questions]

    async def create_question(
        self, actor: LecturerActor, payload: QuestionVersionCreate, request_id: UUID
    ) -> QuestionVersionResponse:
        question_key = uuid4()
        version_no = 1
        if payload.previous_version_id is not None:
            previous = await self.session.scalar(
                select(QuestionVersion)
                .where(
                    QuestionVersion.id == payload.previous_version_id,
                    QuestionVersion.source == QuestionSource.LECTURER,
                    QuestionVersion.author_id == actor.user_id,
                    QuestionVersion.status != QuestionStatus.INACTIVE,
                )
                .with_for_update()
            )
            if previous is None:
                raise ExamNotFoundError("previous question version not found in lecturer scope")
            question_key = previous.question_key
            version_no = previous.version_no + 1
            previous.status = QuestionStatus.INACTIVE
        question = QuestionVersion(
            question_key=question_key,
            author_id=actor.user_id,
            source=QuestionSource.LECTURER,
            kind=payload.kind,
            stimulus=payload.stimulus.strip(),
            answer_reference=payload.answer_reference,
            scope=payload.scope,
            version_no=version_no,
            status=QuestionStatus.DRAFT,
        )
        self.session.add(question)
        await self.session.flush()
        self.session.add(
            AuditEvent(
                actor_id=actor.user_id,
                action="question_version.created",
                object_type="question_version",
                object_reference=str(question.id),
                request_id=request_id,
                before_data=None,
                after_data={
                    "question_id": str(question.id),
                    "source": question.source.value,
                    "kind": question.kind.value,
                    "version_no": question.version_no,
                },
            )
        )
        await self.session.flush()
        return self._question_response(question)

    async def _completed_parts(self, enrollment_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(distinct(VideoAttempt.part_id)))
                .select_from(VideoAssessment)
                .join(AssessmentRecord, AssessmentRecord.id == VideoAssessment.id)
                .join(VideoVersion, VideoVersion.id == VideoAssessment.video_version_id)
                .join(VideoAttempt, VideoAttempt.id == VideoVersion.attempt_id)
                .where(
                    AssessmentRecord.enrollment_id == enrollment_id,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                    VideoAssessment.outcome == VideoAssessmentOutcome.ENOUGH,
                )
            )
            or 0
        )

    async def _lecturer_enrollment(
        self, actor: LecturerActor, enrollment_id: UUID, *, lock: bool = False
    ) -> Enrollment:
        now = utc_now()
        statement = (
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.id == enrollment_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
            .options(
                selectinload(Enrollment.user),
                selectinload(Enrollment.cohort).selectinload(Cohort.policy_version),
            )
        )
        if lock:
            statement = statement.with_for_update(of=Enrollment)
        enrollment = await self.session.scalar(statement)
        if enrollment is None:
            raise ExamNotFoundError("participant not found in active lecturer assignment")
        return enrollment

    async def _lecturer_exam(
        self,
        actor: LecturerActor,
        exam_id: UUID,
        *,
        lock: bool = False,
        author: bool = False,
    ) -> Exam:
        now = utc_now()
        statement = (
            self._base_statement()
            .join(Enrollment, Enrollment.id == Exam.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Exam.id == exam_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
        )
        if author:
            statement = statement.where(Exam.lecturer_id == actor.user_id)
        if lock:
            statement = statement.with_for_update(of=Exam)
        exam = await self.session.scalar(statement)
        if exam is None:
            raise ExamNotFoundError("exam not found in active lecturer assignment")
        return exam

    @staticmethod
    def _base_statement() -> Select[Exam]:
        return select(Exam).options(
            selectinload(Exam.enrollment).selectinload(Enrollment.user),
            selectinload(Exam.policy_version),
            selectinload(Exam.items),
        )

    async def _load(self, exam_id: UUID) -> Exam:
        exam = await self.session.scalar(self._base_statement().where(Exam.id == exam_id))
        if exam is None:
            raise ExamNotFoundError("exam not found")
        return exam

    @staticmethod
    def _active_assignment(
        lecturer_id: UUID,
        enrollment_id: ColumnElement[UUID] | InstrumentedAttribute[UUID],
        now: datetime,
    ) -> ColumnElement[bool]:
        return exists(
            select(Assignment.id).where(
                Assignment.enrollment_id == enrollment_id,
                Assignment.staff_id == lecturer_id,
                Assignment.role == AssignmentRole.LECTURER,
                Assignment.valid_from <= now,
                or_(Assignment.valid_to.is_(None), Assignment.valid_to > now),
            )
        )

    @staticmethod
    def _question_allowed(actor: LecturerActor, question: QuestionVersion | None) -> bool:
        if question is None or question.status is QuestionStatus.INACTIVE:
            return False
        if question.source is QuestionSource.APPLICATION:
            return question.status is QuestionStatus.VERIFIED
        return question.author_id == actor.user_id

    @staticmethod
    def _snapshot(question: QuestionVersion) -> dict[str, object]:
        return {
            "source": question.source.value,
            "kind": question.kind.value,
            "stimulus": question.stimulus,
            "scope": question.scope,
            "answer_reference": question.answer_reference,
            "question_key": str(question.question_key),
            "version_no": question.version_no,
        }

    @staticmethod
    def _package_policy(exam: Exam) -> PackagePolicyResponse:
        rule = PolicyRules.model_validate(exam.policy_version.rules).exam_package
        blockers: list[str] = []
        if not rule.approved:
            blockers.append("exam_package_policy_not_approved")
        else:
            if len(exam.items) != rule.required_item_count:
                blockers.append("exam_item_count_mismatch")
            weights = [item.weight for item in exam.items]
            if any(weight is None for weight in weights):
                blockers.append("exam_item_weights_incomplete")
            elif sum((weight for weight in weights if weight is not None), Decimal()) != Decimal(
                rule.expected_total_weight or 0
            ):
                blockers.append("exam_item_weight_total_mismatch")
        return PackagePolicyResponse(
            approved=rule.approved,
            required_item_count=rule.required_item_count,
            expected_total_weight=(
                Decimal(rule.expected_total_weight)
                if rule.expected_total_weight is not None
                else None
            ),
            blockers=blockers,
        )

    @staticmethod
    def _require_draft(exam: Exam) -> None:
        if exam.status is not ExamStatus.DRAFT:
            raise ExamConflictError("only a draft exam can be edited")

    @staticmethod
    def _require_version(exam: Exam, expected_version: int) -> None:
        if exam.row_version != expected_version:
            raise ExamVersionConflictError(exam.row_version)

    @staticmethod
    def _participant(enrollment: Enrollment) -> SessionParticipant:
        return SessionParticipant(
            enrollment_id=enrollment.id,
            user_id=enrollment.user.id,
            display_name=enrollment.user.name,
            nim=enrollment.nim_snapshot,
        )

    @staticmethod
    def _note(value: str | None) -> str | None:
        normalized = value.strip() if value is not None else ""
        return normalized or None

    @staticmethod
    def _audit(actor_id: UUID, request_id: UUID, action: str, exam: Exam) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="exam",
            object_reference=str(exam.id),
            request_id=request_id,
            before_data=None,
            after_data={
                "exam_id": str(exam.id),
                "status": exam.status.value,
                "row_version": exam.row_version,
                "item_count": len(exam.items),
            },
        )

    @staticmethod
    def _question_response(question: QuestionVersion) -> QuestionVersionResponse:
        return QuestionVersionResponse(
            id=question.id,
            question_key=question.question_key,
            author_id=question.author_id,
            source=question.source,
            kind=question.kind,
            stimulus=question.stimulus,
            answer_reference=question.answer_reference,
            scope=question.scope,
            version_no=question.version_no,
            status=question.status,
        )

    @staticmethod
    def _response(exam: Exam) -> ExamResponse:
        package = ExamPackageService._package_policy(exam)
        return ExamResponse(
            id=exam.id,
            participant=ExamPackageService._participant(exam.enrollment),
            lecturer_id=exam.lecturer_id,
            policy_version_id=exam.policy_version_id,
            policy_version=exam.policy_version.version,
            scheduled_at=exam.scheduled_at,
            actual_at=exam.actual_at,
            lecturer_note=exam.notes,
            status=exam.status,
            items=[ExamPackageService._item_response(item) for item in exam.items],
            package_policy=package,
            row_version=exam.row_version,
            finalized_at=exam.finalized_at,
            allowed_actions=(
                ["edit_exam", "edit_items", *(["review_package"] if not package.blockers else [])]
                if exam.status is ExamStatus.DRAFT
                else ["view_exam"]
            ),
        )

    @staticmethod
    def _item_response(item: ExamItem) -> ExamItemResponse:
        snapshot = item.question_snapshot
        scope = snapshot.get("scope")
        answer_reference = snapshot.get("answer_reference")
        version_no = snapshot.get("version_no")
        return ExamItemResponse(
            id=item.id,
            sequence_no=item.sequence_no,
            question_version_id=item.question_version_id,
            source=QuestionSource(str(snapshot["source"])),
            kind=QuestionKind(str(snapshot["kind"])),
            stimulus=str(snapshot["stimulus"]),
            scope=scope if isinstance(scope, dict) else {},
            answer_reference=answer_reference if isinstance(answer_reference, dict) else {},
            question_version_no=version_no if isinstance(version_no, int) else 1,
            weight=item.weight,
        )
