"""Participant authorization derived from the active session context."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.modules.auth.access import AuthenticatedSessionDependency
from app.modules.identity.models import Role


@dataclass(frozen=True, slots=True)
class ParticipantActor:
    user_id: UUID
    organization_id: UUID


async def get_participant_actor(
    authenticated: AuthenticatedSessionDependency,
) -> ParticipantActor:
    context = authenticated.active_context
    if context is None or context.role is not Role.PARTICIPANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "participant_scope_required"},
        )
    return ParticipantActor(
        user_id=authenticated.user_id,
        organization_id=context.organization_id,
    )


ParticipantActorDependency = Annotated[ParticipantActor, Depends(get_participant_actor)]
