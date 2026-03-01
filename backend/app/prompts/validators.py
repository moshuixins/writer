"""LLM 返回结果校验工具"""
import json
import re
from typing import Any
from app.errors import logger

VALID_DOC_TYPES = {
    "通知", "报告", "请示", "批复", "函",
    "纪要", "方案", "总结", "讲话稿", "其他",
}


def validate_classify(raw: str) -> str:
    """校验分类结果，不合法则返回'其他'"""
    cleaned = raw.strip().strip("\"'。.，,")
    if cleaned in VALID_DOC_TYPES:
        return cleaned
    for t in VALID_DOC_TYPES:
        if t in cleaned:
            return t
    logger.warning("Invalid classification result: %s", raw)
    return "其他"


def parse_json_response(raw: str, silent: bool = False) -> Any | None:
    """从 LLM 返回中提取 JSON，支持 markdown 代码块"""
    text = raw.strip()
    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if not silent:
            logger.warning("Failed to parse JSON from LLM: %s", text[:200])
        return None


def validate_keywords(raw: str, max_keywords: int = 10) -> list[str]:
    """校验关键词提取结果，兼容 JSON 数组/JSON 对象/分隔字符串。"""
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
        normalized = text
        if normalized.lower().startswith("keywords"):
            normalized = re.sub(r"^keywords\s*[:：]\s*", "", normalized, flags=re.IGNORECASE)
        if normalized.startswith("关键词") or normalized.startswith("关键字"):
            normalized = re.sub(r"^(关键词|关键字)\s*[:：]\s*", "", normalized)
        values = re.split(r"[，,、;；\n\r\t]+", normalized)

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item is None:
            continue
        keyword = str(item).strip().strip("\"'`[]")
        keyword = re.sub(r"^\d+[\.\)\、]\s*", "", keyword)
        keyword = re.sub(r"^keywords\s*[:：]\s*", "", keyword, flags=re.IGNORECASE)
        keyword = re.sub(r"^(关键词|关键字)\s*[:：]\s*", "", keyword)
        if not keyword:
            continue
        if keyword in seen:
            continue
        seen.add(keyword)
        cleaned.append(keyword)
        if len(cleaned) >= max_keywords:
            break

    return cleaned


def validate_writing_json(raw: str) -> dict:
    """校验写作生成的 JSON 结构，返回合法 dict 或兜底结构"""
    data = parse_json_response(raw)
    if data and isinstance(data, dict):
        # 确保 body_sections 是 list
        if "body_sections" in data and not isinstance(data["body_sections"], list):
            data["body_sections"] = []
        return data
    # 兜底：把原始文本包装成结构化格式
    return {
        "title": "",
        "recipients": "",
        "body_sections": [{"heading": "", "content": raw, "level": 0}],
        "signing_org": "",
        "date": "",
    }


def validate_style_json(raw: str) -> dict:
    """校验风格分析 JSON，失败返回 raw_analysis"""
    data = parse_json_response(raw)
    if data and isinstance(data, dict):
        return data
    return {"raw_analysis": raw}
