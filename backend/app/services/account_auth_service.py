from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.errors import AppError
from app.models.account import Account
from app.models.invite_code import InviteCode
from app.models.user import User
from app.rbac import ROLE_WRITER
from app.services.rbac_service import RBACService


class AccountAuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_with_invite(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        department: str,
        invite_code: str,
    ) -> User:
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise AppError("用户名已存在", status_code=400)

        invite = self._get_invite(invite_code)
        now = self._utc_now_for_invite()
        if invite.expires_at and invite.expires_at < now:
            invite.status = "expired"
            self.db.commit()
            raise AppError("邀请码已过期", status_code=400)

        account = self.db.query(Account).filter(
            Account.id == invite.account_id,
            Account.status == "active",
        ).first()
        if not account:
            raise AppError("邀请码所属账户不存在或已禁用", status_code=400)

        try:
            reserved = self.db.query(InviteCode).filter(
                InviteCode.id == invite.id,
                InviteCode.status == "active",
                or_(InviteCode.expires_at.is_(None), InviteCode.expires_at >= now),
            ).update({"status": "consuming"}, synchronize_session=False)
            if reserved != 1:
                self.db.rollback()
                raise AppError("邀请码已失效", status_code=400)

            user = User(
                account_id=invite.account_id,
                username=username,
                password_hash=hash_password(password),
                display_name=display_name or username,
                department=department,
            )
            self.db.add(user)
            self.db.flush()

            rbac = RBACService(self.db)
            rbac.ensure_account_system_roles(int(invite.account_id or 1))
            rbac.set_user_roles(user, [ROLE_WRITER])

            invite_row = self.db.query(InviteCode).filter(InviteCode.id == invite.id).first()
            invite_row.status = "used"
            invite_row.used_by = user.id
            invite_row.used_at = now
            self.db.commit()
            self.db.refresh(user)
            return user
        except AppError:
            raise
        except Exception as exc:
            self.db.rollback()
            raise AppError("注册失败，请稍后重试", detail=str(exc)) from exc

    def _get_invite(self, invite_code: str) -> InviteCode:
        code_hash = hashlib.sha256(invite_code.encode("utf-8")).hexdigest()
        invite = self.db.query(InviteCode).filter(InviteCode.code_hash == code_hash).first()
        if not invite:
            raise AppError("邀请码无效", status_code=400)
        return invite

    @staticmethod
    def _utc_now_for_invite() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
