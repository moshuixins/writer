from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.auth import AuthTokenResponse, AuthUserResponse, PermissionCodesResponse, ProfileUpdateResponse
from app.schemas.common import MessageResponse
from app.serializers import (
    serialize_auth_token_response,
    serialize_auth_user,
    serialize_message_response,
    serialize_permission_codes_response,
    serialize_profile_update_response,
)
from app.services.account_auth_service import AccountAuthService

router = APIRouter()


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


@router.post("/register", response_model=AuthTokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user = AccountAuthService(db).register_with_invite(
        username=req.username,
        password=req.password,
        display_name=req.display_name,
        department=req.department,
        invite_code=req.invite_code,
    )
    token = create_access_token(user.id)
    return serialize_auth_token_response(db, user, token)


@router.post("/login", response_model=AuthTokenResponse)
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


@router.get("/profile", response_model=AuthUserResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return serialize_auth_user(db, current_user)


@router.get("/permissions", response_model=PermissionCodesResponse)
def get_permissions(current_user: User = Depends(get_current_user)):
    return serialize_permission_codes_response(getattr(current_user, "_permission_codes", []))


@router.put("/profile", response_model=ProfileUpdateResponse)
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
    return serialize_profile_update_response(db, current_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(req.password, current_user.password_hash):
        raise HTTPException(400, "当前密码错误")
    current_user.password_hash = hash_password(req.newPassword)
    db.commit()
    return serialize_message_response("密码已修改")
