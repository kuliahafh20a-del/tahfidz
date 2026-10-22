"""Validated request and response contracts for browser authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.identity.models import Role


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().casefold()


class RoleContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Role
    organization_id: UUID
    organization_name: str


class RoleContextSelection(BaseModel):
    role: Role
    organization_id: UUID


class SessionUser(BaseModel):
    id: UUID
    display_name: str
    login_identifier: str
    roles: list[RoleContext]


class SessionResponse(BaseModel):
    user: SessionUser
    active_context: RoleContext | None
    csrf_token: str
    expires_at: datetime


class SessionRotateRequest(BaseModel):
    active_context: RoleContextSelection | None = None


class PasswordRecoveryRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().casefold()


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


class GenericAuthResponse(BaseModel):
    message: str
