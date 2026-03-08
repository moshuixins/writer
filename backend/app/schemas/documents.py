from __future__ import annotations

from app.schemas.common import ListResponse, ApiModel


class GeneratedDocumentHistoryItemResponse(ApiModel):
    id: int
    title: str
    doc_type: str
    version: int
    created_at: str | None = None


class GeneratedDocumentHistoryListResponse(ListResponse[GeneratedDocumentHistoryItemResponse]):
    pass
