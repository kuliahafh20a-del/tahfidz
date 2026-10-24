"""Transactional theme-assessment use cases and scoped history projections."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.time import ensure_utc, utc_now
from app.modules.assessments.models import (
    AssessmentKind,
    AssessmentRecord,
    AssessmentStatus,
    AssistanceType,
    Incident,
    ThemeAssessment,
    ThemeOutcome,
)
from app.modules.assessments.schemas import (
    IncidentInput,
    IncidentResponse,
    MentorParticipantResponse,
    ThemeAssessmentDraftCreate,
    ThemeAssessmentDraftUpdate,
    ThemeAssessmentResponse,
)
from app.modules.audit.models import AuditEvent
from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.models import Target, TargetStatus
from app.modules.cohorts.models import (
    Assignment,
    AssignmentRole,
    Cohort,
    Enrollment,
    EnrollmentStatus,
)
from app.modules.curriculum.models import PolicyStatus, Theme
from app.modules.curriculum.ordering import memorization_code
from app.modules.curriculum.schemas import PolicyRules
from app.modules.mentoring.access import MentorActor
from app.modules.mentoring.models import MentoringSession, SessionStatus, SessionTheme
from app.modules.mentoring.schemas import SessionParticipant, SessionThemeResponse


class AssessmentResourceNotFoundError(LookupError):
    pass


class AssessmentConflictError(ValueError):
    pass


class AssessmentVersionConflictError(AssessmentConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("assessment was updated by another request")
        self.current_version = current_version


class ThemeAssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_draft(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: ThemeAssessmentDraftCreate,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        mentoring_session = await self._mentor_session(actor, session_id, lock=True)
        if mentoring_session.status is not SessionStatus.IN_PROGRESS:
            raise AssessmentConflictError("session must be in progress before it can be assessed")
        actual_at = ensure_utc(payload.actual_at)
        self._validate_actual_time(mentoring_session, actual_at)
        session_theme = next(
            (
                item
                for item in mentoring_session.session_themes
                if item.theme_id == payload.theme_id
            ),
            None,
        )
        if session_theme is None:
            raise AssessmentResourceNotFoundError("theme is not selected in this session")
        duplicate = await self.session.scalar(
            select(ThemeAssessment.id).where(ThemeAssessment.session_theme_id == session_theme.id)
        )
        if duplicate is not None:
            raise AssessmentConflictError("this session theme already has an assessment")

        target = await self._lock_target(mentoring_session.enrollment_id, payload.theme_id)
        if target.status is TargetStatus.COMPLETED:
            raise AssessmentConflictError("completed themes cannot receive another assessment")
        attempt_no = await self._next_attempt(mentoring_session.enrollment_id, payload.theme_id)
        self._validate_draft(payload.outcome, attempt_no, payload.incidents)
        policy = mentoring_session.enrollment.cohort.policy_version
        if policy.status is not PolicyStatus.PUBLISHED:
            raise AssessmentConflictError("the cohort policy version is not published")

        record = AssessmentRecord(
            enrollment_id=mentoring_session.enrollment_id,
            assessor_id=actor.user_id,
            policy_version_id=policy.id,
            kind=AssessmentKind.THEME,
            actual_at=actual_at,
            manual_score=self._score(payload.manual_score),
            incidents=[],
        )
        self.session.add(record)
        await self.session.flush()
        self.session.add(
            ThemeAssessment(
                id=record.id,
                session_theme_id=session_theme.id,
                attempt_no=attempt_no,
                outcome=payload.outcome,
                notes=self._note(payload.mentor_note),
            )
        )
        self._replace_incidents(record, payload.incidents)
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "theme_assessment.draft_created",
                record,
                before=None,
                after=self._state(record, attempt_no, payload.outcome),
            )
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def update_draft(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        payload: ThemeAssessmentDraftUpdate,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        record = await self._mentor_assessment(actor, assessment_id, lock=True, author=True)
        self._require_version(record, payload.expected_version)
        if record.status is not AssessmentStatus.DRAFT:
            raise AssessmentConflictError("final assessments are immutable")
        subtype = self._subtype(record)
        actual_at = ensure_utc(payload.actual_at)
        self._validate_actual_time(subtype.session_theme.session, actual_at)
        self._validate_draft(payload.outcome, subtype.attempt_no, payload.incidents)
        previous = self._state(record, subtype.attempt_no, subtype.outcome)
        record.actual_at = actual_at
        record.manual_score = self._score(payload.manual_score)
        subtype.outcome = payload.outcome
        subtype.notes = self._note(payload.mentor_note)
        self._replace_incidents(record, payload.incidents)
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "theme_assessment.draft_updated",
                record,
                before=previous,
                after=self._state(record, subtype.attempt_no, subtype.outcome),
            )
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def finalize(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        expected_version: int,
        request_id: UUID,
    ) -> ThemeAssessmentResponse:
        record = await self._mentor_assessment(actor, assessment_id, lock=True, author=True)
        self._require_version(record, expected_version)
        if record.status is not AssessmentStatus.DRAFT:
            raise AssessmentConflictError("assessment is already final")
        subtype = self._subtype(record)
        target = await self._lock_target(record.enrollment_id, subtype.session_theme.theme_id)
        if target.status is TargetStatus.COMPLETED:
            raise AssessmentConflictError("the theme already has an effective enough result")
        self._validate_final(record, subtype)
        previous = self._state(record, subtype.attempt_no, subtype.outcome)
        if subtype.attempt_no == 5 and subtype.outcome is ThemeOutcome.REPEAT:
            subtype.outcome = ThemeOutcome.FOLLOW_UP
        record.status = AssessmentStatus.FINAL
        record.finalized_at = utc_now()
        if subtype.outcome is ThemeOutcome.ENOUGH:
            target.status = TargetStatus.COMPLETED
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "theme_assessment.finalized",
                record,
                before=previous,
                after=self._state(record, subtype.attempt_no, subtype.outcome),
            )
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def get_for_mentor(
        self, actor: MentorActor, assessment_id: UUID
    ) -> ThemeAssessmentResponse:
        return self._response(await self._mentor_assessment(actor, assessment_id))

    async def list_for_session(
        self, actor: MentorActor, session_id: UUID
    ) -> list[ThemeAssessmentResponse]:
        await self._mentor_session(actor, session_id)
        records = list(
            await self.session.scalars(
                self._base_statement()
                .join(ThemeAssessment, ThemeAssessment.id == AssessmentRecord.id)
                .join(SessionTheme, SessionTheme.id == ThemeAssessment.session_theme_id)
                .where(SessionTheme.session_id == session_id)
                .order_by(ThemeAssessment.attempt_no, AssessmentRecord.created_at)
            )
        )
        return [self._response(record) for record in records]

    async def list_participant_results(
        self, actor: ParticipantActor
    ) -> list[ThemeAssessmentResponse]:
        enrollment = await self.session.scalar(
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.user_id == actor.user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
            )
            .order_by(Enrollment.joined_at.desc())
        )
        if enrollment is None:
            raise AssessmentResourceNotFoundError("active enrollment not found")
        records = list(
            await self.session.scalars(
                self._base_statement()
                .where(
                    AssessmentRecord.enrollment_id == enrollment.id,
                    AssessmentRecord.kind == AssessmentKind.THEME,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                )
                .order_by(AssessmentRecord.finalized_at.desc(), AssessmentRecord.id)
            )
        )
        return [self._response(record, participant=True) for record in records]

    async def list_mentor_participants(self, actor: MentorActor) -> list[MentorParticipantResponse]:
        now = utc_now()
        enrollments = list(
            await self.session.scalars(
                select(Enrollment)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .where(
                    Cohort.organization_id == actor.organization_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                    self._active_assignment(actor.user_id, Enrollment.id, now),
                )
                .options(selectinload(Enrollment.user))
                .order_by(Enrollment.nim_snapshot)
            )
        )
        return [await self._participant_summary(item) for item in enrollments]

    async def get_mentor_participant(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> MentorParticipantResponse:
        enrollment = await self._mentor_enrollment(actor, enrollment_id)
        return await self._participant_summary(enrollment)

    async def assessment_history(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> list[ThemeAssessmentResponse]:
        await self._mentor_enrollment(actor, enrollment_id)
        records = list(
            await self.session.scalars(
                self._base_statement()
                .where(
                    AssessmentRecord.enrollment_id == enrollment_id,
                    AssessmentRecord.kind == AssessmentKind.THEME,
                )
                .order_by(AssessmentRecord.created_at.desc(), AssessmentRecord.id.desc())
            )
        )
        return [self._response(record) for record in records]

    async def _mentor_session(
        self, actor: MentorActor, session_id: UUID, *, lock: bool = False
    ) -> MentoringSession:
        now = utc_now()
        statement = (
            select(MentoringSession)
            .join(Enrollment, Enrollment.id == MentoringSession.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                MentoringSession.id == session_id,
                MentoringSession.mentor_id == actor.user_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
            .options(
                selectinload(MentoringSession.enrollment).selectinload(Enrollment.user),
                selectinload(MentoringSession.enrollment)
                .selectinload(Enrollment.cohort)
                .selectinload(Cohort.policy_version),
                selectinload(MentoringSession.session_themes)
                .selectinload(SessionTheme.theme)
                .selectinload(Theme.part),
            )
        )
        if lock:
            statement = statement.with_for_update(of=MentoringSession)
        record = await self.session.scalar(statement)
        if record is None:
            raise AssessmentResourceNotFoundError("session not found in active assignment")
        return record

    async def _mentor_assessment(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        *,
        lock: bool = False,
        author: bool = False,
    ) -> AssessmentRecord:
        now = utc_now()
        statement = (
            self._base_statement()
            .join(Enrollment, Enrollment.id == AssessmentRecord.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                AssessmentRecord.id == assessment_id,
                AssessmentRecord.kind == AssessmentKind.THEME,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
        )
        if author:
            statement = statement.where(AssessmentRecord.assessor_id == actor.user_id)
        if lock:
            statement = statement.with_for_update(of=AssessmentRecord)
        record = await self.session.scalar(statement)
        if record is None:
            raise AssessmentResourceNotFoundError("assessment not found in active assignment")
        return record

    async def _mentor_enrollment(self, actor: MentorActor, enrollment_id: UUID) -> Enrollment:
        now = utc_now()
        record = await self.session.scalar(
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.id == enrollment_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
            .options(selectinload(Enrollment.user))
        )
        if record is None:
            raise AssessmentResourceNotFoundError("participant not found in active assignment")
        return record

    async def _lock_target(self, enrollment_id: UUID, theme_id: UUID) -> Target:
        target = await self.session.scalar(
            select(Target)
            .where(Target.enrollment_id == enrollment_id, Target.theme_id == theme_id)
            .with_for_update(of=Target)
        )
        if target is None:
            raise AssessmentResourceNotFoundError("participant theme target not found")
        return target

    async def _next_attempt(self, enrollment_id: UUID, theme_id: UUID) -> int:
        current = await self.session.scalar(
            select(func.max(ThemeAssessment.attempt_no))
            .join(AssessmentRecord, AssessmentRecord.id == ThemeAssessment.id)
            .join(SessionTheme, SessionTheme.id == ThemeAssessment.session_theme_id)
            .join(MentoringSession, MentoringSession.id == SessionTheme.session_id)
            .where(
                AssessmentRecord.enrollment_id == enrollment_id,
                SessionTheme.theme_id == theme_id,
                AssessmentRecord.status != AssessmentStatus.SUPERSEDED,
            )
        )
        attempt_no = int(current or 0) + 1
        if attempt_no > 5:
            raise AssessmentConflictError("a sixth theme attempt cannot be created automatically")
        return attempt_no

    def _base_statement(self) -> Select[AssessmentRecord]:
        return select(AssessmentRecord).options(
            selectinload(AssessmentRecord.enrollment).selectinload(Enrollment.user),
            selectinload(AssessmentRecord.assessor),
            selectinload(AssessmentRecord.policy_version),
            selectinload(AssessmentRecord.incidents),
            selectinload(AssessmentRecord.theme_assessment)
            .selectinload(ThemeAssessment.session_theme)
            .selectinload(SessionTheme.theme)
            .selectinload(Theme.part),
            selectinload(AssessmentRecord.theme_assessment)
            .selectinload(ThemeAssessment.session_theme)
            .selectinload(SessionTheme.session),
        )

    async def _load(self, assessment_id: UUID) -> AssessmentRecord:
        record = await self.session.scalar(
            self._base_statement().where(AssessmentRecord.id == assessment_id)
        )
        if record is None:
            raise AssessmentResourceNotFoundError("assessment not found")
        return record

    async def _participant_summary(self, enrollment: Enrollment) -> MentorParticipantResponse:
        final_assessments = int(
            await self.session.scalar(
                select(func.count(AssessmentRecord.id)).where(
                    AssessmentRecord.enrollment_id == enrollment.id,
                    AssessmentRecord.kind == AssessmentKind.THEME,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                )
            )
            or 0
        )
        enough_themes = int(
            await self.session.scalar(
                select(func.count(ThemeAssessment.id))
                .join(AssessmentRecord, AssessmentRecord.id == ThemeAssessment.id)
                .where(
                    AssessmentRecord.enrollment_id == enrollment.id,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                    ThemeAssessment.outcome == ThemeOutcome.ENOUGH,
                )
            )
            or 0
        )
        follow_up_themes = int(
            await self.session.scalar(
                select(func.count(ThemeAssessment.id))
                .join(AssessmentRecord, AssessmentRecord.id == ThemeAssessment.id)
                .where(
                    AssessmentRecord.enrollment_id == enrollment.id,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                    ThemeAssessment.outcome == ThemeOutcome.FOLLOW_UP,
                )
            )
            or 0
        )
        return MentorParticipantResponse(
            enrollment_id=enrollment.id,
            user_id=enrollment.user.id,
            display_name=enrollment.user.name,
            nim=enrollment.nim_snapshot,
            final_assessments=final_assessments,
            enough_themes=enough_themes,
            follow_up_themes=follow_up_themes,
            allowed_actions=["view_assessment_history"],
        )

    @staticmethod
    def _active_assignment(
        mentor_id: UUID,
        enrollment_id: ColumnElement[UUID] | InstrumentedAttribute[UUID],
        moment: datetime,
    ) -> ColumnElement[bool]:
        return exists(
            select(Assignment.id).where(
                Assignment.enrollment_id == enrollment_id,
                Assignment.staff_id == mentor_id,
                Assignment.role == AssignmentRole.MENTOR,
                Assignment.valid_from <= moment,
                or_(Assignment.valid_to.is_(None), Assignment.valid_to > moment),
            )
        )

    @staticmethod
    def _validate_actual_time(session: MentoringSession, actual_at: object) -> None:
        if session.actual_at is None:
            raise AssessmentConflictError("session actual time has not been recorded")
        actual = ensure_utc(actual_at)  # type: ignore[arg-type]
        if actual < session.actual_at:
            raise AssessmentConflictError("assessment time cannot precede the session start")
        if actual > utc_now() + timedelta(minutes=5):
            raise AssessmentConflictError("assessment time cannot be in the future")

    @staticmethod
    def _validate_draft(
        outcome: ThemeOutcome | None,
        attempt_no: int,
        incidents: list[IncidentInput],
    ) -> None:
        if outcome is ThemeOutcome.FOLLOW_UP and attempt_no < 5:
            raise AssessmentConflictError("follow_up is only valid on the fifth attempt")
        for item in incidents:
            if item.video_second is not None:
                raise AssessmentConflictError("theme incidents cannot use a video timestamp")
            if item.assistance is AssistanceType.ANSWER and item.self_corrected:
                raise AssessmentConflictError(
                    "an incident answered by the mentor cannot be self-corrected"
                )
            if not item.counted and (
                not item.self_corrected or item.assistance is AssistanceType.ANSWER
            ):
                raise AssessmentConflictError(
                    "a non-counted incident must be self-corrected without an answer"
                )

    def _validate_final(self, record: AssessmentRecord, subtype: ThemeAssessment) -> None:
        if record.manual_score is None:
            raise AssessmentConflictError("manual score is required before finalization")
        rules = PolicyRules.model_validate(record.policy_version.rules)
        score = int(record.manual_score)
        if Decimal(score) != record.manual_score or not (
            rules.score.minimum <= score <= rules.score.maximum
        ):
            raise AssessmentConflictError("manual score must be a whole number from 1 to 10")
        if subtype.outcome is None:
            raise AssessmentConflictError("theme outcome is required before finalization")
        if subtype.outcome is ThemeOutcome.FOLLOW_UP and subtype.attempt_no < 5:
            raise AssessmentConflictError("follow_up is only valid on the fifth attempt")
        for incident in record.incidents:
            if not self._note(incident.count_reason):
                raise AssessmentConflictError("every final incident requires a counting reason")
            if incident.assistance_type is AssistanceType.ANSWER and incident.self_corrected:
                raise AssessmentConflictError(
                    "an incident answered by the mentor cannot be self-corrected"
                )
            if not incident.counted and (
                not incident.self_corrected or incident.assistance_type is AssistanceType.ANSWER
            ):
                raise AssessmentConflictError(
                    "a non-counted incident must be self-corrected without an answer"
                )

    @staticmethod
    def _score(value: int | None) -> Decimal | None:
        return Decimal(value) if value is not None else None

    @staticmethod
    def _note(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _replace_incidents(self, record: AssessmentRecord, items: list[IncidentInput]) -> None:
        record.incidents.clear()
        record.incidents.extend(
            Incident(
                category=item.primary_category.strip(),
                location_text=item.location_text.strip(),
                video_second=item.video_second,
                context=self._note(item.context),
                assistance_type=item.assistance,
                self_corrected=item.self_corrected,
                counted=item.counted,
                count_reason=self._note(item.counting_reason),
                notes=self._note(item.note),
            )
            for item in items
        )

    @staticmethod
    def _subtype(record: AssessmentRecord) -> ThemeAssessment:
        if record.theme_assessment is None:
            raise AssessmentConflictError("theme assessment subtype is missing")
        return record.theme_assessment

    @staticmethod
    def _require_version(record: AssessmentRecord, expected_version: int) -> None:
        if record.row_version != expected_version:
            raise AssessmentVersionConflictError(record.row_version)

    @staticmethod
    def _state(
        record: AssessmentRecord,
        attempt_no: int,
        outcome: ThemeOutcome | None,
    ) -> dict[str, object]:
        return {
            "status": record.status.value,
            "attempt_no": attempt_no,
            "outcome": outcome.value if outcome is not None else None,
            "manual_score": int(record.manual_score) if record.manual_score is not None else None,
            "actual_at": record.actual_at.isoformat(),
            "finalized_at": record.finalized_at.isoformat() if record.finalized_at else None,
        }

    @staticmethod
    def _audit(
        actor_id: UUID,
        request_id: UUID,
        action: str,
        record: AssessmentRecord,
        *,
        before: Mapping[str, object] | None,
        after: Mapping[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="theme_assessment",
            object_reference=str(record.id),
            request_id=request_id,
            before_data=dict(before) if before is not None else None,
            after_data=dict(after),
        )

    def _response(
        self, record: AssessmentRecord, *, participant: bool = False
    ) -> ThemeAssessmentResponse:
        subtype = self._subtype(record)
        session_theme = subtype.session_theme
        theme = session_theme.theme
        return ThemeAssessmentResponse(
            assessment_id=record.id,
            session_id=session_theme.session_id,
            session_theme_id=session_theme.id,
            participant=SessionParticipant(
                enrollment_id=record.enrollment.id,
                user_id=record.enrollment.user.id,
                display_name=record.enrollment.user.name,
                nim=record.enrollment.nim_snapshot,
            ),
            theme=SessionThemeResponse(
                id=session_theme.id,
                theme_id=theme.id,
                code=memorization_code(theme.part.sequence_no, theme.sequence_no),
                name=theme.title,
                part_id=theme.part.id,
                part_no=theme.part.sequence_no,
                part_name=theme.part.title,
            ),
            status=record.status,
            attempt_no=subtype.attempt_no,
            outcome=subtype.outcome,
            manual_score=int(record.manual_score) if record.manual_score is not None else None,
            actual_at=record.actual_at,
            finalized_at=record.finalized_at,
            mentor_note=subtype.notes,
            incidents=[
                IncidentResponse(
                    id=item.id,
                    location_text=item.location_text,
                    video_second=item.video_second,
                    primary_category=item.category,
                    context=item.context,
                    assistance=item.assistance_type,
                    self_corrected=item.self_corrected,
                    counted=item.counted,
                    counting_reason=item.count_reason,
                    note=item.notes,
                )
                for item in record.incidents
            ],
            counted_incidents=sum(item.counted for item in record.incidents),
            policy_version_id=record.policy_version_id,
            policy_version=record.policy_version.version,
            row_version=record.row_version,
            allowed_actions=[]
            if participant or record.status is not AssessmentStatus.DRAFT
            else ["edit", "review", "finalize"],
        )
