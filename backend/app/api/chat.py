from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.writing_service import WritingService
from app.services.context_bridge import ContextBridge
from app.errors import logger

router = APIRouter()
ctx_bridge = ContextBridge()


class CreateSessionRequest(BaseModel):
    title: str
    doc_type: str = None


class ChatRequest(BaseModel):
    message: str
    session_id: int


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建写作会话"""
    svc = WritingService(db)
    session = svc.create_session(
        user_id=current_user.id, title=req.title, doc_type=req.doc_type,
    )

    # 同步创建 OpenViking 会话
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


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表"""
    svc = WritingService(db)
    sessions = svc.get_sessions(user_id=current_user.id)
    return [
        {
            "id": s.id, "title": s.title,
            "doc_type": s.doc_type, "status": s.status,
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
    """获取会话消息历史"""
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
            "id": m.id, "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.post("/send")
async def send_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息并获取AI回复（HTTP方式）"""
    from app.models.chat import ChatSession
    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db)

    # 保存用户消息
    svc.add_message(req.session_id, "user", req.message)

    # 同步消息到 OpenViking
    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    # 判断是否是首条消息（需要引导）
    msgs = svc.get_session_messages(req.session_id)
    if len(msgs) <= 1:
        doc_type = session.doc_type or "公文"
        reply = svc.get_guidance(req.message, doc_type)
    else:
        reply = await svc.generate(
            req.session_id, req.message,
        )

    # 保存AI回复
    svc.add_message(req.session_id, "assistant", reply)

    # 同步AI回复到 OpenViking
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
    """流式发送消息，SSE 逐字返回AI回复"""
    from app.models.chat import ChatSession
    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    svc = WritingService(db)
    svc.add_message(req.session_id, "user", req.message)

    # 同步消息到 OpenViking
    ov_sid = getattr(session, "ov_session_id", None)
    if ov_sid:
        try:
            await ctx_bridge.add_message(ov_sid, "user", req.message)
        except Exception:
            pass

    # 判断是否首条消息
    msgs = svc.get_session_messages(req.session_id)
    is_first = len(msgs) <= 1
    doc_type = session.doc_type or "公文"

    async def event_generator():
        full_reply = ""
        try:
            if is_first:
                chunks = svc.guidance_stream(req.message, doc_type)
            else:
                chunks = await svc.generate_stream(req.session_id, req.message)

            for chunk in chunks:
                full_reply += chunk
                data = json.dumps({"chunk": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            logger.error("Stream error: %s", e)
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

        # 保存完整回复
        svc.add_message(req.session_id, "assistant", full_reply)

        # 同步到 OpenViking
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
    """删除会话及其消息"""
    from app.models.chat import ChatSession, ChatMessage
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    # 提交 OpenViking 记忆提取
    if session.ov_session_id:
        try:
            await ctx_bridge.commit_session(session.ov_session_id)
            logger.info("OV session committed: %s", session.ov_session_id)
        except Exception as e:
            logger.warning("OV commit failed: %s", e)

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "会话已删除"}


@router.post("/sessions/{session_id}/finish")
async def finish_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """结束会话，触发 OpenViking 记忆提取"""
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

    return {"message": "会话已结束，记忆已提取"}


class ReviewRequest(BaseModel):
    content: str
    doc_type: str = "公文"


@router.post("/review")
def review_document(
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """对公文内容进行质量自检"""
    svc = WritingService(db)
    return svc.review(req.content, req.doc_type)
