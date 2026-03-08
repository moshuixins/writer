from __future__ import annotations

import json
import re

import jieba
import jieba.analyse
from sqlalchemy.orm import Session

from app.errors import logger
from app.models.style import StyleProfile
from app.prompts.style_analysis import STYLE_ANALYSIS_PROMPT, STYLE_KEYWORDS_PROMPT
from app.prompts.validators import parse_json_response, validate_keywords, validate_style_json
from app.services.llm_service import LLMService


class StyleAnalyzer:
    """Analyze writing style and store per-account style features."""

    def __init__(self, db: Session | None = None, *, account_id: int = 1):
        self.db = db
        self.account_id = int(account_id or 1)
        self.llm = LLMService()

    def analyze_statistics(self, text: str) -> dict:
        sentences = re.split(r"[。！？；]", text or "")
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p.strip() for p in (text or "").split("\n") if p.strip()]

        avg_sent_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
        avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)

        return {
            "avg_sentence_length": round(avg_sent_len, 1),
            "avg_paragraph_length": round(avg_para_len, 1),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
        }

    def analyze_vocabulary(self, text: str) -> dict:
        keywords = jieba.analyse.extract_tags(text or "", topK=20, withWeight=True)
        domain_terms = jieba.analyse.extract_tags(text or "", topK=10)

        llm_keywords: list[str] = []
        llm_domain_terms: list[str] = []
        try:
            raw = self.llm.invoke(STYLE_KEYWORDS_PROMPT.format(content=text or ""))
            parsed = parse_json_response(raw, silent=True)
            if isinstance(parsed, dict):
                kw_raw = parsed.get("keywords", [])
                term_raw = parsed.get("domain_terms", [])
                if isinstance(kw_raw, list):
                    llm_keywords = validate_keywords(json.dumps(kw_raw, ensure_ascii=False), max_keywords=12)
                elif isinstance(kw_raw, str):
                    llm_keywords = validate_keywords(kw_raw, max_keywords=12)
                if isinstance(term_raw, list):
                    llm_domain_terms = validate_keywords(json.dumps(term_raw, ensure_ascii=False), max_keywords=12)
                elif isinstance(term_raw, str):
                    llm_domain_terms = validate_keywords(term_raw, max_keywords=12)
        except Exception as e:
            logger.warning("Style LLM keyword analysis failed: %s", e)

        return {
            "top_keywords": [{"word": w, "weight": round(s, 4)} for w, s in keywords],
            "domain_terms": domain_terms,
            "llm_keywords": llm_keywords,
            "llm_domain_terms": llm_domain_terms,
        }

    def analyze_with_llm(self, text: str) -> dict:
        try:
            result = self.llm.invoke(STYLE_ANALYSIS_PROMPT.format(content=text or ""))
            return validate_style_json(result)
        except Exception as e:
            logger.warning("Style LLM analysis failed: %s", e)
            return {"raw_analysis": "分析失败"}

    def analyze(self, text: str) -> dict:
        return {
            "statistics": self.analyze_statistics(text),
            "vocabulary": self.analyze_vocabulary(text),
            "llm_analysis": self.analyze_with_llm(text),
        }

    def _require_db(self) -> Session:
        if self.db is None:
            raise RuntimeError("database session required for style persistence")
        return self.db

    def store_analysis(self, doc_type: str, features: dict, *, commit: bool = True) -> dict:
        db = self._require_db()
        for name, value in features.items():
            existing = db.query(StyleProfile).filter(
                StyleProfile.account_id == self.account_id,
                StyleProfile.doc_type == doc_type,
                StyleProfile.feature_name == name,
            ).first()

            if existing:
                existing.feature_value = value
                existing.sample_count += 1
            else:
                profile = StyleProfile(
                    account_id=self.account_id,
                    doc_type=doc_type,
                    feature_name=name,
                    feature_value=value,
                    sample_count=1,
                )
                db.add(profile)

        if commit:
            db.commit()
        else:
            db.flush()
        return features

    def analyze_and_store(self, text: str, doc_type: str, *, commit: bool = True):
        features = self.analyze(text)
        return self.store_analysis(doc_type, features, commit=commit)

    def get_style_guidelines(self, doc_type: str) -> str:
        db = self._require_db()
        profiles = db.query(StyleProfile).filter(
            StyleProfile.account_id == self.account_id,
            StyleProfile.doc_type == doc_type,
        ).all()

        if not profiles:
            return "暂无该类型公文的风格数据，将使用通用公文风格。"

        parts = []
        for p in profiles:
            if p.feature_name == "statistics":
                v = p.feature_value
                parts.append(
                    f"- 平均句长约 {v.get('avg_sentence_length', '未知')} 字，"
                    f"平均段落长度约 {v.get('avg_paragraph_length', '未知')} 字"
                )
            elif p.feature_name == "vocabulary":
                terms = p.feature_value.get("llm_domain_terms") or p.feature_value.get("domain_terms", [])
                keywords = p.feature_value.get("llm_keywords") or []
                if terms:
                    parts.append(f"- 常用术语：{', '.join(terms[:10])}")
                if keywords:
                    parts.append(f"- 关键词偏好：{', '.join(keywords[:10])}")
            elif p.feature_name == "llm_analysis":
                v = p.feature_value
                if "opening_pattern" in v:
                    parts.append(f"- 开头模式：{v['opening_pattern']}")
                if "closing_pattern" in v:
                    parts.append(f"- 结尾模式：{v['closing_pattern']}")
                if "body_structure" in v:
                    parts.append(f"- 正文结构：{v['body_structure']}")
                if "sentence_style" in v:
                    parts.append(f"- 句式偏好：{v['sentence_style']}")
                if "reason_pattern" in v:
                    parts.append(f"- 缘由句式：{v['reason_pattern']}")
                if "requirement_strength" in v:
                    parts.append(f"- 要求力度：{v['requirement_strength']}")
                if "characteristic_phrases" in v:
                    phrases = v["characteristic_phrases"][:8]
                    parts.append(f"- 特征短语：{', '.join(phrases)}")
                if "transition_words" in v:
                    words = v["transition_words"][:6]
                    parts.append(f"- 过渡词：{', '.join(words)}")
                data_elements = v.get("data_elements")
                if isinstance(data_elements, list) and data_elements:
                    for item in data_elements[:6]:
                        if not isinstance(item, dict):
                            continue
                        dtype = str(item.get("type", "")).strip()
                        topic = str(item.get("topic", "")).strip()
                        usage = str(item.get("usage_pattern", "")).strip()
                        example = str(item.get("value_example", "")).strip()
                        line_parts = []
                        if dtype:
                            line_parts.append(f"类型：{dtype}")
                        if topic:
                            line_parts.append(f"主题：{topic}")
                        if usage:
                            line_parts.append(f"方式：{usage}")
                        if example:
                            line_parts.append(f"示例：{example}")
                        if line_parts:
                            parts.append(f"- 数据要素：{'；'.join(line_parts)}")

        return "\n".join(parts) if parts else "暂无风格数据"
