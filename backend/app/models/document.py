from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    __table_args__ = (
        Index("ix_gendocs_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500))
    doc_type = Column(String(50))
    content_json = Column(JSON)
    content_text = Column(Text)
    docx_file_path = Column(String(1000))
    version = Column(Integer, default=1)
    parent_doc_id = Column(Integer, ForeignKey("generated_documents.id"))
    created_at = Column(DateTime, default=_utcnow)
