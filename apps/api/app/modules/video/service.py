"""Transactional participant video-attempt workflows."""

from datetime import date
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import Select, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
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
from app.modules.curriculum.models import Part, Theme
from app.modules.mentoring.access import MentorActor
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.video.models import (
    EligibilityCheck,
    EligibilityDecision,
    EligibilityReview,
    EligibilityReviewStatus,
    VideoAttempt,
    VideoAttemptStatus,
    VideoVersion,
    VideoVersionStatus,
)
from app.modules.video.schemas import (
    ChecklistCriterionResponse,
    EligibilityCheckInput,
    EligibilityCheckResponse,
    EligibilityDraftUpdate,
    EligibilityFinalize,
    EligibilityReviewResponse,
    VideoAttemptResponse,
    VideoEligibilityResponse,
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
            await self.session.execute(
                update(EligibilityReview)
                .where(
                    EligibilityReview.video_version_id == previous.id,
                    EligibilityReview.status != EligibilityReviewStatus.SUPERSEDED,
                )
                .values(
                    status=EligibilityReviewStatus.SUPERSEDED,
                    finalized_at=utc_now(),
                )
            )
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


ELIGIBILITY_CHECKLISTS: dict[str, tuple[tuple[str, str], ...]] = {
    "technical-v1": (
        ("duration_ok", "Durasi rekaman sesuai bagian yang dikirim"),
        ("audio_clear", "Audio terdengar jelas dari awal hingga akhir"),
        ("continuous_recording", "Rekaman utuh tanpa potongan"),
    )
}


class EligibilityVersionConflictError(VideoConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("eligibility review was updated by another request")
        self.current_version = current_version


class VideoEligibilityService:
    """Mentor review and participant projection for technical video eligibility."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_mentor(self, actor: MentorActor) -> list[VideoEligibilityResponse]:
        versions = list(
            await self.session.scalars(
                self._mentor_statement(actor)
                .where(VideoVersion.status != VideoVersionStatus.REPLACED)
                .order_by(VideoVersion.submitted_at.desc(), VideoVersion.id)
            )
        )
        return [self._eligibility_response(item, mentor=True) for item in versions]

    async def list_for_participant(self, actor: ParticipantActor) -> list[VideoEligibilityResponse]:
        versions = list(
            await self.session.scalars(
                self._base_version_statement()
                .join(VideoAttempt, VideoAttempt.id == VideoVersion.attempt_id)
                .join(Enrollment, Enrollment.id == VideoAttempt.enrollment_id)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .where(
                    Enrollment.user_id == actor.user_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                    Cohort.organization_id == actor.organization_id,
                    VideoVersion.status != VideoVersionStatus.REPLACED,
                )
                .order_by(VideoVersion.submitted_at.desc(), VideoVersion.id)
            )
        )
        return [self._eligibility_response(item, mentor=False) for item in versions]

    async def get_for_mentor(
        self, actor: MentorActor, video_version_id: UUID
    ) -> VideoEligibilityResponse:
        return self._eligibility_response(
            await self._mentor_version(actor, video_version_id), mentor=True
        )

    async def save_draft(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: EligibilityDraftUpdate,
        request_id: UUID,
    ) -> VideoEligibilityResponse:
        version = await self._mentor_version(actor, video_version_id, lock=True)
        self._require_reviewable(version)
        self._validate_checks(payload.checklist_version, payload.checks, complete=False)
        review = self._active_review(version)
        if review is None:
            if payload.expected_version is not None:
                raise EligibilityVersionConflictError(0)
            review = EligibilityReview(
                video_version_id=version.id,
                reviewer_id=actor.user_id,
                checklist_version=payload.checklist_version,
                status=EligibilityReviewStatus.DRAFT,
                checks=[],
            )
            version.eligibility_reviews.append(review)
        else:
            self._require_draft_author(review, actor, payload.expected_version)

        review.checklist_version = payload.checklist_version
        review.decision = payload.decision
        review.reason = self._note(payload.reason)
        self._replace_checks(review, payload.checks)
        version.attempt.status = VideoAttemptStatus.UNDER_REVIEW
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "video_eligibility.draft_saved",
                review,
                after=self._review_state(review),
            )
        )
        await self.session.flush()
        return self._eligibility_response(version, mentor=True)

    async def finalize(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: EligibilityFinalize,
        request_id: UUID,
    ) -> VideoEligibilityResponse:
        version = await self._mentor_version(actor, video_version_id, lock=True)
        self._require_reviewable(version)
        review = self._active_review(version)
        if review is None:
            raise VideoConflictError("save an eligibility draft before finalization")
        self._require_draft_author(review, actor, payload.expected_version)
        self._validate_checks(payload.checklist_version, payload.checks, complete=True)
        if payload.decision is EligibilityDecision.ELIGIBLE and not all(
            item.passed for item in payload.checks
        ):
            raise VideoConflictError("every required check must pass for an eligible decision")
        if payload.decision is EligibilityDecision.INELIGIBLE and all(
            item.passed for item in payload.checks
        ):
            raise VideoConflictError("an ineligible decision must identify a failed check")

        review.checklist_version = payload.checklist_version
        review.decision = payload.decision
        review.reason = self._note(payload.reason)
        self._replace_checks(review, payload.checks)
        review.status = EligibilityReviewStatus.FINAL
        review.finalized_at = utc_now()
        if payload.decision is EligibilityDecision.ELIGIBLE:
            version.status = VideoVersionStatus.AVAILABLE
            version.attempt.status = VideoAttemptStatus.UNDER_REVIEW
        else:
            version.status = VideoVersionStatus.FAILED
            version.attempt.status = VideoAttemptStatus.SUBMITTED
        await self.session.flush()
        self.session.add(
            self._audit(
                actor.user_id,
                request_id,
                "video_eligibility.finalized",
                review,
                after=self._review_state(review),
            )
        )
        await self.session.flush()
        return self._eligibility_response(version, mentor=True)

    def _mentor_statement(self, actor: MentorActor) -> Select[VideoVersion]:
        now = utc_now()
        return (
            self._base_version_statement()
            .join(VideoAttempt, VideoAttempt.id == VideoVersion.attempt_id)
            .join(Enrollment, Enrollment.id == VideoAttempt.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Cohort.organization_id == actor.organization_id,
                exists(
                    select(Assignment.id).where(
                        Assignment.enrollment_id == Enrollment.id,
                        Assignment.staff_id == actor.user_id,
                        Assignment.role == AssignmentRole.MENTOR,
                        Assignment.valid_from <= now,
                        or_(Assignment.valid_to.is_(None), Assignment.valid_to > now),
                    )
                ),
            )
        )

    async def _mentor_version(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        *,
        lock: bool = False,
    ) -> VideoVersion:
        statement = self._mentor_statement(actor).where(VideoVersion.id == video_version_id)
        if lock:
            statement = statement.with_for_update(of=VideoVersion)
        version = await self.session.scalar(statement)
        if version is None:
            raise VideoResourceNotFoundError("video version not found in an active assignment")
        return version

    @staticmethod
    def _base_version_statement() -> Select[VideoVersion]:
        return select(VideoVersion).options(
            selectinload(VideoVersion.attempt).selectinload(VideoAttempt.part),
            selectinload(VideoVersion.attempt)
            .selectinload(VideoAttempt.enrollment)
            .selectinload(Enrollment.user),
            selectinload(VideoVersion.eligibility_reviews).selectinload(EligibilityReview.checks),
        )

    @staticmethod
    def _active_review(version: VideoVersion) -> EligibilityReview | None:
        return next(
            (
                item
                for item in reversed(version.eligibility_reviews)
                if item.status is not EligibilityReviewStatus.SUPERSEDED
            ),
            None,
        )

    @staticmethod
    def _require_reviewable(version: VideoVersion) -> None:
        if version.status is not VideoVersionStatus.SUBMITTED:
            raise VideoConflictError("only a submitted video version can be reviewed")

    @staticmethod
    def _require_draft_author(
        review: EligibilityReview,
        actor: MentorActor,
        expected_version: int | None,
    ) -> None:
        if review.status is not EligibilityReviewStatus.DRAFT:
            raise VideoConflictError("a final eligibility review is immutable")
        if review.reviewer_id != actor.user_id:
            raise VideoConflictError("only the draft author can update this review")
        if expected_version is None or review.row_version != expected_version:
            raise EligibilityVersionConflictError(review.row_version)

    @staticmethod
    def _validate_checks(
        checklist_version: str,
        checks: list[EligibilityCheckInput],
        *,
        complete: bool,
    ) -> None:
        definition = ELIGIBILITY_CHECKLISTS.get(checklist_version)
        if definition is None:
            raise VideoConflictError("unsupported eligibility checklist version")
        codes = [item.code for item in checks]
        if len(codes) != len(set(codes)):
            raise VideoConflictError("eligibility check codes must be unique")
        required = {code for code, _label in definition}
        supplied = set(codes)
        if not supplied <= required:
            raise VideoConflictError("eligibility checklist contains an unknown criterion")
        if complete and supplied != required:
            raise VideoConflictError("every required eligibility criterion must be supplied")

    @staticmethod
    def _replace_checks(review: EligibilityReview, checks: list[EligibilityCheckInput]) -> None:
        review.checks.clear()
        review.checks.extend(
            EligibilityCheck(
                criterion_code=item.code,
                passed=item.passed,
                notes=VideoEligibilityService._note(item.note),
            )
            for item in checks
        )

    @staticmethod
    def _note(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _audit(
        actor_id: UUID,
        request_id: UUID,
        action: str,
        review: EligibilityReview,
        *,
        after: dict[str, object],
    ) -> AuditEvent:
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="eligibility_review",
            object_reference=str(review.id),
            request_id=request_id,
            before_data=None,
            after_data=after,
        )

    @staticmethod
    def _review_state(review: EligibilityReview) -> dict[str, object]:
        return {
            "review_id": str(review.id),
            "checklist_version": review.checklist_version,
            "decision": review.decision.value if review.decision else None,
            "status": review.status.value,
            "row_version": review.row_version,
        }

    @staticmethod
    def _eligibility_response(version: VideoVersion, *, mentor: bool) -> VideoEligibilityResponse:
        attempt = version.attempt
        enrollment = attempt.enrollment
        review = VideoEligibilityService._active_review(version)
        checklist_version = review.checklist_version if review else "technical-v1"
        definition = ELIGIBILITY_CHECKLISTS[checklist_version]
        review_response = (
            EligibilityReviewResponse(
                id=review.id,
                reviewer_id=review.reviewer_id,
                checklist_version=review.checklist_version,
                decision=review.decision,
                reason=review.reason,
                status=review.status,
                finalized_at=review.finalized_at,
                row_version=review.row_version,
                checks=[
                    EligibilityCheckResponse(
                        code=item.criterion_code,
                        passed=item.passed,
                        note=item.notes,
                    )
                    for item in review.checks
                ],
            )
            if review
            else None
        )
        if mentor:
            allowed_actions = (
                ["edit_eligibility", "finalize_eligibility"]
                if version.status is VideoVersionStatus.SUBMITTED
                else (
                    ["start_academic_assessment"]
                    if version.status is VideoVersionStatus.AVAILABLE
                    else []
                )
            )
        elif version.status is VideoVersionStatus.FAILED:
            allowed_actions = ["replace_video"]
        elif version.status is VideoVersionStatus.AVAILABLE:
            allowed_actions = ["await_academic_assessment"]
        else:
            allowed_actions = ["await_eligibility"]
        return VideoEligibilityResponse(
            video_version_id=version.id,
            attempt_id=attempt.id,
            participant=SessionParticipant(
                enrollment_id=enrollment.id,
                user_id=enrollment.user.id,
                display_name=enrollment.user.name,
                nim=enrollment.nim_snapshot,
            ),
            part_id=attempt.part_id,
            part_no=attempt.part.sequence_no,
            part_name=attempt.part.title,
            cycle_no=attempt.cycle_no,
            revision_no=attempt.revision_no,
            video_version_no=version.version_no,
            video_url=version.video_url,
            recorded_on=version.recorded_date,
            submitted_at=version.submitted_at,
            video_status=version.status,
            checklist_version=checklist_version,
            criteria=[
                ChecklistCriterionResponse(code=code, label=label, required=True)
                for code, label in definition
            ],
            review=review_response,
            allowed_actions=allowed_actions,
        )
