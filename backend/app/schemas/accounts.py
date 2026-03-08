from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import ApiModel, ListResponse, WarningMixin


class AccountResponse(ApiModel):
    id: int
    code: str
    name: str
    status: str
    user_count: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AccountListResponse(ListResponse[AccountResponse]):
    pass


class PermissionInfoResponse(ApiModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool


class PermissionListResponse(ListResponse[PermissionInfoResponse]):
    pass


class RoleInfoResponse(ApiModel):
    id: int
    account_id: int
    code: str
    role: str
    name: str
    description: str
    status: str
    is_system: bool
    permissions: list[str] = Field(default_factory=list)


class RoleListResponse(ListResponse[RoleInfoResponse]):
    pass


class UserRoleSummaryResponse(ApiModel):
    id: int
    code: str
    name: str
    is_system: bool


class AccountUserResponse(ApiModel):
    id: int
    username: str
    display_name: str
    department: str
    role: str
    role_codes: list[str] = Field(default_factory=list)
    roles: list[UserRoleSummaryResponse] = Field(default_factory=list)
    created_at: str | None = None


class AccountUsersResponse(ApiModel):
    account: AccountResponse
    items: list[AccountUserResponse] = Field(default_factory=list)
    total: int


class AccountInviteResponse(ApiModel):
    id: int
    account_id: int | None = None
    status: str
    created_by: int | None = None
    used_by: int | None = None
    created_at: str | None = None
    used_at: str | None = None
    expires_at: str | None = None
    invite_id: int | None = None
    invite_code: str | None = None


class AccountInviteListResponse(ListResponse[AccountInviteResponse]):
    pass


class InviteStatusResponse(ApiModel):
    id: int
    status: str


class RoleDeleteResponse(ApiModel):
    id: int
    deleted: bool


class RebindUserResponse(WarningMixin):
    user_id: int
    old_account_id: int
    new_account_id: int
    migrated: bool
    migrate_data: bool
    counts: dict[str, int] = Field(default_factory=dict)


class UserRoleUpdateResponse(ApiModel):
    id: int
    role: str
    role_codes: list[str] = Field(default_factory=list)
