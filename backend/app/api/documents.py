from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.models.document import GeneratedDocument
from app.models.user import User
from app.prompts.doc_types_catalog import OTHER_DOC_TYPE
from app.prompts.validators import ensure_canonical_doc_type
from app.serializers import serialize_collection_response, serialize_generated_document_history_item
from app.services.docx_generator import DocxGenerator
from app.services.draft_service import DraftService
from app.services.editor_doc_parser import EditorDocParser

router = APIRouter()


DEFAULT_BODY_JSON = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}


class ExportRequest(BaseModel):
    content_json: dict
    title: str = ""
    doc_type: str = OTHER_DOC_TYPE
    session_id: int | None = None


class WriterDraftPayload(BaseModel):
    title: str = ""
    recipients: str = ""
    body_json: dict = Field(default_factory=lambda: DEFAULT_BODY_JSON.copy())
    signing_org: str = ""
    date: str = ""


class ExportEditorRequest(BaseModel):
    session_id: int
    doc_type: str = OTHER_DOC_TYPE
    draft: WriterDraftPayload


@router.post("/export")
def export_document(
    req: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:write")),
):
    try:
        canonical_doc_type = ensure_canonical_doc_type(req.doc_type)
    except ValueError:
        raise HTTPException(400, "doc_type 非法，必须为规范文种")

    gen = DocxGenerator()
    filepath = gen.generate(req.content_json)

    doc = GeneratedDocument(
        account_id=current_user.account_id,
        user_id=current_user.id,
        session_id=req.session_id,
        title=req.title,
        doc_type=canonical_doc_type,
        content_json=req.content_json,
        docx_file_path=filepath,
    )
    db.add(doc)
    db.commit()

    filename = f"{req.title or '文稿'}.docx"
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.post("/export-editor")
def export_editor_document(
    req: ExportEditorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:write")),
):
    draft_service = DraftService(db, account_id=current_user.account_id)
    session = draft_service.validate_session_owner(
        user_id=current_user.id,
        session_id=req.session_id,
    )

    parser = EditorDocParser()
    normalized_draft = parser.normalize_draft(
        req.draft.model_dump(),
        title_fallback="",
    )
    content_json = parser.draft_to_content_json(normalized_draft)

    if not content_json.get("title") and not content_json.get("body_sections"):
        raise HTTPException(400, "文稿内容为空，无法导出")

    gen = DocxGenerator()
    filepath = gen.generate(content_json)

    title = (
        str(content_json.get("title", "") or "").strip()
        or str(normalized_draft.get("title", "") or "").strip()
        or "文稿"
    )
    resolved_doc_type = req.doc_type or session.doc_type or OTHER_DOC_TYPE
    try:
        doc_type = ensure_canonical_doc_type(resolved_doc_type)
    except ValueError:
        raise HTTPException(400, "doc_type 非法，必须为规范文种")

    doc = GeneratedDocument(
        account_id=current_user.account_id,
        user_id=current_user.id,
        session_id=req.session_id,
        title=title,
        doc_type=doc_type,
        content_json=content_json,
        content_text=parser.draft_to_plain_text(normalized_draft),
        docx_file_path=filepath,
    )
    db.add(doc)
    db.commit()

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{title}.docx",
    )


@router.get("/history")
def list_export_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:read")),
):
    base_query = db.query(GeneratedDocument).filter(
        GeneratedDocument.account_id == current_user.account_id,
        GeneratedDocument.user_id == current_user.id,
    )
    total = base_query.count()
    docs = base_query.order_by(GeneratedDocument.created_at.desc()).offset(skip).limit(limit).all()
    items = [serialize_generated_document_history_item(document) for document in docs]
    return serialize_collection_response(items, total=total)


@router.get("/history/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:read")),
):
    doc = db.query(GeneratedDocument).filter(
        GeneratedDocument.account_id == current_user.account_id,
        GeneratedDocument.id == doc_id,
        GeneratedDocument.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    if not doc.docx_file_path or not Path(doc.docx_file_path).exists():
        raise HTTPException(404, "文件已被清理，请重新导出")
    return FileResponse(
        doc.docx_file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{doc.title or '文稿'}.docx",
    )
