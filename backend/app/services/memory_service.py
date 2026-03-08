from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.preference import UserPreference


class MemoryService:
    """Manage explicit user preferences."""

    def __init__(self, db: Session, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)

    def set_preference(
        self,
        user_id: int,
        key: str,
        value: str,
        source: str = "explicit",
        *,
        commit: bool = True,
    ):
        existing = self.db.query(UserPreference).filter(
            UserPreference.account_id == self.account_id,
            UserPreference.user_id == user_id,
            UserPreference.pref_key == key,
        ).first()

        if existing:
            existing.pref_value = value
            existing.source = source
        else:
            pref = UserPreference(
                account_id=self.account_id,
                user_id=user_id,
                pref_key=key,
                pref_value=value,
                source=source,
                confidence=1.0,
            )
            self.db.add(pref)
        if commit:
            self.db.commit()
        else:
            self.db.flush()

    def get_preferences(self, user_id: int) -> dict:
        prefs = self.db.query(UserPreference).filter(
            UserPreference.account_id == self.account_id,
            UserPreference.user_id == user_id,
        ).all()
        return {p.pref_key: p.pref_value for p in prefs}

    def get_user_context(self, user_id: int) -> str:
        prefs = self.get_preferences(user_id)
        if not prefs:
            return ""
        pref_lines = [f"- {k}: {v}" for k, v in prefs.items()]
        return "用户偏好：\n" + "\n".join(pref_lines)
