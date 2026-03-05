from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.book_style_rule import BookStyleRule


class BookRuleService:
    def __init__(self, db: Session, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)

    def replace_rules(
        self,
        *,
        source_id: int,
        doc_type: str,
        rules: Iterable[dict[str, object]],
    ) -> int:
        self.db.query(BookStyleRule).filter(
            BookStyleRule.account_id == self.account_id,
            BookStyleRule.source_id == source_id,
        ).delete()

        count = 0
        for rule in rules:
            text = str(rule.get("rule_text", "")).strip()
            if not text:
                continue
            row = BookStyleRule(
                account_id=self.account_id,
                source_id=source_id,
                doc_type=doc_type,
                rule_type=str(rule.get("rule_type", "structure")).strip() or "structure",
                rule_text=text[:4000],
                confidence=max(0.0, min(1.0, float(rule.get("confidence", 0.6) or 0.6))),
                origin_ref=str(rule.get("origin_ref", "")).strip()[:300],
            )
            self.db.add(row)
            count += 1

        self.db.commit()
        return count

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        lowered = (text or "").lower()
        tokens = [t for t in re.split(r"[^\w\u4e00-\u9fff]+", lowered) if len(t) >= 2]
        return set(tokens)

    def get_rules_for_prompt(self, *, doc_type: str, query: str, top_k: int) -> list[str]:
        base_rows = (
            self.db.query(BookStyleRule)
            .filter(
                BookStyleRule.account_id == self.account_id,
                BookStyleRule.doc_type == doc_type,
            )
            .all()
        )
        if not base_rows:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            sorted_rows = sorted(base_rows, key=lambda x: (x.confidence, x.id), reverse=True)
        else:
            scored_rows: list[tuple[float, BookStyleRule]] = []
            for row in base_rows:
                haystack = f"{row.rule_text} {row.origin_ref}"
                tokens = self._tokenize(haystack)
                overlap = len(tokens.intersection(query_tokens))
                score = overlap + float(row.confidence or 0.0)
                scored_rows.append((score, row))
            scored_rows.sort(key=lambda x: x[0], reverse=True)
            sorted_rows = [row for _, row in scored_rows]

        items: list[str] = []
        for row in sorted_rows[: max(0, top_k)]:
            prefix = f"[{row.rule_type}]"
            if row.origin_ref:
                items.append(f"{prefix} {row.rule_text}（来源：{row.origin_ref}）")
            else:
                items.append(f"{prefix} {row.rule_text}")
        return items
