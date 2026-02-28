import re
from sqlalchemy.orm import Session
import jieba
import jieba.analyse
from app.services.llm_service import LLMService
from app.models.style import StyleProfile
from app.prompts.style_analysis import STYLE_ANALYSIS_PROMPT
from app.prompts.validators import validate_style_json
from app.errors import logger


class StyleAnalyzer:
    """风格分析服务：从素材中提取写作风格特征"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()

    def analyze_statistics(self, text: str) -> dict:
        """提取统计特征"""
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        avg_sent_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
        avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)

        return {
            "avg_sentence_length": round(avg_sent_len, 1),
            "avg_paragraph_length": round(avg_para_len, 1),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
        }

    def analyze_vocabulary(self, text: str) -> dict:
        """提取词汇特征"""
        keywords = jieba.analyse.extract_tags(text, topK=20, withWeight=True)
        return {
            "top_keywords": [{"word": w, "weight": round(s, 4)} for w, s in keywords],
            "domain_terms": jieba.analyse.extract_tags(text, topK=10),
        }

    def analyze_with_llm(self, text: str) -> dict:
        """使用LLM分析写作风格"""
        truncated = text[:3000]
        try:
            result = self.llm.invoke(STYLE_ANALYSIS_PROMPT.format(content=truncated))
            return validate_style_json(result)
        except Exception as e:
            logger.warning("Style LLM analysis failed: %s", e)
            return {"raw_analysis": "分析失败"}

    def analyze_and_store(self, text: str, doc_type: str):
        """完整分析并存入风格档案"""
        stats = self.analyze_statistics(text)
        vocab = self.analyze_vocabulary(text)
        llm_analysis = self.analyze_with_llm(text)

        features = {
            "statistics": stats,
            "vocabulary": vocab,
            "llm_analysis": llm_analysis,
        }

        for name, value in features.items():
            existing = self.db.query(StyleProfile).filter(
                StyleProfile.doc_type == doc_type,
                StyleProfile.feature_name == name,
            ).first()

            if existing:
                existing.feature_value = value
                existing.sample_count += 1
            else:
                profile = StyleProfile(
                    doc_type=doc_type,
                    feature_name=name,
                    feature_value=value,
                    sample_count=1,
                )
                self.db.add(profile)

        self.db.commit()
        return features

    def get_style_guidelines(self, doc_type: str) -> str:
        """获取某类公文的风格指南文本"""
        profiles = self.db.query(StyleProfile).filter(
            StyleProfile.doc_type == doc_type,
        ).all()

        if not profiles:
            return "暂无该类型公文的风格数据，将使用通用公文风格。"

        parts = []
        for p in profiles:
            if p.feature_name == "statistics":
                v = p.feature_value
                parts.append(
                    f"- 平均句长约{v.get('avg_sentence_length', '未知')}字，"
                    f"平均段落长度约{v.get('avg_paragraph_length', '未知')}字"
                )
            elif p.feature_name == "vocabulary":
                terms = p.feature_value.get("domain_terms", [])
                if terms:
                    parts.append(f"- 常用术语：{', '.join(terms[:10])}")
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

        return "\n".join(parts) if parts else "暂无风格数据"
