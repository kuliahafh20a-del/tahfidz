"""Calculate the auditable activity component from immutable source facts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Select, distinct, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import ensure_utc, utc_now
from app.modules.assessments.models import (
    AssessmentKind,
    AssessmentRecord,
    AssessmentStatus,
    ExamAssessment,
    ThemeAssessment,
    VideoAssessment,
    VideoAssessmentOutcome,
)
from app.modules.audit.models import AuditEvent
from app.modules.auth.service import AuthenticatedSession
from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.models import Target
from app.modules.cohorts.models import (
    Assignment,
    AssignmentRole,
    Cohort,
    Enrollment,
    EnrollmentStatus,
)
from app.modules.curriculum.models import Theme
from app.modules.curriculum.schemas import PolicyRules
from app.modules.exams.models import Exam, ExamItem, ExamStatus
from app.modules.grading.models import GradeComponent, GradeSnapshot, GradeSource, GradeStatus
from app.modules.grading.schemas import (
    ActivityScoreResponse,
    ActivitySourceContext,
    ActivityThemeScore,
    GradeComponentResponse,
    GradeHistoryResponse,
    GradeSnapshotResponse,
    GradeSourceResponse,
)
from app.modules.identity.models import Role
from app.modules.mentoring.models import SessionTheme
from app.modules.organizations.models import Organization
from app.modules.video.models import VideoAttempt, VideoVersion

BUSINESS_TIMEZONE = ZoneInfo("Asia/Jakarta")


class ActivityEnrollmentNotFoundError(LookupError):
    """The participant has no enrollment in the requested organization."""


class ActivityScoreCalculator:
    """Pure scoring rules shared by live views and future grade snapshots."""

    @staticmethod
    def score_for_submission(due_date: date, submitted_at: datetime) -> tuple[int, int]:
        submitted_date = ActivityScoreCalculator.local_date(submitted_at)
        days_late = (submitted_date - due_date).days
        if days_late <= 0:
            return 10, days_late
        return max(2, 10 - ((days_late + 6) // 7)), days_late

    @staticmethod
    def score_for_target(
        due_date: date,
        first_submission_at: datetime | None,
        *,
        cutoff_date: date,
        period_closed: bool,
    ) -> tuple[int | None, int | None]:
        if first_submission_at is not None:
            return ActivityScoreCalculator.score_for_submission(due_date, first_submission_at)
        if period_closed and due_date < cutoff_date:
            return 1, None
        return None, None

    @staticmethod
    def local_date(moment: datetime) -> date:
        if moment.tzinfo is None or moment.utcoffset() is None:
            moment = moment.replace(tzinfo=UTC)
        return moment.astimezone(BUSINESS_TIMEZONE).date()


class ActivityScoreService:
    """Derive K without mutating target or assessment history."""

    REQUIRED_TARGETS = 44

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def for_participant(
        self, actor: ParticipantActor, *, cutoff_at: datetime | None = None
    ) -> ActivityScoreResponse:
        enrollment = await self.session.scalar(
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.user_id == actor.user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
            )
            .options(selectinload(Enrollment.cohort))
            .order_by(Enrollment.joined_at.desc())
        )
        if enrollment is None:
            raise ActivityEnrollmentNotFoundError("active enrollment not found")
        return await self.for_enrollment(enrollment, cutoff_at=cutoff_at)

    async def for_enrollment(
        self, enrollment: Enrollment, *, cutoff_at: datetime | None = None
    ) -> ActivityScoreResponse:
        cutoff = ensure_utc(cutoff_at or utc_now())
        targets = list(
            await self.session.scalars(
                select(Target)
                .where(Target.enrollment_id == enrollment.id)
                .options(selectinload(Target.theme).selectinload(Theme.part))
                .order_by(Target.effective_due_date, Target.id)
            )
        )
        first_submissions = dict(
            (
                await self.session.execute(
                    select(SessionTheme.theme_id, func.min(AssessmentRecord.actual_at))
                    .join(
                        ThemeAssessment,
                        ThemeAssessment.session_theme_id == SessionTheme.id,
                    )
                    .join(AssessmentRecord, AssessmentRecord.id == ThemeAssessment.id)
                    .where(
                        AssessmentRecord.enrollment_id == enrollment.id,
                        AssessmentRecord.status == AssessmentStatus.FINAL,
                        AssessmentRecord.actual_at <= cutoff,
                        AssessmentRecord.finalized_at <= cutoff,
                    )
                    .group_by(SessionTheme.theme_id)
                )
            ).all()
        )
        local_cutoff = ActivityScoreCalculator.local_date(cutoff)
        period_closed = (
            enrollment.cohort.close_date is not None
            and enrollment.cohort.close_date <= local_cutoff
        )
        theme_scores: list[ActivityThemeScore] = []
        scores: list[int] = []
        overdue = 0
        for target in targets:
            first = first_submissions.get(target.theme_id)
            score, days_late = ActivityScoreCalculator.score_for_target(
                target.effective_due_date,
                first,
                cutoff_date=local_cutoff,
                period_closed=period_closed,
            )
            if score is not None:
                scores.append(score)
            if first is None and target.effective_due_date < local_cutoff:
                overdue += 1
            theme_scores.append(
                ActivityThemeScore(
                    target_id=target.id,
                    theme_id=target.theme_id,
                    effective_due_date=target.effective_due_date,
                    first_valid_submission_at=first,
                    days_late=days_late,
                    score=score,
                )
            )
        value = (
            (sum((Decimal(item) for item in scores), Decimal()) / Decimal(len(scores))).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
            if scores
            else None
        )
        is_final = len(targets) == self.REQUIRED_TARGETS and len(scores) == len(targets)
        return ActivityScoreResponse(
            value=value,
            is_final=is_final,
            source_context=ActivitySourceContext(
                cutoff_at=cutoff,
                total_target_count=len(targets),
                scored_target_count=len(scores),
                overdue_target_count=overdue,
                themes=theme_scores,
            ),
        )


class GradeSnapshotNotFoundError(LookupError):
    """No grade snapshot has been published for the participant."""


class GradeScopeDeniedError(PermissionError):
    """The active role cannot read or publish this enrollment's grades."""


