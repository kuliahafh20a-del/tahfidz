"""Read services for effective policy and curriculum reference data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.modules.curriculum.models import (
    CurriculumStatus,
    CurriculumVersion,
    Part,
    PolicyStatus,
    PolicyVersion,
    Theme,
)
from app.modules.curriculum.schemas import (
    AssessmentRubricResponse,
    CurriculumResponse,
    PolicyRules,
    PolicySummary,
)


class ReferenceService:
    """Load the currently effective immutable reference versions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def assessment_rubric(self) -> AssessmentRubricResponse:
        policy = await self._current_policy()
        rules = PolicyRules.model_validate(policy.rules)
        return AssessmentRubricResponse(
            policy_id=policy.id,
            policy_version=policy.version,
            score=rules.score,
        )

    async def current_policy(self) -> PolicySummary:
        policy = await self._current_policy()
        if policy.effective_from is None:
            raise LookupError("published policy has no effective date")
        return PolicySummary.model_validate(policy)

    async def current_curriculum(self) -> CurriculumResponse:
        statement = (
            select(CurriculumVersion)
            .where(CurriculumVersion.status == CurriculumStatus.PUBLISHED)
            .options(
                selectinload(CurriculumVersion.parts)
                .selectinload(Part.themes)
                .selectinload(Theme.ranges)
            )
            .order_by(CurriculumVersion.published_at.desc())
            .limit(1)
        )
        curriculum = await self.session.scalar(statement)
        if curriculum is None:
            raise LookupError("no published curriculum is available")
        if curriculum.published_at is None:
            raise LookupError("published curriculum has no publication timestamp")
        return CurriculumResponse.model_validate(curriculum)

    async def _current_policy(self) -> PolicyVersion:
        now = utc_now()
        statement = (
            select(PolicyVersion)
            .where(
                PolicyVersion.status == PolicyStatus.PUBLISHED,
                PolicyVersion.effective_from <= now,
            )
            .order_by(PolicyVersion.effective_from.desc())
            .limit(1)
        )
        policy = await self.session.scalar(statement)
        if policy is None:
            raise LookupError("no effective policy is available")
        return policy
