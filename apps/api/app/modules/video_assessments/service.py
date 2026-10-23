"""Transactional academic grading for technically eligible video versions."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.time import utc_now
from app.modules.assessments.models import (
    AssessmentKind,
    AssessmentRecord,
    AssessmentStatus,
    AssistanceType,
    Incident,
    VideoAssessment,
    VideoAssessmentOutcome,
)
from app.modules.assessments.schemas import IncidentInput, IncidentResponse
from app.modules.audit.models import AuditEvent
from app.modules.calendar.access import ParticipantActor
from app.modules.cohorts.models import (
    Assignment,
    AssignmentRole,
    Cohort,
    Enrollment,
    EnrollmentStatus,
)
from app.modules.curriculum.models import PolicyStatus
from app.modules.curriculum.schemas import PolicyRules
from app.modules.media.models import MediaAsset, MediaAssetStatus, MediaPurpose
from app.modules.media.storage import S3ObjectStorage
from app.modules.mentoring.access import MentorActor
from app.modules.mentoring.schemas import SessionParticipant
from app.modules.video.models import (
    EligibilityDecision,
    EligibilityReview,
    EligibilityReviewStatus,
    VideoAttempt,
    VideoAttemptStatus,
    VideoVersion,
    VideoVersionStatus,
)
from app.modules.video_assessments.schemas import (
    VideoAssessmentAudio,
    VideoAssessmentDraftCreate,
    VideoAssessmentDraftUpdate,
    VideoAssessmentPlayback,
    VideoAssessmentResponse,
)


class VideoAssessmentNotFoundError(LookupError):
    pass


class VideoAssessmentConflictError(ValueError):
    pass


class VideoAssessmentVersionConflictError(VideoAssessmentConflictError):
    def __init__(self, current_version: int) -> None:
        super().__init__("video assessment was updated by another request")
        self.current_version = current_version


class VideoAssessmentService:
    def __init__(self, session: AsyncSession, storage: S3ObjectStorage) -> None:
        self.session = session
        self.storage = storage

    async def create_draft(
        self,
        actor: MentorActor,
        video_version_id: UUID,
        payload: VideoAssessmentDraftCreate,
        request_id: UUID,
    ) -> VideoAssessmentResponse:
        version = await self._mentor_video_version(actor, video_version_id, lock=True)
        review = self._eligible_review(version)
        duplicate = await self.session.scalar(
            select(VideoAssessment.id)
            .join(AssessmentRecord, AssessmentRecord.id == VideoAssessment.id)
            .where(
                VideoAssessment.video_version_id == version.id,
                AssessmentRecord.status != AssessmentStatus.SUPERSEDED,
            )
        )
        if duplicate is not None:
            raise VideoAssessmentConflictError("this video version already has an assessment")
        policy = version.attempt.enrollment.cohort.policy_version
        if policy.status is not PolicyStatus.PUBLISHED:
            raise VideoAssessmentConflictError("the cohort policy version is not published")
        self._validate_incidents(payload.incidents, final=False)
        audio = (
            await self._audio(actor, payload.feedback_audio_id)
            if payload.feedback_audio_id
            else None
        )
        counted = self.counted_errors(payload.incidents)
        outcome = self.outcome_for(counted, policy.rules)
        record = AssessmentRecord(
            enrollment_id=version.attempt.enrollment_id,
            assessor_id=actor.user_id,
            policy_version_id=policy.id,
            kind=AssessmentKind.VIDEO,
            actual_at=utc_now(),
            manual_score=self._score(payload.manual_score),
            incidents=[],
        )
        self.session.add(record)
        await self.session.flush()
        self.session.add(
            VideoAssessment(
                id=record.id,
                video_version_id=version.id,
                eligibility_review_id=review.id,
                audio_asset_id=audio.id if audio else None,
                counted_errors=counted,
                outcome=outcome,
                notes=self._note(payload.mentor_note),
            )
        )
        self._replace_incidents(record, payload.incidents)
        await self.session.flush()
        self.session.add(
            self._audit(actor.user_id, request_id, "video_assessment.draft_created", record)
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def update_draft(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        payload: VideoAssessmentDraftUpdate,
        request_id: UUID,
    ) -> VideoAssessmentResponse:
        record = await self._mentor_assessment(actor, assessment_id, lock=True, author=True)
        self._require_version(record, payload.expected_version)
        if record.status is not AssessmentStatus.DRAFT:
            raise VideoAssessmentConflictError("final assessments are immutable")
        subtype = self._subtype(record)
        self._eligible_review(subtype.video_version, expected_id=subtype.eligibility_review_id)
        self._validate_incidents(payload.incidents, final=False)
        audio = (
            await self._audio(actor, payload.feedback_audio_id)
            if payload.feedback_audio_id
            else None
        )
        subtype.audio_asset_id = audio.id if audio else None
        subtype.notes = self._note(payload.mentor_note)
        subtype.counted_errors = self.counted_errors(payload.incidents)
        subtype.outcome = self.outcome_for(subtype.counted_errors, record.policy_version.rules)
        record.manual_score = self._score(payload.manual_score)
        self._replace_incidents(record, payload.incidents)
        await self.session.flush()
        self.session.add(
            self._audit(actor.user_id, request_id, "video_assessment.draft_updated", record)
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def finalize(
        self,
        actor: MentorActor,
        assessment_id: UUID,
        expected_version: int,
        request_id: UUID,
    ) -> VideoAssessmentResponse:
        record = await self._mentor_assessment(actor, assessment_id, lock=True, author=True)
        self._require_version(record, expected_version)
        if record.status is not AssessmentStatus.DRAFT:
            raise VideoAssessmentConflictError("assessment is already final")
        subtype = self._subtype(record)
        attempt = await self.session.scalar(
            select(VideoAttempt)
            .where(VideoAttempt.id == subtype.video_version.attempt_id)
            .with_for_update()
        )
        if attempt is None:
            raise VideoAssessmentNotFoundError("video attempt not found")
        self._eligible_review(subtype.video_version, expected_id=subtype.eligibility_review_id)
        self._validate_incidents(
            [
                IncidentInput(
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
            final=True,
        )
        if record.manual_score is None:
            raise VideoAssessmentConflictError("manual score is required before finalization")
        if subtype.audio_asset_id is None:
            raise VideoAssessmentConflictError("feedback audio is required before finalization")
        audio = await self.session.scalar(
            select(MediaAsset).where(MediaAsset.id == subtype.audio_asset_id).with_for_update()
        )
        if audio is None or audio.status is not MediaAssetStatus.AVAILABLE:
            raise VideoAssessmentConflictError(
                "feedback audio must be available before finalization"
            )
        subtype.counted_errors = sum(1 for item in record.incidents if item.counted)
        subtype.outcome = self.outcome_for(subtype.counted_errors, record.policy_version.rules)
        record.status = AssessmentStatus.FINAL
        record.finalized_at = utc_now()
        attempt.status = (
            VideoAttemptStatus.FINALIZED
            if subtype.outcome is VideoAssessmentOutcome.ENOUGH
            else VideoAttemptStatus.CLOSED
        )
        await self.session.flush()
        self.session.add(
            self._audit(actor.user_id, request_id, "video_assessment.finalized", record)
        )
        await self.session.flush()
        return self._response(await self._load(record.id))

    async def get_for_mentor(
        self, actor: MentorActor, assessment_id: UUID
    ) -> VideoAssessmentResponse:
        return self._response(await self._mentor_assessment(actor, assessment_id))

    async def list_for_mentor(self, actor: MentorActor) -> list[VideoAssessmentResponse]:
        now = utc_now()
        records = list(
            await self.session.scalars(
                self._base_statement()
                .join(Enrollment, Enrollment.id == AssessmentRecord.enrollment_id)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .where(
                    AssessmentRecord.kind == AssessmentKind.VIDEO,
                    Cohort.organization_id == actor.organization_id,
                    self._active_assignment(actor.user_id, Enrollment.id, now),
                )
                .order_by(AssessmentRecord.created_at.desc(), AssessmentRecord.id.desc())
            )
        )
        return [self._response(item) for item in records]

    async def list_for_participant(self, actor: ParticipantActor) -> list[VideoAssessmentResponse]:
        records = list(
            await self.session.scalars(
                self._base_statement()
                .join(Enrollment, Enrollment.id == AssessmentRecord.enrollment_id)
                .join(Cohort, Cohort.id == Enrollment.cohort_id)
                .where(
                    AssessmentRecord.kind == AssessmentKind.VIDEO,
                    AssessmentRecord.status == AssessmentStatus.FINAL,
                    Enrollment.user_id == actor.user_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                    Cohort.organization_id == actor.organization_id,
                )
                .order_by(AssessmentRecord.finalized_at.desc(), AssessmentRecord.id.desc())
            )
        )
        return [self._response(item, participant=True) for item in records]

    async def history_for_mentor(
        self, actor: MentorActor, enrollment_id: UUID
    ) -> list[VideoAssessmentResponse]:
        now = utc_now()
        allowed = await self.session.scalar(
            select(Enrollment.id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Enrollment.id == enrollment_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
        )
        if allowed is None:
            raise VideoAssessmentNotFoundError("participant not found in active assignment")
        records = list(
            await self.session.scalars(
                self._base_statement()
                .where(
                    AssessmentRecord.kind == AssessmentKind.VIDEO,
                    AssessmentRecord.enrollment_id == enrollment_id,
                )
                .order_by(AssessmentRecord.created_at.desc(), AssessmentRecord.id.desc())
            )
        )
        return [self._response(item) for item in records]

    async def playback_for_mentor(
        self, actor: MentorActor, assessment_id: UUID, request_id: UUID
    ) -> VideoAssessmentPlayback:
        return await self._playback(
            await self._mentor_assessment(actor, assessment_id), actor.user_id, request_id
        )

    async def playback_for_participant(
        self, actor: ParticipantActor, assessment_id: UUID, request_id: UUID
    ) -> VideoAssessmentPlayback:
        record = await self.session.scalar(
            self._base_statement()
            .join(Enrollment, Enrollment.id == AssessmentRecord.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                AssessmentRecord.id == assessment_id,
                AssessmentRecord.kind == AssessmentKind.VIDEO,
                AssessmentRecord.status == AssessmentStatus.FINAL,
                Enrollment.user_id == actor.user_id,
                Cohort.organization_id == actor.organization_id,
            )
        )
        if record is None:
            raise VideoAssessmentNotFoundError("video assessment not found")
        return await self._playback(record, actor.user_id, request_id)

    async def _playback(
        self, record: AssessmentRecord, actor_id: UUID, request_id: UUID
    ) -> VideoAssessmentPlayback:
        subtype = self._subtype(record)
        if record.status is not AssessmentStatus.FINAL or subtype.audio_asset is None:
            raise VideoAssessmentConflictError("final feedback audio is not available")
        if subtype.audio_asset.status is not MediaAssetStatus.AVAILABLE:
            raise VideoAssessmentConflictError("feedback audio is not available")
        signed = self.storage.playback_request(subtype.audio_asset.storage_key)
        self.session.add(
            self._audit(actor_id, request_id, "video_assessment.audio_playback_issued", record)
        )
        await self.session.flush()
        return VideoAssessmentPlayback(
            assessment_id=record.id,
            playback_url=signed.url,
            expires_at=signed.expires_at,
        )

    async def _mentor_video_version(
        self, actor: MentorActor, video_version_id: UUID, *, lock: bool = False
    ) -> VideoVersion:
        now = utc_now()
        statement = (
            select(VideoVersion)
            .join(VideoAttempt, VideoAttempt.id == VideoVersion.attempt_id)
            .join(Enrollment, Enrollment.id == VideoAttempt.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                VideoVersion.id == video_version_id,
                Cohort.organization_id == actor.organization_id,
                self._active_assignment(actor.user_id, Enrollment.id, now),
            )
            .options(
                selectinload(VideoVersion.eligibility_reviews),
                selectinload(VideoVersion.attempt).selectinload(VideoAttempt.part),
                selectinload(VideoVersion.attempt)
                .selectinload(VideoAttempt.enrollment)
                .selectinload(Enrollment.user),
                selectinload(VideoVersion.attempt)
                .selectinload(VideoAttempt.enrollment)
                .selectinload(Enrollment.cohort)
                .selectinload(Cohort.policy_version),
            )
        )
        if lock:
            statement = statement.with_for_update(of=VideoVersion)
        version = await self.session.scalar(statement)
        if version is None:
            raise VideoAssessmentNotFoundError("video version not found in active assignment")
        return version

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
                AssessmentRecord.kind == AssessmentKind.VIDEO,
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
            raise VideoAssessmentNotFoundError("video assessment not found in active assignment")
        return record

    @staticmethod
    def _base_statement() -> Select[AssessmentRecord]:
        return select(AssessmentRecord).options(
            selectinload(AssessmentRecord.enrollment).selectinload(Enrollment.user),
            selectinload(AssessmentRecord.policy_version),
            selectinload(AssessmentRecord.incidents),
            selectinload(AssessmentRecord.video_assessment)
            .selectinload(VideoAssessment.video_version)
            .selectinload(VideoVersion.attempt)
            .selectinload(VideoAttempt.part),
            selectinload(AssessmentRecord.video_assessment)
            .selectinload(VideoAssessment.video_version)
            .selectinload(VideoVersion.attempt)
            .selectinload(VideoAttempt.enrollment)
            .selectinload(Enrollment.user),
            selectinload(AssessmentRecord.video_assessment)
            .selectinload(VideoAssessment.video_version)
            .selectinload(VideoVersion.eligibility_reviews),
            selectinload(AssessmentRecord.video_assessment).selectinload(
                VideoAssessment.eligibility_review
            ),
            selectinload(AssessmentRecord.video_assessment).selectinload(
                VideoAssessment.audio_asset
            ),
        )

    async def _load(self, assessment_id: UUID) -> AssessmentRecord:
        record = await self.session.scalar(
            self._base_statement().where(AssessmentRecord.id == assessment_id)
        )
        if record is None:
            raise VideoAssessmentNotFoundError("video assessment not found")
        return record

    async def _audio(self, actor: MentorActor, audio_id: UUID) -> MediaAsset:
        asset = await self.session.scalar(
            select(MediaAsset).where(
                MediaAsset.id == audio_id,
                MediaAsset.owner_id == actor.user_id,
                MediaAsset.organization_id == actor.organization_id,
                MediaAsset.purpose == MediaPurpose.MENTOR_FEEDBACK,
                MediaAsset.status != MediaAssetStatus.DELETED,
            )
        )
        if asset is None:
            raise VideoAssessmentNotFoundError("feedback audio not found in active scope")
        return asset

    @staticmethod
    def _eligible_review(
        version: VideoVersion, *, expected_id: UUID | None = None
    ) -> EligibilityReview:
        review = next(
            (
                item
                for item in reversed(version.eligibility_reviews)
                if item.status is EligibilityReviewStatus.FINAL
                and item.decision is EligibilityDecision.ELIGIBLE
            ),
            None,
        )
        if (
            version.status is not VideoVersionStatus.AVAILABLE
            or review is None
            or review.video_version_id != version.id
            or (expected_id is not None and review.id != expected_id)
        ):
            raise VideoAssessmentConflictError(
                "assessment requires the matching final eligible video review"
            )
        return review

    @staticmethod
    def counted_errors(incidents: list[IncidentInput]) -> int:
        return sum(1 for item in incidents if item.counted)

    @staticmethod
    def outcome_for(
        counted_errors: int, policy_rules: Mapping[str, object]
    ) -> VideoAssessmentOutcome:
        rules = PolicyRules.model_validate(policy_rules)
        return (
            VideoAssessmentOutcome.ENOUGH
            if counted_errors <= rules.video_assessment.maximum_errors_for_enough
            else VideoAssessmentOutcome.NOT_ENOUGH
        )

    @staticmethod
    def _validate_incidents(incidents: list[IncidentInput], *, final: bool) -> None:
        for item in incidents:
            if item.video_second is None:
                raise VideoAssessmentConflictError("video incidents require a timestamp")
            if item.assistance is AssistanceType.ANSWER and item.self_corrected:
                raise VideoAssessmentConflictError(
                    "an answered incident cannot be marked self-corrected"
                )
            if not item.counted and (
                not item.self_corrected or item.assistance is AssistanceType.ANSWER
            ):
                raise VideoAssessmentConflictError(
                    "an uncounted incident must be self-corrected without an answer"
                )
            if final and not (item.counting_reason and item.counting_reason.strip()):
                raise VideoAssessmentConflictError(
                    "every incident requires a counting reason before finalization"
                )

    @staticmethod
    def _replace_incidents(record: AssessmentRecord, incidents: list[IncidentInput]) -> None:
        record.incidents.clear()
        record.incidents.extend(
            Incident(
                category=item.primary_category.strip(),
                location_text=item.location_text.strip(),
                video_second=item.video_second,
                context=VideoAssessmentService._note(item.context),
                assistance_type=item.assistance,
                self_corrected=item.self_corrected,
                counted=item.counted,
                count_reason=VideoAssessmentService._note(item.counting_reason),
                notes=VideoAssessmentService._note(item.note),
            )
            for item in incidents
        )

    @staticmethod
    def _active_assignment(
        mentor_id: UUID,
        enrollment_id: ColumnElement[UUID] | InstrumentedAttribute[UUID],
        now: datetime,
    ) -> ColumnElement[bool]:
        return exists(
            select(Assignment.id).where(
                Assignment.enrollment_id == enrollment_id,
                Assignment.staff_id == mentor_id,
                Assignment.role == AssignmentRole.MENTOR,
                Assignment.valid_from <= now,
                or_(Assignment.valid_to.is_(None), Assignment.valid_to > now),
            )
        )

    @staticmethod
    def _require_version(record: AssessmentRecord, expected_version: int) -> None:
        if record.row_version != expected_version:
            raise VideoAssessmentVersionConflictError(record.row_version)

    @staticmethod
    def _subtype(record: AssessmentRecord) -> VideoAssessment:
        if record.video_assessment is None:
            raise VideoAssessmentNotFoundError("video assessment subtype not found")
        return record.video_assessment

    @staticmethod
    def _score(value: int | None) -> Decimal | None:
        return Decimal(value) if value is not None else None

    @staticmethod
    def _note(value: str | None) -> str | None:
        normalized = value.strip() if value is not None else ""
        return normalized or None

    @staticmethod
    def _audit(
        actor_id: UUID, request_id: UUID, action: str, record: AssessmentRecord
    ) -> AuditEvent:
        subtype = record.video_assessment
        return AuditEvent(
            actor_id=actor_id,
            action=action,
            object_type="video_assessment",
            object_reference=str(record.id),
            request_id=request_id,
            before_data=None,
            after_data={
                "assessment_id": str(record.id),
                "status": record.status.value,
                "counted_errors": subtype.counted_errors if subtype else None,
                "outcome": subtype.outcome.value if subtype and subtype.outcome else None,
                "row_version": record.row_version,
            },
        )

    @staticmethod
    def _response(
        record: AssessmentRecord, *, participant: bool = False
    ) -> VideoAssessmentResponse:
        subtype = VideoAssessmentService._subtype(record)
        version = subtype.video_version
        attempt = version.attempt
        enrollment = attempt.enrollment
        audio = subtype.audio_asset
        return VideoAssessmentResponse(
            assessment_id=record.id,
            video_version_id=version.id,
            eligibility_review_id=subtype.eligibility_review_id,
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
            status=record.status,
            manual_score=int(record.manual_score) if record.manual_score is not None else None,
            mentor_note=subtype.notes,
            counted_errors=subtype.counted_errors,
            outcome=subtype.outcome,
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
            feedback_audio=(
                VideoAssessmentAudio(
                    id=audio.id,
                    file_name=audio.original_file_name,
                    status=audio.status,
                )
                if audio
                else None
            ),
            actual_at=record.actual_at,
            finalized_at=record.finalized_at,
            policy_version_id=record.policy_version_id,
            policy_version=record.policy_version.version,
            row_version=record.row_version,
            allowed_actions=(
                [
                    "view_result",
                    "play_audio",
                    *(
                        ["create_next_revision"]
                        if subtype.outcome is VideoAssessmentOutcome.NOT_ENOUGH
                        else []
                    ),
                ]
                if participant
                else (
                    ["edit", "finalize"]
                    if record.status is AssessmentStatus.DRAFT
                    else ["view_result", "play_audio"]
                )
            ),
        )
