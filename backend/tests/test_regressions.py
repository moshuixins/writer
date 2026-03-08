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
from alembic.script import ScriptDirectory  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import chat as chat_api  # noqa: E402
from app.api import documents as documents_api  # noqa: E402
from app.api import materials as materials_api  # noqa: E402
from app.auth import create_access_token, hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.main import app  # noqa: E402
from app.migration import _alembic_config  # noqa: E402
from app.models.book_import_task import BookImportTask  # noqa: E402
from app.models.account import Account  # noqa: E402
from app.models.chat import ChatMessage, ChatSession, SessionDraft  # noqa: E402
from app.models.document import GeneratedDocument  # noqa: E402
from app.models.material import Material  # noqa: E402
from app.models.invite_code import InviteCode  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.preference import UserPreference  # noqa: E402
from app.models.style import WritingHabit  # noqa: E402
from app.schema_bootstrap import ensure_account_schema, _mark_interrupted_book_tasks  # noqa: E402
from app.serializers import (  # noqa: E402
    serialize_book_scan_item,
    serialize_chat_chunk_sse,
    serialize_chat_done_sse,
    serialize_chat_error_sse,
    serialize_chat_final_sse,
    serialize_chat_workflow_sse,
)
from app.services import book_import_service as book_import_service_module  # noqa: E402
from app.services import material_ingestion_service as material_ingestion_service_module  # noqa: E402
from app.services.account_resource_sync_service import AccountResourceSyncService  # noqa: E402
from app.services.book_import_task_service import BookImportTaskTracker, book_import_task_tracker  # noqa: E402
from app.services.rbac_service import RBACService  # noqa: E402
from app.services.upload_progress_service import upload_progress_tracker  # noqa: E402


class BackendRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        ensure_account_schema(engine, run_post_schema_tasks=False)

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

    def test_alembic_migration_creates_default_account(self) -> None:
        db = self._db()
        try:
            from app.models.account import Account

            row = db.query(Account).filter(Account.id == 1).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.code, "default")
            self.assertEqual(row.status, "active")
        finally:
            db.close()

    def test_legacy_schema_is_stamped_to_alembic_head(self) -> None:
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))

        Base.metadata.create_all(bind=engine)

        db = self._db()
        try:
            from app.models.account import Account

            db.query(Account).delete()
            db.commit()
        finally:
            db.close()

        ensure_account_schema(engine, run_post_schema_tasks=False)

        with engine.begin() as conn:
            version = conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
            config = _alembic_config(engine.url.render_as_string(hide_password=False))
            head = ScriptDirectory.from_config(config).get_current_head()
            self.assertEqual(version, head)

        db = self._db()
        try:
            from app.models.account import Account

            row = db.query(Account).filter(Account.id == 1).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.code, "default")
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

    def test_auth_serialized_responses(self) -> None:
        user = self._create_user('auth_shape_user', role_codes=['writer'])

        login_response = self.client.post(
            '/api/auth/login',
            json={'username': user.username, 'password': 'password123'},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        login_payload = login_response.json()
        self.assertIsInstance(login_payload['token'], str)
        self.assertEqual(login_payload['user']['id'], user.id)
        self.assertEqual(login_payload['user']['username'], user.username)
        self.assertIsInstance(login_payload['user']['roles'], list)
        self.assertEqual(login_payload['user']['account_id'], user.account_id)

        headers = {'Authorization': f"Bearer {login_payload['token']}"}

        profile_response = self.client.get('/api/auth/profile', headers=headers)
        self.assertEqual(profile_response.status_code, 200, profile_response.text)
        profile_payload = profile_response.json()
        self.assertEqual(profile_payload['id'], user.id)
        self.assertIsInstance(profile_payload['roles'], list)

        permissions_response = self.client.get('/api/auth/permissions', headers=headers)
        self.assertEqual(permissions_response.status_code, 200, permissions_response.text)
        permissions_payload = permissions_response.json()
        self.assertIsInstance(permissions_payload['permissions'], list)
        self.assertTrue(permissions_payload['permissions'])

        update_response = self.client.put(
            '/api/auth/profile',
            json={'display_name': 'Updated Name', 'department': 'Office'},
            headers=headers,
        )
        self.assertEqual(update_response.status_code, 200, update_response.text)
        update_payload = update_response.json()
        self.assertIsInstance(update_payload['message'], str)
        self.assertEqual(update_payload['user']['display_name'], 'Updated Name')
        self.assertEqual(update_payload['user']['department'], 'Office')

        password_response = self.client.post(
            '/api/auth/change-password',
            json={'password': 'password123', 'newPassword': 'password456'},
            headers=headers,
        )
        self.assertEqual(password_response.status_code, 200, password_response.text)
        password_payload = password_response.json()
        self.assertIsInstance(password_payload['message'], str)

    def test_accounts_serialized_responses(self) -> None:
        admin = self._create_user('accounts_shape_admin', role_codes=['admin'], legacy_role='admin')
        member = self._create_user('accounts_shape_member', role_codes=['writer'])
        headers = self._auth_headers(admin.id)

        my_account_response = self.client.get('/api/accounts/me', headers=headers)
        self.assertEqual(my_account_response.status_code, 200, my_account_response.text)
        my_account_payload = my_account_response.json()
        self.assertEqual(my_account_payload['id'], 1)
        self.assertEqual(my_account_payload['code'], 'default')
        self.assertIsInstance(my_account_payload['status'], str)

        accounts_response = self.client.get('/api/accounts', headers=headers)
        self.assertEqual(accounts_response.status_code, 200, accounts_response.text)
        accounts_payload = accounts_response.json()
        self.assertGreaterEqual(accounts_payload['total'], 1)
        self.assertIsInstance(accounts_payload['items'], list)
        self.assertIn('user_count', accounts_payload['items'][0])

        permissions_response = self.client.get('/api/accounts/permissions', headers=headers)
        self.assertEqual(permissions_response.status_code, 200, permissions_response.text)
        permissions_payload = permissions_response.json()
        self.assertGreater(permissions_payload['total'], 0)
        permission_code = permissions_payload['items'][0]['code']
        self.assertIsInstance(permissions_payload['items'][0]['is_system'], bool)

        roles_response = self.client.get('/api/accounts/roles', headers=headers)
        self.assertEqual(roles_response.status_code, 200, roles_response.text)
        roles_payload = roles_response.json()
        self.assertGreaterEqual(roles_payload['total'], 2)
        self.assertIsInstance(roles_payload['items'][0]['permissions'], list)

        users_response = self.client.get('/api/accounts/1/users', headers=headers)
        self.assertEqual(users_response.status_code, 200, users_response.text)
        users_payload = users_response.json()
        self.assertEqual(users_payload['account']['id'], 1)
        self.assertGreaterEqual(users_payload['total'], 2)
        member_payload = next(item for item in users_payload['items'] if item['id'] == member.id)
        self.assertIsInstance(member_payload['role_codes'], list)
        self.assertIsInstance(member_payload['roles'], list)

        create_role_response = self.client.post(
            '/api/accounts/1/roles',
            json={
                'code': 'reviewer',
                'name': 'Reviewer',
                'description': 'Review role',
                'permission_codes': [permission_code],
            },
            headers=headers,
        )
        self.assertEqual(create_role_response.status_code, 200, create_role_response.text)
        created_role_payload = create_role_response.json()
        self.assertEqual(created_role_payload['code'], 'reviewer')
        self.assertEqual(created_role_payload['permissions'], [permission_code])

        update_role_response = self.client.put(
            f"/api/accounts/1/roles/{created_role_payload['id']}",
            json={
                'name': 'Reviewer Updated',
                'description': 'Updated role',
                'status': 'active',
                'permission_codes': [permission_code],
            },
            headers=headers,
        )
        self.assertEqual(update_role_response.status_code, 200, update_role_response.text)
        updated_role_payload = update_role_response.json()
        self.assertEqual(updated_role_payload['name'], 'Reviewer Updated')
        self.assertEqual(updated_role_payload['permissions'], [permission_code])

        update_roles_response = self.client.put(
            f'/api/accounts/1/users/{member.id}/roles',
            json={'role_codes': ['reviewer']},
            headers=headers,
        )
        self.assertEqual(update_roles_response.status_code, 200, update_roles_response.text)
        update_roles_payload = update_roles_response.json()
        self.assertEqual(update_roles_payload['id'], member.id)
        self.assertEqual(update_roles_payload['role_codes'], ['reviewer'])

        update_role_response = self.client.put(
            f'/api/accounts/1/users/{member.id}/role',
            json={'role': 'writer'},
            headers=headers,
        )
        self.assertEqual(update_role_response.status_code, 200, update_role_response.text)
        update_role_payload = update_role_response.json()
        self.assertEqual(update_role_payload['id'], member.id)
        self.assertEqual(update_role_payload['role_codes'], ['writer'])

        invite_response = self.client.post(
            '/api/accounts/1/invites',
            json={'expires_in_hours': 24},
            headers=headers,
        )
        self.assertEqual(invite_response.status_code, 200, invite_response.text)
        invite_payload = invite_response.json()
        self.assertEqual(invite_payload['account_id'], 1)
        self.assertIsInstance(invite_payload['invite_code'], str)
        self.assertIsInstance(invite_payload['invite_id'], int)

        invites_response = self.client.get('/api/accounts/1/invites', headers=headers)
        self.assertEqual(invites_response.status_code, 200, invites_response.text)
        invites_payload = invites_response.json()
        self.assertGreaterEqual(invites_payload['total'], 1)
        self.assertIsInstance(invites_payload['items'][0]['status'], str)

        revoke_response = self.client.put(
            f"/api/accounts/invites/{invite_payload['invite_id']}/revoke",
            json={'reason': 'test'},
            headers=headers,
        )
        self.assertEqual(revoke_response.status_code, 200, revoke_response.text)
        revoke_payload = revoke_response.json()
        self.assertEqual(revoke_payload, {'id': invite_payload['invite_id'], 'status': 'revoked'})

        create_account_response = self.client.post(
            '/api/accounts',
            json={'code': 'shape-2', 'name': 'Shape Account'},
            headers=headers,
        )
        self.assertEqual(create_account_response.status_code, 200, create_account_response.text)
        created_account_payload = create_account_response.json()
        self.assertEqual(created_account_payload['code'], 'shape-2')
        self.assertEqual(created_account_payload['status'], 'active')

        rebind_response = self.client.put(
            f"/api/accounts/{created_account_payload['id']}/users/{member.id}",
            json={'migrate_data': False},
            headers=headers,
        )
        self.assertEqual(rebind_response.status_code, 200, rebind_response.text)
        rebind_payload = rebind_response.json()
        self.assertEqual(rebind_payload['user_id'], member.id)
        self.assertEqual(rebind_payload['old_account_id'], 1)
        self.assertEqual(rebind_payload['new_account_id'], created_account_payload['id'])
        self.assertTrue(rebind_payload['migrated'])
        self.assertFalse(rebind_payload['migrate_data'])
        self.assertIsInstance(rebind_payload['counts'], dict)

        status_response = self.client.put(
            f"/api/accounts/{created_account_payload['id']}/status",
            json={'status': 'disabled'},
            headers=headers,
        )
        self.assertEqual(status_response.status_code, 200, status_response.text)
        status_payload = status_response.json()
        self.assertEqual(status_payload['id'], created_account_payload['id'])
        self.assertEqual(status_payload['status'], 'disabled')

        delete_role_response = self.client.delete(
            f"/api/accounts/1/roles/{created_role_payload['id']}",
            headers=headers,
        )
        self.assertEqual(delete_role_response.status_code, 200, delete_role_response.text)
        delete_role_payload = delete_role_response.json()
        self.assertEqual(delete_role_payload, {'id': created_role_payload['id'], 'deleted': True})

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

    def test_batch_delete_materials_only_deletes_current_user_rows(self) -> None:
        owner = self._create_user("material_owner")
        other = self._create_user("material_other")

        db = self._db()
        try:
            own_material = Material(
                account_id=owner.account_id,
                user_id=owner.id,
                title="own-material",
                original_filename="own.txt",
                file_path="",
                content_text="own",
                char_count=3,
            )
            other_material = Material(
                account_id=other.account_id,
                user_id=other.id,
                title="other-material",
                original_filename="other.txt",
                file_path="",
                content_text="other",
                char_count=5,
            )
            db.add(own_material)
            db.add(other_material)
            db.commit()
            db.refresh(own_material)
            db.refresh(other_material)
        finally:
            db.close()

        headers = self._auth_headers(owner.id)
        response = self.client.post(
            "/api/materials/batch-delete",
            headers=headers,
            json={"ids": [own_material.id, other_material.id]},
        )
        self.assertEqual(response.status_code, 200, response.text)

        db = self._db()
        try:
            own_row = db.query(Material).filter(Material.id == own_material.id).first()
            other_row = db.query(Material).filter(Material.id == other_material.id).first()
            self.assertIsNone(own_row)
            self.assertIsNotNone(other_row)
        finally:
            db.close()

    def test_chat_sse_event_serializers(self) -> None:
        workflow = serialize_chat_workflow_sse("分析请求意图", "running")
        chunk = serialize_chat_chunk_sse("段落")
        final = serialize_chat_final_sse(
            ChatMessage(
                id=7,
                role="assistant",
                content="完整回复",
                created_at=datetime(2026, 3, 1, 8, 0, 0),
            ),
            warnings=["外部上下文未同步"],
        )
        error = serialize_chat_error_sse("流式生成失败（错误ID: err-1）")
        done = serialize_chat_done_sse()

        self.assertEqual(workflow, "data: {\"event\": \"workflow\", \"step\": \"分析请求意图\", \"status\": \"running\"}\n\n")
        self.assertEqual(chunk, "data: {\"event\": \"chunk\", \"chunk\": \"段落\"}\n\n")
        self.assertIn('"event": "final"', final)
        self.assertIn('"warnings": ["外部上下文未同步"]', final)
        self.assertIn('"content": "完整回复"', final)
        self.assertEqual(error, "data: {\"event\": \"error\", \"error\": \"流式生成失败（错误ID: err-1）\"}\n\n")
        self.assertEqual(done, "data: [DONE]\n\n")

    def test_material_search_returns_collection_shape(self) -> None:
        user = self._create_user("search_user")
        headers = self._auth_headers(user.id)
        mocked_results = [
            {
                "text": "关于开展专项整治的素材内容",
                "metadata": {
                    "uri": "viking://accounts/1/materials/通知/1",
                    "title": "专项整治通知",
                    "score": 0.82,
                },
            },
        ]

        with patch.object(materials_api.ctx_bridge, 'search_materials', new=AsyncMock(return_value=mocked_results)):
            response = self.client.get('/api/materials/search', params={'query': '专项整治'}, headers=headers)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(payload['items'][0]['text'], mocked_results[0]['text'])
        self.assertEqual(payload['items'][0]['metadata']['title'], '专项整治通知')
        self.assertAlmostEqual(payload['items'][0]['metadata']['score'], 0.82)

    def test_openapi_declares_stream_review_and_docx_responses(self) -> None:
        app.openapi_schema = None
        schema = app.openapi()

        stream_response = schema['paths']['/api/chat/send-stream']['post']['responses']['200']
        self.assertIn('text/event-stream', stream_response['content'])
        self.assertEqual(stream_response['content']['text/event-stream']['schema']['type'], 'string')

        review_schema = schema['paths']['/api/chat/review']['post']['responses']['200']['content']['application/json']['schema']
        self.assertTrue('$ref' in review_schema or review_schema.get('type') or review_schema.get('oneOf'))

        for path_key, method in (
            ('/api/documents/export', 'post'),
            ('/api/documents/export-editor', 'post'),
            ('/api/documents/history/{doc_id}/download', 'get'),
        ):
            schema_obj = schema['paths'][path_key][method]['responses']['200']['content'][documents_api.DOCX_MEDIA_TYPE]['schema']
            self.assertEqual(schema_obj['type'], 'string')
            self.assertEqual(schema_obj['format'], 'binary')

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
        self.assertTrue(any(item.get("event") == "error" for item in sse_payloads))
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
        self.assertEqual(sessions_payload["total"], 1)
        self.assertEqual(len(sessions_payload["items"]), 1)
        self.assertEqual(sessions_payload["items"][0]["title"], "chat-shape")
        self.assertEqual(sessions_payload["items"][0]["doc_type"], "\u5176\u4ed6")
        self.assertEqual(sessions_payload["items"][0]["status"], "active")
        self.assertIsInstance(sessions_payload["items"][0]["created_at"], str)

        messages_response = self.client.get(f"/api/chat/sessions/{session.id}/messages", headers=headers)
        self.assertEqual(messages_response.status_code, 200, messages_response.text)
        messages_payload = messages_response.json()
        self.assertEqual(messages_payload["total"], 1)
        self.assertEqual(len(messages_payload["items"]), 1)
        self.assertEqual(messages_payload["items"][0]["role"], "assistant")
        self.assertEqual(messages_payload["items"][0]["content"], "reply")
        self.assertIsInstance(messages_payload["items"][0]["created_at"], str)

    def test_create_session_returns_warning_when_context_sync_degraded(self) -> None:
        user = self._create_user("session_warning_user")
        headers = self._auth_headers(user.id)

        with patch.object(chat_api.ctx_bridge, "create_session", AsyncMock(side_effect=RuntimeError("ov down"))):
            response = self.client.post(
                "/api/chat/sessions",
                headers=headers,
                json={"title": "warning-session", "doc_type": "其他"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["title"], "warning-session")
        self.assertIn("warnings", payload)
        self.assertTrue(any("错误ID" in item for item in payload["warnings"]))

    def test_chat_send_returns_warning_when_side_effects_degraded(self) -> None:
        user = self._create_user("chat_warning_user")
        session = self._create_session(user.id, title="chat-warning", doc_type="其他")
        db = self._db()
        try:
            row = db.query(ChatSession).filter(ChatSession.id == session.id).first()
            row.ov_session_id = "ov-session-1"
            db.commit()
        finally:
            db.close()
        headers = self._auth_headers(user.id)

        with patch.object(chat_api.WritingService, "get_guidance", return_value="warning-reply"):
            with patch.object(chat_api.ctx_bridge, "add_message", AsyncMock(side_effect=RuntimeError("ov down"))):
                with patch.object(chat_api.ctx_bridge, "add_memory_note", AsyncMock(side_effect=RuntimeError("memory down"))):
                    response = self.client.post(
                        "/api/chat/send",
                        headers=headers,
                        json={"message": "draft notice", "session_id": session.id},
                    )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["reply"], "warning-reply")
        self.assertIn("warnings", payload)
        self.assertGreaterEqual(len(payload["warnings"]), 2)
        self.assertTrue(all("错误ID" in item for item in payload["warnings"]))

    def test_material_upload_returns_warning_when_context_sync_degraded(self) -> None:
        user = self._create_user("material_warning_user")
        headers = self._auth_headers(user.id)
        llm_payload = json.dumps(
            {
                "title": "测试材料",
                "doc_type": "其他",
                "summary": "测试摘要",
                "keywords": ["测试", "材料"],
            },
            ensure_ascii=False,
        )
        style_features = {
            "statistics": {"avg_sentence_length": 10.0, "avg_paragraph_length": 20.0, "sentence_count": 1, "paragraph_count": 1},
            "vocabulary": {"top_keywords": [], "domain_terms": [], "llm_keywords": [], "llm_domain_terms": []},
            "llm_analysis": {"opening_pattern": "直接开头"},
        }

        with patch.object(material_ingestion_service_module.MaterialService, "save_upload", return_value=str(TEMP_DIR / "fake-upload.txt")):
            with patch.object(material_ingestion_service_module.MaterialService, "extract_text", return_value="这是测试素材正文"):
                with patch.object(material_ingestion_service_module.MaterialService, "guess_title", return_value="测试材料"):
                    with patch.object(material_ingestion_service_module.LLMService, "invoke_async", AsyncMock(return_value=llm_payload)):
                        with patch.object(material_ingestion_service_module.StyleAnalyzer, "analyze", return_value=style_features):
                            with patch.object(materials_api.ctx_bridge, "add_material", AsyncMock(side_effect=RuntimeError("ov down"))):
                                response = self.client.post(
                                    "/api/materials/upload",
                                    headers=headers,
                                    files={"file": ("warning.txt", b"test-content", "text/plain")},
                                )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["title"], "测试材料")
        self.assertIn("warnings", payload)
        self.assertTrue(any("知识库同步未完成" in item for item in payload["warnings"]))

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

    def test_upload_books_endpoint_persists_files_for_scan(self) -> None:
        user = self._create_user("book_uploader")
        headers = self._auth_headers(user.id)
        books_dir = TEMP_DIR / "books-upload"
        books_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(materials_api.settings, "books_dir", str(books_dir)), patch.object(book_import_service_module.settings, "books_dir", str(books_dir)):
            response = self.client.post(
                "/api/materials/books/upload",
                headers=headers,
                files=[
                    ("files", ("guide.epub", b"epub-content", "application/epub+zip")),
                    ("files", ("scan.pdf", b"%PDF-1.4 fake pdf", "application/pdf")),
                    ("files", ("bad.txt", b"not-supported", "text/plain")),
                ],
            )
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["uploaded_count"], 2)
            self.assertEqual(payload["failed_count"], 1)
            self.assertEqual(len(payload["items"]), 2)
            self.assertEqual(payload["errors"][0]["source_name"], "bad.txt")
            self.assertTrue(all(item["relative_path"].startswith("imports/") for item in payload["items"]))

            scan_response = self.client.get("/api/materials/books/scan", headers=headers)
            self.assertEqual(scan_response.status_code, 200, scan_response.text)
            scan_payload = scan_response.json()
            self.assertEqual(scan_payload["total"], 2)
            self.assertEqual(sorted(item["source_name"] for item in scan_payload["items"]), ["guide.epub", "scan.pdf"])

            imports_dir = books_dir / "imports"
            self.assertTrue((imports_dir / "guide.epub").exists())
            self.assertTrue((imports_dir / "scan.pdf").exists())

    def test_account_resource_sync_service_rebuilds_materials_and_memory(self) -> None:
        db = self._db()
        try:
            account = Account(code='sync-target', name='Sync Target', status='active')
            db.add(account)
            db.flush()
            user = User(
                account_id=account.id,
                username='sync_user',
                password_hash=hash_password('password123'),
                display_name='sync_user',
                department='test',
                role='writer',
            )
            db.add(user)
            db.flush()
            RBACService(db).ensure_account_system_roles(account.id)
            RBACService(db).set_user_roles(user, ['writer'])
            material = Material(
                account_id=account.id,
                user_id=user.id,
                title='同步素材',
                original_filename='sync.txt',
                file_path='ignored.txt',
                content_text='同步内容',
                doc_type='通知',
                summary='摘要',
                keywords=['同步'],
                char_count=4,
            )
            session = ChatSession(account_id=account.id, user_id=user.id, title='会话', doc_type='通知', status='active', ov_session_id='legacy-ov')
            db.add_all([material, session])
            db.flush()
            db.add_all([
                ChatMessage(account_id=account.id, session_id=session.id, role='user', content='用户问题'),
                ChatMessage(account_id=account.id, session_id=session.id, role='assistant', content='助手回复'),
            ])
            db.commit()

            with patch('app.services.account_resource_sync_service.ContextBridge.clear_namespace', new=AsyncMock()) as clear_mock,                  patch('app.services.account_resource_sync_service.ContextBridge.add_material', new=AsyncMock()) as add_material_mock,                  patch('app.services.account_resource_sync_service.ContextBridge.add_memory_note', new=AsyncMock()) as add_memory_mock:
                counts = AccountResourceSyncService(db).rebuild_accounts([account.id])

            self.assertEqual(counts[f'account_{account.id}_materials_rebuilt'], 1)
            self.assertEqual(counts[f'account_{account.id}_memory_notes_rebuilt'], 1)
            self.assertEqual(clear_mock.await_count, 2)
            add_material_mock.assert_awaited_once()
            add_memory_mock.assert_awaited_once()
        finally:
            db.close()

    def test_rebind_user_migrate_data_resets_ov_session_and_rebuilds_resources(self) -> None:
        admin = self._create_user('platform_admin', role_codes=['admin'], legacy_role='admin')
        member = self._create_user('member_to_rebind')
        admin_headers = self._auth_headers(admin.id)

        db = self._db()
        try:
            target_account = Account(code='target-a', name='Target A', status='active')
            db.add(target_account)
            db.flush()
            session = ChatSession(account_id=1, user_id=member.id, title='旧会话', doc_type='通知', status='active', ov_session_id='legacy-ov-session')
            material = Material(
                account_id=1,
                user_id=member.id,
                title='旧素材',
                original_filename='legacy.txt',
                file_path='legacy.txt',
                content_text='旧内容',
                doc_type='通知',
                summary='旧摘要',
                keywords=['旧'],
                char_count=3,
            )
            preference = UserPreference(account_id=1, user_id=member.id, pref_key='default_tone', pref_value='formal')
            habit = WritingHabit(account_id=1, user_id=member.id, habit_type='tone', doc_type='通知', description='正式', frequency=1)
            db.add_all([session, material, preference, habit])
            db.flush()
            db.add_all([
                ChatMessage(account_id=1, session_id=session.id, role='user', content='用户问题'),
                ChatMessage(account_id=1, session_id=session.id, role='assistant', content='助手回复'),
                SessionDraft(account_id=1, session_id=session.id, user_id=member.id, draft_json={'title': '草稿'}),
                GeneratedDocument(account_id=1, user_id=member.id, session_id=session.id, title='导出稿', doc_type='通知', content_json={'title': '导出稿'}),
            ])
            db.commit()
            target_account_id = target_account.id
            session_id = session.id
        finally:
            db.close()

        with patch.object(AccountResourceSyncService, 'rebuild_accounts', return_value={
            'account_1_materials_rebuilt': 0,
            f'account_{target_account_id}_materials_rebuilt': 1,
            f'account_{target_account_id}_memory_notes_rebuilt': 1,
        }) as rebuild_mock:
            response = self.client.put(
                f'/api/accounts/{target_account_id}/users/{member.id}',
                json={'migrate_data': True},
                headers=admin_headers,
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload['migrated'])
        self.assertTrue(payload['migrate_data'])
        self.assertEqual(payload['counts']['ov_sessions_reset'], 1)
        self.assertEqual(payload['counts'][f'account_{target_account_id}_materials_rebuilt'], 1)
        rebuild_mock.assert_called_once_with([1, target_account_id])

        db = self._db()
        try:
            user = db.query(User).filter(User.id == member.id).first()
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            material = db.query(Material).filter(Material.user_id == member.id).first()
            self.assertEqual(user.account_id, target_account_id)
            self.assertEqual(session.account_id, target_account_id)
            self.assertIsNone(session.ov_session_id)
            self.assertEqual(material.account_id, target_account_id)
        finally:
            db.close()

    def test_book_import_task_persistence_and_interrupted_recovery(self) -> None:
        tracker = BookImportTaskTracker(ttl_seconds=3600)
        reserved, active_id = tracker.reserve_slot("task-1", account_id=1)
        self.assertTrue(reserved)
        self.assertIsNone(active_id)

        tracker.create_task(
            "task-1",
            total_files=4,
            rebuild=True,
            account_id=1,
            selected_files=["book-a.pdf", "nested/book-b.epub"],
        )
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
        self.assertEqual(current["selected_files"], ["book-a.pdf", "nested/book-b.epub"])
        self.assertEqual(reloaded.list_recoverable_task_ids(), ["task-1"])

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


