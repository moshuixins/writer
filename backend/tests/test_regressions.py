import hashlib
import json
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

TEMP_DIR = Path(tempfile.mkdtemp(prefix="writer-backend-tests-"))
os.environ.setdefault("SECRET_KEY", "test-secret-key-1234567890")
os.environ.setdefault("OPENVIKING_ROOT_API_KEY", "ov-test-secret-key-1234567890")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DIR / 'writer-test.db'}"
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: E402,F401
from fastapi.testclient import TestClient  # noqa: E402

from app.api import chat as chat_api  # noqa: E402
from app.auth import create_access_token, hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.book_import_task import BookImportTask  # noqa: E402
from app.models.chat import ChatMessage, ChatSession  # noqa: E402
from app.models.document import GeneratedDocument  # noqa: E402
from app.models.material import Material  # noqa: E402
from app.models.invite_code import InviteCode  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schema_bootstrap import ensure_account_schema, _mark_interrupted_book_tasks  # noqa: E402
from app.serializers import (  # noqa: E402
    serialize_book_scan_item,
    serialize_chat_chunk_sse,
    serialize_chat_done_sse,
    serialize_chat_error_sse,
    serialize_chat_workflow_sse,
)
from app.services.book_import_task_service import BookImportTaskTracker, book_import_task_tracker  # noqa: E402
from app.services.rbac_service import RBACService  # noqa: E402
from app.services.upload_progress_service import upload_progress_tracker  # noqa: E402


class BackendRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        ensure_account_schema(engine)

    def _db(self):
        return SessionLocal()

    def _auth_headers(self, user_id: int) -> dict[str, str]:
        token = create_access_token(user_id)
        return {"Authorization": f"Bearer {token}"}

    def _create_user(
        self,
        username: str,
        *,
        account_id: int = 1,
        role_codes: list[str] | None = None,
        legacy_role: str = "writer",
    ) -> User:
        db = self._db()
        try:
            user = User(
                account_id=account_id,
                username=username,
                password_hash=hash_password("password123"),
                display_name=username,
                department="test",
                role=legacy_role,
            )
            db.add(user)
            db.flush()
            service = RBACService(db)
            service.ensure_account_system_roles(account_id)
            service.set_user_roles(user, role_codes or ["writer"])
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user
        finally:
            db.close()

    def _create_session(
        self,
        user_id: int,
        *,
        account_id: int = 1,
        title: str = "会话",
        doc_type: str | None = None,
        status: str = "active",
    ) -> ChatSession:
        db = self._db()
        try:
            session = ChatSession(account_id=account_id, user_id=user_id, title=title, doc_type=doc_type, status=status)
            db.add(session)
            db.commit()
            db.refresh(session)
            db.expunge(session)
            return session
        finally:
            db.close()

    def test_register_invite_code_single_use(self) -> None:
        invite_code = "INVITE-ONE-TIME"
        db = self._db()
        try:
            invite = InviteCode(
                account_id=1,
                code_hash=hashlib.sha256(invite_code.encode("utf-8")).hexdigest(),
                status="active",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(invite)
            db.commit()
        finally:
            db.close()

        first = self.client.post(
            "/api/auth/register",
            json={
                "username": "writer_a",
                "password": "password123",
                "display_name": "writer_a",
                "department": "test",
                "invite_code": invite_code,
            },
        )
        self.assertEqual(first.status_code, 200, first.text)

        second = self.client.post(
            "/api/auth/register",
            json={
                "username": "writer_b",
                "password": "password123",
                "display_name": "writer_b",
                "department": "test",
                "invite_code": invite_code,
            },
        )
        self.assertEqual(second.status_code, 400, second.text)

        db = self._db()
        try:
            invite = db.query(InviteCode).filter(InviteCode.code_hash == hashlib.sha256(invite_code.encode("utf-8")).hexdigest()).first()
            self.assertIsNotNone(invite)
            self.assertEqual(invite.status, "used")
            self.assertIsNotNone(invite.used_by)

            users = db.query(User).filter(User.username.in_(["writer_a", "writer_b"])).order_by(User.username.asc()).all()
            self.assertEqual([user.username for user in users], ["writer_a"])

            created = users[0]
            role_codes = RBACService(db).get_user_role_codes(created)
            self.assertEqual(role_codes, ["writer"])
        finally:
            db.close()

    def test_accounts_permission_depends_on_persisted_roles(self) -> None:
        user = self._create_user("writer_only", role_codes=["writer"], legacy_role="writer")
        headers = self._auth_headers(user.id)

        denied = self.client.get("/api/accounts/permissions", headers=headers)
        self.assertEqual(denied.status_code, 403, denied.text)

        db = self._db()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            RBACService(db).set_user_roles(db_user, ["admin"])
            db.commit()
        finally:
            db.close()

        allowed = self.client.get("/api/accounts/permissions", headers=headers)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        payload = allowed.json()
        self.assertTrue(any(item["code"] == "accounts:read" for item in payload.get("items", [])))

    def test_finish_session_does_not_submit_memory(self) -> None:
        user = self._create_user("finish_user")
        session = self._create_session(user.id)
        headers = self._auth_headers(user.id)

        with patch.object(chat_api.ctx_bridge, "add_memory_note", new=AsyncMock()) as add_memory_note:
            response = self.client.post(f"/api/chat/sessions/{session.id}/finish", headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            add_memory_note.assert_not_awaited()

        db = self._db()
        try:
            row = db.query(ChatSession).filter(ChatSession.id == session.id).first()
            self.assertEqual(row.status, "finished")
        finally:
            db.close()

    def test_chat_sse_event_serializers(self) -> None:
        workflow = serialize_chat_workflow_sse("分析请求意图", "running")
        chunk = serialize_chat_chunk_sse("段落")
        error = serialize_chat_error_sse("流式生成失败（错误ID: err-1）")
        done = serialize_chat_done_sse()

        self.assertEqual(workflow, "data: {\"event\": \"workflow\", \"step\": \"分析请求意图\", \"status\": \"running\"}\n\n")
        self.assertEqual(chunk, "data: {\"chunk\": \"段落\"}\n\n")
        self.assertEqual(error, "data: {\"error\": \"流式生成失败（错误ID: err-1）\"}\n\n")
        self.assertEqual(done, "data: [DONE]\n\n")

    def test_stream_failure_does_not_persist_assistant_message(self) -> None:
        user = self._create_user("stream_user")
        session = self._create_session(user.id)
        headers = self._auth_headers(user.id)

        with patch.object(chat_api.WritingService, "guidance_stream", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/api/chat/send-stream",
                json={"session_id": session.id, "message": "请帮我起草通知"},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("流式生成失败", response.text)
        sse_payloads = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: {")
        ]
        self.assertTrue(any(item.get("event") == "workflow" for item in sse_payloads))
        self.assertTrue(any("error" in item for item in sse_payloads))
        self.assertTrue(response.text.strip().endswith("data: [DONE]"))

        db = self._db()
        try:
            messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.id.asc()).all()
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0].role, "user")
            self.assertEqual(messages[0].content, "请帮我起草通知")
        finally:
            db.close()

    def test_chat_serialized_responses(self) -> None:
        user = self._create_user("chat_shape_user")
        session = self._create_session(user.id, title="chat-shape", doc_type="\u5176\u4ed6")

        db = self._db()
        try:
            db.add(ChatMessage(account_id=1, session_id=session.id, role="assistant", content="reply"))
            db.commit()
        finally:
            db.close()

        headers = self._auth_headers(user.id)

        sessions_response = self.client.get("/api/chat/sessions", headers=headers)
        self.assertEqual(sessions_response.status_code, 200, sessions_response.text)
        sessions_payload = sessions_response.json()
        self.assertEqual(len(sessions_payload), 1)
        self.assertEqual(sessions_payload[0]["title"], "chat-shape")
        self.assertEqual(sessions_payload[0]["doc_type"], "\u5176\u4ed6")
        self.assertEqual(sessions_payload[0]["status"], "active")
        self.assertIsInstance(sessions_payload[0]["created_at"], str)

        messages_response = self.client.get(f"/api/chat/sessions/{session.id}/messages", headers=headers)
        self.assertEqual(messages_response.status_code, 200, messages_response.text)
        messages_payload = messages_response.json()
        self.assertEqual(len(messages_payload), 1)
        self.assertEqual(messages_payload[0]["role"], "assistant")
        self.assertEqual(messages_payload[0]["content"], "reply")
        self.assertIsInstance(messages_payload[0]["created_at"], str)

    def test_chat_send_and_task_endpoints_use_serializers(self) -> None:
        user = self._create_user("chat_task_shape_user")
        session = self._create_session(user.id, title="chat-send-shape", doc_type="\u5176\u4ed6")
        headers = self._auth_headers(user.id)

        with patch.object(chat_api.WritingService, "get_guidance", return_value="serializer-reply"):
            with patch.object(chat_api.ctx_bridge, "add_message", AsyncMock()):
                with patch.object(chat_api.ctx_bridge, "add_memory_note", AsyncMock()):
                    send_response = self.client.post(
                        "/api/chat/send",
                        headers=headers,
                        json={"message": "draft notice", "session_id": session.id},
                    )
        self.assertEqual(send_response.status_code, 200, send_response.text)
        self.assertEqual(send_response.json(), {"reply": "serializer-reply"})

        upload_task_id = f"upload-{uuid.uuid4().hex}"
        upload_progress_tracker.update(
            upload_task_id,
            account_id=user.account_id,
            status="running",
            stage="parsing",
            message="processing",
            parse_progress=42,
        )
        upload_response = self.client.get(f"/api/materials/upload-tasks/{upload_task_id}", headers=headers)
        self.assertEqual(upload_response.status_code, 200, upload_response.text)
        upload_payload = upload_response.json()
        self.assertEqual(set(upload_payload.keys()), {"task_id", "status", "stage", "message", "parse_progress", "updated_at"})
        self.assertEqual(upload_payload["parse_progress"], 42)
        self.assertEqual(upload_payload["status"], "running")
        self.assertIsInstance(upload_payload["updated_at"], int)
        self.assertNotIn("account_id", upload_payload)

        book_task_id = f"book-{uuid.uuid4().hex}"
        reserved, active_task_id = book_import_task_tracker.reserve_slot(book_task_id, account_id=user.account_id)
        self.assertTrue(reserved)
        self.assertIsNone(active_task_id)
        book_import_task_tracker.create_task(book_task_id, total_files=4, rebuild=False, account_id=user.account_id)
        book_import_task_tracker.update(
            book_task_id,
            status="running",
            stage="importing",
            message="processing",
            running_file="book-a.pdf",
            total_chunks_add=10,
            completed_chunks_add=4,
            ocr_used_files_add=1,
            ocr_pages_add=12,
            completed_files_add=1,
            file_result={
                "source_name": "book-a.pdf",
                "status": "completed",
                "chunk_count": 4,
                "ocr_used": True,
                "ocr_pages": 12,
                "error_message": "",
            },
        )
        book_response = self.client.get(f"/api/materials/books/tasks/{book_task_id}", headers=headers)
        self.assertEqual(book_response.status_code, 200, book_response.text)
        book_payload = book_response.json()
        self.assertEqual(book_payload["task_id"], book_task_id)
        self.assertEqual(book_payload["status"], "running")
        self.assertEqual(book_payload["running_file"], "book-a.pdf")
        self.assertEqual(book_payload["file_results"][0]["source_name"], "book-a.pdf")
        self.assertEqual(book_payload["file_results"][0]["ocr_pages"], 12)
        self.assertIsInstance(book_payload["started_at"], int)
        self.assertIsInstance(book_payload["updated_at"], int)
        self.assertNotIn("account_id", book_payload)

    def test_book_scan_item_serializer_formats_shanghai_time(self) -> None:
        payload = serialize_book_scan_item(
            {
                "source_name": "book-a.pdf",
                "relative_path": "book-a.pdf",
                "source_hash": "hash-a",
                "file_ext": ".pdf",
                "file_size": 128,
                "imported": True,
                "status": "completed",
                "doc_type": "\u5176\u4ed6",
                "updated_at": datetime(2026, 3, 6, 0, 0, tzinfo=timezone.utc),
                "source_id": 9,
            },
        )
        self.assertEqual(payload["source_name"], "book-a.pdf")
        self.assertEqual(payload["updated_at"], "2026-03-06T08:00:00+08:00")

    def test_material_and_document_serialized_responses(self) -> None:
        user = self._create_user("asset_shape_user")

        db = self._db()
        try:
            material = Material(
                account_id=1,
                user_id=user.id,
                title="material-a",
                original_filename="material-a.txt",
                content_text="abc",
                doc_type="\u5176\u4ed6",
                summary="summary",
                keywords=["kw"],
                char_count=3,
            )
            document = GeneratedDocument(
                account_id=1,
                user_id=user.id,
                title="doc-a",
                doc_type="\u5176\u4ed6",
                version=2,
                content_json={},
            )
            db.add(material)
            db.add(document)
            db.commit()
            db.refresh(material)
        finally:
            db.close()

        headers = self._auth_headers(user.id)

        materials_response = self.client.get("/api/materials", headers=headers)
        self.assertEqual(materials_response.status_code, 200, materials_response.text)
        materials_payload = materials_response.json()
        self.assertEqual(materials_payload["total"], 1)
        self.assertEqual(len(materials_payload["items"]), 1)
        self.assertEqual(materials_payload["items"][0]["title"], "material-a")
        self.assertEqual(materials_payload["items"][0]["keywords"], ["kw"])
        self.assertEqual(materials_payload["items"][0]["char_count"], 3)
        self.assertIsInstance(materials_payload["items"][0]["created_at"], str)

        material_detail = self.client.get(f"/api/materials/{material.id}", headers=headers)
        self.assertEqual(material_detail.status_code, 200, material_detail.text)
        detail_payload = material_detail.json()
        self.assertEqual(detail_payload["original_filename"], "material-a.txt")
        self.assertEqual(detail_payload["content_text"], "abc")
        self.assertEqual(detail_payload["char_count"], 3)
        self.assertIsInstance(detail_payload["created_at"], str)

        history_response = self.client.get("/api/documents/history", headers=headers)
        self.assertEqual(history_response.status_code, 200, history_response.text)
        history_payload = history_response.json()
        self.assertEqual(history_payload["total"], 1)
        self.assertEqual(history_payload["items"][0]["title"], "doc-a")
        self.assertEqual(history_payload["items"][0]["version"], 2)
        self.assertIsInstance(history_payload["items"][0]["created_at"], str)

    def test_book_import_task_persistence_and_interrupted_recovery(self) -> None:
        tracker = BookImportTaskTracker(ttl_seconds=3600)
        reserved, active_id = tracker.reserve_slot("task-1", account_id=1)
        self.assertTrue(reserved)
        self.assertIsNone(active_id)

        tracker.create_task("task-1", total_files=4, rebuild=True, account_id=1)
        tracker.update(
            "task-1",
            status="running",
            stage="解析中",
            message="processing",
            running_file="book-a.pdf",
            total_chunks_add=10,
            completed_chunks_add=4,
            ocr_used_files_add=1,
            ocr_pages_add=12,
            completed_files_add=1,
        )

        reloaded = BookImportTaskTracker(ttl_seconds=3600)
        current = reloaded.get("task-1")
        self.assertIsNotNone(current)
        self.assertEqual(current["status"], "running")
        self.assertEqual(current["running_file"], "book-a.pdf")
        self.assertEqual(current["ocr_pages"], 12)
        self.assertEqual(current["overall_progress"], 32)

        _mark_interrupted_book_tasks()

        after_restart = BookImportTaskTracker(ttl_seconds=3600).get("task-1")
        self.assertIsNotNone(after_restart)
        self.assertEqual(after_restart["status"], "interrupted")
        self.assertEqual(after_restart["stage"], "已中断")

        db = self._db()
        try:
            row = db.query(BookImportTask).filter(BookImportTask.task_id == "task-1").first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "interrupted")
            self.assertIsNotNone(row.finished_at)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()


