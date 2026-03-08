from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import jieba
import jieba.analyse
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import FileValidationError, logger
from app.models.material import Material

settings = get_settings()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class MaterialService:
    """Material upload/parse/persist service."""

    def __init__(self, db: Session):
        self.db = db

    def save_upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        if len(file_bytes) > MAX_FILE_SIZE:
            raise FileValidationError(f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")
        ext = Path(filename).suffix.lower()
        if ext not in {".doc", ".docx", ".pdf", ".txt"}:
            raise FileValidationError(f"不支持的文件格式: {ext}")

        unique_name = f"{uuid.uuid4().hex}{ext}"
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / unique_name
        file_path.write_bytes(file_bytes)
        logger.info("File saved: %s (%d bytes) user_id=%s", file_path, len(file_bytes), user_id)
        return str(file_path)

    def extract_text(self, file_path: str, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".doc":
                return self._extract_doc(file_path)
            if ext == ".docx":
                return self._extract_docx(file_path)
            if ext == ".pdf":
                return self._extract_pdf(file_path)
            if ext == ".txt":
                return self._extract_txt(file_path)
            raise FileValidationError(f"不支持的文件格式: {ext}")
        except FileValidationError:
            raise
        except Exception as e:
            logger.error("Text extraction failed for %s: %s", filename, e)
            raise FileValidationError("文件解析失败")

    def _extract_docx(self, file_path: str) -> str:
        doc = DocxDocument(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_doc(self, file_path: str) -> str:
        for tool in ("antiword", "catdoc", "wvText"):
            tool_path = shutil.which(tool)
            if not tool_path:
                continue

            try:
                result = subprocess.run(
                    [tool_path, file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                    check=False,
                )
            except Exception as e:
                logger.warning("%s failed for file: %s", tool, e)
                continue

            raw = result.stdout or b""
            text = ""
            for encoding in ("utf-8", "gbk", "gb2312", "utf-16", "latin-1"):
                try:
                    text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue

            text = text.replace("\x00", "").strip() if text else ""
            if text:
                return text

            stderr_preview = (result.stderr or b"").decode("utf-8", errors="ignore")[:200]
            logger.warning("%s extracted empty text: %s", tool, stderr_preview)

        raise FileValidationError("DOC 文件解析失败：服务器缺少 antiword/catdoc，或文件内容不可读取")

    def _extract_pdf(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
        except Exception as e:
            raise FileValidationError("PDF 文件损坏或加密") from e

        texts = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    texts.append(text.strip())
            except Exception:
                logger.warning("Failed to extract one PDF page")
        return "\n".join(texts)

    def _extract_txt(self, file_path: str) -> str:
        raw = Path(file_path).read_bytes()
        for encoding in ("utf-8", "gbk", "gb2312", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        raise FileValidationError("无法识别文件编码")

    def extract_keywords(self, text: str, top_k: int = 10) -> list[str]:
        return jieba.analyse.extract_tags(text or "", topK=top_k)

    def guess_title(self, text: str, filename: str) -> str:
        first_line = text.strip().split("\n")[0].strip() if text else ""
        if 5 < len(first_line) < 100:
            return first_line
        return Path(filename).stem

    def create_material(
        self,
        user_id: int,
        title: str,
        filename: str,
        file_path: str,
        content_text: str,
        doc_type: str | None = None,
        summary: str | None = None,
        keywords: list[str] | None = None,
        account_id: int = 1,
        *,
        commit: bool = True,
    ) -> Material:
        material = Material(
            account_id=account_id,
            user_id=user_id,
            title=title,
            original_filename=filename,
            file_path=file_path,
            content_text=content_text,
            doc_type=doc_type,
            summary=summary,
            keywords=keywords or [],
            char_count=self.calculate_char_count(content_text),
        )
        self.db.add(material)
        self.db.flush()
        if commit:
            self.db.commit()
            self.db.refresh(material)
        return material

    def calculate_char_count(self, text: str) -> int:
        if not text:
            return 0
        normalized = text.replace("\ufeff", "")
        normalized = re.sub(r"[\s\u00a0\u3000\u200b-\u200f\u2060\u2066-\u2069\ufeff]+", "", normalized)
        return len(normalized)

    def normalize_material_char_count(self, material: Material) -> int:
        expected = self.calculate_char_count(material.content_text or "")
        if material.char_count != expected:
            material.char_count = expected
        return expected

    def normalize_materials_char_count(self, materials: list[Material], *, commit: bool = False) -> bool:
        changed = False
        for material in materials:
            expected = self.calculate_char_count(material.content_text or "")
            if material.char_count != expected:
                material.char_count = expected
                changed = True
        if changed and commit:
            self.db.commit()
        return changed

    def get_materials(
        self,
        user_id: int,
        account_id: int,
        doc_type: str | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Material]:
        q = self._build_query(user_id=user_id, account_id=account_id, doc_type=doc_type, keyword=keyword)
        return q.order_by(Material.created_at.desc()).offset(skip).limit(limit).all()

    def count_materials(
        self,
        user_id: int,
        account_id: int,
        doc_type: str | None = None,
        keyword: str | None = None,
    ) -> int:
        return self._build_query(user_id=user_id, account_id=account_id, doc_type=doc_type, keyword=keyword).count()

    def get_material(self, material_id: int, *, account_id: int) -> Material | None:
        return (
            self.db.query(Material)
            .filter(
                Material.id == material_id,
                Material.account_id == account_id,
            )
            .first()
        )

    @staticmethod
    def cleanup_material_file(file_path: str | None) -> None:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    def delete_material(self, material_id: int, *, account_id: int, commit: bool = True) -> str | None:
        material = self.get_material(material_id, account_id=account_id)
        if not material:
            return None
        file_path = material.file_path or None
        self.db.delete(material)
        self.db.flush()
        if commit:
            self.db.commit()
            self.cleanup_material_file(file_path)
        return file_path

    def _build_query(
        self,
        user_id: int,
        account_id: int,
        doc_type: str | None = None,
        keyword: str | None = None,
    ):
        q = self.db.query(Material).filter(
            Material.user_id == user_id,
            Material.account_id == account_id,
        )
        if doc_type:
            q = q.filter(Material.doc_type == doc_type)
        if keyword:
            q = q.filter(Material.content_text.contains(keyword))
        return q
