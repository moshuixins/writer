from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.errors import FileValidationError, logger
from app.models.material import Material
from app.prompts.doc_types_catalog import DOC_TYPE_CHOICES_TEXT
from app.prompts.material_analysis import MATERIAL_ANALYSIS_PROMPT
from app.prompts.validators import parse_json_response, validate_classify, validate_keywords, validate_title
from app.services.context_bridge import ContextBridge
from app.services.llm_service import LLMService
from app.services.material_service import MaterialService
from app.services.style_analyzer import StyleAnalyzer
from app.side_effects import collect_side_effect_warning

ProgressCallback = Callable[[int, str, str, str], None]


@dataclass(slots=True)
class MaterialIngestionResult:
    material: Material
    warnings: list[str]


class MaterialIngestionService:
    def __init__(self, db: Session, *, account_id: int, user_id: int):
        self.db = db
        self.account_id = int(account_id or 1)
        self.user_id = int(user_id or 0)
        self.materials = MaterialService(db)
        self.llm = LLMService()

    async def ingest_upload(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        context_bridge: ContextBridge,
        progress_callback: ProgressCallback | None = None,
    ) -> MaterialIngestionResult:
        warnings: list[str] = []
        self._update_progress(progress_callback, 3, "开始解析")

        file_path = await asyncio.to_thread(self.materials.save_upload, file_bytes, filename, self.user_id)
        self._update_progress(progress_callback, 12, "文件已保存")

        content_text = await asyncio.to_thread(self.materials.extract_text, file_path, filename)
        if not content_text.strip():
            raise FileValidationError("文件内容为空，无法处理")
        self._update_progress(progress_callback, 28, "文本提取完成")

        analysis = await self._analyze_material(content_text, filename)
        title = analysis["title"]
        doc_type = analysis["doc_type"]
        keywords = analysis["keywords"]
        summary = analysis["summary"]
        self._update_progress(progress_callback, 64, "AI 信息识别完成")

        style_features = await self._analyze_style(content_text, filename, warnings)
        self._update_progress(progress_callback, 76, "风格特征分析完成")

        if style_features:
            StyleAnalyzer(self.db, account_id=self.account_id).store_analysis(
                doc_type,
                style_features,
                commit=False,
            )

        material = self.materials.create_material(
            self.user_id,
            title,
            filename,
            file_path,
            content_text,
            doc_type,
            summary,
            keywords,
            self.account_id,
            commit=False,
        )
        self.db.commit()
        self.db.refresh(material)
        self._update_progress(progress_callback, 88, "素材已入库")

        await self._sync_context(context_bridge, material, file_path, doc_type, title, content_text, warnings)

        final_message = "ok" if not warnings else "部分增强处理已降级"
        self._update_progress(progress_callback, 100, "解析完成", status="completed", message=final_message)
        return MaterialIngestionResult(material=material, warnings=warnings)

    async def _analyze_material(self, content_text: str, filename: str) -> dict[str, object]:
        fallback_title = await asyncio.to_thread(self.materials.guess_title, content_text, filename)
        raw_analysis = (
            await self.llm.invoke_async(
                MATERIAL_ANALYSIS_PROMPT.format(
                    doc_type_choices=DOC_TYPE_CHOICES_TEXT,
                    filename=filename,
                    content=content_text[:8000],
                ),
            )
        ).strip()
        parsed = parse_json_response(raw_analysis, silent=True)
        if not isinstance(parsed, dict):
            logger.warning("Invalid material analysis JSON, fallback validators: %s", raw_analysis[:200])
            parsed = {}

        title = validate_title(str(parsed.get("title", "")), fallback=fallback_title)
        doc_type = validate_classify(str(parsed.get("doc_type", "")))
        keyword_source = parsed.get("keywords", "")
        if isinstance(keyword_source, (list, dict)):
            raw_keywords = json.dumps(keyword_source, ensure_ascii=False)
        else:
            raw_keywords = str(keyword_source or "")
        keywords = validate_keywords(raw_keywords)
        if not keywords:
            logger.warning("LLM keywords empty, fallback to jieba for file: %s", filename)
            keywords = await asyncio.to_thread(self.materials.extract_keywords, content_text)

        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            summary = (content_text or "").replace("\n", " ").strip()[:200]

        return {
            "title": title,
            "doc_type": doc_type,
            "keywords": keywords,
            "summary": summary,
        }

    async def _analyze_style(self, content_text: str, filename: str, warnings: list[str]) -> dict | None:
        try:
            return await asyncio.to_thread(
                StyleAnalyzer(account_id=self.account_id).analyze,
                content_text,
            )
        except Exception as exc:
            collect_side_effect_warning(
                warnings,
                operation="materials.style_analysis",
                public_message="风格分析未完成",
                error=exc,
                user_id=self.user_id,
                account_id=self.account_id,
                filename=filename,
            )
            return None

    async def _sync_context(
        self,
        context_bridge: ContextBridge,
        material: Material,
        file_path: str,
        doc_type: str,
        title: str,
        content_text: str,
        warnings: list[str],
    ) -> None:
        try:
            await context_bridge.add_material(
                file_path,
                doc_type,
                title,
                content_text=content_text,
                account_id=self.account_id,
            )
        except Exception as exc:
            collect_side_effect_warning(
                warnings,
                operation="materials.context_sync",
                public_message="知识库同步未完成",
                error=exc,
                user_id=self.user_id,
                account_id=self.account_id,
                material_id=material.id,
            )

    @staticmethod
    def _update_progress(
        progress_callback: ProgressCallback | None,
        progress: int,
        stage: str,
        *,
        status: str = "parsing",
        message: str = "",
    ) -> None:
        if progress_callback is not None:
            progress_callback(progress, stage, status, message)
