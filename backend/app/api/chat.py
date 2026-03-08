from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.errors import AppError, logger
from app.side_effects import collect_side_effect_warning, new_error_id
from app.models.user import User
from app.prompts.doc_types_catalog import OTHER_DOC_TYPE
from app.prompts.validators import ensure_canonical_doc_type
from app.schemas.chat import (
    ChatMessageListResponse,
    ChatReplyResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionWithWarningsResponse,
    ReviewResponse,
    SessionDraftResponse,
)
from app.schemas.common import MessageResponse
from app.serializers import (
    serialize_chat_message,
    serialize_chat_reply,
    serialize_chat_session,
    serialize_collection_response,
    serialize_review_response,
    serialize_draft_response,
    serialize_message_response,
)
from app.services.chat_stream_service import ChatStreamService
from app.services.chat_turn_service import ChatTurnService
from app.services.context_bridge import ContextBridge
from app.services.draft_service import DraftService
from app.services.writing_service import WritingService

router = APIRouter()
ctx_bridge = ContextBridge()

CHAT_STREAM_RESPONSE = {
    200: {
        "description": "SSE stream of workflow, chunk, error, and final events.",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": 'data: {"event":"workflow","step":"分析请求意图","status":"running"}\n\ndata: [DONE]\n\n',
                },
            },
        },
    },
}

DEFAULT_BODY_JSON = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}


class CreateSessionRequest(BaseModel):
    title: str
    doc_type: str | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: int


class UpdateSessionRequest(BaseModel):
    title: str


class WriterDraftPayload(BaseModel):
    title: str = ""
    recipients: str = ""
    body_json: dict = Field(default_factory=lambda: DEFAULT_BODY_JSON.copy())
    signing_org: str = ""
    date: str = ""


class SaveDraftRequest(BaseModel):
    save_mode: Literal["auto", "manual"] = "manual"
    draft: WriterDraftPayload


class ReviewRequest(BaseModel):
    content: str
    doc_type: str = OTHER_DOC_TYPE


@router.post("/sessions", response_model=ChatSessionWithWarningsResponse)
async def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    canonical_doc_type = None
    if req.doc_type:
        try:
            canonical_doc_type = ensure_canonical_doc_type(req.doc_type)
        except ValueError:
            raise HTTPException(400, "doc_type 非法，必须为规范文种")

    svc = WritingService(db, account_id=current_user.account_id)
    warnings: list[str] = []
    try:
        session = svc.create_session(
            user_id=current_user.id,
            title=req.title,
            doc_type=canonical_doc_type,
            commit=False,
        )
        try:
            ov_session = await ctx_bridge.create_session()
            session.ov_session_id = ov_session.get("session_id", "")
        except Exception as e:
            collect_side_effect_warning(
                warnings,
                operation="chat.create_session.sync",
                public_message="外部会话上下文未创建",
                error=e,
                user_id=current_user.id,
                account_id=current_user.account_id,
            )
        db.commit()
        db.refresh(session)
    except Exception:
        db.rollback()
        raise

    return serialize_chat_session(session, warnings=warnings)


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: int,
    req: UpdateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    from app.models.chat import ChatSession

    title = (req.title or "").strip()
    if not title:
        raise HTTPException(400, "标题不能为空")

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    session.title = title
    db.commit()
    db.refresh(session)
    return serialize_chat_session(session)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:read")),
):
    svc = WritingService(db, account_id=current_user.account_id)
    sessions = svc.get_sessions(user_id=current_user.id)
    items = [serialize_chat_session(session) for session in sessions]
    return serialize_collection_response(items, total=len(items))


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:read")),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db, account_id=current_user.account_id)
    msgs = svc.get_session_messages(session_id)
    items = [serialize_chat_message(message) for message in msgs]
    return serialize_collection_response(items, total=len(items))


@router.get("/sessions/{session_id}/draft", response_model=SessionDraftResponse)
def get_session_draft(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:read")),
):
    draft_service = DraftService(db, account_id=current_user.account_id)
    payload = draft_service.get_or_default_draft(
        user_id=current_user.id,
        session_id=session_id,
    )
    return payload


