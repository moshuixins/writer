from __future__ import annotations

from typing import Any, Generator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.chat import ChatMessage, ChatSession
from app.prompts.doc_type_guides import get_doc_type_guide
from app.prompts.doc_types_catalog import OTHER_DOC_TYPE, is_canonical_doc_type, normalize_doc_type
from app.prompts.validators import parse_json_response
from app.prompts.writing_registry import get_prompt_set
from app.services.book_rule_service import BookRuleService
from app.services.context_bridge import ContextBridge
from app.services.llm_service import LLMService
from app.services.style_analyzer import StyleAnalyzer

settings = get_settings()

PLAIN_TEXT_OUTPUT_REQUIREMENTS = """
## Output constraints (must follow)
1. Return plain, readable Chinese official-document content.
2. Do NOT output JSON.
3. Do NOT output Markdown code blocks.
4. Do NOT output schema/field names such as "title", "recipients", "body_sections", "attachments", "signing_org", "date".
5. If required facts are missing, keep placeholders like [具体日期] in text.
"""

BOOK_REUSE_CONSTRAINTS = """
## Reuse constraints (must follow)
1. You may only absorb structure/style from references, do not copy source text.
2. Do not output any sentence with 20+ consecutive characters identical to references.
3. Prefer user-provided materials over book snippets when conflicts appear.
"""

MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_MESSAGE_CHARS = 0


