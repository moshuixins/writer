from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("uq_roles_account_code", "account_id", "code", unique=True),
        Index("ix_roles_account_status", "account_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    code = Column(String(64), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="active", nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)