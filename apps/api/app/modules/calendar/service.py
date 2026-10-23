"""Target generation and participant-facing calendar projections."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.models import Target, TargetStatus
from app.modules.calendar.schemas import (
    DashboardResponse,
    ParticipantSummary,
    PartProgress,
    ProgressResponse,
    TargetResponse,
    TargetTheme,
)
from app.modules.cohorts.models import Cohort, Enrollment, EnrollmentStatus
from app.modules.curriculum.models import Part, Theme
from app.modules.grading.schemas import ActivityScoreResponse, ActivityThemeScore
from app.modules.grading.service import ActivityScoreService


class ParticipantEnrollmentNotFoundError(LookupError):
    """The signed-in participant has no active enrollment in the selected scope."""


class ParticipantTargetService:
    """Build and read the immutable 44-theme calendar for one participant."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_for_enrollment(self, enrollment_id: UUID) -> int:
        """Insert every curriculum target once and safely tolerate repeated calls."""
        enrollment = await self.session.scalar(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .options(joinedload(Enrollment.cohort))
        )
        if enrollment is None:
            raise ParticipantEnrollmentNotFoundError("enrollment not found")

        themes = list(
            await self.session.scalars(
                select(Theme)
                .join(Part, Part.id == Theme.part_id)
                .where(Part.curriculum_version_id == enrollment.cohort.curriculum_version_id)
                .options(joinedload(Theme.part))
                .order_by(Part.sequence_no, Theme.sequence_no)
            )
        )
        rows = [
            {
                "enrollment_id": enrollment.id,
                "theme_id": theme.id,
                "initial_due_date": enrollment.cohort.start_date + timedelta(weeks=index),
                "effective_due_date": enrollment.cohort.start_date + timedelta(weeks=index),
                "status": (
                    TargetStatus.ACTIVE.value
                    if theme.part.sequence_no == 1
                    else TargetStatus.SCHEDULED.value
                ),
            }
            for index, theme in enumerate(themes)
        ]
        if not rows:
            return 0

        statement = (
            insert(Target)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Target.enrollment_id, Target.theme_id])
            .returning(Target.id)
        )
        result = await self.session.execute(statement)
        await self.session.commit()
        return len(result.scalars().all())

    async def list_targets(
        self,
        actor: ParticipantActor,
        *,
        part_id: UUID | None = None,
        target_status: TargetStatus | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
    ) -> list[TargetResponse]:
        enrollment = await self._active_enrollment(actor)
        await self.generate_for_enrollment(enrollment.id)
        records = await self._target_records(enrollment.id)
        responses = await self._target_responses_with_activity(enrollment, records)
        return [
            item
            for item in responses
            if (part_id is None or item.theme.part_id == part_id)
            and (target_status is None or item.status is target_status)
            and (due_from is None or item.effective_due_date >= due_from)
            and (due_to is None or item.effective_due_date <= due_to)
        ]

    async def progress(self, actor: ParticipantActor) -> ProgressResponse:
        enrollment = await self._active_enrollment(actor)
        await self.generate_for_enrollment(enrollment.id)
        records = await self._target_records(enrollment.id)
        return self._progress(await self._target_responses_with_activity(enrollment, records))

    async def dashboard(self, actor: ParticipantActor) -> DashboardResponse:
        enrollment = await self._active_enrollment(actor)
        await self.generate_for_enrollment(enrollment.id)
        records = await self._target_records(enrollment.id)
        targets = await self._target_responses_with_activity(enrollment, records)
        actionable = [item for item in targets if item.allowed_actions]
        upcoming = [
            item for item in targets if item.status in {TargetStatus.ACTIVE, TargetStatus.SCHEDULED}
        ][:5]
        return DashboardResponse(
            participant=ParticipantSummary(
                id=enrollment.user.id,
                display_name=enrollment.user.name,
                enrollment_id=enrollment.id,
                cohort_name=enrollment.cohort.name,
                cohort_start_date=enrollment.cohort.start_date,
                cohort_close_date=enrollment.cohort.close_date,
            ),
            progress=self._progress(targets),
            next_target=actionable[0] if actionable else None,
            upcoming_targets=upcoming,
        )

    async def activity_score(self, actor: ParticipantActor) -> ActivityScoreResponse:
        enrollment = await self._active_enrollment(actor)
        await self.generate_for_enrollment(enrollment.id)
        return await ActivityScoreService(self.session).for_enrollment(enrollment)

    async def _active_enrollment(self, actor: ParticipantActor) -> Enrollment:
        enrollment = await self.session.scalar(
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.user_id == actor.user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
            )
            .options(joinedload(Enrollment.user), joinedload(Enrollment.cohort))
            .order_by(Enrollment.joined_at.desc())
        )
        if enrollment is None:
            raise ParticipantEnrollmentNotFoundError("active enrollment not found")
        return enrollment

    async def _target_records(self, enrollment_id: UUID) -> list[Target]:
        return list(
            await self.session.scalars(
                select(Target)
                .where(Target.enrollment_id == enrollment_id)
                .options(selectinload(Target.theme).selectinload(Theme.part))
                .join(Theme, Theme.id == Target.theme_id)
                .join(Part, Part.id == Theme.part_id)
                .order_by(Part.sequence_no, Theme.sequence_no)
            )
        )

    async def _target_responses_with_activity(
        self, enrollment: Enrollment, targets: list[Target]
    ) -> list[TargetResponse]:
        activity = await ActivityScoreService(self.session).for_enrollment(enrollment)
        activity_by_theme = {item.theme_id: item for item in activity.source_context.themes}
        return self._target_responses(targets, activity_by_theme=activity_by_theme)

    def _target_responses(
        self,
        targets: list[Target],
        *,
        activity_by_theme: dict[UUID, ActivityThemeScore] | None = None,
    ) -> list[TargetResponse]:
        if not targets:
            return []
        active_part_no = next(
            (item.theme.part.sequence_no for item in targets if item.status is TargetStatus.ACTIVE),
            None,
        )
        if active_part_no is None:
            incomplete = [item for item in targets if item.status is TargetStatus.SCHEDULED]
            active_part_no = incomplete[0].theme.part.sequence_no if incomplete else None

        responses: list[TargetResponse] = []
        for ordinal, target in enumerate(targets, start=1):
            activity = (activity_by_theme or {}).get(target.theme_id)
            part_no = target.theme.part.sequence_no
            locked_reason = None
            allowed_actions: list[str] = []
            if target.status is TargetStatus.ACTIVE:
                allowed_actions = ["request_session"]
            elif target.status is TargetStatus.SCHEDULED and active_part_no is not None:
                if part_no > active_part_no:
                    locked_reason = f"Selesaikan Bagian {part_no - 1} untuk membuka bagian ini."
                else:
                    locked_reason = "Target belum memasuki periode aktif."
            elif target.status is TargetStatus.CLOSED:
                locked_reason = "Target ditutup oleh pengelola program."

            responses.append(
                TargetResponse(
                    id=target.id,
                    theme=TargetTheme(
                        id=target.theme.id,
                        code=f"T{ordinal:02d}",
                        name=target.theme.title,
                        part_id=target.theme.part.id,
                        part_no=part_no,
                        part_name=target.theme.part.title,
                    ),
                    initial_due_date=target.initial_due_date,
                    effective_due_date=target.effective_due_date,
                    status=target.status,
                    first_valid_submission_at=(
                        activity.first_valid_submission_at if activity is not None else None
                    ),
                    activity_score=activity.score if activity is not None else None,
                    locked_reason=locked_reason,
                    allowed_actions=allowed_actions,
                )
            )
        return responses

    def _progress(self, targets: list[TargetResponse]) -> ProgressResponse:
        today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        completed = sum(item.status is TargetStatus.COMPLETED for item in targets)
        overdue = sum(
            item.status not in {TargetStatus.COMPLETED, TargetStatus.CLOSED}
            and item.effective_due_date < today
            for item in targets
        )
        expected = sum(item.effective_due_date < today for item in targets)
        parts: list[PartProgress] = []
        for part_no in sorted({item.theme.part_no for item in targets}):
            part_targets = [item for item in targets if item.theme.part_no == part_no]
            part_completed = sum(item.status is TargetStatus.COMPLETED for item in part_targets)
            if part_targets and part_completed == len(part_targets):
                part_status = "completed"
                locked_reason = None
            elif any(item.status is TargetStatus.ACTIVE for item in part_targets):
                part_status = "active"
                locked_reason = None
            else:
                part_status = "locked"
                locked_reason = part_targets[0].locked_reason if part_targets else None
            first = part_targets[0]
            parts.append(
                PartProgress(
                    id=first.theme.part_id,
                    part_no=part_no,
                    name=first.theme.part_name,
                    total_targets=len(part_targets),
                    completed_targets=part_completed,
                    status=part_status,
                    locked_reason=locked_reason,
                )
            )

        total = len(targets)
        active_part = next((part for part in parts if part.status == "active"), None)
        return ProgressResponse(
            total_targets=total,
            completed_targets=completed,
            overdue_targets=overdue,
            expected_completed_targets=expected,
            completion_percentage=round((completed / total) * 100, 1) if total else 0,
            on_track=completed >= expected,
            projected_completion_date=max(
                (item.effective_due_date for item in targets),
                default=None,
            ),
            active_part=active_part,
            parts=parts,
        )
