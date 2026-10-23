"""Lecturer authorization derived from the active organization context."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.modules.auth.access import AuthenticatedSessionDependency
from app.modules.identity.models import Role


@dataclass(frozen=True, slots=True)
class LecturerActor:
    user_id: UUID
    organization_id: UUID


async def get_lecturer_actor(authenticated: AuthenticatedSessionDependency) -> LecturerActor:
    context = authenticated.active_context
    if context is None or context.role is not Role.LECTURER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "lecturer_scope_required"},
        )
    return LecturerActor(authenticated.user_id, context.organization_id)


LecturerActorDependency = Annotated[LecturerActor, Depends(get_lecturer_actor)]
