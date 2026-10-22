"""Participant and mentor authorization for mentoring sessions."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.modules.auth.access import AuthenticatedSessionDependency
from app.modules.identity.models import Role


@dataclass(frozen=True, slots=True)
class MentorActor:
    user_id: UUID
    organization_id: UUID


async def get_mentor_actor(authenticated: AuthenticatedSessionDependency) -> MentorActor:
    context = authenticated.active_context
    if context is None or context.role is not Role.MENTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "mentor_scope_required"},
        )
    return MentorActor(authenticated.user_id, context.organization_id)


MentorActorDependency = Annotated[MentorActor, Depends(get_mentor_actor)]
