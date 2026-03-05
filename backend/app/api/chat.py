from __future__ import annotations

import asyncio
import json
import threading
import uuid
from pathlib import Path
from typing import Generator, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.errors import logger
from app.models.user import User
from app.prompts.doc_types_catalog import OTHER_DOC_TYPE
from app.prompts.validators import ensure_canonical_doc_type
from app.services.context_bridge import ContextBridge
from app.services.draft_service import DraftService
from app.services.writing_service import WritingService
from app.timezone import to_shanghai_iso

router = APIRouter()
ctx_bridge = ContextBridge()

DEFAULT_BODY_JSON = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}


def _new_error_id() -> str:
    return uuid.uuid4().hex[:12]


async def _iterate_sync_generator(gen: Generator[str, None, None]):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, str | Exception | None]] = asyncio.Queue()

    def worker() -> None:
        try:
            for item in gen:
                loop.call_soon_threadsafe(queue.put_nowait, ("chunk", item))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", e))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    threading.Thread(target=worker, daemon=True).start()

    while True:
        kind, payload = await queue.get()
        if kind == "chunk":
            yield str(payload or "")
            continue
        if kind == "error":
            raise payload if isinstance(payload, Exception) else RuntimeError("stream failed")
        break


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


@router.post("/sessions")
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
    session = svc.create_session(
        user_id=current_user.id,
        title=req.title,
        doc_type=canonical_doc_type,
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
    return {
        "id": session.id,
        "title": session.title,
        "doc_type": session.doc_type,
        "status": session.status,
        "created_at": to_shanghai_iso(session.created_at),
    }


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:read")),
):
    svc = WritingService(db, account_id=current_user.account_id)
    sessions = svc.get_sessions(user_id=current_user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "doc_type": s.doc_type,
            "status": s.status,
            "created_at": to_shanghai_iso(s.created_at),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
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
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": to_shanghai_iso(m.created_at),
        }
        for m in msgs
    ]


@router.get("/sessions/{session_id}/draft")
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


@router.put("/sessions/{session_id}/draft")
def save_session_draft(
    session_id: int,
    req: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    draft_service = DraftService(db, account_id=current_user.account_id)
    row, normalized_draft = draft_service.upsert_draft(
        user_id=current_user.id,
        session_id=session_id,
        draft=req.draft.model_dump(),
        save_mode=req.save_mode,
    )
    return {
        "exists": True,
        "session_id": session_id,
        "updated_at": to_shanghai_iso(row.updated_at),
        "save_mode": req.save_mode,
        "draft": normalized_draft,
    }


@router.post("/send")
async def send_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db, account_id=current_user.account_id)

    svc.add_message(req.session_id, "user", req.message)

    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    msgs = svc.get_session_messages(req.session_id)
    if len(msgs) <= 1:
        doc_type = session.doc_type or OTHER_DOC_TYPE
        reply = await asyncio.to_thread(svc.get_guidance, req.message, doc_type)
    else:
        reply = await svc.generate(req.session_id, req.message)

    svc.add_message(req.session_id, "assistant", reply)

    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "assistant", reply)
        except Exception:
            pass

    try:
        await ctx_bridge.add_memory_note(
            account_id=current_user.account_id,
            session_id=req.session_id,
            user_text=req.message,
            assistant_text=reply,
        )
    except Exception as e:
        logger.warning("Auto memory note skipped: %s", e)

    return {"reply": reply}


@router.post("/send-stream")
async def send_message_stream(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("chat:write")),
):
    from app.models.chat import ChatSession

    session = db.query(ChatSession).filter(
        ChatSession.account_id == current_user.account_id,
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db, account_id=current_user.account_id)
    svc.add_message(req.session_id, "user", req.message)

    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    msgs = svc.get_session_messages(req.session_id)
    is_first = len(msgs) <= 1
    doc_type = session.doc_type or OTHER_DOC_TYPE

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
                async for item in emit("workflow", step="检索书籍知识", status="running"):
                    yield item
                async for item in emit("workflow", step="融合书籍风格规则", status="running"):
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
                    step="检索书籍知识",
                    status="done",
                    detail=f"命中 {meta.get('book_reference_count', 0)} 条书籍参考",
                ):
                    yield item
                async for item in emit(
                    "workflow",
                    step="融合书籍风格规则",
                    status="done",
                    detail=f"命中 {meta.get('book_rule_count', 0)} 条规则",
                ):
                    yield item
                async for item in emit("workflow", step="分析请求意图", status="done"):
                    yield item
                async for item in emit("workflow", step="生成回复", status="running"):
                    yield item

            async for chunk in _iterate_sync_generator(chunks):
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
            error_id = _new_error_id()
            logger.exception("Stream error. error_id=%s session=%s err=%s", error_id, req.session_id, e)
            err = json.dumps({"error": f"流式生成失败（错误ID: {error_id}）"}, ensure_ascii=False)
            yield f"data: {err}\n\n"

        svc.add_message(req.session_id, "assistant", full_reply)

        if ov_sid:
            try:
                await ctx_bridge.add_message(ov_sid, "assistant", full_reply)
            except Exception:
                pass

        try:
            await ctx_bridge.add_memory_note(
                account_id=current_user.account_id,
                session_id=req.session_id,
                user_text=req.message,
                assistant_text=full_reply,
            )
        except Exception as e:
            logger.warning("Auto memory note skipped: %s", e)

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

    try:
        from app.models.chat import ChatMessage

        last_user = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.account_id == current_user.account_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_assistant = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.account_id == current_user.account_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        await ctx_bridge.add_memory_note(
            account_id=current_user.account_id,
            session_id=session_id,
            user_text=(last_user.content if last_user else ""),
            assistant_text=(last_assistant.content if last_assistant else ""),
        )
    except Exception as e:
        logger.warning("Account memory note skipped: %s", e)

    return {"message": "会话已结束，记忆已提交"}


@router.post("/review")
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
    return svc.review(req.content, canonical_doc_type)
