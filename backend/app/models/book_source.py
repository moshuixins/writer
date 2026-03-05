from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BookSource(Base):
    __tablename__ = "book_sources"
    __table_args__ = (
        Index("uq_book_sources_account_source_hash", "account_id", "source_hash", unique=True),
        Index("ix_book_sources_account_updated_at", "account_id", "updated_at"),
        Index("ix_book_sources_status", "status"),
        Index("ix_book_sources_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    source_name = Column(String(500), nullable=False)
    source_path = Column(String(1200), nullable=False)
    source_hash = Column(String(64), nullable=False)
    file_ext = Column(String(16), nullable=False)
    file_size = Column(Integer, default=0)
    status = Column(String(20), default="pending", nullable=False)
    doc_type = Column(String(50), nullable=False)
    summary = Column(Text, default="")
    keywords = Column(JSON, default=list)
    chunk_count = Column(Integer, default=0)
    ocr_used = Column(Boolean, default=False)
    error_message = Column(Text, default="")
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
