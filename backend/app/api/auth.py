from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models.account import Account
from app.models.invite_code import InviteCode
from app.models.user import User
from app.rbac import ROLE_WRITER
from app.serializers import serialize_auth_token_response, serialize_auth_user
from app.services.rbac_service import RBACService

router = APIRouter()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _utc_now_for_invite() -> datetime:
    # SQLite strips tzinfo for DateTime columns, so invite comparisons use naive UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    department: str = "交管支队"
    invite_code: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("用户名长度需在 2-50 字符之间")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度不能少于 6 位")
        return v

    @field_validator("invite_code")
    @classmethod
    def invite_code_valid(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("invite_code 不能为空")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: str = ""
    department: str = ""


class ChangePasswordRequest(BaseModel):
    password: str
    newPassword: str

    @field_validator("newPassword")
    @classmethod
    def new_password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("新密码长度不能少于 6 位")
        return v


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")

    code_hash = _hash_code(req.invite_code)
    now = _utc_now_for_invite()
    invite = db.query(InviteCode).filter(InviteCode.code_hash == code_hash).first()
    if not invite:
        raise HTTPException(400, "邀请码无效")

    if invite.expires_at and invite.expires_at < now:
        invite.status = "expired"
        db.commit()
        raise HTTPException(400, "邀请码已过期")

    account = db.query(Account).filter(
        Account.id == invite.account_id,
        Account.status == "active",
    ).first()
    if not account:
        raise HTTPException(400, "邀请码所属账户不存在或已禁用")

    try:
        reserved = db.query(InviteCode).filter(
            InviteCode.id == invite.id,
            InviteCode.status == "active",
            or_(InviteCode.expires_at.is_(None), InviteCode.expires_at >= now),
        ).update({"status": "consuming"}, synchronize_session=False)
        if reserved != 1:
            db.rollback()
            raise HTTPException(400, "邀请码已失效")

        user = User(
            account_id=invite.account_id,
            username=req.username,
            password_hash=hash_password(req.password),
            display_name=req.display_name or req.username,
            department=req.department,
        )
        db.add(user)
        db.flush()

        rbac = RBACService(db)
        rbac.ensure_account_system_roles(int(invite.account_id or 1))
        rbac.set_user_roles(user, [ROLE_WRITER])

        invite_row = db.query(InviteCode).filter(InviteCode.id == invite.id).first()
        invite_row.status = "used"
        invite_row.used_by = user.id
        invite_row.used_at = now
        db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    token = create_access_token(user.id)
    return serialize_auth_token_response(db, user, token)


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    account = db.query(Account).filter(
        Account.id == user.account_id,
        Account.status == "active",
    ).first()
    if not account:
        raise HTTPException(403, "账户已禁用")

    token = create_access_token(user.id)
    return serialize_auth_token_response(db, user, token)


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return serialize_auth_user(db, current_user)


@router.get("/permissions")
def get_permissions(current_user: User = Depends(get_current_user)):
    return {"permissions": list(getattr(current_user, "_permission_codes", []) or [])}


@router.put("/profile")
def update_profile(
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.display_name:
        current_user.display_name = req.display_name
    if req.department:
        current_user.department = req.department
    db.commit()
    db.refresh(current_user)
    return {
        "message": "资料已更新",
        "user": serialize_auth_user(db, current_user),
    }


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(req.password, current_user.password_hash):
        raise HTTPException(400, "当前密码错误")
    current_user.password_hash = hash_password(req.newPassword)
    db.commit()
    return {"message": "密码已修改"}
