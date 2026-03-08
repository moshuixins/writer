from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.rbac import ROLE_ADMIN
from app.services.rbac_service import user_has_role
from app.config import get_settings
from app.database import get_db
from app.errors import AppError, FileValidationError, logger
from app.models.book_source import BookSource
from app.models.user import User
from app.prompts.validators import ensure_canonical_doc_type
from app.schemas.common import MessageResponse
from app.schemas.materials import (
    BookImportStartResponse,
    BookImportTaskResponse,
    BookScanResponse,
    BookSourceListResponse,
    BookUploadResponse,
    MaterialListResponse,
    MaterialResponse,
    MaterialSearchResponse,
    MaterialUploadResponse,
    UploadTaskResponse,
)
from app.serializers import (
    serialize_book_import_start_response,
    serialize_book_import_task,
    serialize_book_scan_item,
    serialize_book_source,
    serialize_book_upload_response,
    serialize_collection_response,
    serialize_material_detail,
    serialize_material_list_item,
    serialize_material_search_hit,
    serialize_material_upload_result,
    serialize_message_response,
    serialize_upload_task,
)
from app.services.book_import_service import BookImportConflictError, BookImportService
from app.services.book_import_task_service import book_import_task_tracker
from app.services.context_bridge import ContextBridge
from app.services.material_ingestion_service import MaterialIngestionService
from app.services.material_service import MaterialService
from app.side_effects import new_error_id
from app.services.upload_progress_service import upload_progress_tracker

router = APIRouter()
ctx_bridge = ContextBridge()
settings = get_settings()


def _safe_books_dir() -> str:
    # avoid leaking absolute server path
    configured = Path(settings.books_dir)
    parts = configured.parts
    if "data" in parts:
        idx = parts.index("data")
        return "/".join(parts[idx:])
    return "data/book"


@router.post("/upload", response_model=MaterialUploadResponse)
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
        file_bytes = await file.read()
        result = await MaterialIngestionService(
            db,
            account_id=current_user.account_id,
            user_id=current_user.id,
        ).ingest_upload(
            file_bytes=file_bytes,
            filename=file.filename,
            context_bridge=ctx_bridge,
            progress_callback=update_progress,
        )
    except AppError as e:
        db.rollback()
        if task_id:
            upload_progress_tracker.fail(task_id, message=e.message)
        raise
    except Exception as e:
        db.rollback()
        error_id = new_error_id()
        logger.exception("upload material failed. error_id=%s user_id=%s err=%s", error_id, current_user.id, e)
        if task_id:
            upload_progress_tracker.fail(task_id, message=f"处理失败，请重试（错误ID: {error_id}）")
        raise AppError(
            "上传处理失败，请稍后重试",
            detail=str(e),
            error_id=error_id,
        ) from e

    return serialize_material_upload_result(result.material, warnings=result.warnings)


@router.get("/upload-tasks/{task_id}", response_model=UploadTaskResponse)
def get_upload_task(
    task_id: str,
    current_user: User = Depends(require_permission("materials:read")),
):
    task = upload_progress_tracker.get(task_id)
    if not task:
        raise HTTPException(404, "上传任务不存在")
    if int(task.get("account_id", 1)) != int(current_user.account_id):
        raise HTTPException(404, "上传任务不存在")
    return serialize_upload_task(task)


@router.get("", response_model=MaterialListResponse)
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
    changed = svc.normalize_materials_char_count(materials)
    if changed:
        db.commit()
    items = [
        serialize_material_list_item(material, char_count=svc.calculate_char_count(material.content_text or ""))
        for material in materials
    ]
    return serialize_collection_response(items, total=total)


@router.get("/search", response_model=MaterialSearchResponse)
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
    items = [serialize_material_search_hit(item) for item in results]
    return serialize_collection_response(items, total=len(items))


@router.get("/{material_id}", response_model=MaterialResponse)
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

    return serialize_material_detail(material, char_count=char_count)


