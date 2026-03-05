from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.account import Account
from app.models.user import User

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"
ROLE_ADMIN = "admin"
ROLE_WRITER = "writer"

ROLE_PERMISSIONS = {
    ROLE_ADMIN: {"*"},
    ROLE_WRITER: {
        "chat:read",
        "chat:write",
        "materials:read",
        "materials:write",
        "documents:read",
        "documents:write",
        "preferences:read",
        "preferences:write",
        "books:read",
        "books:write",
        # account management is admin-only (ROLE_ADMIN has '*')
    },
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    account = db.query(Account).filter(Account.id == user.account_id).first()
    if not account or account.status != "active":
        raise HTTPException(status_code=403, detail="账户已禁用")
    return user


def user_has_permission(user: User, permission: str) -> bool:
    role = (getattr(user, "role", "") or ROLE_WRITER).strip() or ROLE_WRITER
    granted = ROLE_PERMISSIONS.get(role, set())
    return "*" in granted or permission in granted


def require_permission(permission: str) -> Callable[[User], User]:
    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user

    return _dep


def require_roles(*roles: str) -> Callable[[User], User]:
    allowed = {role.strip() for role in roles if role and role.strip()}

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        role = (getattr(current_user, "role", "") or ROLE_WRITER).strip() or ROLE_WRITER
        if role not in allowed:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user

    return _dep
