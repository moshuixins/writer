from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class WarningMixin(ApiModel):
    warnings: list[str] | None = None


class MessageResponse(ApiModel):
    message: str


class ListResponse(ApiModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int
