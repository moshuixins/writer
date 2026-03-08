from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings
from app.errors import OpenVikingError, logger

settings = get_settings()

MAX_RETRIES = 2
RETRY_DELAY = 1.0


class ContextBridge:
    """HTTP adapter for OpenViking."""

    def __init__(self):
        self._base_url = settings.openviking_server_url.rstrip('/')
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if settings.openviking_root_api_key:
                headers['Authorization'] = f'Bearer {settings.openviking_root_api_key}'
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=120.0,
                headers=headers,
            )
        return self._client

    @staticmethod
    def _account_root(account_id: int) -> str:
        return f'viking://resources/accounts/{int(account_id or 1)}'

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _delayed_cleanup(self, file_path: Path, delay_seconds: int = 900) -> None:
        await asyncio.sleep(delay_seconds)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as exc:
            logger.warning('Failed to cleanup OV staging file %s: %s', file_path, exc)

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                client = await self._ensure_client()
                response = await getattr(client, method)(url, **kwargs)
                return response
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    'OpenViking %s %s failed (attempt %d/%d): %s',
                    method.upper(),
                    url,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        raise OpenVikingError(detail=f'连接失败: {last_error}')

    async def _request_json(self, method: str, url: str, **kwargs) -> dict:
        response = await self._request_with_retry(method, url, **kwargs)
        return self._parse_response(response)

    def _parse_response(self, resp: httpx.Response) -> dict:
        if resp.status_code >= 400:
            detail = ''
            try:
                detail = resp.json().get('detail', resp.text)
            except Exception:
                detail = resp.text
            logger.error('OpenViking error %d: %s', resp.status_code, detail)
            raise OpenVikingError(detail=f'({resp.status_code}) {detail}')
        try:
            data = resp.json()
        except Exception:
            return {}
        if isinstance(data, dict) and 'result' in data:
            return data['result']
        return data

    async def add_resource(
        self,
        *,
        target: str | None,
        reason: str,
        instruction: str,
        file_path: str = '',
        content_text: str = '',
        timeout: float = 120.0,
    ) -> dict:
        actual_path = file_path
        staged_file: Path | None = None

        if content_text:
            backend_staging_dir = Path(settings.openviking_shared_backend_dir)
            backend_staging_dir.mkdir(parents=True, exist_ok=True)
            staged_file = backend_staging_dir / f'{uuid.uuid4().hex}.txt'
            staged_file.write_text(content_text, encoding='utf-8')

            ov_staging_dir = settings.openviking_shared_ov_dir.rstrip('/')
            actual_path = f'{ov_staging_dir}/{staged_file.name}' if ov_staging_dir else str(staged_file)

        try:
            return await self._request_json(
                'post',
                '/api/v1/resources',
                json={
                    'path': actual_path,
                    'target': target,
                    'reason': reason,
                    'instruction': instruction,
                    'wait': True,
                    'timeout': timeout,
                },
            )
        finally:
            if staged_file is not None:
                asyncio.create_task(self._delayed_cleanup(staged_file))

    async def add_material(
        self,
        file_path: str,
        doc_type: str = '',
        title: str = '',
        content_text: str = '',
        account_id: int = 1,
    ) -> dict:
        base = f'{self._account_root(account_id)}/materials'
        target = f'{base}/{doc_type}' if doc_type else base
        return await self.add_resource(
            target=target,
            reason=f'公文素材: {title}',
            instruction=f'类型: {doc_type}, 标题: {title}',
            file_path=file_path,
            content_text=content_text,
            timeout=120.0,
        )

    async def add_book_chunk(
        self,
        *,
        account_id: int,
        doc_type: str,
        source_name: str,
        source_hash: str,
        chapter: str,
        content_text: str,
        page_range: str = '',
    ) -> None:
        if not content_text.strip():
            return

        account_root = f'{self._account_root(account_id)}/books'
        targets = [f'{account_root}/{doc_type}', f'{account_root}/common']
        instruction = (
            f'doc_type={doc_type}; source={source_name}; source_hash={source_hash}; '
            f'chapter={chapter}; page_range={page_range}'
        )
        for target in targets:
            await self.add_resource(
                target=target,
                reason=f'书籍知识片段: {source_name}',
                instruction=instruction,
                content_text=content_text,
                timeout=180.0,
            )

    async def add_memory_note(
        self,
        *,
        account_id: int,
        session_id: int | str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        user_part = (user_text or '').strip()[:1200]
        assistant_part = (assistant_text or '').strip()[:1800]
        if not user_part and not assistant_part:
            return

        note = (
            f'session_id={session_id}\n'
            f'用户: {user_part}\n'
            f'助手: {assistant_part}'
        ).strip()

        await self.add_resource(
            target=f'{self._account_root(account_id)}/memory',
            reason=f'会话记忆片段: {session_id}',
            instruction='写作会话记忆（按账户隔离）',
            content_text=note,
            timeout=120.0,
        )

    async def delete_material(self, uri: str) -> None:
        response = await self._request_with_retry('delete', '/api/v1/fs', params={'uri': uri, 'recursive': True})
        if response.status_code == 404:
            response = await self._request_with_retry('post', '/api/v1/fs/rm', json={'uri': uri, 'recursive': True})
        self._parse_response(response)

    async def clear_namespace(self, uri: str) -> None:
        try:
            await self.delete_material(uri)
        except OpenVikingError as exc:
            if '404' not in str(exc.detail):
                raise

    async def search_materials(
        self,
        query: str,
        doc_type: str | None = None,
        top_k: int = 5,
        account_id: int = 1,
    ) -> list[dict]:
        base = f'{self._account_root(account_id)}/materials'
        target_uri = f'{base}/{doc_type}' if doc_type else base
        data = await self._request_json(
            'post',
            '/api/v1/search/find',
            json={
                'query': query,
                'target_uri': target_uri,
                'limit': top_k,
            },
        )
        results = []
        for item in data.get('results', []):
            results.append(
                {
                    'text': item.get('content', ''),
                    'metadata': {
                        'uri': item.get('uri', ''),
                        'title': item.get('title', ''),
                        'score': item.get('score', 0),
                    },
                },
            )
        return results

    async def search_books(
        self,
        query: str,
        doc_type: str = '',
        top_k: int = 4,
        account_id: int = 1,
    ) -> list[dict]:
        account_root = f'{self._account_root(account_id)}/books'
        targets = []
        if doc_type:
            targets.append(f'{account_root}/{doc_type}')
        targets.append(f'{account_root}/common')

        merged: list[dict] = []
        seen_keys: set[str] = set()

        for target_uri in targets:
            data = await self._request_json(
                'post',
                '/api/v1/search/find',
                json={
                    'query': query,
                    'target_uri': target_uri,
                    'limit': top_k,
                },
            )
            for item in data.get('results', []):
                content = item.get('content', '') or ''
                uri = item.get('uri', '') or ''
                key = f'{uri}:{hash(content)}'
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                merged.append(
                    {
                        'text': content,
                        'metadata': {
                            'uri': uri,
                            'title': item.get('title', ''),
                            'score': item.get('score', 0),
                        },
                    },
                )
                if len(merged) >= top_k:
                    return merged
        return merged

    async def create_session(self) -> dict:
        return await self._request_json('post', '/api/v1/sessions', json={})

    async def add_message(self, session_id: str, role: str, content: str) -> dict:
        return await self._request_json(
            'post',
            f'/api/v1/sessions/{session_id}/messages',
            json={'role': role, 'content': content},
        )

    async def get_memory_context(self, query: str, account_id: int = 1) -> str:
        target_uri = f'{self._account_root(account_id)}/memory'
        data = await self._request_json(
            'post',
            '/api/v1/search/find',
            json={
                'query': query,
                'target_uri': target_uri,
                'limit': 5,
            },
        )
        parts = []
        for item in data.get('results', []):
            content = item.get('content', '')
            if content:
                parts.append(content)
        return '\n'.join(parts) if parts else ''

    async def health_check(self) -> bool:
        try:
            response = await self._request_with_retry('get', '/health', timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
