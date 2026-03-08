from __future__ import annotations

from typing import Any

from app.errors import AppError, logger
from app.serializers import (
    serialize_chat_chunk_sse,
    serialize_chat_done_sse,
    serialize_chat_error_sse,
    serialize_chat_final_sse,
    serialize_chat_workflow_sse,
)
from app.services.background_executor import chat_stream_executor
from app.services.chat_turn_service import ChatTurnService, PreparedChatTurn
from app.services.writing_service import WritingService
from app.side_effects import new_error_id


class ChatStreamService:
    def __init__(
        self,
        *,
        turn_service: ChatTurnService,
        writing_service: WritingService,
    ):
        self.turn_service = turn_service
        self.writing_service = writing_service

    async def stream_turn(self, turn: PreparedChatTurn, user_message: str):
        full_reply = ""
        stream_ok = False
        pending_sync_warnings = list(turn.warnings)
        assistant_message = None

        try:
            if turn.is_first_turn:
                for event in self._guidance_start_events():
                    yield event
                chunks = self.writing_service.guidance_stream(user_message, turn.doc_type)
                completion_step = "生成写作引导"
            else:
                for event in self._generation_running_events():
                    yield event
                chunks, meta = await self.writing_service.generate_stream_with_meta(turn.session_id, user_message)
                for event in self._generation_ready_events(meta):
                    yield event
                completion_step = "生成回复"

            async for chunk in chat_stream_executor.iterate_sync_generator(chunks):
                full_reply += chunk
                yield serialize_chat_chunk_sse(chunk)

            yield serialize_chat_workflow_sse(completion_step, "done")
            stream_ok = True
        except Exception as exc:
            error_id = new_error_id()
            logger.exception(
                "Stream error. error_id=%s session=%s err=%s",
                error_id,
                turn.session_id,
                exc,
            )
            yield serialize_chat_error_sse(f"流式生成失败（错误ID: {error_id}）")

        if stream_ok and full_reply.strip():
            try:
                assistant_message = await self.turn_service.complete_turn(
                    turn,
                    user_message=user_message,
                    assistant_text=full_reply,
                    writing_service=self.writing_service,
                    warnings=pending_sync_warnings,
                    stream=True,
                )
            except AppError as exc:
                yield serialize_chat_error_sse(self._format_app_error(exc))
                if pending_sync_warnings:
                    yield serialize_chat_workflow_sse(
                        "同步外部上下文",
                        "error",
                        detail="；".join(pending_sync_warnings),
                    )
                yield serialize_chat_done_sse()
                return

        if pending_sync_warnings:
            yield serialize_chat_workflow_sse(
                "同步外部上下文",
                "error",
                detail="；".join(pending_sync_warnings),
            )

        if assistant_message is not None:
            yield serialize_chat_final_sse(assistant_message, warnings=pending_sync_warnings)

        yield serialize_chat_done_sse()

    def _guidance_start_events(self) -> list[str]:
        return [
            serialize_chat_workflow_sse("分析写作需求", "running"),
            serialize_chat_workflow_sse("分析写作需求", "done"),
            serialize_chat_workflow_sse("生成写作引导", "running"),
        ]

    def _generation_running_events(self) -> list[str]:
        return [
            serialize_chat_workflow_sse("分析请求意图", "running"),
            serialize_chat_workflow_sse("搜索素材", "running"),
            serialize_chat_workflow_sse("检索书籍知识", "running"),
            serialize_chat_workflow_sse("融合书籍风格规则", "running"),
        ]

    def _generation_ready_events(self, meta: dict[str, Any]) -> list[str]:
        return [
            serialize_chat_workflow_sse(
                "搜索素材",
                "done",
                detail=f"命中 {meta.get('reference_count', 0)} 条素材",
            ),
            serialize_chat_workflow_sse(
                "检索书籍知识",
                "done",
                detail=f"命中 {meta.get('book_reference_count', 0)} 条书籍参考",
            ),
            serialize_chat_workflow_sse(
                "融合书籍风格规则",
                "done",
                detail=f"命中 {meta.get('book_rule_count', 0)} 条规则",
            ),
            serialize_chat_workflow_sse("分析请求意图", "done"),
            serialize_chat_workflow_sse("生成回复", "running"),
        ]

    @staticmethod
    def _format_app_error(exc: AppError) -> str:
        if exc.error_id:
            return f"{exc.message}（错误ID: {exc.error_id}）"
        return exc.message