@router.delete("/{material_id}", response_model=MessageResponse)
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
    try:
        file_path = svc.delete_material(material_id, account_id=current_user.account_id, commit=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    svc.cleanup_material_file(file_path)
    return serialize_message_response("删除成功")


class BatchDeleteRequest(BaseModel):
    ids: list[int]


class BatchClassifyRequest(BaseModel):
    ids: list[int]
    doc_type: str


class BookImportRequest(BaseModel):
    rebuild: bool = False
    selected_files: list[str] = Field(default_factory=list)


@router.post("/books/upload", response_model=BookUploadResponse)
async def upload_books(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:write")),
):
    if not files:
        raise HTTPException(400, "请选择要导入的书籍文件")

    svc = BookImportService(db, account_id=current_user.account_id)
    uploaded_items: list[dict] = []
    errors: list[dict[str, str]] = []

    for file in files:
        source_name = Path(file.filename or '').name or '未命名文件'
        try:
            file_bytes = await file.read()
            item = await asyncio.to_thread(svc.save_book_upload, file_bytes, source_name)
            uploaded_items.append(item)
        except FileValidationError as exc:
            errors.append({
                "source_name": source_name,
                "error_message": str(exc),
            })
        except Exception as exc:
            error_id = new_error_id()
            logger.exception(
                "upload books failed. error_id=%s user_id=%s filename=%s err=%s",
                error_id,
                current_user.id,
                source_name,
                exc,
            )
            errors.append({
                "source_name": source_name,
                "error_message": f"上传失败，请稍后重试（错误ID: {error_id}）",
            })

    return serialize_book_upload_response(
        uploaded_items,
        uploaded_count=len(uploaded_items),
        failed_count=len(errors),
        errors=errors,
    )


@router.get("/books/scan", response_model=BookScanResponse)
def scan_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:read")),
):
    svc = BookImportService(db, account_id=current_user.account_id)
    items = svc.scan_books()
    public_items = [serialize_book_scan_item(item) for item in items]
    return serialize_collection_response(public_items, total=len(public_items), books_dir=_safe_books_dir())


@router.post("/books/import", response_model=BookImportStartResponse)
def import_books(
    req: BookImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("books:write")),
):
    if req.rebuild and not user_has_role(current_user, ROLE_ADMIN):
        raise HTTPException(403, "仅管理员可执行重建导入")

    svc = BookImportService(db, account_id=current_user.account_id)
    try:
        task_id, total_files = svc.start_import_task(
            rebuild=bool(req.rebuild),
            selected_files=req.selected_files,
        )
    except BookImportConflictError as e:
        raise HTTPException(409, f"已有导入任务在运行，请稍后重试（task_id: {e.active_task_id}）")

    return serialize_book_import_start_response(task_id, total_files=total_files)


@router.get("/books/tasks/{task_id}", response_model=BookImportTaskResponse)
def get_book_import_task(
    task_id: str,
    current_user: User = Depends(require_permission("books:read")),
):
    task = book_import_task_tracker.get(task_id)
    if not task:
        raise HTTPException(404, "书籍学习任务不存在")
    if int(task.get("account_id", 1)) != int(current_user.account_id):
        raise HTTPException(404, "书籍学习任务不存在")
    return serialize_book_import_task(task)


@router.get("/books/sources", response_model=BookSourceListResponse)
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
    items = [serialize_book_source(row) for row in rows]
    return serialize_collection_response(items, total=total)


@router.post("/batch-delete", response_model=MessageResponse)
def batch_delete_materials(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("materials:write")),
):
    if not req.ids:
        raise HTTPException(400, "请选择要删除的素材")
    svc = MaterialService(db)
    deleted = 0
    file_paths: list[str | None] = []
    try:
        for mid in req.ids:
            material = svc.get_material(mid, account_id=current_user.account_id)
            if not material or material.user_id != current_user.id:
                continue
            file_paths.append(svc.delete_material(mid, account_id=current_user.account_id, commit=False))
            deleted += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    for file_path in file_paths:
        svc.cleanup_material_file(file_path)
    return serialize_message_response(f"已删除 {deleted} 条素材")


@router.post("/batch-classify", response_model=MessageResponse)
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
    return serialize_message_response(f"已更新 {updated} 条素材的分类")
