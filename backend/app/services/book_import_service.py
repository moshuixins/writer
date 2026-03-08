from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import uuid
from pathlib import Path
from typing import Any

import jieba.analyse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.errors import FileValidationError, logger
from app.models.book_source import BookSource
from app.models.book_style_rule import BookStyleRule
from app.prompts.doc_types_catalog import DOC_TYPE_CHOICES_TEXT, OTHER_DOC_TYPE
from app.prompts.validators import parse_json_response, validate_classify, validate_keywords, validate_title
from app.services.book_import_task_service import book_import_task_tracker
from app.services.book_rule_service import BookRuleService
from app.services.context_bridge import ContextBridge
from app.services.epub_parser import EpubParser
from app.services.llm_service import LLMService
from app.services.pdf_ocr_service import PdfOcrService

settings = get_settings()

SUPPORTED_BOOK_EXTS = {".epub", ".pdf"}

BOOK_ANALYSIS_PROMPT = """你是“公文写作知识提炼助手”。请基于输入书籍内容，做结构化提炼。
只允许输出 JSON 对象，不要 markdown，不要解释。禁止直接搬运书中原句；只能提炼写法规则、结构套路和表达要点。
输出格式：{{
  "title": "书籍标题",
  "doc_type": "{doc_type_choices}",
  "doc_types_candidates": ["候选文种1", "候选文种2"],
  "summary": "150-220字，概括适用场景与写作方法",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "style_rules": [
    {{
      "rule_type": "structure|tone|lexicon|logic|format|avoidance",
      "rule_text": "规则描述",
      "confidence": 0.0,
      "origin_ref": "章节或页码"
    }}
  ],
  "template_skeletons": ["模板骨架1", "模板骨架2"]
}}
要求：
1. doc_type 必须从给定文种里选主文种。
2. doc_types_candidates 给出 2-6 个候选（可少）。
3. style_rules 给出 6-20 条“可执行规则”。
4. 仅抽象提炼，不输出可直接复用的大段原文。
文件名：{filename}
内容片段：{content}
"""


class BookImportConflictError(Exception):
    def __init__(self, active_task_id: str):
        self.active_task_id = active_task_id
        super().__init__(f"book import task conflict, active_task_id={active_task_id}")


