from sqlalchemy.orm import Session
from app.models.preference import UserPreference


class MemoryService:
    """长期记忆服务：管理用户显式偏好（隐式记忆由 OpenViking 自动提取）"""

    def __init__(self, db: Session):
        self.db = db

    def set_preference(self, user_id: int, key: str, value: str, source: str = "explicit"):
        """设置用户偏好"""
        existing = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
            UserPreference.pref_key == key,
        ).first()

        if existing:
            existing.pref_value = value
            existing.source = source
        else:
            pref = UserPreference(
                user_id=user_id, pref_key=key,
                pref_value=value, source=source, confidence=1.0,
            )
            self.db.add(pref)
        self.db.commit()

    def get_preferences(self, user_id: int) -> dict:
        """获取用户所有偏好"""
        prefs = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
        ).all()
        return {p.pref_key: p.pref_value for p in prefs}

    def get_user_context(self, user_id: int) -> str:
        """构建显式偏好上下文（隐式记忆由 ContextBridge 从 OpenViking 获取）"""
        prefs = self.get_preferences(user_id)
        if not prefs:
            return ""
        pref_lines = [f"- {k}: {v}" for k, v in prefs.items()]
        return "用户偏好：\n" + "\n".join(pref_lines)
