import json
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.material_service import MaterialService
from app.services.llm_service import LLMService
from app.services.context_bridge import ContextBridge
from app.services.upload_progress_service import upload_progress_tracker
from app.prompts.material_analysis import MATERIAL_ANALYSIS_PROMPT
from app.prompts.validators import (
    parse_json_response,
    validate_classify,
    validate_keywords,
    validate_title,
)
from app.errors import logger
from app.timezone import to_shanghai_iso

router = APIRouter()
ctx_bridge = ContextBridge()


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    task_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材文件，自动分类和摘要"""
    allowed_ext = {".doc", ".docx", ".pdf", ".txt"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_ext:
        raise HTTPException(400, f"不支持的文件格式，仅支持: {', '.join(allowed_ext)}")

    svc = MaterialService(db)
    llm = LLMService()

    def update_progress(progress: int, stage: str, status: str = "parsing", message: str = ""):
        if task_id:
            upload_progress_tracker.update(
                task_id,
                parse_progress=progress,
                stage=stage,
                status=status,
                message=message,
            )

    try:
        update_progress(3, "开始解析")

        # 1. 保存文件
        file_bytes = await file.read()
        file_path = svc.save_upload(file_bytes, file.filename, user_id=current_user.id)
        update_progress(12, "文件已保存")

        # 2. 提取文本
        content_text = svc.extract_text(file_path, file.filename)
        if not content_text.strip():
            raise HTTPException(400, "文件内容为空，无法处理")
        update_progress(28, "文本提取完成")

        # 3-6. 一次 LLM 调用识别标题/关键词/类型/摘要
        fallback_title = svc.guess_title(content_text, file.filename)
        raw_analysis = llm.invoke(
            MATERIAL_ANALYSIS_PROMPT.format(filename=file.filename, content=content_text[:8000]),
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
            keywords = svc.extract_keywords(content_text)
        update_progress(64, "AI 信息识别完成")

        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            # 兜底为文本前 200 字，避免摘要字段为空。
            summary = (content_text or "").replace("\n", " ").strip()[:200]

        # 6.5 风格学习
        try:
            from app.services.style_analyzer import StyleAnalyzer

            StyleAnalyzer(db).analyze_and_store(content_text, doc_type)
        except Exception as e:
            logger.warning("风格分析失败: %s", e)
        update_progress(76, "风格特征分析完成")

        # 7. 存入数据库
        material = svc.create_material(
            user_id=current_user.id,
            title=title,
            filename=file.filename,
            file_path=file_path,
            content_text=content_text,
            doc_type=doc_type,
            summary=summary,
            keywords=keywords,
        )
        update_progress(88, "素材已入库")

        # 8. 存入 OpenViking 向量库（传纯文本，避免 OV 解析 docx 兼容性问题）
        try:
            await ctx_bridge.add_material(
                file_path, doc_type, title, content_text=content_text
            )
        except Exception:
            pass  # OpenViking 不可用时不阻塞上传
        update_progress(100, "解析完成", status="completed", message="ok")
    except HTTPException as e:
        if task_id:
            upload_progress_tracker.fail(task_id, message=e.detail if isinstance(e.detail, str) else "upload_failed")
        raise
    except Exception as e:
        if task_id:
            upload_progress_tracker.fail(task_id, message=str(e))
        raise

    return {
        "id": material.id,
        "title": material.title,
        "doc_type": material.doc_type,
        "summary": material.summary,
        "keywords": material.keywords,
        "char_count": material.char_count,
    }


@router.get("/upload-tasks/{task_id}")
def get_upload_task(task_id: str):
    task = upload_progress_tracker.get(task_id)
    if not task:
        raise HTTPException(404, "上传任务不存在")
    return task


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
    total = svc.count_materials(
        user_id=current_user.id,
        doc_type=doc_type,
        keyword=keyword,
    )
    materials = svc.get_materials(
        user_id=current_user.id,
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
    old_char_count = m.char_count
    char_count = svc.normalize_material_char_count(m)
    if old_char_count != char_count:
        db.commit()
    return {
        "id": m.id,
        "title": m.title,
        "doc_type": m.doc_type,
        "summary": m.summary,
        "keywords": m.keywords,
        "content_text": m.content_text,
        "char_count": char_count,
        "original_filename": m.original_filename,
        "created_at": to_shanghai_iso(m.created_at),
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

    updated = (
        db.query(Material)
        .filter(
            Material.id.in_(req.ids),
            Material.user_id == current_user.id,
        )
        .update({"doc_type": req.doc_type}, synchronize_session="fetch")
    )
    db.commit()
    return {"message": f"已更新 {updated} 条素材的分类"}
