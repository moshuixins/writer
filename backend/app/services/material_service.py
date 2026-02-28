import os
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
import jieba
import jieba.analyse
from app.config import get_settings
from app.models.material import Material
from app.errors import FileValidationError, logger

settings = get_settings()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class MaterialService:
    """素材处理服务：上传、解析、分类、摘要"""

    def __init__(self, db: Session):
        self.db = db

    def save_upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        """保存上传文件到磁盘，返回存储路径"""
        if len(file_bytes) > MAX_FILE_SIZE:
            raise FileValidationError(f"文件大小超过限制（最大{MAX_FILE_SIZE // 1024 // 1024}MB）")
        ext = Path(filename).suffix.lower()
        if ext not in {".docx", ".pdf", ".txt"}:
            raise FileValidationError(f"不支持的文件格式: {ext}")
        unique_name = f"{uuid.uuid4().hex}{ext}"
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / unique_name
        file_path.write_bytes(file_bytes)
        logger.info("File saved: %s (%d bytes)", file_path, len(file_bytes))
        return str(file_path)

    def extract_text(self, file_path: str, filename: str) -> str:
        """从文件中提取纯文本"""
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".docx":
                return self._extract_docx(file_path)
            elif ext == ".pdf":
                return self._extract_pdf(file_path)
            elif ext == ".txt":
                return self._extract_txt(file_path)
            else:
                raise FileValidationError(f"不支持的文件格式: {ext}")
        except FileValidationError:
            raise
        except Exception as e:
            logger.error("Text extraction failed for %s: %s", filename, e)
            raise FileValidationError(f"文件解析失败: {e}")

    def _extract_docx(self, file_path: str) -> str:
        doc = DocxDocument(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_pdf(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
        except Exception as e:
            raise FileValidationError(f"PDF文件损坏或加密: {e}")
        texts = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    texts.append(text.strip())
            except Exception:
                logger.warning("Failed to extract page from %s", file_path)
        return "\n".join(texts)

    def _extract_txt(self, file_path: str) -> str:
        """读取txt文件，自动检测编码"""
        raw = Path(file_path).read_bytes()
        for encoding in ("utf-8", "gbk", "gb2312", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        raise FileValidationError("无法识别文件编码")

    def extract_keywords(self, text: str, top_k: int = 10) -> list[str]:
        """使用jieba提取关键词"""
        return jieba.analyse.extract_tags(text, topK=top_k)

    def guess_title(self, text: str, filename: str) -> str:
        """从文本首行或文件名猜测标题"""
        first_line = text.strip().split("\n")[0].strip()
        if len(first_line) > 5 and len(first_line) < 100:
            return first_line
        return Path(filename).stem

    def create_material(
        self, user_id: int, title: str, filename: str,
        file_path: str, content_text: str,
        doc_type: str = None, summary: str = None,
        keywords: list[str] = None,
    ) -> Material:
        """创建素材记录"""
        material = Material(
            user_id=user_id,
            title=title,
            original_filename=filename,
            file_path=file_path,
            content_text=content_text,
            doc_type=doc_type,
            summary=summary,
            keywords=keywords or [],
            char_count=len(content_text),
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        return material

    def get_materials(
        self, user_id: int, doc_type: str = None,
        keyword: str = None, skip: int = 0, limit: int = 20,
    ) -> list[Material]:
        """查询素材列表"""
        q = self.db.query(Material).filter(Material.user_id == user_id)
        if doc_type:
            q = q.filter(Material.doc_type == doc_type)
        if keyword:
            q = q.filter(Material.content_text.contains(keyword))
        return q.order_by(Material.created_at.desc()).offset(skip).limit(limit).all()

    def get_material(self, material_id: int) -> Material | None:
        return self.db.query(Material).filter(Material.id == material_id).first()

    def delete_material(self, material_id: int) -> bool:
        material = self.get_material(material_id)
        if not material:
            return False
        if material.file_path and os.path.exists(material.file_path):
            os.remove(material.file_path)
        self.db.delete(material)
        self.db.commit()
        return True
