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
        self._base_url = settings.openviking_server_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if settings.openviking_root_api_key:
                headers["Authorization"] = f"Bearer {settings.openviking_root_api_key}"
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=120.0,
                headers=headers,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _delayed_cleanup(self, file_path: Path, delay_seconds: int = 900) -> None:
        await asyncio.sleep(delay_seconds)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning("Failed to cleanup OV staging file %s: %s", file_path, e)

    async def add_material(
        self,
        file_path: str,
        doc_type: str = "",
        title: str = "",
        content_text: str = "",
    ) -> dict:
        """Add material resource to OpenViking."""
        client = await self._ensure_client()
        target = f"viking://resources/materials/{doc_type}" if doc_type else None

        actual_path = file_path
        staged_file: Path | None = None

        if content_text:
            # The OpenViking service runs in another container.
            # Write text into a shared host-mounted directory and pass OV-visible path.
            backend_staging_dir = Path(settings.openviking_shared_backend_dir)
            backend_staging_dir.mkdir(parents=True, exist_ok=True)
            staged_file = backend_staging_dir / f"{uuid.uuid4().hex}.txt"
            staged_file.write_text(content_text, encoding="utf-8")

            ov_staging_dir = settings.openviking_shared_ov_dir.rstrip("/")
            actual_path = f"{ov_staging_dir}/{staged_file.name}" if ov_staging_dir else str(staged_file)

        try:
            resp = await client.post(
                "/api/v1/resources",
                json={
                    "path": actual_path,
                    "target": target,
                    "reason": f"公文素材: {title}",
                    "instruction": f"类型: {doc_type}, 标题: {title}",
                    "wait": True,
                    "timeout": 120.0,
                },
            )
            return self._parse_response(resp)
        finally:
            if staged_file is not None:
                # Keep file briefly to avoid parser race, then cleanup in background.
                asyncio.create_task(self._delayed_cleanup(staged_file))

    async def delete_material(self, uri: str) -> None:
        """Delete a material resource."""
        client = await self._ensure_client()
        resp = await client.post("/api/v1/fs/rm", json={"uri": uri, "recursive": True})
        self._parse_response(resp)

    async def search_materials(self, query: str, doc_type: str = None, top_k: int = 5) -> list[dict]:
        """Semantic search for material resources."""
        client = await self._ensure_client()
        target_uri = f"viking://resources/materials/{doc_type}" if doc_type else ""
        resp = await client.post(
            "/api/v1/search/find",
            json={
                "query": query,
                "target_uri": target_uri,
                "limit": top_k,
            },
        )
        data = self._parse_response(resp)
        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "text": item.get("content", ""),
                    "metadata": {
                        "uri": item.get("uri", ""),
                        "title": item.get("title", ""),
                        "score": item.get("score", 0),
                    },
                },
            )
        return results

    async def create_session(self) -> dict:
        """Create a session in OpenViking."""
        client = await self._ensure_client()
        resp = await client.post("/api/v1/sessions", json={})
        return self._parse_response(resp)

    async def add_message(self, session_id: str, role: str, content: str) -> dict:
        """Append a message to an OpenViking session."""
        client = await self._ensure_client()
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": role, "content": content},
        )
        return self._parse_response(resp)

    async def commit_session(self, session_id: str) -> dict:
        """Commit a session to trigger memory extraction."""
        client = await self._ensure_client()
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/commit",
            timeout=180.0,
        )
        return self._parse_response(resp)

    async def get_memory_context(self, query: str) -> str:
        """Fetch memory snippets from OpenViking and return merged text."""
        client = await self._ensure_client()
        resp = await client.post(
            "/api/v1/search/find",
            json={
                "query": query,
                "target_uri": "viking://user/",
                "limit": 5,
            },
        )
        data = self._parse_response(resp)
        parts = []
        for item in data.get("results", []):
            content = item.get("content", "")
            if content:
                parts.append(content)
        return "\n".join(parts) if parts else ""

    async def health_check(self) -> bool:
        """Check whether OpenViking server is reachable."""
        try:
            client = await self._ensure_client()
            resp = await client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Issue HTTP request with retry."""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                client = await self._ensure_client()
                resp = await getattr(client, method)(url, **kwargs)
                return resp
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning(
                    "OpenViking %s %s failed (attempt %d/%d): %s",
                    method.upper(),
                    url,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    e,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        raise OpenVikingError(detail=f"连接失败: {last_error}")

    def _parse_response(self, resp: httpx.Response) -> dict:
        """Parse OpenViking HTTP response."""
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            logger.error("OpenViking error %d: %s", resp.status_code, detail)
            raise OpenVikingError(detail=f"({resp.status_code}) {detail}")
        try:
            data = resp.json()
        except Exception:
            return {}
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return data
