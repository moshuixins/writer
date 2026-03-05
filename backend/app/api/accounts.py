from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import ROLE_PERMISSIONS, get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.chat import ChatMessage, ChatSession, SessionDraft
from app.models.document import GeneratedDocument
from app.models.invite_code import InviteCode
from app.models.material import Material
from app.models.preference import UserPreference
from app.models.style import WritingHabit
from app.models.user import User
from app.timezone import to_shanghai_iso

router = APIRouter()


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
        if cleaned not in ROLE_PERMISSIONS:
            raise ValueError("role 非法")
        return cleaned


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(12)


def _hash_code(code: str) -> str:
    import hashlib

    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@router.get("/me")
def get_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.query(Account).filter(Account.id == current_user.account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")
    return {
        "id": account.id,
        "code": account.code,
        "name": account.name,
        "status": account.status,
        "created_at": to_shanghai_iso(account.created_at),
        "updated_at": to_shanghai_iso(account.updated_at),
    }


@router.get("")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    rows = db.query(Account).order_by(Account.id.asc()).all()
    count_rows = db.query(User.account_id).all()
    count_map: dict[int, int] = {}
    for (account_id,) in count_rows:
        count_map[int(account_id or 0)] = count_map.get(int(account_id or 0), 0) + 1

    return {
        "items": [
            {
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "status": row.status,
                "user_count": count_map.get(row.id, 0),
                "created_at": to_shanghai_iso(row.created_at),
                "updated_at": to_shanghai_iso(row.updated_at),
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/roles")
def list_roles(
    current_user: User = Depends(require_permission("accounts:read")),
):
    explicit_permissions = sorted(
        {perm for perms in ROLE_PERMISSIONS.values() for perm in perms if perm != "*"},
    )
    items = []
    for role, perms in ROLE_PERMISSIONS.items():
        if "*" in perms:
            permissions = ["*"] + explicit_permissions
        else:
            permissions = sorted(perms)
        items.append({"role": role, "permissions": permissions})
    return {"items": items, "total": len(items)}


@router.post("")
def create_account(
    req: CreateAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    existing = db.query(Account).filter(Account.code == req.code).first()
    if existing:
        raise HTTPException(400, "账户 code 已存在")

    row = Account(
        code=req.code,
        name=req.name,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "status": row.status,
        "created_at": to_shanghai_iso(row.created_at),
        "updated_at": to_shanghai_iso(row.updated_at),
    }


@router.put("/{account_id}/status")
def update_account_status(
    account_id: int,
    req: UpdateAccountStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    row = db.query(Account).filter(Account.id == account_id).first()
    if not row:
        raise HTTPException(404, "账户不存在")
    row.status = req.status
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "status": row.status,
        "created_at": to_shanghai_iso(row.created_at),
        "updated_at": to_shanghai_iso(row.updated_at),
    }


@router.get("/{account_id}/users")
def list_account_users(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")

    users = db.query(User).filter(User.account_id == account_id).order_by(User.id.asc()).all()
    return {
        "account": {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "status": account.status,
        },
        "items": [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "department": user.department,
                "role": user.role,
                "created_at": to_shanghai_iso(user.created_at),
            }
            for user in users
        ],
        "total": len(users),
    }


@router.post("/{account_id}/invites")
def create_invite(
    account_id: int,
    req: CreateInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.status != "active":
        raise HTTPException(400, "账户已禁用")

    hours = max(1, min(int(req.expires_in_hours or 72), 720))
    invite_code = _generate_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    row = InviteCode(
        account_id=account_id,
        code_hash=_hash_code(invite_code),
        status="active",
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "invite_id": row.id,
        "invite_code": invite_code,
        "account_id": account_id,
        "expires_at": to_shanghai_iso(row.expires_at),
    }


@router.get("/{account_id}/invites")
def list_invites(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:read")),
):
    rows = db.query(InviteCode).filter(
        InviteCode.account_id == account_id,
    ).order_by(InviteCode.id.desc()).all()

    return {
        "items": [
            {
                "id": row.id,
                "status": row.status,
                "created_by": row.created_by,
                "used_by": row.used_by,
                "created_at": to_shanghai_iso(row.created_at),
                "used_at": to_shanghai_iso(row.used_at) if row.used_at else None,
                "expires_at": to_shanghai_iso(row.expires_at) if row.expires_at else None,
            }
            for row in rows
        ],
        "total": len(rows),
    }


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
    if invite.status != "active":
        return {"id": invite.id, "status": invite.status}
    invite.status = "revoked"
    db.commit()
    return {"id": invite.id, "status": invite.status}


@router.put("/{account_id}/users/{user_id}")
def rebind_user_account(
    account_id: int,
    user_id: int,
    req: RebindUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
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


@router.put("/{account_id}/users/{user_id}/role")
def update_user_role(
    account_id: int,
    user_id: int,
    req: UpdateUserRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounts:write")),
):
    user = db.query(User).filter(
        User.id == user_id,
        User.account_id == account_id,
    ).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == req.role:
        return {"id": user.id, "role": user.role}
    user.role = req.role
    db.commit()
    db.refresh(user)
    return {"id": user.id, "role": user.role}
