from __future__ import annotations

import json

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.book_source import BookSource
from app.models.chat import ChatMessage, ChatSession
from app.models.document import GeneratedDocument
from app.models.invite_code import InviteCode
from app.models.material import Material
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services.rbac_service import RBACService
from app.timezone import to_shanghai_iso


def _sanitize_display_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    placeholder_chars = {"?", "？", "\uFFFD"}
    if all(char in placeholder_chars for char in text):
        return ""

    return text


def serialize_auth_user(db: Session, user: User) -> dict[str, Any]:
    service = RBACService(db)
    service.attach_user_access_context(user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": _sanitize_display_text(user.display_name),
        "department": _sanitize_display_text(user.department),
        "role": getattr(user, "_primary_role", user.role),
        "roles": list(getattr(user, "_role_codes", []) or []),
        "account_id": user.account_id,
    }


def serialize_auth_token_response(db: Session, user: User, token: str) -> dict[str, Any]:
    return {
        "token": token,
        "user": serialize_auth_user(db, user),
    }


def serialize_message_response(message: str) -> dict[str, str]:
    return {"message": message}


def serialize_chat_reply(reply: str) -> dict[str, str]:
    return {"reply": reply}


def _serialize_sse_payload(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def serialize_chat_workflow_sse(step: str, status: str, detail: str | None = None) -> str:
    payload: dict[str, Any] = {
        "event": "workflow",
        "step": step,
        "status": status,
    }
    if detail:
        payload["detail"] = detail
    return _serialize_sse_payload(payload)


def serialize_chat_chunk_sse(chunk: str) -> str:
    return _serialize_sse_payload({"chunk": chunk})


def serialize_chat_error_sse(message: str) -> str:
    return _serialize_sse_payload({"error": message})


def serialize_chat_done_sse() -> str:
    return "data: [DONE]\n\n"


def serialize_collection_response(items: list[Any], *, total: int, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "items": items,
        "total": int(total),
    }
    payload.update(extra)
    return payload


def serialize_account(account: Account, *, user_count: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": account.id,
        "code": account.code,
        "name": account.name,
        "status": account.status,
        "created_at": to_shanghai_iso(account.created_at),
        "updated_at": to_shanghai_iso(account.updated_at),
    }
    if user_count is not None:
        payload["user_count"] = int(user_count)
    return payload


def serialize_permission(permission: Permission) -> dict[str, Any]:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "description": permission.description or "",
        "is_system": bool(permission.is_system),
    }


def serialize_role_list(db: Session, account_id: int) -> list[dict[str, Any]]:
    service = RBACService(db)
    roles = service.list_roles(account_id)
    perm_map = service.role_permission_codes(roles)
    return [service.serialize_role(role, perm_map.get(int(role.id), [])) for role in roles]


def serialize_account_users(db: Session, users: list[User]) -> list[dict[str, Any]]:
    service = RBACService(db)
    user_ids = [int(user.id) for user in users]
    role_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    if user_ids:
        rows = (
            db.query(UserRole.user_id, Role.id, Role.code, Role.name, Role.is_system)
            .join(Role, Role.id == UserRole.role_id)
            .filter(UserRole.user_id.in_(user_ids), Role.status == "active")
            .order_by(Role.is_system.desc(), Role.created_at.asc(), Role.id.asc())
            .all()
        )
        for user_id, role_id, code, name, is_system in rows:
            role_map[int(user_id)].append(
                {
                    "id": int(role_id),
                    "code": str(code),
                    "name": str(name),
                    "is_system": bool(is_system),
                },
            )

    items: list[dict[str, Any]] = []
    for user in users:
        role_items = role_map.get(int(user.id), [])
        role_codes = [item["code"] for item in role_items]
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "display_name": _sanitize_display_text(user.display_name),
                "department": _sanitize_display_text(user.department),
                "role": service.get_primary_role_code(user, role_codes),
                "role_codes": role_codes,
                "roles": role_items,
                "created_at": to_shanghai_iso(user.created_at),
            },
        )
    return items


def serialize_invite(invite: InviteCode, *, invite_code: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": invite.id,
        "account_id": invite.account_id,
        "status": invite.status,
        "created_by": invite.created_by,
        "used_by": invite.used_by,
        "created_at": to_shanghai_iso(invite.created_at),
        "used_at": to_shanghai_iso(invite.used_at),
        "expires_at": to_shanghai_iso(invite.expires_at),
    }
    if invite_code is not None:
        payload["invite_id"] = invite.id
        payload["invite_code"] = invite_code
    return payload


def serialize_chat_session(
    session: ChatSession,
    *,
    include_status: bool = True,
    include_created_at: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": session.id,
        "title": session.title,
        "doc_type": session.doc_type,
    }
    if include_status:
        payload["status"] = session.status
    if include_created_at:
        payload["created_at"] = to_shanghai_iso(session.created_at)
    return payload


def serialize_chat_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": to_shanghai_iso(message.created_at),
    }


