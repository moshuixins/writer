from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.chat import ChatMessage, ChatSession, SessionDraft
from app.models.document import GeneratedDocument
from app.models.material import Material
from app.models.preference import UserPreference
from app.models.style import WritingHabit
from app.models.user import User
from app.rbac import ROLE_WRITER
from app.services.account_resource_sync_service import AccountResourceSyncService
from app.services.rbac_service import RBACService
from app.side_effects import collect_side_effect_warning


class AccountMembershipService:
    def __init__(self, db: Session):
        self.db = db

    def rebind_user(
        self,
        user: User,
        *,
        target_account_id: int,
        migrate_data: bool,
    ) -> dict[str, Any]:
        old_account_id = int(user.account_id or 0)
        if old_account_id == int(target_account_id):
            return {
                "user_id": int(user.id),
                "old_account_id": old_account_id,
                "new_account_id": int(target_account_id),
                "migrated": False,
                "migrate_data": bool(migrate_data),
                "counts": {},
                "warnings": [],
            }

        counts: dict[str, int] = {}
        warnings: list[str] = []
        rbac = RBACService(self.db)
        existing_role_codes = rbac.get_user_role_codes(user)

        try:
            user.account_id = int(target_account_id)
            if migrate_data:
                self._migrate_user_records(user.id, int(target_account_id), counts)
            self._rebind_user_roles(rbac, user, int(target_account_id), existing_role_codes)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise AppError("迁移账户失败", detail=str(exc)) from exc

        if migrate_data:
            self._rebuild_account_resources(
                counts=counts,
                warnings=warnings,
                user_id=int(user.id),
                old_account_id=old_account_id,
                new_account_id=int(target_account_id),
            )

        return {
            "user_id": int(user.id),
            "old_account_id": old_account_id,
            "new_account_id": int(target_account_id),
            "migrated": True,
            "migrate_data": bool(migrate_data),
            "counts": counts,
            "warnings": warnings,
        }

    def _migrate_user_records(self, user_id: int, target_account_id: int, counts: dict[str, int]) -> None:
        counts["materials"] = self.db.query(Material).filter(
            Material.user_id == user_id,
        ).update({"account_id": target_account_id}, synchronize_session=False)

        session_ids = [
            sid
            for (sid,) in self.db.query(ChatSession.id).filter(ChatSession.user_id == user_id).all()
        ]
        counts["chat_sessions"] = self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
        ).update({"account_id": target_account_id, "ov_session_id": None}, synchronize_session=False)
        counts["ov_sessions_reset"] = len(session_ids)

        if session_ids:
            counts["chat_messages"] = self.db.query(ChatMessage).filter(
                ChatMessage.session_id.in_(session_ids),
            ).update({"account_id": target_account_id}, synchronize_session=False)
        else:
            counts["chat_messages"] = 0

        counts["session_drafts"] = self.db.query(SessionDraft).filter(
            SessionDraft.user_id == user_id,
        ).update({"account_id": target_account_id}, synchronize_session=False)

        counts["generated_documents"] = self.db.query(GeneratedDocument).filter(
            GeneratedDocument.user_id == user_id,
        ).update({"account_id": target_account_id}, synchronize_session=False)

        counts["user_preferences"] = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
        ).update({"account_id": target_account_id}, synchronize_session=False)

        counts["writing_habits"] = self.db.query(WritingHabit).filter(
            WritingHabit.user_id == user_id,
        ).update({"account_id": target_account_id}, synchronize_session=False)

    def _rebind_user_roles(
        self,
        rbac: RBACService,
        user: User,
        target_account_id: int,
        existing_role_codes: list[str],
    ) -> None:
        rbac.ensure_account_system_roles(target_account_id)
        mapped_codes: list[str] = []
        for code in existing_role_codes:
            role = rbac.get_role_by_code(target_account_id, code)
            if role is not None and role.status == "active":
                mapped_codes.append(code)
        if not mapped_codes:
            mapped_codes = [ROLE_WRITER]
        rbac.set_user_roles(user, mapped_codes)

    def _rebuild_account_resources(
        self,
        *,
        counts: dict[str, int],
        warnings: list[str],
        user_id: int,
        old_account_id: int,
        new_account_id: int,
    ) -> None:
        sync_service = AccountResourceSyncService(self.db)
        try:
            counts.update(sync_service.rebuild_accounts([old_account_id, new_account_id]))
        except Exception as exc:
            collect_side_effect_warning(
                warnings,
                operation="accounts.rebind_user.resource_rebuild",
                public_message="账户级知识资源重建未完成",
                error=exc,
                user_id=user_id,
                old_account_id=old_account_id,
                new_account_id=new_account_id,
            )
