from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.chat import ChatMessage, ChatSession, SessionDraft
from app.models.document import GeneratedDocument
from app.models.invite_code import InviteCode
from app.models.material import Material
from app.models.preference import UserPreference
from app.models.role import Role
from app.models.style import WritingHabit
from app.models.user import User
from app.rbac import ROLE_ADMIN, ROLE_WRITER
from app.serializers import (
    serialize_account,
    serialize_account_users,
    serialize_invite,
    serialize_permission,
    serialize_role_list,
)
from app.services.rbac_service import RBACError, RBACService, user_has_role

router = APIRouter()


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(12)



def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()



def _is_platform_admin(current_user: User) -> bool:
    return int(current_user.account_id or 0) == 1 and user_has_role(current_user, ROLE_ADMIN)



def _ensure_account_scope(current_user: User, account_id: int) -> None:
    if _is_platform_admin(current_user):
        return
    if int(current_user.account_id or 0) != int(account_id or 0):
        raise HTTPException(403, "无权访问该账户")




class CreateAccountRequest(BaseModel):
    code: str
    name: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("code 不能为空")
        if len(cleaned) < 2 or len(cleaned) > 64:
            raise ValueError("code 长度需在 2-64 之间")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name 不能为空")
        if len(cleaned) > 120:
            raise ValueError("name 长度不能超过 120")
        return cleaned


class UpdateAccountStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = (value or "").strip().lower()
        if cleaned not in {"active", "disabled"}:
            raise ValueError("status 必须为 active 或 disabled")
        return cleaned


class RebindUserRequest(BaseModel):
    migrate_data: bool = True


class CreateInviteRequest(BaseModel):
    expires_in_hours: int = 72


class RevokeInviteRequest(BaseModel):
    reason: str = ""


class UpdateUserRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("role 不能为空")
        return cleaned


class UpdateUserRolesRequest(BaseModel):
    role_codes: list[str] = Field(default_factory=list)


class CreateRoleRequest(BaseModel):
    code: str
    name: str
    description: str = ""
    permission_codes: list[str] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("角色编码不能为空")
        if len(cleaned) > 64:
            raise ValueError("角色编码不能超过 64 个字符")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("角色名称不能为空")
        if len(cleaned) > 120:
            raise ValueError("角色名称不能超过 120 个字符")
        return cleaned


class UpdateRoleRequest(BaseModel):
    name: str
    description: str = ""
    status: str = "active"
    permission_codes: list[str] = Field(default_factory=list)


