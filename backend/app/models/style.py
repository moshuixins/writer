from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint, Index
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class WritingHabit(Base):
    __tablename__ = "writing_habits"
    __table_args__ = (
        Index("ix_habits_account_type", "account_id", "habit_type"),
        Index("ix_habits_user_type", "user_id", "habit_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    habit_type = Column(String(50), nullable=False)
    doc_type = Column(String(50))
    description = Column(Text, nullable=False)
    frequency = Column(Integer, default=1)
    last_seen = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)


class StyleProfile(Base):
    __tablename__ = "style_profiles"
    __table_args__ = (
        UniqueConstraint("account_id", "doc_type", "feature_name", name="uq_account_style_doc_feature"),
        Index("ix_style_profiles_account_doctype", "account_id", "doc_type"),
        Index("ix_style_profiles_doctype", "doc_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    doc_type = Column(String(50), nullable=False)
    feature_name = Column(String(100), nullable=False)
    feature_value = Column(JSON, nullable=False)
    sample_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
