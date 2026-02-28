from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        Index("ix_materials_user_doctype", "user_id", "doc_type"),
        Index("ix_materials_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    original_filename = Column(String(500))
    file_path = Column(String(1000))
    content_text = Column(Text)
    doc_type = Column(String(50), index=True)
    summary = Column(Text)
    keywords = Column(JSON)
    metadata_ = Column("metadata", JSON)
    char_count = Column(Integer)
    is_reference = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
