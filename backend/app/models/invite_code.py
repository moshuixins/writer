from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class InviteCode(Base):
    __tablename__ = "account_invite_codes"
    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_invite_code_hash"),
        Index("ix_invite_account_status", "account_id", "status"),
        Index("ix_invite_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    status = Column(String(16), default="active", nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
