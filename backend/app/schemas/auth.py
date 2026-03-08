from __future__ import annotations

from pydantic import Field

from app.schemas.common import ApiModel, MessageResponse


class AuthUserResponse(ApiModel):
    id: int
    username: str
    display_name: str
    department: str
    role: str | None = None
    roles: list[str] = Field(default_factory=list)
    account_id: int | None = None


class AuthTokenResponse(ApiModel):
    token: str
    user: AuthUserResponse


class PermissionCodesResponse(ApiModel):
    permissions: list[str] = Field(default_factory=list)


class ProfileUpdateResponse(MessageResponse):
    user: AuthUserResponse
