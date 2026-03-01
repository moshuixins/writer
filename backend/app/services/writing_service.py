from typing import Any, Generator

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.prompts.doc_type_guides import get_doc_type_guide
from app.prompts.validators import parse_json_response
from app.prompts.writing import (
    WRITING_EDIT_PROMPT,
    WRITING_GENERATE_PROMPT,
    WRITING_GUIDANCE_PROMPT,
    WRITING_REVIEW_PROMPT,
)
from app.services.context_bridge import ContextBridge
from app.services.llm_service import LLMService
from app.services.style_analyzer import StyleAnalyzer

PLAIN_TEXT_OUTPUT_REQUIREMENTS = """
## Output constraints (must follow)
1. Return plain, readable Chinese official-document content.
2. Do NOT output JSON.
3. Do NOT output Markdown code blocks.
4. Do NOT output schema/field names such as "title", "recipients", "body_sections", "attachments", "signing_org", "date".
5. If required facts are missing, keep placeholders like [具体日期] in text.
"""

MAX_CONTEXT_MESSAGES = 10
MAX_CONTEXT_MESSAGE_CHARS = 1200


class WritingService:
    """写作服务：引导、生成、编辑。"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()
        self.ctx_bridge = ContextBridge()
        self.style = StyleAnalyzer(db)

    def create_session(self, user_id: int, title: str, doc_type: str = None) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            title=title,
            doc_type=doc_type,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_guidance(self, request: str, doc_type: str) -> str:
        prompt = WRITING_GUIDANCE_PROMPT.format(
            request=request,
            doc_type=doc_type,
        )
        return self.llm.invoke(prompt)

    def _build_search_query(self, user_data: str, doc_type: str) -> str:
        """从用户输入中提取核心意图，构建检索查询。"""
        paragraphs = [p.strip() for p in (user_data or "").split("\n") if p.strip()]
        first_para = paragraphs[0] if paragraphs else (user_data or "")[:200]
        return f"{doc_type} {first_para[:150]}"

    def _build_session_context(self, session_id: int) -> str:
        """提取同会话近期消息，增强单会话上下文连续性。"""
        recent_messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(MAX_CONTEXT_MESSAGES)
            .all()
        )

        if not recent_messages:
            return ""

        lines: list[str] = []
        for msg in reversed(recent_messages):
            content = (msg.content or "").strip()
            if not content:
                continue
            if len(content) > MAX_CONTEXT_MESSAGE_CHARS:
                content = f"{content[:MAX_CONTEXT_MESSAGE_CHARS]}...(内容已截断)"
            role = "用户" if msg.role == "user" else "助手"
            lines.append(f"{role}：{content}")
        return "\n\n".join(lines)

    def _merge_user_data_with_context(self, session_id: int, user_data: str) -> str:
        """把当前请求和同会话上下文合并成生成输入。"""
        current_request = (user_data or "").strip()
        context = self._build_session_context(session_id)
        if not context:
            return current_request
        return f"【用户当前请求】\n{current_request}\n\n【同会话最近对话上下文】\n{context}"

    async def _prepare_generate_prompt(
        self,
        session_id: int,
        user_data: str,
        user_prefs: str = "",
    ) -> tuple[str, dict[str, Any]]:
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError("会话不存在")

        doc_type = session.doc_type or "公文"
        doc_type_guide = get_doc_type_guide(doc_type)
        search_query = self._build_search_query(user_data, doc_type)

        refs: list[dict[str, Any]] = []
        try:
            refs = await self.ctx_bridge.search_materials(
                search_query,
                doc_type=doc_type,
                top_k=5,
            )
        except Exception:
            refs = []

        ref_texts = [
            (item.get("text") or "").strip()
            for item in refs
            if (item.get("text") or "").strip()
        ]
        ref_text = "\n---\n".join(ref_texts) if ref_texts else "暂无参考范文"

        memory_context = ""
        try:
            memory_context = await self.ctx_bridge.get_memory_context(search_query)
        except Exception:
            memory_context = ""

        memory_count = len([line for line in memory_context.splitlines() if line.strip()]) if memory_context else 0
        style_guide = self.style.get_style_guidelines(doc_type)

        combined_prefs = user_prefs or "无特殊偏好"
        if memory_context:
            combined_prefs += f"\n\n从历史写作中学到的习惯：\n{memory_context}"

        prompt_user_data = self._merge_user_data_with_context(session_id, user_data)
        prompt = WRITING_GENERATE_PROMPT.format(
            doc_type=doc_type,
            doc_type_guide=doc_type_guide,
            style_guidelines=style_guide,
            reference_examples=ref_text,
            user_preferences=combined_prefs,
            user_data=prompt_user_data,
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}"
        meta = {
            "doc_type": doc_type,
            "search_query": search_query,
            "reference_count": len(ref_texts),
            "memory_count": memory_count,
        }
        return prompt, meta

    async def generate(self, session_id: int, user_data: str, user_prefs: str = "") -> str:
        prompt, _ = await self._prepare_generate_prompt(session_id, user_data, user_prefs)
        return self.llm.invoke(prompt)

    def guidance_stream(self, request: str, doc_type: str) -> Generator[str, None, None]:
        prompt = WRITING_GUIDANCE_PROMPT.format(
            request=request,
            doc_type=doc_type,
        )
        yield from self.llm.stream(prompt)

    async def generate_stream_with_meta(
        self,
        session_id: int,
        user_data: str,
        user_prefs: str = "",
    ) -> tuple[Generator[str, None, None], dict[str, Any]]:
        prompt, meta = await self._prepare_generate_prompt(session_id, user_data, user_prefs)
        return self.llm.stream(prompt), meta

    async def generate_stream(self, session_id: int, user_data: str, user_prefs: str = "") -> Generator[str, None, None]:
        stream, _ = await self.generate_stream_with_meta(session_id, user_data, user_prefs)
        return stream

    def edit(self, current_content: str, edit_request: str, doc_type: str = "公文") -> str:
        prompt = WRITING_EDIT_PROMPT.format(
            current_content=current_content,
            edit_request=edit_request,
            doc_type=doc_type,
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}"
        return self.llm.invoke(prompt)

    def review(self, content: str, doc_type: str = "公文") -> dict:
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
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

    def get_sessions(self, user_id: int) -> list[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
            .all()
        )
