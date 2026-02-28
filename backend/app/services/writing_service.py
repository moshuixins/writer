from typing import Generator
from sqlalchemy.orm import Session
from app.services.llm_service import LLMService
from app.services.context_bridge import ContextBridge
from app.services.style_analyzer import StyleAnalyzer
from app.models.chat import ChatSession, ChatMessage
from app.prompts.writing import (
    WRITING_GUIDANCE_PROMPT,
    WRITING_GENERATE_PROMPT,
    WRITING_EDIT_PROMPT,
    WRITING_REVIEW_PROMPT,
)
from app.prompts.validators import parse_json_response
from app.prompts.doc_type_guides import get_doc_type_guide


class WritingService:
    """写作服务：引导、生成、编辑"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()
        self.ctx_bridge = ContextBridge()
        self.style = StyleAnalyzer(db)

    def create_session(self, user_id: int, title: str, doc_type: str = None) -> ChatSession:
        """创建写作会话"""
        session = ChatSession(
            user_id=user_id, title=title, doc_type=doc_type,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        """添加对话消息"""
        msg = ChatMessage(
            session_id=session_id, role=role, content=content,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_guidance(self, request: str, doc_type: str) -> str:
        """分析写作需求，返回所需材料清单"""
        prompt = WRITING_GUIDANCE_PROMPT.format(
            request=request, doc_type=doc_type,
        )
        return self.llm.invoke(prompt)

    def _build_search_query(self, user_data: str, doc_type: str) -> str:
        """从用户素材中提取关键信息构建检索查询，而非简单截断"""
        # 提取第一段作为核心意图（通常包含主题和目的）
        paragraphs = [p.strip() for p in user_data.split("\n") if p.strip()]
        first_para = paragraphs[0] if paragraphs else user_data[:200]
        # 拼接文种，提高检索相关性
        return f"{doc_type} {first_para[:150]}"

    async def generate(self, session_id: int, user_data: str, user_prefs: str = "") -> str:
        """生成公文内容"""
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
        ).first()
        doc_type = session.doc_type or "公文"

        # 获取文种写作规范
        doc_type_guide = get_doc_type_guide(doc_type)

        # 构建语义检索查询
        search_query = self._build_search_query(user_data, doc_type)

        # RAG检索参考素材（通过 OpenViking 层级检索）
        try:
            refs = await self.ctx_bridge.search_materials(
                search_query, doc_type=doc_type, top_k=5,
            )
            ref_text = "\n---\n".join(r["text"] for r in refs) if refs else "暂无参考范文"
        except Exception:
            ref_text = "暂无参考范文"

        # 获取 OpenViking 记忆上下文
        memory_context = ""
        try:
            memory_context = await self.ctx_bridge.get_memory_context(search_query)
        except Exception:
            pass

        # 获取风格指南
        style_guide = self.style.get_style_guidelines(doc_type)

        # 合并偏好：显式偏好 + OpenViking 隐式记忆
        combined_prefs = user_prefs or "无特殊偏好"
        if memory_context:
            combined_prefs += f"\n\n从历史写作中学到的习惯：\n{memory_context}"

        prompt = WRITING_GENERATE_PROMPT.format(
            doc_type=doc_type,
            doc_type_guide=doc_type_guide,
            style_guidelines=style_guide,
            reference_examples=ref_text,
            user_preferences=combined_prefs,
            user_data=user_data,
        )
        return self.llm.invoke(prompt)

    def guidance_stream(self, request: str, doc_type: str) -> Generator[str, None, None]:
        """流式返回写作引导"""
        prompt = WRITING_GUIDANCE_PROMPT.format(request=request, doc_type=doc_type)
        yield from self.llm.stream(prompt)

    async def generate_stream(self, session_id: int, user_data: str, user_prefs: str = "") -> Generator[str, None, None]:
        """流式生成公文内容"""
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        doc_type = session.doc_type or "公文"

        doc_type_guide = get_doc_type_guide(doc_type)
        search_query = self._build_search_query(user_data, doc_type)

        try:
            refs = await self.ctx_bridge.search_materials(search_query, doc_type=doc_type, top_k=5)
            ref_text = "\n---\n".join(r["text"] for r in refs) if refs else "暂无参考范文"
        except Exception:
            ref_text = "暂无参考范文"

        memory_context = ""
        try:
            memory_context = await self.ctx_bridge.get_memory_context(search_query)
        except Exception:
            pass

        style_guide = self.style.get_style_guidelines(doc_type)
        combined_prefs = user_prefs or "无特殊偏好"
        if memory_context:
            combined_prefs += f"\n\n从历史写作中学到的习惯：\n{memory_context}"

        prompt = WRITING_GENERATE_PROMPT.format(
            doc_type=doc_type, doc_type_guide=doc_type_guide,
            style_guidelines=style_guide, reference_examples=ref_text,
            user_preferences=combined_prefs, user_data=user_data,
        )
        return self.llm.stream(prompt)

    def edit(self, current_content: str, edit_request: str, doc_type: str = "公文") -> str:
        """根据用户要求修改公文"""
        prompt = WRITING_EDIT_PROMPT.format(
            current_content=current_content,
            edit_request=edit_request,
            doc_type=doc_type,
        )
        return self.llm.invoke(prompt)

    def review(self, content: str, doc_type: str = "公文") -> dict:
        """对生成的公文进行质量自检"""
        prompt = WRITING_REVIEW_PROMPT.format(
            content=content,
            doc_type=doc_type,
        )
        raw = self.llm.invoke(prompt)
        result = parse_json_response(raw)
        if result and isinstance(result, dict):
            return result
        return {"score": 0, "issues": [], "summary": "自检服务暂时不可用"}

    def get_session_messages(self, session_id: int) -> list[ChatMessage]:
        """获取会话的所有消息"""
        return self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
        ).order_by(ChatMessage.created_at).all()

    def get_sessions(self, user_id: int) -> list[ChatSession]:
        """获取用户的所有会话"""
        return self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
        ).order_by(ChatSession.created_at.desc()).all()
