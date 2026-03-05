"""Validation helpers for LLM outputs and doc types."""

from __future__ import annotations

import json
import re
from typing import Any

from app.errors import logger
from app.prompts.doc_types_catalog import (
    CANONICAL_DOC_TYPE_SET,
    CANONICAL_DOC_TYPES,
    DOC_TYPE_ALIASES,
    OTHER_DOC_TYPE,
    is_canonical_doc_type,
    normalize_doc_type,
)

VALID_DOC_TYPES = set(CANONICAL_DOC_TYPES)


def ensure_canonical_doc_type(raw: str) -> str:
    """Validate API input doc_type strictly against canonical values."""
    cleaned = (raw or "").strip()
    if cleaned in CANONICAL_DOC_TYPE_SET:
        return cleaned
    raise ValueError(f"invalid_doc_type:{raw}")


def validate_classify(raw: str) -> str:
    """Normalize LLM classification output; fallback to '其他'."""
    cleaned = (raw or "").strip().strip("\"'“”‘’[]()")
    if not cleaned:
        return OTHER_DOC_TYPE

    normalized = normalize_doc_type(cleaned)
    if normalized:
        return normalized

    # Fuzzy contains for robust model output parsing.
    for alias, target in DOC_TYPE_ALIASES.items():
        if alias and alias in cleaned:
            return target
    for doc_type in VALID_DOC_TYPES:
        if doc_type in cleaned:
            return doc_type

    logger.warning("Invalid classification result: %s", raw)
    return OTHER_DOC_TYPE


def parse_json_response(raw: str, silent: bool = False) -> Any | None:
    """Parse JSON from model output, including fenced markdown."""
    text = (raw or "").strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if not silent:
            logger.warning("Failed to parse JSON from LLM: %s", text[:300])
        return None


def validate_keywords(raw: str, max_keywords: int = 10) -> list[str]:
    """Validate keywords from list/json/string and normalize duplicates."""
    text = (raw or "").strip()
    if not text:
        return []

    values: list[Any] = []
    data = parse_json_response(text, silent=True)
    if isinstance(data, list):
        values = data
    elif isinstance(data, dict):
        maybe = data.get("keywords")
        if isinstance(maybe, list):
            values = maybe
        elif isinstance(maybe, str):
            values = [maybe]

    if not values:
        normalized = re.sub(r"^(keywords|关键词)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
        values = re.split(r"[,，;；、\n\r\t]+", normalized)

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item is None:
            continue
        keyword = str(item).strip().strip("\"'`[]")
        keyword = re.sub(r"^\d+[\.\)．、\s]*", "", keyword)
        keyword = re.sub(r"^(keywords|关键词)\s*[:：]\s*", "", keyword, flags=re.IGNORECASE)
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        cleaned.append(keyword)
        if len(cleaned) >= max_keywords:
            break
    return cleaned


def validate_title(raw: str, fallback: str = "", max_len: int = 100) -> str:
    """Validate title from model output."""
    text = (raw or "").strip()
    if not text:
        return (fallback or "").strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return (fallback or "").strip()

    title = lines[0]
    title = re.sub(r"^(标题|题目)\s*[:：]\s*", "", title)
    title = title.strip().strip("\"'“”‘’【】[]")
    title = re.sub(r"\s+", " ", title)

    invalid_titles = {"无", "无标题", "未提供标题", "N/A", "NA"}
    if not title or title in invalid_titles:
        return (fallback or "").strip()

    if len(title) > max_len:
        title = title[:max_len].rstrip("，。；,.!?！？")
    return title or (fallback or "").strip()


def validate_writing_json(raw: str) -> dict[str, Any]:
    """Validate writing JSON output with fallback wrapper."""
    data = parse_json_response(raw)
    if data and isinstance(data, dict):
        if "body_sections" in data and not isinstance(data["body_sections"], list):
            data["body_sections"] = []
        return data
    return {
        "title": "",
        "recipients": "",
        "body_sections": [{"heading": "", "content": raw, "level": 0}],
        "signing_org": "",
        "date": "",
    }


def validate_style_json(raw: str) -> dict[str, Any]:
    """Validate style analysis JSON; keep raw text on failure."""
    data = parse_json_response(raw)
    if data and isinstance(data, dict):
        return data
    return {"raw_analysis": raw}


__all__ = [
    "VALID_DOC_TYPES",
    "ensure_canonical_doc_type",
    "is_canonical_doc_type",
    "normalize_doc_type",
    "validate_classify",
    "parse_json_response",
    "validate_keywords",
    "validate_title",
    "validate_writing_json",
    "validate_style_json",
]

