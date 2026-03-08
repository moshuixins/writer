from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from app.schemas.common import ApiModel, ListResponse, WarningMixin


class ChatSessionResponse(ApiModel):
    id: int
    title: str
    doc_type: str | None = None
    status: str
    created_at: str | None = None


class ChatSessionWithWarningsResponse(ChatSessionResponse, WarningMixin):
    pass


class ChatSessionListResponse(ListResponse[ChatSessionResponse]):
    pass


class ChatMessageResponse(ApiModel):
    id: int | str
    role: str
    content: str
    created_at: str | None = None


class ChatMessageListResponse(ListResponse[ChatMessageResponse]):
    pass


class ChatReplyResponse(WarningMixin):
    reply: str


class ReviewIssueResponse(ApiModel):
    type: str = ""
    severity: str = ""
    detail: str = ""
    suggestion: str = ""


class ReviewResponse(ApiModel):
    score: int = 0
    issues: list[ReviewIssueResponse] = Field(default_factory=list)
    summary: str = ""


class SessionDraftResponse(ApiModel):
    exists: bool
    session_id: int
    updated_at: str | None = None
    draft: dict[str, Any] = Field(default_factory=dict)
    save_mode: str | None = None


class ChatWorkflowSseEventResponse(ApiModel):
    event: Literal['workflow']
    step: str
    status: Literal['running', 'done', 'error']
    detail: str | None = None


class ChatChunkSseEventResponse(ApiModel):
    event: Literal['chunk']
    chunk: str


class ChatErrorSseEventResponse(ApiModel):
    event: Literal['error']
    error: str


class ChatFinalSseEventResponse(WarningMixin):
    event: Literal['final']
    message: ChatMessageResponse


ChatStreamEventResponse = Annotated[
    ChatWorkflowSseEventResponse | ChatChunkSseEventResponse | ChatErrorSseEventResponse | ChatFinalSseEventResponse,
    Field(discriminator='event'),
]
