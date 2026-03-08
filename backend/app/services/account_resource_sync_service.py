from __future__ import annotations

import asyncio
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.material import Material
from app.services.context_bridge import ContextBridge


class AccountResourceSyncService:
    """Rebuild account-scoped OpenViking resources from the database truth."""

    def __init__(self, db: Session):
        self.db = db

    def rebuild_accounts(self, account_ids: Iterable[int]) -> dict[str, int]:
        normalized = sorted({int(account_id or 0) for account_id in account_ids if int(account_id or 0) > 0})
        if not normalized:
            return {}
        return asyncio.run(self._rebuild_accounts(normalized))

    async def _rebuild_accounts(self, account_ids: list[int]) -> dict[str, int]:
        bridge = ContextBridge()
        counts: dict[str, int] = {}
        try:
            for account_id in account_ids:
                rebuilt = await self._rebuild_account(bridge, account_id)
                for key, value in rebuilt.items():
                    counts[f'account_{account_id}_{key}'] = int(value)
        finally:
            await bridge.close()
        return counts

    async def _rebuild_account(self, bridge: ContextBridge, account_id: int) -> dict[str, int]:
        account_root = f'viking://resources/accounts/{account_id}'
        await bridge.clear_namespace(f'{account_root}/materials')
        await bridge.clear_namespace(f'{account_root}/memory')

        materials = (
            self.db.query(Material)
            .filter(Material.account_id == account_id)
            .order_by(Material.id.asc())
            .all()
        )
        material_count = 0
        for material in materials:
            await bridge.add_material(
                file_path=material.file_path or '',
                doc_type=material.doc_type or '',
                title=material.title or '',
                content_text=material.content_text or '',
                account_id=account_id,
            )
            material_count += 1

        sessions = (
            self.db.query(ChatSession)
            .filter(ChatSession.account_id == account_id)
            .order_by(ChatSession.id.asc())
            .all()
        )
        memory_note_count = 0
        for session in sessions:
            messages = (
                self.db.query(ChatMessage)
                .filter(
                    ChatMessage.account_id == account_id,
                    ChatMessage.session_id == session.id,
                )
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                .all()
            )
            pending_user = ''
            for message in messages:
                role = str(message.role or '').strip().lower()
                content = str(message.content or '').strip()
                if not content:
                    continue
                if role == 'user':
                    pending_user = content
                    continue
                if role == 'assistant' and pending_user:
                    await bridge.add_memory_note(
                        account_id=account_id,
                        session_id=session.id,
                        user_text=pending_user,
                        assistant_text=content,
                    )
                    memory_note_count += 1
                    pending_user = ''

        return {
            'materials_rebuilt': material_count,
            'memory_notes_rebuilt': memory_note_count,
        }
