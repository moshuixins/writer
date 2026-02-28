from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.memory_service import MemoryService

router = APIRouter()


class SetPreferenceRequest(BaseModel):
    key: str
    value: str


class BatchPreferenceRequest(BaseModel):
    signature_org: str = ""
    default_tone: str = "formal"
    default_recipients: str = ""
    avoid_phrases: str = ""


@router.get("")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户所有偏好"""
    svc = MemoryService(db)
    return svc.get_preferences(user_id=current_user.id)


@router.put("")
def set_preference(
    req: SetPreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置用户偏好"""
    svc = MemoryService(db)
    svc.set_preference(user_id=current_user.id, key=req.key, value=req.value)
    return {"message": "偏好已保存"}


@router.put("/batch")
def set_preferences_batch(
    req: BatchPreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量设置用户偏好"""
    svc = MemoryService(db)
    for key, value in req.model_dump().items():
        svc.set_preference(user_id=current_user.id, key=key, value=value)
    return {"message": "偏好已保存"}
