from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import ROLE_PERMISSIONS, ROLE_WRITER, create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models.account import Account
from app.models.invite_code import InviteCode
from app.models.user import User

router = APIRouter()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


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
    invite = db.query(InviteCode).filter(
        InviteCode.code_hash == code_hash,
    ).first()
    if not invite:
        raise HTTPException(400, "邀请码无效")

    if invite.status != "active":
        raise HTTPException(400, "邀请码已失效")

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        invite.status = "expired"
        db.commit()
        raise HTTPException(400, "邀请码已过期")

    account = db.query(Account).filter(
        Account.id == invite.account_id,
        Account.status == "active",
    ).first()
    if not account:
        raise HTTPException(400, "邀请码所属账户不存在或已禁用")

    user = User(
        account_id=invite.account_id,
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.username,
        department=req.department,
    )
    db.add(user)
    db.flush()

    invite.status = "used"
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(user.id)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "department": user.department,
            "role": user.role,
            "account_id": user.account_id,
        },
    }


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
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "department": user.department,
            "role": user.role,
            "account_id": user.account_id,
        },
    }


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "department": current_user.department,
        "role": current_user.role,
        "account_id": current_user.account_id,
    }


@router.get("/permissions")
def get_permissions(current_user: User = Depends(get_current_user)):
    role = (current_user.role or ROLE_WRITER).strip() or ROLE_WRITER
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        explicit = {perm for values in ROLE_PERMISSIONS.values() for perm in values if perm != "*"}
        permissions = ["*"] + sorted(explicit)
    else:
        permissions = sorted(perms)
    return {"permissions": permissions}


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
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
            "department": current_user.department,
            "role": current_user.role,
            "account_id": current_user.account_id,
        },
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
