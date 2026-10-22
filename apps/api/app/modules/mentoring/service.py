"""Session proposal, scheduling, queue, and lifecycle use cases."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.time import ensure_utc, utc_now
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
from app.modules.curriculum.models import Theme
from app.modules.identity.models import User
from app.modules.mentoring.access import MentorActor
from app.modules.mentoring.models import (
    MentoringSession,
    SessionStatus,
    SessionTheme,
)
from app.modules.mentoring.schemas import (
    SessionCreate,
    SessionMentor,
    SessionParticipant,
    SessionResponse,
    SessionSchedule,
    SessionThemeResponse,
    SessionTransition,
)


class SessionResourceNotFoundError(LookupError):
    pass


class SessionConflictError(ValueError):
    pass


class SessionVersionConflictError(SessionConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("session was updated by another request")
        self.current_version = current_version


class MentoringSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        actor: ParticipantActor,
        payload: SessionCreate,
        request_id: UUID,
    ) -> SessionResponse:
        proposed_at = ensure_utc(payload.proposed_at)
        if proposed_at < utc_now():
            raise SessionConflictError("proposed time must not be in the past")
        enrollment = await self._participant_enrollment(actor, lock=True)
        proposed_local_date = proposed_at.astimezone(ZoneInfo("Asia/Jakarta")).date()
        if proposed_local_date < enrollment.cohort.start_date:
            raise SessionConflictError("proposed time is before the cohort starts")
        if (
            enrollment.cohort.close_date is not None
            and proposed_local_date > enrollment.cohort.close_date
        ):
            raise SessionConflictError("proposed time is outside the cohort period")

        targets = list(
            await self.session.scalars(
                select(Target)
                .join(Theme, Theme.id == Target.theme_id)
                .where(
                    Target.enrollment_id == enrollment.id,
                    Target.theme_id.in_(payload.theme_ids),
                    Target.status == TargetStatus.ACTIVE,
                )
                .options(selectinload(Target.theme).selectinload(Theme.part))
                .order_by(Target.id)
                .with_for_update(of=Target)
            )
        )
        if len(targets) != len(payload.theme_ids):
            raise SessionConflictError("every theme must be an active target of the participant")
        part_ids = {target.theme.part_id for target in targets}
        if len(part_ids) != 1:
            raise SessionConflictError("all session themes must belong to one active part")

        assignment = await self._mentor_assignment(enrollment.id, proposed_at)
        if assignment is None:
            raise SessionConflictError("an active mentor assignment is required")
        record = MentoringSession(
            enrollment_id=enrollment.id,
            part_id=part_ids.pop(),
            mentor_id=assignment.staff_id,
            proposed_at=proposed_at,
            method=payload.method,
            participant_note=self._note(payload.participant_note),
        )
        self.session.add(record)
        await self.session.flush()
        for target in targets:
            self.session.add(SessionTheme(session_id=record.id, theme_id=target.theme_id))
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "session.proposed",
                record,
                before=None,
                after={
                    "status": record.status.value,
                    "proposed_at": record.proposed_at.isoformat(),
                    "theme_count": len(targets),
                },
            )
        )
        await self.session.flush()
        return self._response(await self._load(record.id), role="participant")

    async def list_participant(self, actor: ParticipantActor) -> list[SessionResponse]:
        enrollment = await self._participant_enrollment(actor)
        records = list(
            await self.session.scalars(
                self._base_statement()
                .where(MentoringSession.enrollment_id == enrollment.id)
                .order_by(MentoringSession.created_at.desc(), MentoringSession.id.desc())
            )
        )
        return [self._response(record, role="participant") for record in records]

    async def get_for_participant(
        self, actor: ParticipantActor, session_id: UUID
    ) -> SessionResponse:
        record = await self._participant_session(actor, session_id)
        return self._response(record, role="participant")

    async def cancel(
        self,
        actor: ParticipantActor,
        session_id: UUID,
        payload: SessionTransition,
        request_id: UUID,
    ) -> SessionResponse:
        record = await self._participant_session(actor, session_id, lock=True)
        self._require_version(record, payload.expected_version)
        if record.status not in {SessionStatus.PROPOSED, SessionStatus.SCHEDULED}:
            raise SessionConflictError("only proposed or scheduled sessions can be cancelled")
        previous = self._state(record)
        record.status = SessionStatus.CANCELLED
        if payload.note:
            record.participant_note = self._note(payload.note)
        await self.session.flush()
        self._record_transition(actor.user_id, request_id, "session.cancelled", record, previous)
        await self.session.flush()
        return self._response(await self._load(record.id), role="participant")

    async def mentor_queue(
        self,
        actor: MentorActor,
        *,
        session_status: SessionStatus | None = None,
        scheduled_from: datetime | None = None,
        scheduled_to: datetime | None = None,
        query: str | None = None,
    ) -> list[SessionResponse]:
        now = utc_now()
        statement = (
            self._base_statement()
            .join(Enrollment, Enrollment.id == MentoringSession.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                MentoringSession.mentor_id == actor.user_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment_exists(actor.user_id, now),
            )
        )
        if session_status is not None:
            statement = statement.where(MentoringSession.status == session_status)
        if scheduled_from is not None:
            statement = statement.where(MentoringSession.scheduled_at >= ensure_utc(scheduled_from))
        if scheduled_to is not None:
            statement = statement.where(MentoringSession.scheduled_at <= ensure_utc(scheduled_to))
        if query:
            needle = f"%{query.strip().casefold()}%"
            statement = statement.join(Enrollment.user).where(
                or_(
                    func.lower(Enrollment.nim_snapshot).like(needle),
                    func.lower(User.name).like(needle),
                )
            )
        records = list(
            await self.session.scalars(
                statement.order_by(
                    func.coalesce(MentoringSession.scheduled_at, MentoringSession.proposed_at),
                    MentoringSession.id,
                )
            )
        )
        return [self._response(record, role="mentor") for record in records]

    async def schedule(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: SessionSchedule,
        request_id: UUID,
    ) -> SessionResponse:
        record = await self._mentor_session(actor, session_id, lock=True)
        self._require_version(record, payload.expected_version)
        if record.status not in {SessionStatus.PROPOSED, SessionStatus.SCHEDULED}:
            raise SessionConflictError("only proposed or scheduled sessions can be scheduled")
        scheduled_at = ensure_utc(payload.scheduled_at)
        if scheduled_at < utc_now():
            raise SessionConflictError("scheduled time must not be in the past")
        scheduled_local_date = scheduled_at.astimezone(ZoneInfo("Asia/Jakarta")).date()
        cohort = record.enrollment.cohort
        if scheduled_local_date < cohort.start_date or (
            cohort.close_date is not None and scheduled_local_date > cohort.close_date
        ):
            raise SessionConflictError("scheduled time is outside the cohort period")
        if await self._mentor_assignment(record.enrollment_id, scheduled_at, actor.user_id) is None:
            raise SessionConflictError("mentor assignment does not cover the scheduled time")
        previous = self._state(record)
        record.scheduled_at = scheduled_at
        record.method = payload.method
        record.mentor_note = self._note(payload.mentor_note)
        record.status = SessionStatus.SCHEDULED
        await self.session.flush()
        self._record_transition(actor.user_id, request_id, "session.scheduled", record, previous)
        await self.session.flush()
        return self._response(await self._load(record.id), role="mentor")

    async def transition(
        self,
        actor: MentorActor,
        session_id: UUID,
        payload: SessionTransition,
        request_id: UUID,
        *,
        action: str,
    ) -> SessionResponse:
        record = await self._mentor_session(actor, session_id, lock=True)
        self._require_version(record, payload.expected_version)
        transitions = {
            "start": (SessionStatus.SCHEDULED, SessionStatus.IN_PROGRESS),
            "complete": (SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED),
            "no-show": (SessionStatus.SCHEDULED, SessionStatus.NO_SHOW),
        }
        expected, target_status = transitions[action]
        if record.status is not expected:
            raise SessionConflictError(f"session must be {expected.value} before {action}")
        previous = self._state(record)
        record.status = target_status
        if action == "start":
            record.actual_at = utc_now()
        if payload.note:
            record.mentor_note = self._note(payload.note)
        await self.session.flush()
        self._record_transition(
            actor.user_id,
            request_id,
            f"session.{target_status.value}",
            record,
            previous,
        )
        await self.session.flush()
        return self._response(await self._load(record.id), role="mentor")

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
            .options(selectinload(Enrollment.user), selectinload(Enrollment.cohort))
            .order_by(Enrollment.joined_at.desc())
        )
        if lock:
            statement = statement.with_for_update(of=Enrollment)
        enrollment = await self.session.scalar(statement)
        if enrollment is None:
            raise SessionResourceNotFoundError("active enrollment not found")
        return enrollment

    async def _participant_session(
        self,
        actor: ParticipantActor,
        session_id: UUID,
        *,
        lock: bool = False,
    ) -> MentoringSession:
        statement = (
            self._base_statement()
            .join(Enrollment, Enrollment.id == MentoringSession.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                MentoringSession.id == session_id,
                Enrollment.user_id == actor.user_id,
                Cohort.organization_id == actor.organization_id,
            )
        )
        if lock:
            statement = statement.with_for_update(of=MentoringSession)
        record = await self.session.scalar(statement)
        if record is None:
            raise SessionResourceNotFoundError("session not found")
        return record

    async def _mentor_session(
        self,
        actor: MentorActor,
        session_id: UUID,
        *,
        lock: bool = False,
    ) -> MentoringSession:
        now = utc_now()
        statement = (
            self._base_statement()
            .join(Enrollment, Enrollment.id == MentoringSession.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                MentoringSession.id == session_id,
                MentoringSession.mentor_id == actor.user_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment_exists(actor.user_id, now),
            )
        )
        if lock:
            statement = statement.with_for_update(of=MentoringSession)
        record = await self.session.scalar(statement)
        if record is None:
            raise SessionResourceNotFoundError("session not found")
        return record

    async def _mentor_assignment(
        self,
        enrollment_id: UUID,
        moment: datetime,
        mentor_id: UUID | None = None,
    ) -> Assignment | None:
        statement = select(Assignment).where(
            Assignment.enrollment_id == enrollment_id,
            Assignment.role == AssignmentRole.MENTOR,
            Assignment.valid_from <= moment,
            or_(Assignment.valid_to.is_(None), Assignment.valid_to > moment),
        )
        if mentor_id is not None:
            statement = statement.where(Assignment.staff_id == mentor_id)
        return await self.session.scalar(statement.order_by(Assignment.valid_from.desc()))

    @staticmethod
    def _active_assignment_exists(mentor_id: UUID, moment: datetime) -> ColumnElement[bool]:
        return exists(
            select(Assignment.id).where(
                Assignment.enrollment_id == MentoringSession.enrollment_id,
                Assignment.staff_id == mentor_id,
                Assignment.role == AssignmentRole.MENTOR,
                Assignment.valid_from <= moment,
                or_(Assignment.valid_to.is_(None), Assignment.valid_to > moment),
            )
        )

    def _base_statement(self) -> Select[MentoringSession]:
        return select(MentoringSession).options(
            selectinload(MentoringSession.enrollment).selectinload(Enrollment.user),
            selectinload(MentoringSession.enrollment).selectinload(Enrollment.cohort),
            selectinload(MentoringSession.mentor),
            selectinload(MentoringSession.part),
            selectinload(MentoringSession.session_themes)
            .selectinload(SessionTheme.theme)
            .selectinload(Theme.part),
        )

    async def _load(self, session_id: UUID) -> MentoringSession:
        record = await self.session.scalar(
            self._base_statement().where(MentoringSession.id == session_id)
        )
        if record is None:
            raise SessionResourceNotFoundError("session not found")
        return record

    @staticmethod
    def _require_version(record: MentoringSession, expected_version: int) -> None:
        if record.row_version != expected_version:
            raise SessionVersionConflictError(record.row_version)

    @staticmethod
    def _note(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _state(record: MentoringSession) -> dict[str, object]:
        return {
            "status": record.status.value,
            "scheduled_at": record.scheduled_at.isoformat() if record.scheduled_at else None,
            "actual_at": record.actual_at.isoformat() if record.actual_at else None,
        }

    def _record_transition(
        self,
        actor_id: UUID,
        request_id: UUID,
        action: str,
        record: MentoringSession,
        previous: Mapping[str, object],
    ) -> None:
        self.session.add(
            self._audit(
                actor_id,
                request_id,
                action,
                record,
                before=previous,
                after=self._state(record),
            )
        )

    @staticmethod
    def _audit(
        actor_id: UUID,
        request_id: UUID,
        action: str,
        record: MentoringSession,
        *,
        before: Mapping[str, object] | None,
        after: Mapping[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="session",
            object_reference=str(record.id),
            request_id=request_id,
            before_data=dict(before) if before is not None else None,
            after_data=dict(after),
        )

    def _response(self, record: MentoringSession, *, role: str) -> SessionResponse:
        offsets = {1: 0, 2: 10, 3: 18, 4: 24, 5: 29}
        themes = sorted(
            record.session_themes,
            key=lambda item: (item.theme.part.sequence_no, item.theme.sequence_no),
        )
        return SessionResponse(
            id=record.id,
            participant=SessionParticipant(
                enrollment_id=record.enrollment.id,
                user_id=record.enrollment.user.id,
                display_name=record.enrollment.user.name,
                nim=record.enrollment.nim_snapshot,
            ),
            part_id=record.part_id,
            mentor=SessionMentor(user_id=record.mentor.id, display_name=record.mentor.name),
            proposed_at=record.proposed_at,
            scheduled_at=record.scheduled_at,
            actual_at=record.actual_at,
            method=record.method,
            status=record.status,
            participant_note=record.participant_note,
            mentor_note=record.mentor_note,
            row_version=record.row_version,
            created_at=record.created_at,
            themes=[
                SessionThemeResponse(
                    id=item.id,
                    theme_id=item.theme.id,
                    code=(f"T{offsets[item.theme.part.sequence_no] + item.theme.sequence_no:02d}"),
                    name=item.theme.title,
                    part_id=item.theme.part.id,
                    part_no=item.theme.part.sequence_no,
                    part_name=item.theme.part.title,
                )
                for item in themes
            ],
            allowed_actions=self._allowed_actions(record.status, role),
        )

    @staticmethod
    def _allowed_actions(status: SessionStatus, role: str) -> list[str]:
        if role == "participant":
            return ["cancel"] if status in {SessionStatus.PROPOSED, SessionStatus.SCHEDULED} else []
        if status is SessionStatus.PROPOSED:
            return ["schedule"]
        if status is SessionStatus.SCHEDULED:
            return ["reschedule", "start", "no_show"]
        if status is SessionStatus.IN_PROGRESS:
            return ["complete"]
        return []
