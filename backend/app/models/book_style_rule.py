from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BookStyleRule(Base):
    __tablename__ = "book_style_rules"
    __table_args__ = (
        Index("ix_book_style_rules_account_doc_rule", "account_id", "doc_type", "rule_type"),
        Index("ix_book_style_rules_doc_type_rule_type", "doc_type", "rule_type"),
        Index("ix_book_style_rules_source_id", "source_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, default=1, index=True)
    source_id = Column(Integer, ForeignKey("book_sources.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(50), nullable=False)
    rule_type = Column(String(32), nullable=False)
    rule_text = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    origin_ref = Column(String(300), default="")
    created_at = Column(DateTime, default=_utcnow)