def serialize_draft_response(
    *,
    session_id: int,
    draft: dict[str, Any],
    exists: bool,
    updated_at: datetime | None,
    save_mode: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "exists": bool(exists),
        "session_id": session_id,
        "updated_at": to_shanghai_iso(updated_at),
        "draft": draft,
    }
    if save_mode is not None:
        payload["save_mode"] = save_mode
    return payload


def _material_base(material: Material, *, char_count: int | None = None) -> dict[str, Any]:
    return {
        "id": material.id,
        "title": material.title,
        "doc_type": material.doc_type,
        "summary": material.summary,
        "keywords": material.keywords or [],
        "char_count": int(char_count if char_count is not None else (material.char_count or 0)),
    }


def serialize_material_upload_result(material: Material) -> dict[str, Any]:
    return _material_base(material)


def serialize_material_list_item(material: Material, *, char_count: int | None = None) -> dict[str, Any]:
    payload = _material_base(material, char_count=char_count)
    payload["created_at"] = to_shanghai_iso(material.created_at)
    return payload


def serialize_material_detail(material: Material, *, char_count: int | None = None) -> dict[str, Any]:
    payload = _material_base(material, char_count=char_count)
    payload["content_text"] = material.content_text
    payload["original_filename"] = material.original_filename
    payload["created_at"] = to_shanghai_iso(material.created_at)
    return payload


def _serialize_datetime_like(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_shanghai_iso(value)
    return str(value)


def serialize_book_scan_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": item["source_name"],
        "relative_path": item["relative_path"],
        "source_hash": item["source_hash"],
        "file_ext": item["file_ext"],
        "file_size": item["file_size"],
        "imported": bool(item.get("imported", False)),
        "status": item.get("status", "pending"),
        "doc_type": item.get("doc_type", ""),
        "updated_at": _serialize_datetime_like(item.get("updated_at")),
        "source_id": item.get("source_id"),
    }


def serialize_upload_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(task.get("task_id", "")),
        "status": str(task.get("status", "pending")),
        "stage": str(task.get("stage", "")),
        "message": str(task.get("message", "")),
        "parse_progress": int(task.get("parse_progress", 0) or 0),
        "updated_at": int(task.get("updated_at", 0) or 0),
    }


def serialize_book_import_file_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": str(item.get("source_name", "")),
        "status": str(item.get("status", "pending")),
        "chunk_count": int(item.get("chunk_count", 0) or 0),
        "ocr_used": bool(item.get("ocr_used", False)),
        "ocr_pages": int(item.get("ocr_pages", 0) or 0),
        "error_message": str(item.get("error_message", "")),
    }


def serialize_book_import_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(task.get("task_id", "")),
        "status": str(task.get("status", "pending")),
        "stage": str(task.get("stage", "")),
        "message": str(task.get("message", "")),
        "rebuild": bool(task.get("rebuild", False)),
        "started_at": int(task.get("started_at", 0) or 0),
        "updated_at": int(task.get("updated_at", 0) or 0),
        "finished_at": int(task.get("finished_at", 0)) if task.get("finished_at") else None,
        "total_files": int(task.get("total_files", 0) or 0),
        "completed_files": int(task.get("completed_files", 0) or 0),
        "failed_files": int(task.get("failed_files", 0) or 0),
        "partial_files": int(task.get("partial_files", 0) or 0),
        "skipped_files": int(task.get("skipped_files", 0) or 0),
        "running_file": str(task.get("running_file", "")),
        "file_progress": int(task.get("file_progress", 0) or 0),
        "total_chunks": int(task.get("total_chunks", 0) or 0),
        "completed_chunks": int(task.get("completed_chunks", 0) or 0),
        "chunk_progress": int(task.get("chunk_progress", 0) or 0),
        "overall_progress": int(task.get("overall_progress", 0) or 0),
        "ocr_used_files": int(task.get("ocr_used_files", 0) or 0),
        "ocr_pages": int(task.get("ocr_pages", 0) or 0),
        "file_results": [serialize_book_import_file_result(item) for item in list(task.get("file_results", []))],
    }


def serialize_book_import_start_response(task_id: str, *, total_files: int, status: str = "pending") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": status,
        "total_files": int(total_files),
    }


def serialize_book_source(source: BookSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "source_name": source.source_name,
        "source_hash": source.source_hash,
        "file_ext": source.file_ext,
        "file_size": source.file_size,
        "status": source.status,
        "doc_type": source.doc_type,
        "summary": source.summary,
        "keywords": source.keywords or [],
        "chunk_count": source.chunk_count,
        "ocr_used": bool(source.ocr_used),
        "error_message": source.error_message or "",
        "metadata": source.metadata_ or {},
        "created_at": to_shanghai_iso(source.created_at),
        "updated_at": to_shanghai_iso(source.updated_at),
    }


def serialize_generated_document_history_item(document: GeneratedDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "title": document.title,
        "doc_type": document.doc_type,
        "version": document.version,
        "created_at": to_shanghai_iso(document.created_at),
    }
