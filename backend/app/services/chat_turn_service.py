from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.errors import AppError, logger
from app.models.chat import ChatMessage, ChatSession
from app.prompts.doc_types_catalog import OTHER_DOC_TYPE
from app.services.context_bridge import ContextBridge
from app.services.writing_service import WritingService
from app.side_effects import collect_side_effect_warning, new_error_id


@dataclass(slots=True)
class PreparedChatTurn:
    session_id: int
    ov_session_id: str | None
    doc_type: str
    is_first_turn: bool
    warnings: list[str]


class ChatTurnService:
    def __init__(
        self,
        db: Session,
        *,
        account_id: int,
        user_id: int,
        context_bridge: ContextBridge,
    ):
        self.db = db
        self.account_id = int(account_id or 1)
        self.user_id = int(user_id or 0)
        self.context_bridge = context_bridge

    def get_owned_session(self, session_id: int) -> ChatSession:
        session = self.db.query(ChatSession).filter(
            ChatSession.account_id == self.account_id,
            ChatSession.id == session_id,
            ChatSession.user_id == self.user_id,
        ).first()
        if not session:
            raise HTTPException(404, "会话不存在")
        return session

    async def prepare_turn(
        self,
        session_id: int,
        user_message: str,
        *,
        writing_service: WritingService,
        stream: bool = False,
    ) -> PreparedChatTurn:
        session = self.get_owned_session(session_id)
        self._persist_message(
            session_id=session_id,
            role="user",
            content=user_message,
            writing_service=writing_service,
            public_message="保存用户消息失败，请稍后重试",
        )

        warnings: list[str] = []
        if session.ov_session_id:
            await self._sync_external_message(
                ov_session_id=session.ov_session_id,
                role="user",
                content=user_message,
                session_id=session_id,
                warnings=warnings,
                stream=stream,
                operation_name="user_message_sync",
                public_message="用户消息未同步到外部上下文",
            )

        is_first_turn = len(writing_service.get_session_messages(session_id)) <= 1
        return PreparedChatTurn(
            session_id=int(session_id),
            ov_session_id=str(session.ov_session_id or "") or None,
            doc_type=session.doc_type or OTHER_DOC_TYPE,
            is_first_turn=is_first_turn,
            warnings=warnings,
        )

    async def generate_reply(
        self,
        turn: PreparedChatTurn,
        user_message: str,
        *,
        writing_service: WritingService,
    ) -> str:
        if turn.is_first_turn:
            return await asyncio.to_thread(writing_service.get_guidance, user_message, turn.doc_type)
        return await writing_service.generate(turn.session_id, user_message)

    async def complete_turn(
        self,
        turn: PreparedChatTurn,
        *,
        user_message: str,
        assistant_text: str,
        writing_service: WritingService,
        warnings: list[str],
        stream: bool = False,
    ) -> ChatMessage:
        assistant_message = self._persist_message(
            session_id=turn.session_id,
            role="assistant",
            content=assistant_text,
            writing_service=writing_service,
            public_message="回复保存失败，请稍后重试",
        )
        await self._sync_assistant_turn(
            turn,
            user_message=user_message,
            assistant_text=assistant_text,
            warnings=warnings,
            stream=stream,
        )
        return assistant_message

    def _persist_message(
        self,
        *,
        session_id: int,
        role: str,
        content: str,
        writing_service: WritingService,
        public_message: str,
    ) -> ChatMessage:
        try:
            message = writing_service.add_message(session_id, role, content, commit=False)
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception as exc:
            self.db.rollback()
            error_id = new_error_id()
            logger.exception(
                "Persist chat message failed. error_id=%s session_id=%s role=%s user_id=%s err=%s",
                error_id,
                session_id,
                role,
                self.user_id,
                exc,
            )
            raise AppError(public_message, detail=str(exc), error_id=error_id) from exc

    async def _sync_assistant_turn(
        self,
        turn: PreparedChatTurn,
        *,
        user_message: str,
        assistant_text: str,
        warnings: list[str],
        stream: bool,
    ) -> None:
        if turn.ov_session_id:
            await self._sync_external_message(
                ov_session_id=turn.ov_session_id,
                role="assistant",
                content=assistant_text,
                session_id=turn.session_id,
                warnings=warnings,
                stream=stream,
                operation_name="assistant_message_sync",
                public_message="助手回复未同步到外部上下文",
            )

        try:
            await self.context_bridge.add_memory_note(
                account_id=self.account_id,
                session_id=turn.session_id,
                user_text=user_message,
                assistant_text=assistant_text,
            )
        except Exception as exc:
            collect_side_effect_warning(
                warnings,
                operation=self._operation_name("memory_note_sync", stream=stream),
                public_message="会话记忆未同步到外部上下文",
                error=exc,
                session_id=turn.session_id,
                user_id=self.user_id,
                account_id=self.account_id,
            )

    async def _sync_external_message(
        self,
        *,
        ov_session_id: str,
        role: str,
        content: str,
        session_id: int,
        warnings: list[str],
        stream: bool,
        operation_name: str,
        public_message: str,
    ) -> None:
        try:
            await self.context_bridge.add_message(ov_session_id, role, content)
        except Exception as exc:
            collect_side_effect_warning(
                warnings,
                operation=self._operation_name(operation_name, stream=stream),
                public_message=public_message,
                error=exc,
                session_id=session_id,
                user_id=self.user_id,
                account_id=self.account_id,
            )

    @staticmethod
    def _operation_name(operation_name: str, *, stream: bool) -> str:
        if stream:
            return f"chat.stream_{operation_name}"
        return f"chat.{operation_name}"
