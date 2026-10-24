"""Department calendar previews, proposals, decisions, and audit writes."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.modules.audit.models import AuditEvent
from app.modules.calendar.admin_schemas import (
    CalendarParticipant,
    CalendarTargetResponse,
    CalendarTheme,
    CohortCalendarResponse,
    CohortCalendarSummary,
    DeadlineChangeBatchResponse,
    DeadlineChangePreview,
    DeadlineChangeRequest,
    DeadlineChangeResponse,
    DeadlineDecisionRequest,
    DeadlineImpactItem,
)
from app.modules.calendar.models import DeadlineChange, DeadlineChangeStatus, Target
from app.modules.cohorts.access import DepartmentActor
from app.modules.cohorts.models import Cohort, Enrollment
from app.modules.curriculum.models import Part, Theme
from app.modules.curriculum.ordering import memorization_code


class CalendarResourceNotFoundError(LookupError):
    pass


class CalendarConflictError(ValueError):
    pass


class CalendarVersionConflictError(CalendarConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("calendar was updated by another request")
        self.current_version = current_version


class DeadlineChangeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calendar(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
    ) -> CohortCalendarResponse:
        cohort = await self._cohort(actor, cohort_id)
        targets = await self._targets(actor, cohort_id)
        changes = await self._changes([item.id for item in targets])
        return self._calendar_response(cohort, targets, changes)

    async def preview(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        payload: DeadlineChangeRequest,
    ) -> DeadlineChangePreview:
        cohort = await self._cohort(actor, cohort_id)
        self._require_version(cohort, payload.expected_version)
        targets = await self._selected_targets(actor, cohort_id, payload.target_ids)
        impacts = [self._impact(target, payload.new_due_date) for target in targets]
        if any(item.old_date == item.new_date for item in impacts):
            raise CalendarConflictError("new deadline must differ from every selected target")
        return DeadlineChangePreview(
            cohort_id=cohort.id,
            calendar_version=cohort.calendar_version,
            affected_count=len(impacts),
            earliest_old_date=min(item.old_date for item in impacts),
            latest_old_date=max(item.old_date for item in impacts),
            new_due_date=payload.new_due_date,
            impacts=impacts,
        )

    async def propose(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        payload: DeadlineChangeRequest,
        request_id: UUID,
    ) -> DeadlineChangeBatchResponse:
        cohort = await self._cohort(actor, cohort_id, lock=True)
        self._require_version(cohort, payload.expected_version)
        targets = await self._selected_targets(actor, cohort_id, payload.target_ids, lock=True)
        if any(target.effective_due_date == payload.new_due_date for target in targets):
            raise CalendarConflictError("new deadline must differ from every selected target")
        pending = await self.session.scalar(
            select(DeadlineChange.id).where(
                DeadlineChange.target_id.in_(payload.target_ids),
                DeadlineChange.status == DeadlineChangeStatus.PENDING,
            )
        )
        if pending is not None:
            raise CalendarConflictError("a selected target already has a pending deadline change")

        changes: list[DeadlineChange] = []
        for target in targets:
            change = DeadlineChange(
                target_id=target.id,
                requested_by=actor.user_id,
                old_date=target.effective_due_date,
                new_date=payload.new_due_date,
                reason=payload.reason.strip(),
                impact_note=payload.impact_note.strip() if payload.impact_note else None,
            )
            self.session.add(change)
            changes.append(change)
        cohort.calendar_version += 1
        try:
            await self.session.flush()
        except IntegrityError as error:
            raise CalendarConflictError(
                "deadline change conflicts with a pending request"
            ) from error
        for change in changes:
            self.session.add(
                self._audit(
                    actor.user_id,
                    request_id,
                    "deadline_change.requested",
                    change,
                    before={"effective_due_date": change.old_date.isoformat()},
                    after={"proposed_due_date": change.new_date.isoformat(), "status": "pending"},
                )
            )
        await self.session.flush()
        return DeadlineChangeBatchResponse(
            cohort_id=cohort.id,
            calendar_version=cohort.calendar_version,
            changes=[self._change_response(change) for change in changes],
        )

    async def decide(
        self,
        actor: DepartmentActor,
        change_id: UUID,
        payload: DeadlineDecisionRequest,
        request_id: UUID,
        *,
        approve: bool,
    ) -> DeadlineChangeBatchResponse:
        change = await self.session.scalar(
            select(DeadlineChange)
            .join(Target, Target.id == DeadlineChange.target_id)
            .join(Enrollment, Enrollment.id == Target.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                DeadlineChange.id == change_id,
                Cohort.organization_id == actor.organization_id,
            )
            .with_for_update(of=DeadlineChange)
        )
        if change is None:
            raise CalendarResourceNotFoundError("deadline change not found")
        if change.row_version != payload.expected_version:
            raise CalendarVersionConflictError(change.row_version)
        if change.status is not DeadlineChangeStatus.PENDING:
            raise CalendarConflictError("deadline change has already been decided")
        target = await self.session.scalar(
            select(Target).where(Target.id == change.target_id).with_for_update()
        )
        if target is None:
            raise CalendarResourceNotFoundError("target not found")
        cohort = await self.session.scalar(
            select(Cohort)
            .join(Enrollment, Enrollment.cohort_id == Cohort.id)
            .where(Enrollment.id == target.enrollment_id)
            .with_for_update()
        )
        if cohort is None or cohort.organization_id != actor.organization_id:
            raise CalendarResourceNotFoundError("cohort not found")
        if target.effective_due_date != change.old_date:
            raise CalendarConflictError("target deadline changed after this proposal was created")

        previous = {
            "effective_due_date": target.effective_due_date.isoformat(),
            "status": change.status.value,
        }
        change.status = DeadlineChangeStatus.APPROVED if approve else DeadlineChangeStatus.REJECTED
        change.approved_by = actor.user_id
        change.decided_at = utc_now()
        change.decision_note = payload.decision_note.strip() if payload.decision_note else None
        await self.session.flush()
        if approve:
            await self.session.execute(
                text("SELECT set_config('app.deadline_change_id', :change_id, true)"),
                {"change_id": str(change.id)},
            )
            target.effective_due_date = change.new_date
        cohort.calendar_version += 1
        action = "deadline_change.approved" if approve else "deadline_change.rejected"
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                action,
                change,
                before=previous,
                after={
                    "effective_due_date": target.effective_due_date.isoformat(),
                    "status": change.status.value,
                },
            )
        )
        await self.session.flush()
        return DeadlineChangeBatchResponse(
            cohort_id=cohort.id,
            calendar_version=cohort.calendar_version,
            changes=[self._change_response(change)],
        )

    async def _cohort(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        *,
        lock: bool = False,
    ) -> Cohort:
        statement = select(Cohort).where(
            Cohort.id == cohort_id,
            Cohort.organization_id == actor.organization_id,
        )
        if lock:
            statement = statement.with_for_update()
        cohort = await self.session.scalar(statement)
        if cohort is None:
            raise CalendarResourceNotFoundError("cohort not found")
        return cohort

    async def _targets(self, actor: DepartmentActor, cohort_id: UUID) -> list[Target]:
        return list(
            await self.session.scalars(
                select(Target)
                .join(Enrollment, Enrollment.id == Target.enrollment_id)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .join(Theme, Theme.id == Target.theme_id)
                .join(Part, Part.id == Theme.part_id)
                .where(Cohort.id == cohort_id, Cohort.organization_id == actor.organization_id)
                .options(
                    selectinload(Target.enrollment).selectinload(Enrollment.user),
                    selectinload(Target.theme).selectinload(Theme.part),
                )
                .order_by(Enrollment.nim_snapshot, Part.sequence_no, Theme.sequence_no)
            )
        )

    async def _selected_targets(
        self,
        actor: DepartmentActor,
        cohort_id: UUID,
        target_ids: list[UUID],
        *,
        lock: bool = False,
    ) -> list[Target]:
        statement = (
            select(Target)
            .join(Enrollment, Enrollment.id == Target.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Target.id.in_(target_ids),
                Cohort.id == cohort_id,
                Cohort.organization_id == actor.organization_id,
            )
            .options(
                selectinload(Target.enrollment).selectinload(Enrollment.user),
                selectinload(Target.theme).selectinload(Theme.part),
            )
            .order_by(Target.id)
        )
        if lock:
            statement = statement.with_for_update(of=Target)
        targets = list(await self.session.scalars(statement))
        if len(targets) != len(target_ids):
            raise CalendarResourceNotFoundError("one or more targets were not found")
        return targets

    async def _changes(self, target_ids: list[UUID]) -> list[DeadlineChange]:
        if not target_ids:
            return []
        return list(
            await self.session.scalars(
                select(DeadlineChange)
                .where(DeadlineChange.target_id.in_(target_ids))
                .order_by(DeadlineChange.created_at.desc())
            )
        )

    @staticmethod
    def _require_version(cohort: Cohort, expected_version: int) -> None:
        if cohort.calendar_version != expected_version:
            raise CalendarVersionConflictError(cohort.calendar_version)

    def _calendar_response(
        self,
        cohort: Cohort,
        targets: list[Target],
        changes: list[DeadlineChange],
    ) -> CohortCalendarResponse:
        pending = {
            item.target_id: item for item in changes if item.status is DeadlineChangeStatus.PENDING
        }
        return CohortCalendarResponse(
            cohort=CohortCalendarSummary(
                id=cohort.id,
                name=cohort.name,
                start_date=cohort.start_date,
                close_date=cohort.close_date,
                status=cohort.status,
            ),
            calendar_version=cohort.calendar_version,
            targets=[
                CalendarTargetResponse(
                    id=target.id,
                    participant=self._participant(target),
                    theme=self._theme(target),
                    initial_due_date=target.initial_due_date,
                    effective_due_date=target.effective_due_date,
                    status=target.status,
                    pending_change=(
                        self._change_response(pending[target.id]) if target.id in pending else None
                    ),
                    allowed_actions=([] if target.id in pending else ["propose_deadline_change"]),
                )
                for target in targets
            ],
            history=[self._change_response(item) for item in changes],
            allowed_actions=["preview_deadline_change", "propose_deadline_change"],
        )

    def _impact(self, target: Target, new_date: date) -> DeadlineImpactItem:
        return DeadlineImpactItem(
            target_id=target.id,
            participant=self._participant(target),
            theme=self._theme(target),
            old_date=target.effective_due_date,
            new_date=new_date,
            shift_days=(new_date - target.effective_due_date).days,
        )

    @staticmethod
    def _participant(target: Target) -> CalendarParticipant:
        return CalendarParticipant(
            enrollment_id=target.enrollment.id,
            user_id=target.enrollment.user.id,
            display_name=target.enrollment.user.name,
            nim=target.enrollment.nim_snapshot,
        )

    @staticmethod
    def _theme(target: Target) -> CalendarTheme:
        return CalendarTheme(
            id=target.theme.id,
            code=memorization_code(target.theme.part.sequence_no, target.theme.sequence_no),
            name=target.theme.title,
            part_no=target.theme.part.sequence_no,
            part_name=target.theme.part.title,
        )

    @staticmethod
    def _change_response(change: DeadlineChange) -> DeadlineChangeResponse:
        return DeadlineChangeResponse(
            id=change.id,
            target_id=change.target_id,
            requested_by=change.requested_by,
            approved_by=change.approved_by,
            old_date=change.old_date,
            new_date=change.new_date,
            reason=change.reason,
            impact_note=change.impact_note,
            decision_note=change.decision_note,
            status=change.status,
            decided_at=change.decided_at,
            row_version=change.row_version,
            created_at=change.created_at,
        )

    @staticmethod
    def _audit(
        actor_id: UUID,
        request_id: UUID,
        action: str,
        change: DeadlineChange,
        *,
        before: Mapping[str, object],
        after: Mapping[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="deadline_change",
            object_reference=str(change.id),
            request_id=request_id,
            before_data=dict(before),
            after_data=dict(after),
        )
