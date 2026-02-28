from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.material_service import MaterialService
from app.services.llm_service import LLMService
from app.services.context_bridge import ContextBridge
from app.prompts.classify import CLASSIFY_PROMPT
from app.prompts.summarize import SUMMARIZE_PROMPT
from app.prompts.validators import validate_classify

router = APIRouter()
ctx_bridge = ContextBridge()


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材文件，自动分类和摘要"""
    allowed_ext = {".docx", ".pdf", ".txt"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_ext:
        raise HTTPException(400, f"不支持的文件格式，仅支持: {', '.join(allowed_ext)}")

    svc = MaterialService(db)
    llm = LLMService()

    # 1. 保存文件
    file_bytes = await file.read()
    file_path = svc.save_upload(file_bytes, file.filename, user_id=current_user.id)

    # 2. 提取文本
    content_text = svc.extract_text(file_path, file.filename)
    if not content_text.strip():
        raise HTTPException(400, "文件内容为空，无法处理")

    # 3. 猜测标题
    title = svc.guess_title(content_text, file.filename)

    # 4. 提取关键词
    keywords = svc.extract_keywords(content_text)

    # 5. LLM分类
    truncated = content_text[:3000]
    raw_type = llm.invoke(CLASSIFY_PROMPT.format(content=truncated)).strip()
    doc_type = validate_classify(raw_type)

    # 6. LLM摘要
    summary = llm.invoke(SUMMARIZE_PROMPT.format(content=truncated)).strip()

    # 7. 存入数据库
    material = svc.create_material(
        user_id=current_user.id, title=title, filename=file.filename,
        file_path=file_path, content_text=content_text,
        doc_type=doc_type, summary=summary, keywords=keywords,
    )

    # 8. 存入 OpenViking 向量库（传纯文本，避免 OV 解析 docx 兼容性问题）
    try:
        await ctx_bridge.add_material(file_path, doc_type, title, content_text=content_text)
    except Exception:
        pass  # OpenViking 不可用时不阻塞上传

    return {
        "id": material.id,
        "title": material.title,
        "doc_type": material.doc_type,
        "summary": material.summary,
        "keywords": material.keywords,
        "char_count": material.char_count,
    }


@router.get("")
def list_materials(
    doc_type: str = Query(None),
    keyword: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取素材列表"""
    svc = MaterialService(db)
    materials = svc.get_materials(
        user_id=current_user.id, doc_type=doc_type,
        keyword=keyword, skip=skip, limit=limit,
    )
    return [
        {
            "id": m.id, "title": m.title,
            "doc_type": m.doc_type, "summary": m.summary,
            "keywords": m.keywords, "char_count": m.char_count,
            "created_at": m.created_at.isoformat(),
        }
        for m in materials
    ]


@router.get("/search")
async def search_materials(
    query: str = Query(..., min_length=1),
    doc_type: str = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """语义搜索素材（通过 OpenViking 层级检索）"""
    results = await ctx_bridge.search_materials(query, doc_type=doc_type, top_k=top_k)
    return results


@router.get("/{material_id}")
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取素材详情"""
    svc = MaterialService(db)
    m = svc.get_material(material_id)
    if not m:
        raise HTTPException(404, "素材不存在")
    if m.user_id != current_user.id:
        raise HTTPException(403, "无权访问该素材")
    return {
        "id": m.id, "title": m.title,
        "doc_type": m.doc_type, "summary": m.summary,
        "keywords": m.keywords, "content_text": m.content_text,
        "char_count": m.char_count,
        "original_filename": m.original_filename,
        "created_at": m.created_at.isoformat(),
    }


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除素材"""
    svc = MaterialService(db)
    m = svc.get_material(material_id)
    if not m:
        raise HTTPException(404, "素材不存在")
    if m.user_id != current_user.id:
        raise HTTPException(403, "无权删除该素材")
    svc.delete_material(material_id)
    return {"message": "删除成功"}


class BatchDeleteRequest(BaseModel):
    ids: list[int]


class BatchClassifyRequest(BaseModel):
    ids: list[int]
    doc_type: str


@router.post("/batch-delete")
def batch_delete_materials(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除素材"""
    if not req.ids:
        raise HTTPException(400, "请选择要删除的素材")
    svc = MaterialService(db)
    deleted = 0
    for mid in req.ids:
        if svc.delete_material(mid):
            deleted += 1
    return {"message": f"已删除 {deleted} 条素材"}


@router.post("/batch-classify")
def batch_classify_materials(
    req: BatchClassifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量修改素材分类"""
    if not req.ids:
        raise HTTPException(400, "请选择要分类的素材")
    from app.models.material import Material
    updated = db.query(Material).filter(
        Material.id.in_(req.ids),
        Material.user_id == current_user.id,
    ).update({"doc_type": req.doc_type}, synchronize_session="fetch")
    db.commit()
    return {"message": f"已更新 {updated} 条素材的分类"}