@router.put("/sessions/{session_id}/draft", response_model=SessionDraftResponse)
def save_session_draft(
    session_id: int,
    req: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    draft_service = DraftService(db, account_id=current_user.account_id)
    try:
        row, normalized_draft = draft_service.upsert_draft(
            user_id=current_user.id,
            session_id=session_id,
            draft=req.draft.model_dump(),
            save_mode=req.save_mode,
            commit=False,
        )
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return serialize_draft_response(
        session_id=session_id,
        draft=normalized_draft,
        exists=True,
        updated_at=row.updated_at,
        save_mode=req.save_mode,
    )


@router.post("/send", response_model=ChatReplyResponse, response_model_exclude_none=True)
async def send_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    svc = WritingService(db, account_id=current_user.account_id)
    turn_service = ChatTurnService(
        db,
        account_id=current_user.account_id,
        user_id=current_user.id,
        context_bridge=ctx_bridge,
    )
    turn = await turn_service.prepare_turn(
        req.session_id,
        req.message,
        writing_service=svc,
        stream=False,
    )
    reply = await turn_service.generate_reply(turn, req.message, writing_service=svc)
    await turn_service.complete_turn(
        turn,
        user_message=req.message,
        assistant_text=reply,
        writing_service=svc,
        warnings=turn.warnings,
        stream=False,
    )
    return serialize_chat_reply(reply, warnings=turn.warnings)


@router.post("/send-stream", response_class=StreamingResponse, responses=CHAT_STREAM_RESPONSE)
async def send_message_stream(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    svc = WritingService(db, account_id=current_user.account_id)
    turn_service = ChatTurnService(
        db,
        account_id=current_user.account_id,
        user_id=current_user.id,
        context_bridge=ctx_bridge,
    )
    turn = await turn_service.prepare_turn(
        req.session_id,
        req.message,
        writing_service=svc,
        stream=True,
    )
    stream_service = ChatStreamService(turn_service=turn_service, writing_service=svc)
    return StreamingResponse(
        stream_service.stream_turn(turn, req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    from app.models.chat import ChatMessage, ChatSession, SessionDraft
    from app.models.document import GeneratedDocument

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.account_id == current_user.account_id,
        GeneratedDocument.session_id == session_id,
    ).all()
    doc_paths = [doc.docx_file_path for doc in docs if doc.docx_file_path]

    try:
        db.query(ChatMessage).filter(
            ChatMessage.account_id == current_user.account_id,
            ChatMessage.session_id == session_id,
        ).delete(synchronize_session=False)
        db.query(SessionDraft).filter(
            SessionDraft.account_id == current_user.account_id,
            SessionDraft.session_id == session_id,
        ).delete(synchronize_session=False)
        db.query(GeneratedDocument).filter(
            GeneratedDocument.account_id == current_user.account_id,
            GeneratedDocument.session_id == session_id,
        ).delete(synchronize_session=False)
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        error_id = new_error_id()
        logger.exception(
            "Delete session failed. error_id=%s session_id=%s user_id=%s err=%s",
            error_id,
            session_id,
            current_user.id,
            e,
        )
        raise AppError(
            "删除会话失败，请稍后重试",
            detail=str(e),
            error_id=error_id,
        ) from e

    for doc_path in doc_paths:
        try:
            path_obj = Path(doc_path)
            if path_obj.exists():
                path_obj.unlink()
        except Exception:
            logger.warning("Failed to cleanup docx file: %s", doc_path)

    return serialize_message_response("会话已删除")


@router.post("/sessions/{session_id}/finish", response_model=MessageResponse)
async def finish_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    session.status = "finished"
    db.commit()
    return serialize_message_response("会话已结束")

@router.post("/review", response_model=ReviewResponse)
def review_document(
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    try:
        canonical_doc_type = ensure_canonical_doc_type(req.doc_type)
    except ValueError:
        raise HTTPException(400, "doc_type 非法，必须为规范文种")
    svc = WritingService(db, account_id=current_user.account_id)
    return serialize_review_response(svc.review(req.content, canonical_doc_type))
