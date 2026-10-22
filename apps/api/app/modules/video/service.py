"""Transactional participant video-attempt workflows."""

from datetime import date
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.modules.audit.models import AuditEvent
from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.models import Target, TargetStatus
from app.modules.cohorts.models import Cohort, Enrollment, EnrollmentStatus
from app.modules.curriculum.models import Part, Theme
from app.modules.video.models import (
    VideoAttempt,
    VideoAttemptStatus,
    VideoVersion,
    VideoVersionStatus,
)
from app.modules.video.schemas import (
    VideoAttemptResponse,
    VideoVersionCreate,
    VideoVersionResponse,
)


class VideoResourceNotFoundError(LookupError):
    pass


class VideoConflictError(ValueError):
    pass


class VideoVersionConflictError(VideoConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("video attempt was updated by another request")
        self.current_version = current_version


class VideoUrlNotAllowedError(ValueError):
    pass


class VideoSubmissionService:
    def __init__(self, session: AsyncSession, allowed_hosts: frozenset[str]) -> None:
        self.session = session
        self.allowed_hosts = allowed_hosts

    async def create_attempt(
        self,
        actor: ParticipantActor,
        part_id: UUID,
        request_id: UUID,
    ) -> VideoAttemptResponse:
        enrollment = await self._participant_enrollment(actor, lock=True)
        part = await self.session.scalar(
            select(Part).where(
                Part.id == part_id,
                Part.curriculum_version_id == enrollment.cohort.curriculum_version_id,
            )
        )
        if part is None:
            raise VideoResourceNotFoundError("part is not in the active curriculum")
        await self._require_completed_themes(enrollment.id, part)

        latest = await self.session.scalar(
            select(VideoAttempt)
            .where(
                VideoAttempt.enrollment_id == enrollment.id,
                VideoAttempt.part_id == part.id,
            )
            .order_by(VideoAttempt.cycle_no.desc(), VideoAttempt.revision_no.desc())
            .limit(1)
        )
        cycle_no, revision_no = self._next_slot(latest)
        attempt = VideoAttempt(
            enrollment_id=enrollment.id,
            part_id=part.id,
            cycle_no=cycle_no,
            revision_no=revision_no,
            status=VideoAttemptStatus.OPEN,
        )
        self.session.add(attempt)
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "video_attempt.created",
                attempt,
                after={"cycle_no": cycle_no, "revision_no": revision_no, "status": "open"},
            )
        )
        await self.session.flush()
        attempt.part = part
        return self._response(attempt)

    async def submit_version(
        self,
        actor: ParticipantActor,
        attempt_id: UUID,
        payload: VideoVersionCreate,
        request_id: UUID,
    ) -> VideoAttemptResponse:
        attempt = await self._participant_attempt(actor, attempt_id, lock=True)
        if attempt.row_version != payload.expected_version:
            raise VideoVersionConflictError(attempt.row_version)
        if attempt.status in {VideoAttemptStatus.FINALIZED, VideoAttemptStatus.CLOSED}:
            raise VideoConflictError("a finalized video attempt cannot receive another version")
        if not payload.completeness_declared:
            raise VideoConflictError("the participant must declare the recording complete")
        if payload.recorded_on > date.today():
            raise VideoConflictError("recorded_on cannot be in the future")
        self._validate_host(payload.video_url)

        previous = attempt.versions[-1] if attempt.versions else None
        if previous is not None:
            previous.status = VideoVersionStatus.REPLACED
        version = VideoVersion(
            attempt_id=attempt.id,
            version_no=(previous.version_no + 1) if previous is not None else 1,
            video_url=payload.video_url,
            recorded_date=payload.recorded_on,
            submitted_at=utc_now(),
            status=VideoVersionStatus.SUBMITTED,
        )
        attempt.versions.append(version)
        attempt.status = VideoAttemptStatus.SUBMITTED
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "video_version.submitted",
                attempt,
                after={
                    "cycle_no": attempt.cycle_no,
                    "revision_no": attempt.revision_no,
                    "version_no": version.version_no,
                    "status": attempt.status.value,
                },
            )
        )
        await self.session.flush()
        return self._response(attempt)

    async def get_attempt(self, actor: ParticipantActor, attempt_id: UUID) -> VideoAttemptResponse:
        return self._response(await self._participant_attempt(actor, attempt_id))

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
            .options(selectinload(Enrollment.cohort))
            .order_by(Enrollment.joined_at.desc())
        )
        if lock:
            statement = statement.with_for_update(of=Enrollment)
        enrollment = await self.session.scalar(statement)
        if enrollment is None:
            raise VideoResourceNotFoundError("active enrollment not found")
        return enrollment

    async def _participant_attempt(
        self,
        actor: ParticipantActor,
        attempt_id: UUID,
        *,
        lock: bool = False,
    ) -> VideoAttempt:
        statement = (
            select(VideoAttempt)
            .join(Enrollment, Enrollment.id == VideoAttempt.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                VideoAttempt.id == attempt_id,
                Enrollment.user_id == actor.user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Cohort.organization_id == actor.organization_id,
            )
            .options(selectinload(VideoAttempt.part), selectinload(VideoAttempt.versions))
        )
        if lock:
            statement = statement.with_for_update(of=VideoAttempt)
        attempt = await self.session.scalar(statement)
        if attempt is None:
            raise VideoResourceNotFoundError("video attempt not found")
        return attempt

    async def _require_completed_themes(self, enrollment_id: UUID, part: Part) -> None:
        total = int(
            await self.session.scalar(select(func.count(Theme.id)).where(Theme.part_id == part.id))
            or 0
        )
        completed = int(
            await self.session.scalar(
                select(func.count(Target.id))
                .join(Theme, Theme.id == Target.theme_id)
                .where(
                    Target.enrollment_id == enrollment_id,
                    Theme.part_id == part.id,
                    Target.status == TargetStatus.COMPLETED,
                )
            )
            or 0
        )
        if total == 0 or completed != total:
            raise VideoConflictError(
                f"all themes in the part must be Cukup ({completed} of {total} completed)"
            )

    @staticmethod
    def _next_slot(latest: VideoAttempt | None) -> tuple[int, int]:
        if latest is None:
            return 1, 0
        if latest.status is not VideoAttemptStatus.CLOSED:
            raise VideoConflictError("an academic slot for this part is already active")
        if latest.revision_no < 3:
            return latest.cycle_no, latest.revision_no + 1
        return latest.cycle_no + 1, 0

    def _validate_host(self, video_url: str) -> None:
        host = (urlsplit(video_url).hostname or "").lower().rstrip(".")
        if host not in self.allowed_hosts:
            raise VideoUrlNotAllowedError("video_url host is not allowed")

    @staticmethod
    def _audit(
        actor_id: UUID,
        request_id: UUID,
        action: str,
        attempt: VideoAttempt,
        *,
        after: dict[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="video_attempt",
            object_reference=str(attempt.id),
            request_id=request_id,
            before_data=None,
            after_data=after,
        )

    @staticmethod
    def _response(attempt: VideoAttempt) -> VideoAttemptResponse:
        return VideoAttemptResponse(
            id=attempt.id,
            enrollment_id=attempt.enrollment_id,
            part_id=attempt.part_id,
            part_no=attempt.part.sequence_no,
            part_name=attempt.part.title,
            cycle_no=attempt.cycle_no,
            revision_no=attempt.revision_no,
            status=attempt.status,
            row_version=attempt.row_version,
            versions=[
                VideoVersionResponse(
                    id=item.id,
                    version_no=item.version_no,
                    video_url=item.video_url,
                    recorded_on=item.recorded_date,
                    submitted_at=item.submitted_at,
                    status=item.status,
                )
                for item in attempt.versions
            ],
            allowed_actions=[]
            if attempt.status in {VideoAttemptStatus.FINALIZED, VideoAttemptStatus.CLOSED}
            else ["submit_version"],
        )
