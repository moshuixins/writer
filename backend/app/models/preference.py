from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "pref_key", name="uq_user_pref_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pref_key = Column(String(100), nullable=False)
    pref_value = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    source = Column(String(50))
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
