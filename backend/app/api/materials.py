from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import ROLE_ADMIN, require_permission
from app.config import get_settings
from app.database import get_db
from app.errors import logger
from app.models.book_source import BookSource
from app.models.user import User
from app.prompts.material_analysis import MATERIAL_ANALYSIS_PROMPT
from app.prompts.validators import (
    ensure_canonical_doc_type,
    parse_json_response,
    validate_classify,
    validate_keywords,
    validate_title,
)
from app.services.book_import_service import BookImportConflictError, BookImportService
from app.services.book_import_task_service import book_import_task_tracker
from app.services.context_bridge import ContextBridge
from app.services.llm_service import LLMService
from app.services.material_service import MaterialService
from app.services.upload_progress_service import upload_progress_tracker
from app.timezone import to_shanghai_iso

router = APIRouter()
ctx_bridge = ContextBridge()
settings = get_settings()


def _new_error_id() -> str:
    return uuid.uuid4().hex[:12]


def _safe_books_dir() -> str:
    # avoid leaking absolute server path
    configured = Path(settings.books_dir)
    parts = configured.parts
    if "data" in parts:
        idx = parts.index("data")
        return "/".join(parts[idx:])
    return "data/book"


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    task_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:write")),
):
    """Upload a material file and extract title/doc_type/summary/keywords."""
    allowed_ext = {".doc", ".docx", ".pdf", ".txt"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_ext:
        raise HTTPException(400, f"不支持的文件格式，仅支持: {', '.join(sorted(allowed_ext))}")

    svc = MaterialService(db)
    llm = LLMService()

    def update_progress(progress: int, stage: str, status: str = "parsing", message: str = ""):
        if task_id:
            upload_progress_tracker.update(
                task_id,
                account_id=current_user.account_id,
                parse_progress=progress,
                stage=stage,
                status=status,
                message=message,
            )

    try:
        update_progress(3, "开始解析")

        file_bytes = await file.read()
        file_path = await asyncio.to_thread(svc.save_upload, file_bytes, file.filename, current_user.id)
        update_progress(12, "文件已保存")

        content_text = await asyncio.to_thread(svc.extract_text, file_path, file.filename)
        if not content_text.strip():
            raise HTTPException(400, "文件内容为空，无法处理")
        update_progress(28, "文本提取完成")

        fallback_title = await asyncio.to_thread(svc.guess_title, content_text, file.filename)
        raw_analysis = (
            await llm.invoke_async(
                MATERIAL_ANALYSIS_PROMPT.format(filename=file.filename, content=content_text[:8000]),
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
            logger.warning("LLM keywords empty, fallback to jieba for file: %s", file.filename)
            keywords = await asyncio.to_thread(svc.extract_keywords, content_text)
        update_progress(64, "AI 信息识别完成")

        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            summary = (content_text or "").replace("\n", " ").strip()[:200]

        try:
            from app.services.style_analyzer import StyleAnalyzer

            await asyncio.to_thread(
                StyleAnalyzer(db, account_id=current_user.account_id).analyze_and_store,
                content_text,
                doc_type,
            )
        except Exception as e:
            logger.warning("Style analyze skipped: %s", e)
        update_progress(76, "风格特征分析完成")

        material = await asyncio.to_thread(
            svc.create_material,
            current_user.id,
            title,
            file.filename,
            file_path,
            content_text,
            doc_type,
            summary,
            keywords,
            current_user.account_id,
        )
        update_progress(88, "素材已入库")

        try:
            await ctx_bridge.add_material(
                file_path,
                doc_type,
                title,
                content_text=content_text,
                account_id=current_user.account_id,
            )
        except Exception:
            pass
        update_progress(100, "解析完成", status="completed", message="ok")
    except HTTPException as e:
        if task_id:
            msg = e.detail if isinstance(e.detail, str) else "upload_failed"
            upload_progress_tracker.fail(task_id, message=msg)
        raise
    except Exception as e:
        error_id = _new_error_id()
        logger.exception("upload material failed. error_id=%s user_id=%s err=%s", error_id, current_user.id, e)
        if task_id:
            upload_progress_tracker.fail(task_id, message=f"处理失败，请重试（错误ID: {error_id}）")
        raise HTTPException(500, f"上传处理失败，请稍后重试（错误ID: {error_id}）")

    return {
        "id": material.id,
        "title": material.title,
        "doc_type": material.doc_type,
        "summary": material.summary,
        "keywords": material.keywords,
        "char_count": material.char_count,
    }


@router.get("/upload-tasks/{task_id}")
def get_upload_task(
    task_id: str,
    current_user: User = Depends(require_permission("materials:read")),
):
    task = upload_progress_tracker.get(task_id)
    if not task:
        raise HTTPException(404, "上传任务不存在")
    if int(task.get("account_id", 1)) != int(current_user.account_id):
        raise HTTPException(404, "上传任务不存在")
    return task


@router.get("")
def list_materials(
    doc_type: str = Query(None),
    keyword: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:read")),
):
    if doc_type:
        try:
            doc_type = ensure_canonical_doc_type(doc_type)
        except ValueError:
            raise HTTPException(400, "doc_type 非法，必须为规范文种")

    svc = MaterialService(db)
    total = svc.count_materials(
        user_id=current_user.id,
        account_id=current_user.account_id,
        doc_type=doc_type,
        keyword=keyword,
    )
    materials = svc.get_materials(
        user_id=current_user.id,
        account_id=current_user.account_id,
        doc_type=doc_type,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    svc.normalize_materials_char_count(materials)
    return {
        "items": [
            {
                "id": m.id,
                "title": m.title,
                "doc_type": m.doc_type,
                "summary": m.summary,
                "keywords": m.keywords,
                "char_count": svc.calculate_char_count(m.content_text or ""),
                "created_at": to_shanghai_iso(m.created_at),
            }
            for m in materials
        ],
        "total": total,
    }


@router.get("/search")
async def search_materials(
    query: str = Query(..., min_length=1),
    doc_type: str = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_permission("materials:read")),
):
    if doc_type:
        try:
            doc_type = ensure_canonical_doc_type(doc_type)
        except ValueError:
            raise HTTPException(400, "doc_type 非法，必须为规范文种")

    results = await ctx_bridge.search_materials(
        query,
        doc_type=doc_type,
        top_k=top_k,
        account_id=current_user.account_id,
    )
    return results


@router.get("/{material_id}")
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:read")),
):
    svc = MaterialService(db)
    material = svc.get_material(material_id, account_id=current_user.account_id)
    if not material:
        raise HTTPException(404, "素材不存在")
    if material.user_id != current_user.id:
        raise HTTPException(403, "无权访问该素材")

    old_char_count = material.char_count
    char_count = svc.normalize_material_char_count(material)
    if old_char_count != char_count:
        db.commit()

    return {
        "id": material.id,
        "title": material.title,
        "doc_type": material.doc_type,
        "summary": material.summary,
        "keywords": material.keywords,
        "content_text": material.content_text,
        "char_count": char_count,
        "original_filename": material.original_filename,
        "created_at": to_shanghai_iso(material.created_at),
    }


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:write")),
):
    svc = MaterialService(db)
    material = svc.get_material(material_id, account_id=current_user.account_id)
    if not material:
        raise HTTPException(404, "素材不存在")
    if material.user_id != current_user.id:
        raise HTTPException(403, "无权删除该素材")
    svc.delete_material(material_id, account_id=current_user.account_id)
    return {"message": "删除成功"}


class BatchDeleteRequest(BaseModel):
    ids: list[int]


class BatchClassifyRequest(BaseModel):
    ids: list[int]
    doc_type: str


class BookImportRequest(BaseModel):
    rebuild: bool = False
    selected_files: list[str] = Field(default_factory=list)


@router.get("/books/scan")
def scan_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:read")),
):
    svc = BookImportService(db, account_id=current_user.account_id)
    items = svc.scan_books()
    public_items = [
        {
            "source_name": item["source_name"],
            "relative_path": item["relative_path"],
            "source_hash": item["source_hash"],
            "file_ext": item["file_ext"],
            "file_size": item["file_size"],
            "imported": item.get("imported", False),
            "status": item.get("status", "pending"),
            "doc_type": item.get("doc_type", ""),
            "updated_at": item.get("updated_at"),
            "source_id": item.get("source_id"),
        }
        for item in items
    ]
    return {
        "books_dir": _safe_books_dir(),
        "total": len(public_items),
        "items": public_items,
    }


