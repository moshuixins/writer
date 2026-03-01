from __future__ import annotations

import copy
import json
from typing import Any


class EditorDocParser:
    MAX_DRAFT_BYTES = 1024 * 1024
    MAX_TOTAL_TEXT = 200000
    MAX_NODE_COUNT = 6000

    ALLOWED_NODE_TYPES = {"doc", "paragraph", "heading", "text", "hardBreak"}
    ALLOWED_MARK_TYPES = {"bold", "underline"}

    def default_draft(self, title: str = "") -> dict[str, Any]:
        return {
            "title": (title or "").strip(),
            "recipients": "",
            "body_json": self.default_body_json(),
            "signing_org": "",
            "date": "",
        }

    def default_body_json(self) -> dict[str, Any]:
        return {
            "type": "doc",
            "content": [{"type": "paragraph"}],
        }

    def normalize_draft(self, draft: Any, title_fallback: str = "") -> dict[str, Any]:
        if not isinstance(draft, dict):
            raise ValueError("draft must be an object")

        normalized = {
            "title": str(draft.get("title", "") or "").strip() or (title_fallback or "").strip(),
            "recipients": str(draft.get("recipients", "") or "").strip(),
            "body_json": draft.get("body_json", self.default_body_json()),
            "signing_org": str(draft.get("signing_org", "") or "").strip(),
            "date": str(draft.get("date", "") or "").strip(),
        }

        self.validate_body_json(normalized["body_json"])
        self.validate_draft_size(normalized)
        return normalized

    def normalize_or_default(self, draft: Any, title_fallback: str = "") -> dict[str, Any]:
        if not isinstance(draft, dict):
            return self.default_draft(title_fallback)
        try:
            return self.normalize_draft(draft, title_fallback=title_fallback)
        except ValueError:
            return self.default_draft(title_fallback)

    def validate_draft_size(self, draft: dict[str, Any]) -> None:
        try:
            payload = json.dumps(draft, ensure_ascii=False)
        except Exception as exc:
            raise ValueError("invalid draft payload") from exc

        if len(payload.encode("utf-8")) > self.MAX_DRAFT_BYTES:
            raise ValueError("draft exceeds 1MB limit")

    def validate_body_json(self, body_json: Any) -> None:
        if not isinstance(body_json, dict):
            raise ValueError("body_json must be an object")
        if body_json.get("type") != "doc":
            raise ValueError("body_json root must be doc")

        node_counter = [0]
        total_chars = [0]
        self._validate_node(body_json, node_counter, total_chars)

        if node_counter[0] > self.MAX_NODE_COUNT:
            raise ValueError("body_json node count exceeds limit")
        if total_chars[0] > self.MAX_TOTAL_TEXT:
            raise ValueError("body_json text length exceeds limit")

    def _validate_node(self, node: Any, node_counter: list[int], total_chars: list[int]) -> None:
        if not isinstance(node, dict):
            raise ValueError("invalid node")

        node_counter[0] += 1

        node_type = node.get("type")
        if node_type not in self.ALLOWED_NODE_TYPES:
            raise ValueError(f"unsupported node type: {node_type}")

        marks = node.get("marks")
        if marks is not None:
            if not isinstance(marks, list):
                raise ValueError("marks must be a list")
            for mark in marks:
                if not isinstance(mark, dict):
                    raise ValueError("invalid mark")
                mark_type = mark.get("type")
                if mark_type not in self.ALLOWED_MARK_TYPES:
                    raise ValueError(f"unsupported mark type: {mark_type}")

        if node_type == "heading":
            attrs = node.get("attrs") or {}
            if not isinstance(attrs, dict):
                raise ValueError("heading attrs must be an object")
            level = attrs.get("level", 2)
            if level not in (2, 3):
                raise ValueError("heading level must be 2 or 3")

        if node_type == "text":
            text = node.get("text", "")
            if not isinstance(text, str):
                raise ValueError("text node must contain string text")
            total_chars[0] += len(text)

        content = node.get("content")
        if content is not None:
            if not isinstance(content, list):
                raise ValueError("node content must be a list")
            for child in content:
                self._validate_node(child, node_counter, total_chars)

    def draft_to_content_json(self, draft: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalize_draft(draft)
        body_sections = self.tiptap_body_to_sections(normalized["body_json"])

        return {
            "title": normalized["title"],
            "doc_number": "",
            "recipients": normalized["recipients"],
            "body_sections": body_sections,
            "attachments": [],
            "signing_org": normalized["signing_org"],
            "date": normalized["date"],
        }

    def draft_to_plain_text(self, draft: dict[str, Any]) -> str:
        normalized = self.normalize_draft(draft)
        sections = self.tiptap_body_to_sections(normalized["body_json"])

        lines: list[str] = []
        if normalized["title"]:
            lines.append(normalized["title"])
        if normalized["recipients"]:
            lines.append(normalized["recipients"])

        for section in sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            if heading:
                lines.append(heading)
            if content:
                lines.append(content)

        if normalized["signing_org"]:
            lines.append(normalized["signing_org"])
        if normalized["date"]:
            lines.append(normalized["date"])

        return "\n".join(lines).strip()

    def tiptap_body_to_sections(self, body_json: dict[str, Any]) -> list[dict[str, Any]]:
        self.validate_body_json(body_json)

        root_content = body_json.get("content") or []
        sections: list[dict[str, Any]] = []

        pending_heading = ""
        pending_level = 1

        for node in root_content:
            node_type = node.get("type")
            if node_type == "heading":
                if pending_heading:
                    sections.append({
                        "heading": pending_heading,
                        "content": "",
                        "level": pending_level,
                    })
                pending_heading = self._extract_text(node).strip()
                pending_level = self._map_heading_level(node.get("attrs", {}).get("level", 2))
                continue

            if node_type == "paragraph":
                paragraph_text = self._extract_text(node).strip()
                if pending_heading:
                    sections.append({
                        "heading": pending_heading,
                        "content": paragraph_text,
                        "level": pending_level,
                    })
                    pending_heading = ""
                    pending_level = 1
                elif paragraph_text:
                    sections.append({
                        "heading": "",
                        "content": paragraph_text,
                        "level": 0,
                    })

        if pending_heading:
            sections.append({
                "heading": pending_heading,
                "content": "",
                "level": pending_level,
            })

        return sections

    def _map_heading_level(self, editor_level: int) -> int:
        return 1 if editor_level == 2 else 2

    def _extract_text(self, node: Any) -> str:
        if not isinstance(node, dict):
            return ""

        node_type = node.get("type")
        if node_type == "text":
            text_value = node.get("text", "")
            return text_value if isinstance(text_value, str) else ""
        if node_type == "hardBreak":
            return "\n"

        children = node.get("content") or []
        if not isinstance(children, list):
            return ""

        pieces: list[str] = []
        for child in children:
            pieces.append(self._extract_text(child))
        return "".join(pieces)

    def clone_default_body_json(self) -> dict[str, Any]:
        return copy.deepcopy(self.default_body_json())