class WritingService:
    """Writing service for guidance, generation, editing and review."""

    def __init__(self, db: Session, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)
        self.llm = LLMService()
        self.ctx_bridge = ContextBridge()
        self.style = StyleAnalyzer(db, account_id=self.account_id)
        self.book_rules = BookRuleService(db, account_id=self.account_id)

    @staticmethod
    def _resolve_doc_type(doc_type: str | None) -> str:
        cleaned = (doc_type or "").strip()
        if is_canonical_doc_type(cleaned):
            return cleaned
        normalized = normalize_doc_type(cleaned)
        return normalized or OTHER_DOC_TYPE

    def create_session(self, user_id: int, title: str, doc_type: str | None = None) -> ChatSession:
        session = ChatSession(
            account_id=self.account_id,
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
            account_id=self.account_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_guidance(self, request: str, doc_type: str) -> str:
        resolved_doc_type = self._resolve_doc_type(doc_type)
        prompt = get_prompt_set(resolved_doc_type)["guidance"].format(
            request=request,
            doc_type=resolved_doc_type,
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}\n\n{BOOK_REUSE_CONSTRAINTS}"
        return self.llm.invoke(prompt)

    def _build_search_query(self, user_data: str, doc_type: str) -> str:
        paragraphs = [p.strip() for p in (user_data or "").split("\n") if p.strip()]
        first_para = paragraphs[0] if paragraphs else (user_data or "")[:200]
        return f"{doc_type} {first_para[:150]}"

    def _build_session_messages(self, session_id: int, current_user_text: str = "") -> list[BaseMessage]:
        recent_messages = (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.account_id == self.account_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(MAX_CONTEXT_MESSAGES)
            .all()
        )

        if not recent_messages:
            return []

        trimmed = (current_user_text or "").strip()
        if trimmed and recent_messages:
            latest = recent_messages[0]
            latest_content = (latest.content or "").strip()
            if latest.role == "user" and latest_content == trimmed:
                recent_messages = recent_messages[1:]

        messages: list[BaseMessage] = []
        for msg in reversed(recent_messages):
            content = (msg.content or "").strip()
            if not content:
                continue
            if MAX_CONTEXT_MESSAGE_CHARS > 0 and len(content) > MAX_CONTEXT_MESSAGE_CHARS:
                content = f"{content[:MAX_CONTEXT_MESSAGE_CHARS]}...(内容已截断)"
            if msg.role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    async def _prepare_generate_prompt(
        self,
        session_id: int,
        user_data: str,
        user_prefs: str = "",
    ) -> tuple[str, dict[str, Any]]:
        session = (
            self.db.query(ChatSession)
            .filter(
                ChatSession.account_id == self.account_id,
                ChatSession.id == session_id,
            )
            .first()
        )
        if not session:
            raise ValueError("会话不存在")

        doc_type = self._resolve_doc_type(session.doc_type or OTHER_DOC_TYPE)
        doc_type_guide = get_doc_type_guide(doc_type)
        search_query = self._build_search_query(user_data, doc_type)

        refs: list[dict[str, Any]] = []
        try:
            refs = await self.ctx_bridge.search_materials(
                search_query,
                doc_type=doc_type,
                top_k=5,
                account_id=self.account_id,
            )
        except Exception:
            refs = []

        book_refs: list[dict[str, Any]] = []
        book_rule_items: list[str] = []
        if settings.book_augmentation_enabled:
            try:
                book_refs = await self.ctx_bridge.search_books(
                    search_query,
                    doc_type=doc_type,
                    top_k=max(1, int(settings.book_retrieval_top_k)),
                    account_id=self.account_id,
                )
            except Exception:
                book_refs = []
            try:
                book_rule_items = self.book_rules.get_rules_for_prompt(
                    doc_type=doc_type,
                    query=search_query,
                    top_k=max(1, int(settings.book_style_top_k)),
                )
            except Exception:
                book_rule_items = []

        ref_texts = [(item.get("text") or "").strip() for item in refs if (item.get("text") or "").strip()]
        book_ref_texts = [(item.get("text") or "").strip() for item in book_refs if (item.get("text") or "").strip()]
        material_reference_text = "\n---\n".join(ref_texts)
        book_reference_text = "\n---\n".join(book_ref_texts)

        reference_blocks: list[str] = []
        if ref_texts:
            reference_blocks.append(f"【用户素材参考】\n{material_reference_text}")
        if book_ref_texts:
            reference_blocks.append(f"【书籍知识参考（仅用于写法借鉴）】\n{book_reference_text}")
        ref_text = "\n\n".join(reference_blocks) if reference_blocks else "暂无参考范文"

        memory_context = ""
        try:
            memory_context = await self.ctx_bridge.get_memory_context(search_query, account_id=self.account_id)
        except Exception:
            memory_context = ""

        memory_count = len([line for line in memory_context.splitlines() if line.strip()]) if memory_context else 0
        style_guide = self.style.get_style_guidelines(doc_type)
        if book_rule_items:
            style_guide = (
                f"{style_guide}\n\n"
                "书籍风格规则（仅吸收写法，不直引原文）：\n"
                + "\n".join(f"- {item}" for item in book_rule_items)
            )

        combined_prefs = user_prefs or "无特殊偏好"
        if memory_context:
            combined_prefs += f"\n\n从历史写作中学到的习惯：\n{memory_context}"

        prompt = get_prompt_set(doc_type)["generate"].format(
            doc_type=doc_type,
            doc_type_guide=doc_type_guide,
            style_guidelines=style_guide,
            reference_examples=ref_text,
            user_preferences=combined_prefs,
            user_data=(user_data or "").strip(),
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}\n\n{BOOK_REUSE_CONSTRAINTS}"

        meta = {
            "doc_type": doc_type,
            "search_query": search_query,
            "reference_count": len(ref_texts),
            "memory_count": memory_count,
            "book_reference_count": len(book_ref_texts),
            "book_rule_count": len(book_rule_items),
        }
        return prompt, meta

    async def generate(self, session_id: int, user_data: str, user_prefs: str = "") -> str:
        prompt, _ = await self._prepare_generate_prompt(session_id, user_data, user_prefs)
        history_messages = self._build_session_messages(session_id, current_user_text=user_data)
        messages = [SystemMessage(content=prompt), *history_messages, HumanMessage(content=(user_data or "").strip())]
        return await self.llm.invoke_messages_async(messages)

    def guidance_stream(self, request: str, doc_type: str) -> Generator[str, None, None]:
        resolved_doc_type = self._resolve_doc_type(doc_type)
        prompt = get_prompt_set(resolved_doc_type)["guidance"].format(
            request=request,
            doc_type=resolved_doc_type,
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}\n\n{BOOK_REUSE_CONSTRAINTS}"
        yield from self.llm.stream(prompt)

    async def generate_stream_with_meta(
        self,
        session_id: int,
        user_data: str,
        user_prefs: str = "",
    ) -> tuple[Generator[str, None, None], dict[str, Any]]:
        prompt, meta = await self._prepare_generate_prompt(session_id, user_data, user_prefs)
        history_messages = self._build_session_messages(session_id, current_user_text=user_data)
        messages = [SystemMessage(content=prompt), *history_messages, HumanMessage(content=(user_data or "").strip())]
        return self.llm.stream_messages(messages), meta

    async def generate_stream(self, session_id: int, user_data: str, user_prefs: str = "") -> Generator[str, None, None]:
        stream, _ = await self.generate_stream_with_meta(session_id, user_data, user_prefs)
        return stream

    def edit(self, current_content: str, edit_request: str, doc_type: str = OTHER_DOC_TYPE) -> str:
        resolved_doc_type = self._resolve_doc_type(doc_type)
        prompt = get_prompt_set(resolved_doc_type)["edit"].format(
            current_content=current_content,
            edit_request=edit_request,
            doc_type=resolved_doc_type,
        )
        prompt = f"{prompt}\n\n{PLAIN_TEXT_OUTPUT_REQUIREMENTS}\n\n{BOOK_REUSE_CONSTRAINTS}"
        return self.llm.invoke(prompt)

    def review(self, content: str, doc_type: str = OTHER_DOC_TYPE) -> dict[str, Any]:
        resolved_doc_type = self._resolve_doc_type(doc_type)
        prompt = get_prompt_set(resolved_doc_type)["review"].format(
            content=content,
            doc_type=resolved_doc_type,
        )
        raw = self.llm.invoke(prompt)
        result = parse_json_response(raw)
        if result and isinstance(result, dict):
            return result
        return {"score": 0, "issues": [], "summary": "自检服务暂时不可用"}

    def get_session_messages(self, session_id: int) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.account_id == self.account_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at)
            .all()
        )

    def get_sessions(self, user_id: int) -> list[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.account_id == self.account_id,
                ChatSession.user_id == user_id,
            )
            .order_by(ChatSession.created_at.desc())
            .all()
        )