@router.get("/me")
def get_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.query(Account).filter(Account.id == current_user.account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")
    return serialize_account(account)


@router.get("")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    if _is_platform_admin(current_user):
        rows = db.query(Account).order_by(Account.id.asc()).all()
    else:
        rows = db.query(Account).filter(Account.id == current_user.account_id).order_by(Account.id.asc()).all()
    count_rows = db.query(User.account_id).all()
    count_map: dict[int, int] = {}
    for (account_id,) in count_rows:
        count_map[int(account_id or 0)] = count_map.get(int(account_id or 0), 0) + 1

    items = [serialize_account(row, user_count=count_map.get(int(row.id), 0)) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/permissions")
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    items = [serialize_permission(row) for row in RBACService(db).list_permissions()]
    return {"items": items, "total": len(items)}


@router.get("/roles")
def list_roles(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    target_account_id = int(account_id or current_user.account_id or 1)
    _ensure_account_scope(current_user, target_account_id)
    items = serialize_role_list(db, target_account_id)
    return {"items": items, "total": len(items)}


@router.post("")
def create_account(
    req: CreateAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    if not _is_platform_admin(current_user):
        raise HTTPException(403, "仅平台管理员可创建账户")
    existing = db.query(Account).filter(Account.code == req.code).first()
    if existing:
        raise HTTPException(400, "账户编码已存在")
    row = Account(code=req.code, name=req.name, status="active")
    db.add(row)
    db.flush()
    RBACService(db).ensure_account_system_roles(row.id)
    db.commit()
    db.refresh(row)
    return serialize_account(row)


@router.put("/{account_id}/status")
def update_account_status(
    account_id: int,
    req: UpdateAccountStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    if not _is_platform_admin(current_user):
        raise HTTPException(403, "仅平台管理员可修改账户状态")
    row = db.query(Account).filter(Account.id == account_id).first()
    if not row:
        raise HTTPException(404, "账户不存在")
    row.status = req.status
    db.commit()
    db.refresh(row)
    return serialize_account(row)


@router.get("/{account_id}/users")
def list_account_users(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    _ensure_account_scope(current_user, account_id)
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")

    users = db.query(User).filter(User.account_id == account_id).order_by(User.id.asc()).all()
    items = serialize_account_users(db, users)
    return {
        "account": serialize_account(account),
        "items": items,
        "total": len(items),
    }


@router.post("/{account_id}/roles")
def create_role(
    account_id: int,
    req: CreateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    _ensure_account_scope(current_user, account_id)
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.status != "active":
        raise HTTPException(400, "账户已禁用")
    service = RBACService(db)
    try:
        role = service.create_role(
            account_id=account_id,
            code=req.code,
            name=req.name,
            description=req.description,
            permission_codes=req.permission_codes,
        )
        db.commit()
        db.refresh(role)
    except RBACError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return service.serialize_role(role, service.role_permission_codes([role]).get(int(role.id), []))


@router.put("/{account_id}/roles/{role_id}")
def update_role(
    account_id: int,
    role_id: int,
    req: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    _ensure_account_scope(current_user, account_id)
    role = db.query(Role).filter(Role.id == role_id, Role.account_id == account_id).first()
    if not role:
        raise HTTPException(404, "角色不存在")
    service = RBACService(db)
    try:
        service.update_role(role, name=req.name, description=req.description, status=req.status)
        service.set_role_permissions(role, req.permission_codes)
        db.commit()
        db.refresh(role)
    except RBACError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return service.serialize_role(role, service.role_permission_codes([role]).get(int(role.id), []))


@router.delete("/{account_id}/roles/{role_id}")
def delete_role(
    account_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    _ensure_account_scope(current_user, account_id)
    role = db.query(Role).filter(Role.id == role_id, Role.account_id == account_id).first()
    if not role:
        raise HTTPException(404, "角色不存在")
    try:
        RBACService(db).delete_role(role)
        db.commit()
    except RBACError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return {"id": role_id, "deleted": True}


@router.post("/{account_id}/invites")
def create_invite(
    account_id: int,
    req: CreateInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    _ensure_account_scope(current_user, account_id)
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")
    invite_code = _generate_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=max(1, int(req.expires_in_hours or 72)))
    row = InviteCode(
        account_id=account_id,
        code_hash=_hash_code(invite_code),
        created_by=current_user.id,
        status="active",
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_invite(row, invite_code=invite_code)


@router.get("/{account_id}/invites")
def list_invites(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    _ensure_account_scope(current_user, account_id)
    rows = db.query(InviteCode).filter(
        InviteCode.account_id == account_id,
    ).order_by(InviteCode.id.desc()).all()
    items = [serialize_invite(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.put("/invites/{invite_id}/revoke")
def revoke_invite(
    invite_id: int,
    req: RevokeInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    invite = db.query(InviteCode).filter(InviteCode.id == invite_id).first()
    if not invite:
        raise HTTPException(404, "邀请码不存在")
    _ensure_account_scope(current_user, int(invite.account_id or 0))
    if invite.status != "active":
        return {"id": invite.id, "status": invite.status}
    invite.status = "revoked"
    db.commit()
    return {"id": invite.id, "status": invite.status}


@router.put("/{account_id}/users/{user_id}")
def rebind_user(
    account_id: int,
    user_id: int,
    req: RebindUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    if not _is_platform_admin(current_user):
        raise HTTPException(403, "仅平台管理员可迁移账户")
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "目标账户不存在")
    if account.status != "active":
        raise HTTPException(400, "目标账户已禁用")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    old_account_id = int(user.account_id or 0)
    if old_account_id == account_id:
        return {
            "user_id": user.id,
            "old_account_id": old_account_id,
            "new_account_id": account_id,
            "migrated": False,
            "migrate_data": bool(req.migrate_data),
            "counts": {},
        }

    counts: dict[str, int] = {}
    rbac = RBACService(db)
    existing_role_codes = rbac.get_user_role_codes(user)

    try:
        user.account_id = account_id

        if req.migrate_data:
            counts["materials"] = db.query(Material).filter(
                Material.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

            session_ids = [
                sid
                for (sid,) in db.query(ChatSession.id).filter(ChatSession.user_id == user.id).all()
            ]
            counts["chat_sessions"] = db.query(ChatSession).filter(
                ChatSession.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

            if session_ids:
                counts["chat_messages"] = db.query(ChatMessage).filter(
                    ChatMessage.session_id.in_(session_ids),
                ).update({"account_id": account_id}, synchronize_session=False)
            else:
                counts["chat_messages"] = 0

            counts["session_drafts"] = db.query(SessionDraft).filter(
                SessionDraft.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

            counts["generated_documents"] = db.query(GeneratedDocument).filter(
                GeneratedDocument.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

            counts["user_preferences"] = db.query(UserPreference).filter(
                UserPreference.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

            counts["writing_habits"] = db.query(WritingHabit).filter(
                WritingHabit.user_id == user.id,
            ).update({"account_id": account_id}, synchronize_session=False)

        rbac.ensure_account_system_roles(account_id)
        mapped_codes = []
        for code in existing_role_codes:
            role = rbac.get_role_by_code(account_id, code)
            if role is not None and role.status == "active":
                mapped_codes.append(code)
        if not mapped_codes:
            mapped_codes = [ROLE_WRITER]
        rbac.set_user_roles(user, mapped_codes)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, "迁移账户失败")

    return {
        "user_id": user.id,
        "old_account_id": old_account_id,
        "new_account_id": account_id,
        "migrated": True,
        "migrate_data": bool(req.migrate_data),
        "counts": counts,
    }


@router.put("/{account_id}/users/{user_id}/roles")
def update_user_roles(
    account_id: int,
    user_id: int,
    req: UpdateUserRolesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    _ensure_account_scope(current_user, account_id)
    user = db.query(User).filter(
        User.id == user_id,
        User.account_id == account_id,
    ).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    try:
        roles = RBACService(db).set_user_roles(user, req.role_codes)
        db.commit()
        return {
            "id": user.id,
            "role": user.role,
            "role_codes": [role.code for role in roles],
        }
    except RBACError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.put("/{account_id}/users/{user_id}/role")
def update_user_role(
    account_id: int,
    user_id: int,
    req: UpdateUserRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    payload = UpdateUserRolesRequest(role_codes=[req.role])
    return update_user_roles(account_id, user_id, payload, db, current_user)