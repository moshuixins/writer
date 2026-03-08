from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chat import ChatSession, SessionDraft
from app.serializers import serialize_draft_response
from app.services.editor_doc_parser import EditorDocParser


class DraftService:
    def __init__(self, db: Session, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)
        self.parser = EditorDocParser()

    def validate_session_owner(self, user_id: int, session_id: int) -> ChatSession:
        session = self.db.query(ChatSession).filter(
            ChatSession.account_id == self.account_id,
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        ).first()
        if not session:
            raise HTTPException(404, '会话不存在')
        return session

    def get_or_default_draft(self, user_id: int, session_id: int) -> dict[str, Any]:
        session = self.validate_session_owner(user_id=user_id, session_id=session_id)

        row = self.db.query(SessionDraft).filter(
            SessionDraft.account_id == self.account_id,
            SessionDraft.session_id == session_id,
            SessionDraft.user_id == user_id,
        ).first()

        if not row:
            return serialize_draft_response(
                session_id=session_id,
                draft=self.parser.default_draft(title=session.title or ''),
                exists=False,
                updated_at=None,
            )

        draft = self.parser.normalize_or_default(row.draft_json, title_fallback=session.title or '')
        return serialize_draft_response(
            session_id=session_id,
            draft=draft,
            exists=True,
            updated_at=row.updated_at,
        )

    def upsert_draft(
        self,
        *,
        user_id: int,
        session_id: int,
        draft: dict[str, Any],
        save_mode: str = 'manual',
        commit: bool = True,
    ) -> tuple[SessionDraft, dict[str, Any]]:
        del save_mode
        session = self.validate_session_owner(user_id=user_id, session_id=session_id)
        normalized = self.parser.normalize_draft(draft, title_fallback=session.title or '')
        content_text = self.parser.draft_to_plain_text(normalized)

        row = self.db.query(SessionDraft).filter(
            SessionDraft.account_id == self.account_id,
            SessionDraft.session_id == session_id,
            SessionDraft.user_id == user_id,
        ).first()

        if not row:
            row = SessionDraft(
                account_id=self.account_id,
                session_id=session_id,
                user_id=user_id,
                draft_json=normalized,
                content_text=content_text,
            )
            self.db.add(row)
        else:
            row.draft_json = normalized
            row.content_text = content_text

        self.db.flush()
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row, normalized
