from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.errors import logger
from app.models.user import User
from app.services.context_bridge import ContextBridge
from app.services.draft_service import DraftService
from app.services.writing_service import WritingService

router = APIRouter()
ctx_bridge = ContextBridge()


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
    doc_type: str = "公文"


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = WritingService(db)
    session = svc.create_session(
        user_id=current_user.id,
        title=req.title,
        doc_type=req.doc_type,
    )

    try:
        ov_session = await ctx_bridge.create_session()
        session.ov_session_id = ov_session.get("session_id", "")
        db.commit()
    except Exception:
        pass

    return {
        "id": session.id,
        "title": session.title,
        "doc_type": session.doc_type,
    }


@router.put("/sessions/{session_id}")
def update_session(
    session_id: int,
    req: UpdateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatSession

    title = (req.title or "").strip()
    if not title:
        raise HTTPException(400, "标题不能为空")

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    session.title = title
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "doc_type": session.doc_type,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = WritingService(db)
    sessions = svc.get_sessions(user_id=current_user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "doc_type": s.doc_type,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db)
    msgs = svc.get_session_messages(session_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.get("/sessions/{session_id}/draft")
def get_session_draft(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft_service = DraftService(db)
    payload = draft_service.get_or_default_draft(
        user_id=current_user.id,
        session_id=session_id,
    )
    return payload


@router.put("/sessions/{session_id}/draft")
def save_session_draft(
    session_id: int,
    req: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft_service = DraftService(db)
    row, normalized_draft = draft_service.upsert_draft(
        user_id=current_user.id,
        session_id=session_id,
        draft=req.draft.model_dump(),
        save_mode=req.save_mode,
    )
    return {
        "exists": True,
        "session_id": session_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "save_mode": req.save_mode,
        "draft": normalized_draft,
    }


@router.post("/send")
async def send_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db)

    svc.add_message(req.session_id, "user", req.message)

    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    msgs = svc.get_session_messages(req.session_id)
    if len(msgs) <= 1:
        doc_type = session.doc_type or "公文"
        reply = svc.get_guidance(req.message, doc_type)
    else:
        reply = await svc.generate(req.session_id, req.message)

    svc.add_message(req.session_id, "assistant", reply)

    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "assistant", reply)
        except Exception:
            pass

    return {"reply": reply}


@router.post("/send-stream")
async def send_message_stream(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db)
    svc.add_message(req.session_id, "user", req.message)

    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    msgs = svc.get_session_messages(req.session_id)
    is_first = len(msgs) <= 1
    doc_type = session.doc_type or "公文"

    async def event_generator():
        async def emit(event: str, **payload):
            data = json.dumps({"event": event, **payload}, ensure_ascii=False)
            yield f"data: {data}\n\n"

        full_reply = ""
        try:
            if is_first:
                async for item in emit("workflow", step="分析写作需求", status="running"):
                    yield item
                chunks = svc.guidance_stream(req.message, doc_type)
                async for item in emit("workflow", step="分析写作需求", status="done"):
                    yield item
                async for item in emit("workflow", step="生成写作引导", status="running"):
                    yield item
            else:
                async for item in emit("workflow", step="分析请求意图", status="running"):
                    yield item
                async for item in emit("workflow", step="搜索素材", status="running"):
                    yield item

                chunks, meta = await svc.generate_stream_with_meta(req.session_id, req.message)

                async for item in emit(
                    "workflow",
                    step="搜索素材",
                    status="done",
                    detail=f"命中 {meta.get('reference_count', 0)} 条素材",
                ):
                    yield item
                async for item in emit(
                    "workflow",
                    step="加载历史记忆",
                    status="done",
                    detail=f"命中 {meta.get('memory_count', 0)} 条记忆",
                ):
                    yield item
                async for item in emit("workflow", step="分析请求意图", status="done"):
                    yield item
                async for item in emit("workflow", step="生成回复", status="running"):
                    yield item

            for chunk in chunks:
                full_reply += chunk
                data = json.dumps({"chunk": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            if is_first:
                async for item in emit("workflow", step="生成写作引导", status="done"):
                    yield item
            else:
                async for item in emit("workflow", step="生成回复", status="done"):
                    yield item
        except Exception as e:
            logger.error("Stream error: %s", e)
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

        svc.add_message(req.session_id, "assistant", full_reply)

        if ov_sid:
            try:
                await ctx_bridge.add_message(ov_sid, "assistant", full_reply)
            except Exception:
                pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatMessage, ChatSession, SessionDraft
    from app.models.document import GeneratedDocument

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    if session.ov_session_id:
        try:
            await ctx_bridge.commit_session(session.ov_session_id)
            logger.info("OV session committed: %s", session.ov_session_id)
        except Exception as e:
            logger.warning("OV commit failed: %s", e)

    docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.session_id == session_id,
        GeneratedDocument.user_id == current_user.id,
    ).all()
    doc_paths = [doc.docx_file_path for doc in docs if doc.docx_file_path]

    try:
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
        db.query(SessionDraft).filter(
            SessionDraft.session_id == session_id,
            SessionDraft.user_id == current_user.id,
        ).delete(synchronize_session=False)
        db.query(GeneratedDocument).filter(
            GeneratedDocument.session_id == session_id,
            GeneratedDocument.user_id == current_user.id,
        ).delete(synchronize_session=False)
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(
            "Delete session failed, session_id=%s user_id=%s err=%s",
            session_id,
            current_user.id,
            e,
        )
        raise HTTPException(500, "删除会话失败，请稍后重试")

    for doc_path in doc_paths:
        try:
            path_obj = Path(doc_path)
            if path_obj.exists():
                path_obj.unlink()
        except Exception:
            logger.warning("Failed to cleanup docx file: %s", doc_path)

    return {"message": "会话已删除"}


@router.post("/sessions/{session_id}/finish")
async def finish_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    session.status = "finished"
    db.commit()

    if session.ov_session_id:
        try:
            await ctx_bridge.commit_session(session.ov_session_id)
            logger.info("OV session committed: %s", session.ov_session_id)
        except Exception as e:
            logger.warning("OV commit failed: %s", e)

    return {"message": "会话已结束，记忆已提交"}


@router.post("/review")
def review_document(
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = WritingService(db)
    return svc.review(req.content, req.doc_type)