class GradeSnapshotService:
    """Publish and reconstruct immutable grade snapshots without inventing missing values."""

    REQUIRED_PARTS = 5
    K_WEIGHT = Decimal("0.200")
    M_WEIGHT = Decimal("0.400")
    D_WEIGHT = Decimal("0.400")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest_for_participant(self, actor: ParticipantActor) -> GradeSnapshotResponse:
        enrollment = await self._participant_enrollment(actor)
        snapshot = await self._latest(enrollment.id)
        if snapshot is None:
            raise GradeSnapshotNotFoundError("grade snapshot not found")
        return self._response(snapshot)

    async def history_for_participant(self, actor: ParticipantActor) -> GradeHistoryResponse:
        enrollment = await self._participant_enrollment(actor)
        snapshots = list(
            await self.session.scalars(
                self._snapshot_statement()
                .where(GradeSnapshot.enrollment_id == enrollment.id)
                .order_by(GradeSnapshot.calculated_at.desc(), GradeSnapshot.id.desc())
            )
        )
        return GradeHistoryResponse(items=[self._response(item) for item in snapshots])

    async def publish_for_participant(
        self, actor: ParticipantActor, *, request_id: UUID
    ) -> GradeSnapshotResponse:
        enrollment = await self._participant_enrollment(actor, lock=True)
        return await self.publish(enrollment, actor_id=actor.user_id, request_id=request_id)

    async def latest_for_enrollment(
        self, authenticated: AuthenticatedSession, enrollment_id: UUID
    ) -> GradeSnapshotResponse:
        enrollment = await self._scoped_enrollment(authenticated, enrollment_id)
        snapshot = await self._latest(enrollment.id)
        if snapshot is None:
            raise GradeSnapshotNotFoundError("grade snapshot not found")
        return self._response(snapshot)

    async def history_for_enrollment(
        self, authenticated: AuthenticatedSession, enrollment_id: UUID
    ) -> GradeHistoryResponse:
        enrollment = await self._scoped_enrollment(authenticated, enrollment_id)
        snapshots = list(
            await self.session.scalars(
                self._snapshot_statement()
                .where(GradeSnapshot.enrollment_id == enrollment.id)
                .order_by(GradeSnapshot.calculated_at.desc(), GradeSnapshot.id.desc())
            )
        )
        return GradeHistoryResponse(items=[self._response(item) for item in snapshots])

    async def publish_for_enrollment(
        self,
        authenticated: AuthenticatedSession,
        enrollment_id: UUID,
        *,
        request_id: UUID,
    ) -> GradeSnapshotResponse:
        enrollment = await self._scoped_enrollment(authenticated, enrollment_id, lock=True)
        return await self.publish(enrollment, actor_id=authenticated.user_id, request_id=request_id)

    async def publish(
        self, enrollment: Enrollment, *, actor_id: UUID, request_id: UUID
    ) -> GradeSnapshotResponse:
        calculated_at = ensure_utc(utc_now())
        activity = await ActivityScoreService(self.session).for_enrollment(
            enrollment, cutoff_at=calculated_at
        )
        rules = PolicyRules.model_validate(enrollment.cohort.policy_version.rules)
        mentor_records = list(
            await self.session.scalars(
                select(AssessmentRecord)
                .where(
                    AssessmentRecord.enrollment_id == enrollment.id,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                    AssessmentRecord.kind.in_([AssessmentKind.THEME, AssessmentKind.VIDEO]),
                    AssessmentRecord.finalized_at <= calculated_at,
                )
                .order_by(AssessmentRecord.finalized_at, AssessmentRecord.id)
            )
        )
        current_exam = await self.session.scalar(
            select(Exam)
            .where(
                Exam.enrollment_id == enrollment.id,
                Exam.status != ExamStatus.CANCELLED,
            )
            .order_by(Exam.created_at.desc(), Exam.id.desc())
            .limit(1)
        )
        final_exam = (
            current_exam
            if current_exam is not None
            and current_exam.status is ExamStatus.FINAL
            and current_exam.finalized_at is not None
            and current_exam.finalized_at <= calculated_at
            else None
        )
        exam_records: list[AssessmentRecord] = []
        if final_exam is not None:
            exam_records = list(
                await self.session.scalars(
                    select(AssessmentRecord)
                    .join(ExamAssessment, ExamAssessment.id == AssessmentRecord.id)
                    .join(ExamItem, ExamItem.id == ExamAssessment.exam_item_id)
                    .where(
                        ExamItem.exam_id == final_exam.id,
                        AssessmentRecord.enrollment_id == enrollment.id,
                        AssessmentRecord.status == AssessmentStatus.FINAL,
                    )
                    .order_by(AssessmentRecord.id)
                )
            )

        m_value = self._mentor_value(mentor_records, rules)
        d_value = (
            final_exam.d_score
            if final_exam is not None
            and rules.exam_package.approved
            and final_exam.d_score is not None
            else None
        )
        k_value = activity.value
        completed_parts = await self._completed_parts(enrollment.id)
        missing = self._missing_requirements(
            activity_final=activity.is_final,
            mentor_policy_approved=rules.mentor_aggregation.approved,
            m_value=m_value,
            final_exam=final_exam,
            d_value=d_value,
            grade_policy_approved=rules.grade_calculation.approved,
            completed_parts=completed_parts,
        )
        n_value = None
        if not missing and k_value is not None and m_value is not None and d_value is not None:
            n_value = self.final_score(k_value, m_value, d_value)
        status = self._status(
            completed_parts=completed_parts,
            current_exam=current_exam,
            final_exam=final_exam,
            components_complete=n_value is not None,
            final_score=n_value,
            threshold=Decimal(str(rules.grade_calculation.graduation_threshold)),
        )
        previous = await self._latest(enrollment.id, lock=True)
        source_context: dict[str, object] = {
            "cutoff_at": calculated_at.isoformat(),
            "activity": activity.source_context.model_dump(mode="json"),
            "activity_is_final": activity.is_final,
            "completed_part_count": completed_parts,
            "required_part_count": self.REQUIRED_PARTS,
            "final_exam_id": str(final_exam.id) if final_exam is not None else None,
            "exam_status": current_exam.status.value if current_exam is not None else None,
            "mentor_aggregation": rules.mentor_aggregation.model_dump(mode="json"),
            "exam_aggregation": rules.exam_package.model_dump(mode="json"),
            "grade_calculation": rules.grade_calculation.model_dump(mode="json"),
            "missing_requirements": missing,
        }
        snapshot = GradeSnapshot(
            enrollment_id=enrollment.id,
            policy_version_id=enrollment.cohort.policy_version_id,
            k_value=k_value,
            m_value=m_value,
            d_value=d_value,
            n_value=n_value,
            status=status,
            source_context=source_context,
            calculated_at=calculated_at,
            supersedes_id=previous.id if previous is not None else None,
            sources=[],
        )
        snapshot.sources.extend(
            GradeSource(
                assessment_id=record.id,
                component=GradeComponent.M,
                contribution=record.manual_score,
            )
            for record in mentor_records
        )
        snapshot.sources.extend(
            GradeSource(
                assessment_id=record.id,
                component=GradeComponent.D,
                contribution=record.manual_score,
            )
            for record in exam_records
        )
        self.session.add(snapshot)
        await self.session.flush()
        self.session.add(
            AuditEvent(
                actor_id=actor_id,
                action="grade_snapshot.published",
                object_type="grade_snapshot",
                object_reference=str(snapshot.id),
                request_id=request_id,
                before_data={"snapshot_id": str(previous.id)} if previous is not None else None,
                after_data={
                    "enrollment_id": str(enrollment.id),
                    "status": status.value,
                    "components": {
                        "k": str(k_value) if k_value is not None else None,
                        "m": str(m_value) if m_value is not None else None,
                        "d": str(d_value) if d_value is not None else None,
                        "n": str(n_value) if n_value is not None else None,
                    },
                },
            )
        )
        await self.session.flush()
        return self._response(snapshot, policy_version=enrollment.cohort.policy_version.version)

    @staticmethod
    def final_score(k_value: Decimal, m_value: Decimal, d_value: Decimal) -> Decimal:
        return (
            k_value * GradeSnapshotService.K_WEIGHT
            + m_value * GradeSnapshotService.M_WEIGHT
            + d_value * GradeSnapshotService.D_WEIGHT
        ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _mentor_value(records: list[AssessmentRecord], rules: PolicyRules) -> Decimal | None:
        policy = rules.mentor_aggregation
        if not policy.approved:
            return None
        scores = [item.manual_score for item in records if item.manual_score is not None]
        if not scores:
            return None
        return (sum(scores, Decimal()) / Decimal(len(scores))).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _missing_requirements(
        *,
        activity_final: bool,
        mentor_policy_approved: bool,
        m_value: Decimal | None,
        final_exam: Exam | None,
        d_value: Decimal | None,
        grade_policy_approved: bool,
        completed_parts: int,
    ) -> list[str]:
        missing: list[str] = []
        if not activity_final:
            missing.append("activity_44_themes_incomplete")
        if completed_parts != GradeSnapshotService.REQUIRED_PARTS:
            missing.append("five_parts_not_enough")
        if not mentor_policy_approved:
            missing.append("mentor_aggregation_policy")
        elif m_value is None:
            missing.append("mentor_assessments_incomplete")
        if final_exam is None:
            missing.append("final_exam")
        if final_exam is not None and d_value is None:
            missing.append("lecturer_component_unavailable")
        if not grade_policy_approved:
            missing.append("grade_calculation_policy")
        return missing

    @staticmethod
    def _status(
        *,
        completed_parts: int,
        current_exam: Exam | None,
        final_exam: Exam | None,
        components_complete: bool,
        final_score: Decimal | None,
        threshold: Decimal,
    ) -> GradeStatus:
        if completed_parts != GradeSnapshotService.REQUIRED_PARTS:
            return GradeStatus.INCOMPLETE
        if final_exam is None:
            return (
                GradeStatus.AWAITING_EXAM
                if current_exam is not None
                else GradeStatus.READY_FOR_EXAM
            )
        if not components_complete:
            return GradeStatus.AWAITING_COMPONENTS
        return (
            GradeStatus.GRADUATED
            if final_score is not None and final_score >= threshold
            else GradeStatus.NOT_GRADUATED
        )

    async def _participant_enrollment(
        self, actor: ParticipantActor, *, lock: bool = False
    ) -> Enrollment:
        statement = (
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.user_id == actor.user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
            )
            .options(selectinload(Enrollment.cohort).selectinload(Cohort.policy_version))
            .order_by(Enrollment.joined_at.desc())
        )
        if lock:
            statement = statement.with_for_update(of=Enrollment)
        enrollment = await self.session.scalar(statement)
        if enrollment is None:
            raise ActivityEnrollmentNotFoundError("active enrollment not found")
        return enrollment

    async def _scoped_enrollment(
        self,
        authenticated: AuthenticatedSession,
        enrollment_id: UUID,
        *,
        lock: bool = False,
    ) -> Enrollment:
        context = authenticated.active_context
        if context is None:
            raise GradeScopeDeniedError("active role context required")
        now = utc_now()
        statement = (
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .join(Organization, Organization.id == Cohort.organization_id)
            .where(Enrollment.id == enrollment_id)
            .options(selectinload(Enrollment.cohort).selectinload(Cohort.policy_version))
        )
        if context.role is Role.PARTICIPANT:
            statement = statement.where(
                Enrollment.user_id == authenticated.user_id,
                Cohort.organization_id == context.organization_id,
            )
        elif context.role is Role.DEPARTMENT_ADMIN:
            statement = statement.where(Cohort.organization_id == context.organization_id)
        elif context.role is Role.FACULTY_ADMIN:
            statement = statement.where(Organization.parent_id == context.organization_id)
        elif context.role in {Role.MENTOR, Role.LECTURER}:
            assignment_role = (
                AssignmentRole.MENTOR if context.role is Role.MENTOR else AssignmentRole.LECTURER
            )
            statement = statement.where(
                Cohort.organization_id == context.organization_id,
                exists(
                    select(Assignment.id).where(
                        Assignment.enrollment_id == Enrollment.id,
                        Assignment.staff_id == authenticated.user_id,
                        Assignment.role == assignment_role,
                        Assignment.valid_from <= now,
                        or_(Assignment.valid_to.is_(None), Assignment.valid_to > now),
                    )
                ),
            )
        else:
            raise GradeScopeDeniedError("unsupported active role")
        if lock:
            statement = statement.with_for_update(of=Enrollment)
        enrollment = await self.session.scalar(statement)
        if enrollment is None:
            raise GradeScopeDeniedError("enrollment outside active role scope")
        return enrollment

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

    @staticmethod
    def _snapshot_statement() -> Select[GradeSnapshot]:
        return select(GradeSnapshot).options(
            selectinload(GradeSnapshot.policy_version),
            selectinload(GradeSnapshot.sources),
        )

    async def _latest(self, enrollment_id: UUID, *, lock: bool = False) -> GradeSnapshot | None:
        statement = (
            self._snapshot_statement()
            .where(GradeSnapshot.enrollment_id == enrollment_id)
            .order_by(GradeSnapshot.calculated_at.desc(), GradeSnapshot.id.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update(of=GradeSnapshot)
        return await self.session.scalar(statement)

    def _response(
        self, snapshot: GradeSnapshot, *, policy_version: str | None = None
    ) -> GradeSnapshotResponse:
        raw_missing = snapshot.source_context.get("missing_requirements")
        missing = [str(item) for item in raw_missing] if isinstance(raw_missing, list) else []
        final_exam_id = snapshot.source_context.get("final_exam_id")
        raw_completed = snapshot.source_context.get("completed_part_count")
        completed = raw_completed if isinstance(raw_completed, int) else 0
        exam_status = snapshot.source_context.get("exam_status")
        exam_readiness: Literal["not_ready", "ready_for_exam", "exam_in_progress", "exam_final"]
        if final_exam_id:
            exam_readiness = "exam_final"
        elif exam_status in {
            ExamStatus.DRAFT.value,
            ExamStatus.SCHEDULED.value,
            ExamStatus.IN_PROGRESS.value,
        }:
            exam_readiness = "exam_in_progress"
        elif completed == self.REQUIRED_PARTS:
            exam_readiness = "ready_for_exam"
        else:
            exam_readiness = "not_ready"
        graduation_status: Literal["graduated", "not_graduated"] | None = (
            "graduated"
            if snapshot.status is GradeStatus.GRADUATED
            else "not_graduated"
            if snapshot.status is GradeStatus.NOT_GRADUATED
            else None
        )
        return GradeSnapshotResponse(
            id=snapshot.id,
            enrollment_id=snapshot.enrollment_id,
            status=snapshot.status.value,
            exam_readiness=exam_readiness,
            components={
                "k": GradeComponentResponse(
                    value=snapshot.k_value,
                    weight=self.K_WEIGHT,
                    status="available" if snapshot.k_value is not None else "incomplete",
                ),
                "m": GradeComponentResponse(
                    value=snapshot.m_value,
                    weight=self.M_WEIGHT,
                    status=(
                        "available"
                        if snapshot.m_value is not None
                        else "policy_pending"
                        if "mentor_aggregation_policy" in missing
                        else "not_assessed"
                    ),
                ),
                "d": GradeComponentResponse(
                    value=snapshot.d_value,
                    weight=self.D_WEIGHT,
                    status=(
                        "available"
                        if snapshot.d_value is not None
                        else "policy_pending"
                        if "lecturer_component_unavailable" in missing
                        else "not_assessed"
                    ),
                ),
            },
            final_score=snapshot.n_value,
            graduation_status=graduation_status,
            policy_version_id=snapshot.policy_version_id,
            policy_version=policy_version or snapshot.policy_version.version,
            calculated_at=snapshot.calculated_at,
            supersedes_id=snapshot.supersedes_id,
            missing_requirements=missing,
            source_context=snapshot.source_context,
            sources=[
                GradeSourceResponse(
                    assessment_id=item.assessment_id,
                    component=item.component.value,
                    contribution=item.contribution,
                )
                for item in snapshot.sources
            ],
        )