@router.post("/books/import")
def import_books(
    req: BookImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:write")),
):
    if req.rebuild and (current_user.role or "") != ROLE_ADMIN:
        raise HTTPException(403, "仅管理员可执行重建导入")

    svc = BookImportService(db, account_id=current_user.account_id)
    try:
        task_id, total_files = svc.start_import_task(
            rebuild=bool(req.rebuild),
            selected_files=req.selected_files,
        )
    except BookImportConflictError as e:
        raise HTTPException(409, f"已有导入任务在运行，请稍后重试（task_id: {e.active_task_id}）")

    return {
        "task_id": task_id,
        "status": "pending",
        "total_files": total_files,
    }


@router.get("/books/tasks/{task_id}")
def get_book_import_task(
    task_id: str,
    current_user: User = Depends(require_permission("books:read")),
):
    task = book_import_task_tracker.get(task_id)
    if not task:
        raise HTTPException(404, "书籍学习任务不存在")
    if int(task.get("account_id", 1)) != int(current_user.account_id):
        raise HTTPException(404, "书籍学习任务不存在")
    return task


@router.get("/books/sources")
def list_book_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:read")),
):
    total = db.query(BookSource).filter(BookSource.account_id == current_user.account_id).count()
    rows = (
        db.query(BookSource)
        .filter(BookSource.account_id == current_user.account_id)
        .order_by(BookSource.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": row.id,
                "source_name": row.source_name,
                "source_hash": row.source_hash,
                "file_ext": row.file_ext,
                "file_size": row.file_size,
                "status": row.status,
                "doc_type": row.doc_type,
                "summary": row.summary,
                "keywords": row.keywords or [],
                "chunk_count": row.chunk_count,
                "ocr_used": bool(row.ocr_used),
                "error_message": row.error_message or "",
                "metadata": row.metadata_ or {},
                "created_at": to_shanghai_iso(row.created_at),
                "updated_at": to_shanghai_iso(row.updated_at),
            }
            for row in rows
        ],
    }


@router.post("/batch-delete")
def batch_delete_materials(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:write")),
):
    if not req.ids:
        raise HTTPException(400, "请选择要删除的素材")
    svc = MaterialService(db)
    deleted = 0
    for mid in req.ids:
        if svc.delete_material(mid, account_id=current_user.account_id):
            deleted += 1
    return {"message": f"已删除 {deleted} 条素材"}


@router.post("/batch-classify")
def batch_classify_materials(
    req: BatchClassifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:write")),
):
    if not req.ids:
        raise HTTPException(400, "请选择要分类的素材")
    try:
        canonical_doc_type = ensure_canonical_doc_type(req.doc_type)
    except ValueError:
        raise HTTPException(400, "doc_type 非法，必须为规范文种")

    from app.models.material import Material

    updated = (
        db.query(Material)
        .filter(
            Material.id.in_(req.ids),
            Material.user_id == current_user.id,
            Material.account_id == current_user.account_id,
        )
        .update({"doc_type": canonical_doc_type}, synchronize_session="fetch")
    )
    db.commit()
    return {"message": f"已更新 {updated} 条素材的分类"}
