import asyncio
import tempfile
import os
import httpx
from typing import Optional
from app.config import get_settings
from app.errors import OpenVikingError, logger

settings = get_settings()

MAX_RETRIES = 2
RETRY_DELAY = 1.0


class ContextBridge:
    """OpenViking HTTP 适配层，替代 ChromaDB 向量检索和部分记忆管理"""

    def __init__(self):
        self._base_url = settings.openviking_server_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=120.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ============= 素材管理 =============

    async def add_material(self, file_path: str, doc_type: str = "", title: str = "", content_text: str = "") -> dict:
        """将素材添加到 OpenViking 资源库

        优先使用已提取的纯文本（写入临时txt文件），避免 OV 解析 docx 兼容性问题。
        """
        client = await self._ensure_client()
        target = f"viking://resources/materials/{doc_type}" if doc_type else None

        actual_path = file_path
        tmp_file = None

        if content_text:
            # 写入临时 txt 文件，让 OV 解析纯文本
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", encoding="utf-8", delete=False,
            )
            tmp_file.write(content_text)
            tmp_file.close()
            actual_path = tmp_file.name

        try:
            resp = await client.post("/api/v1/resources", json={
                "path": actual_path,
                "target": target,
                "reason": f"公文素材: {title}",
                "instruction": f"类型: {doc_type}, 标题: {title}",
                "wait": True,
                "timeout": 120.0,
            })
            return self._parse_response(resp)
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

    async def delete_material(self, uri: str) -> None:
        """删除素材资源"""
        client = await self._ensure_client()
        resp = await client.post("/api/v1/fs/rm", json={
            "uri": uri, "recursive": True,
        })
        self._parse_response(resp)

    # ============= 语义检索 =============

    async def search_materials(
        self, query: str, doc_type: str = None, top_k: int = 5,
    ) -> list[dict]:
        """语义搜索素材（替代 VectorStore.search）"""
        client = await self._ensure_client()
        target_uri = ""
        if doc_type:
            target_uri = f"viking://resources/materials/{doc_type}"
        resp = await client.post("/api/v1/search/find", json={
            "query": query,
            "target_uri": target_uri,
            "limit": top_k,
        })
        data = self._parse_response(resp)
        results = []
        for item in data.get("results", []):
            results.append({
                "text": item.get("content", ""),
                "metadata": {
                    "uri": item.get("uri", ""),
                    "title": item.get("title", ""),
                    "score": item.get("score", 0),
                },
            })
        return results

    # ============= 会话管理 =============

    async def create_session(self) -> dict:
        """在 OpenViking 创建会话"""
        client = await self._ensure_client()
        resp = await client.post("/api/v1/sessions", json={})
        return self._parse_response(resp)

    async def add_message(self, session_id: str, role: str, content: str) -> dict:
        """向 OpenViking 会话添加消息"""
        client = await self._ensure_client()
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": role, "content": content},
        )
        return self._parse_response(resp)

    async def commit_session(self, session_id: str) -> dict:
        """提交会话，触发 OpenViking 自动提取记忆"""
        client = await self._ensure_client()
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/commit",
            timeout=180.0,
        )
        return self._parse_response(resp)

    # ============= 记忆上下文 =============

    async def get_memory_context(self, query: str) -> str:
        """从 OpenViking 检索用户记忆，构建上下文字符串"""
        client = await self._ensure_client()
        resp = await client.post("/api/v1/search/find", json={
            "query": query,
            "target_uri": "viking://user/",
            "limit": 5,
        })
        data = self._parse_response(resp)
        parts = []
        for item in data.get("results", []):
            content = item.get("content", "")
            if content:
                parts.append(content)
        return "\n".join(parts) if parts else ""

    # ============= 健康检查 =============

    async def health_check(self) -> bool:
        """检查 OpenViking Server 是否可用"""
        try:
            client = await self._ensure_client()
            resp = await client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    # ============= 内部方法 =============

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带重试的HTTP请求"""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                client = await self._ensure_client()
                resp = await getattr(client, method)(url, **kwargs)
                return resp
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning("OpenViking %s %s failed (attempt %d/%d): %s", method.upper(), url, attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        raise OpenVikingError(detail=f"连接失败: {last_error}")

    def _parse_response(self, resp: httpx.Response) -> dict:
        """解析 OpenViking HTTP 响应"""
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
