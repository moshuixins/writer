import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.docx_generator import DocxGenerator
from app.models.document import GeneratedDocument

router = APIRouter()


class ExportRequest(BaseModel):
    content_json: dict
    title: str = ""
    doc_type: str = ""
    session_id: int = None


@router.post("/export")
def export_document(
    req: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出公文为docx文件"""
    gen = DocxGenerator()
    filepath = gen.generate(req.content_json)

    # 保存记录
    doc = GeneratedDocument(
        user_id=current_user.id,
        session_id=req.session_id,
        title=req.title,
        doc_type=req.doc_type,
        content_json=req.content_json,
        docx_file_path=filepath,
    )
    db.add(doc)
    db.commit()

    filename = f"{req.title or '公文'}.docx"
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/history")
def list_export_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取导出历史列表"""
    docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.user_id == current_user.id,
    ).order_by(GeneratedDocument.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "doc_type": d.doc_type,
            "version": d.version,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/history/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新下载已导出的文档"""
    doc = db.query(GeneratedDocument).filter(
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
        filename=f"{doc.title or '公文'}.docx",
    )