def _safe_json_load(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return None
    return parse_json_response(str(value), silent=True)


def _new_error_id() -> str:
    return uuid.uuid4().hex[:12]


def _public_error_message(error_id: str) -> str:
    return f"处理失败，请稍后重试（错误ID: {error_id}）"


class BookImportService:
    def __init__(self, db: Session | None, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)
        self.ctx_bridge = ContextBridge()
        self.llm = LLMService(temperature=0.2)
        self.epub_parser = EpubParser()
        self.pdf_service = PdfOcrService()

    @staticmethod
    def _books_root() -> Path:
        return Path(settings.books_dir).resolve()

    @staticmethod
    def _sha256_file(file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def _iter_book_files(cls) -> list[Path]:
        root = cls._books_root()
        if not root.exists():
            return []

        files: list[Path] = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_BOOK_EXTS:
                files.append(path)
        return sorted(files, key=lambda p: str(p).lower())

    def scan_books(self) -> list[dict[str, Any]]:
        files = self._iter_book_files()
        hashes: list[str] = []
        file_rows: list[dict[str, Any]] = []

        for path in files:
            file_hash = self._sha256_file(path)
            hashes.append(file_hash)
            relative_path = path.relative_to(self._books_root()).as_posix()
            file_rows.append(
                {
                    "source_name": path.name,
                    "relative_path": relative_path,
                    "absolute_path": str(path),
                    "file_ext": path.suffix.lower(),
                    "file_size": path.stat().st_size,
                    "source_hash": file_hash,
                },
            )

        source_map: dict[str, BookSource] = {}
        if self.db is not None and hashes:
            try:
                rows = (
                    self.db.query(BookSource)
                    .filter(
                        BookSource.account_id == self.account_id,
                        BookSource.source_hash.in_(hashes),
                    )
                    .all()
                )
                source_map = {row.source_hash: row for row in rows}
            except Exception as e:
                logger.warning("book_sources unavailable while scanning, fallback empty map: %s", e)
                source_map = {}

        for item in file_rows:
            existing = source_map.get(item["source_hash"])
            if existing:
                item["imported"] = existing.status in {"completed", "partial"}
                item["status"] = existing.status
                item["doc_type"] = existing.doc_type
                item["updated_at"] = existing.updated_at
                item["source_id"] = existing.id
            else:
                item["imported"] = False
                item["status"] = "pending"
                item["doc_type"] = ""
                item["updated_at"] = None
                item["source_id"] = None
        return file_rows

    def start_import_task(
        self,
        *,
        rebuild: bool = False,
        selected_files: list[str] | None = None,
    ) -> tuple[str, int]:
        if self.db is None:
            raise RuntimeError("database session required")

        scanned = self.scan_books()
        selected_names = {(item or "").strip() for item in (selected_files or []) if (item or "").strip()}

        if selected_names:
            selected = [
                item
                for item in scanned
                if item["source_name"] in selected_names or item["relative_path"] in selected_names
            ]
        else:
            selected = scanned

        task_id = uuid.uuid4().hex
        reserved, active_task_id = book_import_task_tracker.reserve_slot(
            task_id,
            account_id=self.account_id,
        )
        if not reserved:
            raise BookImportConflictError(active_task_id or "")

        book_import_task_tracker.create_task(
            task_id,
            total_files=len(selected),
            rebuild=rebuild,
            account_id=self.account_id,
        )

        worker_thread = threading.Thread(
            target=self._run_in_background,
            args=(task_id, selected, rebuild, self.account_id),
            daemon=True,
        )
        worker_thread.start()
        return task_id, len(selected)

    @classmethod
    def _run_in_background(
        cls,
        task_id: str,
        selected_files: list[dict[str, Any]],
        rebuild: bool,
        account_id: int,
    ) -> None:
        db = SessionLocal()
        worker = cls(db, account_id=account_id)
        try:
            asyncio.run(worker._execute_import(task_id, selected_files, rebuild))
        except Exception as e:
            error_id = _new_error_id()
            logger.exception("Book import task crashed. error_id=%s err=%s", error_id, e)
            book_import_task_tracker.fail(task_id, message=_public_error_message(error_id))
        finally:
            db.close()

    async def _execute_import(self, task_id: str, selected_files: list[dict[str, Any]], rebuild: bool) -> None:
        if not selected_files:
            book_import_task_tracker.finish(task_id, status="completed", message="无可导入文件")
            return

        book_import_task_tracker.update(
            task_id,
            status="running",
            stage="准备导入",
            message="任务已启动",
        )

        if rebuild:
            book_import_task_tracker.update(task_id, stage="重建模式：清理历史书籍知识")
            await self.ctx_bridge.clear_namespace(f"viking://resources/accounts/{self.account_id}/books")
            self.db.query(BookStyleRule).filter(BookStyleRule.account_id == self.account_id).delete()
            self.db.query(BookSource).filter(BookSource.account_id == self.account_id).delete()
            self.db.commit()

        for file_item in selected_files:
            await self._process_one_file(task_id, file_item, rebuild=rebuild)

        task = book_import_task_tracker.get(task_id)
        if not task:
            return

        failed_files = int(task.get("failed_files", 0))
        partial_files = int(task.get("partial_files", 0))
        completed_files = int(task.get("completed_files", 0))
        total_files = int(task.get("total_files", 0))

        if completed_files < total_files:
            book_import_task_tracker.fail(task_id, "任务未完整执行")
            return

        if failed_files and failed_files == total_files:
            book_import_task_tracker.finish(task_id, status="failed", message="全部文件导入失败")
            return

        if failed_files > 0 or partial_files > 0:
            book_import_task_tracker.finish(task_id, status="partial", message="部分文件导入成功")
            return

        book_import_task_tracker.finish(task_id, status="completed", message="导入完成")

    def _extract_candidates(self, raw: Any) -> list[str]:
        values: list[str] = []
        parsed = _safe_json_load(raw)
        if isinstance(parsed, list):
            values = [str(v).strip() for v in parsed]
        elif isinstance(raw, list):
            values = [str(v).strip() for v in raw]
        elif isinstance(raw, str):
            values = [v.strip() for v in raw.replace("，", ",").split(",")]

        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            canonical = validate_classify(item)
            if canonical in seen:
                continue
            seen.add(canonical)
            normalized.append(canonical)
        return normalized

    def _extract_style_rules(self, raw_rules: Any, fallback_doc_type: str) -> list[dict[str, Any]]:
        rules_obj = _safe_json_load(raw_rules)
        rows: list[Any] = []
        if isinstance(rules_obj, list):
            rows = rules_obj
        elif isinstance(raw_rules, list):
            rows = raw_rules
        elif isinstance(raw_rules, str) and raw_rules.strip():
            rows = [line.strip() for line in raw_rules.splitlines() if line.strip()]

        parsed_rules: list[dict[str, Any]] = []
        for item in rows:
            if isinstance(item, dict):
                text = str(item.get("rule_text", "")).strip()
                if not text:
                    continue
                parsed_rules.append(
                    {
                        "doc_type": fallback_doc_type,
                        "rule_type": str(item.get("rule_type", "structure")).strip() or "structure",
                        "rule_text": text,
                        "confidence": item.get("confidence", 0.6),
                        "origin_ref": str(item.get("origin_ref", "")).strip(),
                    },
                )
                continue

            text = str(item).strip()
            if not text:
                continue
            parsed_rules.append(
                {
                    "doc_type": fallback_doc_type,
                    "rule_type": "structure",
                    "rule_text": text,
                    "confidence": 0.5,
                    "origin_ref": "",
                },
            )
        return parsed_rules

    def _build_analysis_content(self, chapters: list[dict[str, Any]], max_chars: int = 12000) -> str:
        blocks: list[str] = []
        total = 0

        for idx, chapter in enumerate(chapters, start=1):
            title = str(chapter.get("chapter_title", f"Chapter {idx}")).strip() or f"Chapter {idx}"
            text = str(chapter.get("text", "")).strip()
            if not text:
                continue
            snippet = text[:800]
            block = f"[{idx}] {title}\n{snippet}"
            if total + len(block) > max_chars:
                remain = max_chars - total
                if remain > 100:
                    blocks.append(block[:remain])
                break
            blocks.append(block)
            total += len(block)

        return "\n\n".join(blocks)

    def _extract_keywords_fallback(self, text: str) -> list[str]:
        keywords = jieba.analyse.extract_tags(text or "", topK=10)
        return [kw.strip() for kw in keywords if kw.strip()]

    def _split_text(self, text: str, size: int, overlap: int) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return []
        if len(raw) <= size:
            return [raw]

        chunks: list[str] = []
        step = max(1, size - overlap)
        start = 0
        while start < len(raw):
            end = min(len(raw), start + size)
            chunk = raw[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(raw):
                break
            start += step
        return chunks

    def _build_chunks(self, chapters: list[dict[str, Any]]) -> list[dict[str, str]]:
        size = max(100, int(settings.book_chunk_size))
        overlap = max(0, int(settings.book_chunk_overlap))
        chunk_rows: list[dict[str, str]] = []

        for idx, chapter in enumerate(chapters, start=1):
            title = str(chapter.get("chapter_title", f"Chapter {idx}")).strip() or f"Chapter {idx}"
            page_start = chapter.get("page_start")
            page_end = chapter.get("page_end")
            page_range = ""
            if page_start and page_end:
                page_range = f"{page_start}-{page_end}"
            elif page_start:
                page_range = str(page_start)

            for piece in self._split_text(str(chapter.get("text", "")), size=size, overlap=overlap):
                chunk_rows.append(
                    {
                        "chapter": title[:200],
                        "page_range": page_range,
                        "text": f"[{title}]\n{piece}",
                    },
                )
        return chunk_rows

    def _analyze_book_once(self, source_name: str, chapters: list[dict[str, Any]]) -> dict[str, Any]:
        content = self._build_analysis_content(chapters)
        fallback_text = content[:2000]
        fallback_title = Path(source_name).stem

        if not content:
            return {
                "title": fallback_title,
                "doc_type": OTHER_DOC_TYPE,
                "doc_types_candidates": [OTHER_DOC_TYPE],
                "summary": "",
                "keywords": [],
                "style_rules": [],
                "template_skeletons": [],
            }

        try:
            raw = self.llm.invoke(
                BOOK_ANALYSIS_PROMPT.format(
                    doc_type_choices=DOC_TYPE_CHOICES_TEXT,
                    filename=source_name,
                    content=content,
                )
            )
            parsed = parse_json_response(raw, silent=True)
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception as e:
            logger.warning("Book analysis LLM failed, fallback used: %s", e)
            parsed = {}

        title = validate_title(str(parsed.get("title", "")), fallback=fallback_title)
        doc_type = validate_classify(str(parsed.get("doc_type", "")))
        summary = str(parsed.get("summary", "")).strip()[:1200]
        if not summary:
            summary = (fallback_text or "").replace("\n", " ")[:220]

        keyword_source = parsed.get("keywords", "")
        if isinstance(keyword_source, (list, dict)):
            keyword_source = json.dumps(keyword_source, ensure_ascii=False)
        keywords = validate_keywords(str(keyword_source or ""))
        if not keywords:
            keywords = self._extract_keywords_fallback(fallback_text)

        candidates = self._extract_candidates(parsed.get("doc_types_candidates", []))
        if doc_type not in candidates:
            candidates = [doc_type, *candidates]
        candidates = candidates[:6]

        style_rules = self._extract_style_rules(parsed.get("style_rules", []), fallback_doc_type=doc_type)
        template_skeletons = parsed.get("template_skeletons", [])
        if not isinstance(template_skeletons, list):
            template_skeletons = []

        return {
            "title": title,
            "doc_type": doc_type,
            "doc_types_candidates": candidates,
            "summary": summary,
            "keywords": keywords[:10],
            "style_rules": style_rules,
            "template_skeletons": [str(item).strip() for item in template_skeletons if str(item).strip()][:10],
        }

    def _upsert_source_row(
        self,
        *,
        existing: BookSource | None,
        file_item: dict[str, Any],
        status: str,
        doc_type: str,
        summary: str,
        keywords: list[str],
        chunk_count: int,
        ocr_used: bool,
        error_message: str,
        metadata: dict[str, Any],
    ) -> BookSource:
        row = existing or BookSource(
            account_id=self.account_id,
            source_name=file_item["source_name"],
            source_path=file_item["relative_path"],
            source_hash=file_item["source_hash"],
            file_ext=file_item["file_ext"],
            file_size=int(file_item["file_size"]),
            doc_type=doc_type,
        )
        row.account_id = self.account_id
        row.source_name = file_item["source_name"]
        row.source_path = file_item["relative_path"]
        row.file_ext = file_item["file_ext"]
        row.file_size = int(file_item["file_size"])
        row.status = status
        row.doc_type = doc_type
        row.summary = summary
        row.keywords = keywords
        row.chunk_count = chunk_count
        row.ocr_used = ocr_used
        row.error_message = error_message[:2000]
        row.metadata_ = metadata
        if existing is None:
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    async def _process_one_file(self, task_id: str, file_item: dict[str, Any], rebuild: bool) -> None:
        source_name = file_item["source_name"]
        source_hash = file_item["source_hash"]
        source_path = file_item["absolute_path"]
        ext = file_item["file_ext"].lower()

        book_import_task_tracker.update(
            task_id,
            stage="处理中",
            running_file=source_name,
            message=f"正在处理 {source_name}",
        )

        existing = (
            self.db.query(BookSource)
            .filter(
                BookSource.account_id == self.account_id,
                BookSource.source_hash == source_hash,
            )
            .first()
        )
        if existing and existing.status in {"completed", "partial"} and not rebuild:
            book_import_task_tracker.update(
                task_id,
                completed_files_add=1,
                skipped_files_add=1,
                file_result={
                    "source_name": source_name,
                    "status": "skipped",
                    "chunk_count": existing.chunk_count,
                    "ocr_used": bool(existing.ocr_used),
                    "ocr_pages": int((existing.metadata_ or {}).get("ocr_pages", 0)),
                    "error_message": "",
                },
            )
            return

        ocr_used = False
        ocr_pages = 0
        parse_stats: dict[str, Any] = {}

        try:
            if ext == ".epub":
                chapters = self.epub_parser.parse(source_path)
            elif ext == ".pdf":
                parsed_pdf = self.pdf_service.parse_pdf(source_path)
                chapters = list(parsed_pdf.get("chapters", []))
                ocr_used = bool(parsed_pdf.get("ocr_used", False))
                ocr_pages = int(parsed_pdf.get("ocr_pages", 0))
                parse_stats = {
                    "total_pages": parsed_pdf.get("total_pages", 0),
                    "text_layer_chars": parsed_pdf.get("text_layer_chars", 0),
                    "non_empty_ratio": parsed_pdf.get("non_empty_ratio", 0.0),
                }
            else:
                raise FileValidationError(f"Unsupported book file type: {ext}")

            if not chapters:
                raise FileValidationError("No readable text extracted")

            analysis = self._analyze_book_once(source_name, chapters)
            doc_type = validate_classify(str(analysis.get("doc_type", OTHER_DOC_TYPE)))
            keywords = analysis.get("keywords", []) or []
            summary = str(analysis.get("summary", "")).strip()
            candidates = analysis.get("doc_types_candidates", []) or []
            style_rules = analysis.get("style_rules", []) or []
            template_skeletons = analysis.get("template_skeletons", []) or []

            chunk_rows = self._build_chunks(chapters)
            book_import_task_tracker.update(task_id, total_chunks_add=len(chunk_rows))

            imported_chunks = 0
            chunk_errors = 0
            first_error = ""
            for chunk in chunk_rows:
                try:
                    await self.ctx_bridge.add_book_chunk(
                        account_id=self.account_id,
                        doc_type=doc_type,
                        source_name=source_name,
                        source_hash=source_hash,
                        chapter=chunk["chapter"],
                        content_text=chunk["text"],
                        page_range=chunk["page_range"],
                    )
                    imported_chunks += 1
                except Exception as e:
                    chunk_errors += 1
                    if not first_error:
                        err_id = _new_error_id()
                        first_error = _public_error_message(err_id)
                        logger.warning("Book chunk import failed. error_id=%s source=%s err=%s", err_id, source_name, e)
                finally:
                    book_import_task_tracker.update(task_id, completed_chunks_add=1)

            if chunk_errors == 0:
                file_status = "completed"
            elif imported_chunks > 0:
                file_status = "partial"
            else:
                file_status = "failed"

            metadata = {
                "title": analysis.get("title", Path(source_name).stem),
                "doc_types_candidates": candidates,
                "template_skeletons": template_skeletons,
                "chapter_count": len(chapters),
                "chunk_total": len(chunk_rows),
                "chunk_imported": imported_chunks,
                "chunk_failed": chunk_errors,
                "ocr_pages": ocr_pages,
                "parse_stats": parse_stats,
            }

            source_row = self._upsert_source_row(
                existing=existing,
                file_item=file_item,
                status=file_status,
                doc_type=doc_type,
                summary=summary,
                keywords=keywords,
                chunk_count=imported_chunks,
                ocr_used=ocr_used,
                error_message=first_error,
                metadata=metadata,
            )

            BookRuleService(self.db, account_id=self.account_id).replace_rules(
                source_id=source_row.id,
                doc_type=doc_type,
                rules=style_rules,
            )

            book_import_task_tracker.update(
                task_id,
                completed_files_add=1,
                partial_files_add=1 if file_status == "partial" else 0,
                failed_files_add=1 if file_status == "failed" else 0,
                ocr_used_files_add=1 if ocr_used else 0,
                ocr_pages_add=ocr_pages,
                file_result={
                    "source_name": source_name,
                    "status": file_status,
                    "chunk_count": imported_chunks,
                    "ocr_used": ocr_used,
                    "ocr_pages": ocr_pages,
                    "error_message": first_error,
                },
            )
        except Exception as e:
            err_id = _new_error_id()
            public_message = _public_error_message(err_id)
            logger.exception("Book import failed. error_id=%s source=%s err=%s", err_id, source_name, e)
            self._upsert_source_row(
                existing=existing,
                file_item=file_item,
                status="failed",
                doc_type=OTHER_DOC_TYPE,
                summary=public_message,
                keywords=[],
                chunk_count=0,
                ocr_used=ocr_used,
                error_message=public_message,
                metadata={"ocr_pages": ocr_pages, "parse_stats": parse_stats, "error_id": err_id},
            )
            book_import_task_tracker.update(
                task_id,
                completed_files_add=1,
                failed_files_add=1,
                ocr_used_files_add=1 if ocr_used else 0,
                ocr_pages_add=ocr_pages,
                file_result={
                    "source_name": source_name,
                    "status": "failed",
                    "chunk_count": 0,
                    "ocr_used": ocr_used,
                    "ocr_pages": ocr_pages,
                    "error_message": public_message,
                },
            )
