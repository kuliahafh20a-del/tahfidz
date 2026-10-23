"""Calculate the auditable activity component from immutable source facts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import ensure_utc, utc_now
from app.modules.assessments.models import AssessmentRecord, AssessmentStatus, ThemeAssessment
from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.models import Target
from app.modules.cohorts.models import Cohort, Enrollment, EnrollmentStatus
from app.modules.curriculum.models import Theme
from app.modules.grading.schemas import (
    ActivityScoreResponse,
    ActivitySourceContext,
    ActivityThemeScore,
)
from app.modules.mentoring.models import SessionTheme

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
