from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BookImportTask(Base):
    __tablename__ = "book_import_tasks"
    __table_args__ = (
        Index("uq_book_import_tasks_task_id", "task_id", unique=True),
        Index("ix_book_import_tasks_account_status", "account_id", "status"),
        Index("ix_book_import_tasks_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    status = Column(String(20), default="pending", nullable=False)
    stage = Column(String(200), default="")
    message = Column(Text, default="")
    rebuild = Column(Boolean, default=False)
    total_files = Column(Integer, default=0)
    completed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    partial_files = Column(Integer, default=0)
    skipped_files = Column(Integer, default=0)
    running_file = Column(String(500), default="")
    total_chunks = Column(Integer, default=0)
    completed_chunks = Column(Integer, default=0)
    ocr_used_files = Column(Integer, default=0)
    ocr_pages = Column(Integer, default=0)
    file_results = Column(JSON, default=list)
    selected_files = Column(JSON, default=list)
    started_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    finished_at = Column(DateTime, nullable=True)