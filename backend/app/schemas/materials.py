from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import ApiModel, ListResponse, WarningMixin


class MaterialResponse(ApiModel):
    id: int
    title: str
    doc_type: str | None = None
    summary: str
    keywords: list[str] = Field(default_factory=list)
    char_count: int
    content_text: str | None = None
    original_filename: str | None = None
    created_at: str | None = None


class MaterialUploadResponse(MaterialResponse, WarningMixin):
    pass


class MaterialListResponse(ListResponse[MaterialResponse]):
    pass


class MaterialSearchHitMetadataResponse(ApiModel):
    uri: str = ""
    title: str = ""
    score: float = 0.0


class MaterialSearchHitResponse(ApiModel):
    text: str
    metadata: MaterialSearchHitMetadataResponse = Field(default_factory=MaterialSearchHitMetadataResponse)


class MaterialSearchResponse(ListResponse[MaterialSearchHitResponse]):
    pass


class UploadTaskResponse(ApiModel):
    task_id: str
    status: str
    stage: str
    message: str
    parse_progress: int
    updated_at: int


class BookScanItemResponse(ApiModel):
    source_name: str
    relative_path: str
    source_hash: str
    file_ext: str
    file_size: int
    imported: bool
    status: str
    doc_type: str | None = None
    updated_at: str | None = None
    source_id: int | None = None


class BookScanResponse(ListResponse[BookScanItemResponse]):
    books_dir: str


class BookImportStartResponse(ApiModel):
    task_id: str
    status: str
    total_files: int


class BookImportFileResultResponse(ApiModel):
    source_name: str
    status: str
    chunk_count: int
    ocr_used: bool
    ocr_pages: int
    error_message: str = ""


class BookImportTaskResponse(ApiModel):
    task_id: str
    status: str
    stage: str
    message: str
    rebuild: bool
    started_at: int
    updated_at: int
    finished_at: int | None = None
    total_files: int
    completed_files: int
    failed_files: int
    partial_files: int
    skipped_files: int
    running_file: str
    file_progress: int
    total_chunks: int
    completed_chunks: int
    chunk_progress: int
    overall_progress: int
    ocr_used_files: int
    ocr_pages: int
    file_results: list[BookImportFileResultResponse] = Field(default_factory=list)
    selected_files: list[str] = Field(default_factory=list)


class BookUploadErrorResponse(ApiModel):
    source_name: str
    error_message: str


class BookUploadResponse(ListResponse[BookScanItemResponse]):
    uploaded_count: int
    failed_count: int
    errors: list[BookUploadErrorResponse] = Field(default_factory=list)


class BookSourceResponse(ApiModel):
    id: int
    source_name: str
    source_hash: str
    file_ext: str
    file_size: int
    status: str
    doc_type: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    chunk_count: int
    ocr_used: bool
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class BookSourceListResponse(ListResponse[BookSourceResponse]):
    pass
