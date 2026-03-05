"""Canonical document type catalog (79 types + fallback)."""

from __future__ import annotations

from typing import Final

OTHER_DOC_TYPE: Final[str] = "其他"

DOC_TYPE_GROUPS: Final[list[dict[str, object]]] = [
    {
        "id": "official",
        "label": "公务类文书",
        "doc_types": [
            "决定",
            "公告",
            "通告",
            "意见",
            "通知",
            "通报",
            "报告",
            "请示",
            "批复",
            "函",
            "会议纪要",
        ],
    },
    {
        "id": "affairs",
        "label": "事务类文书",
        "doc_types": [
            "规划",
            "计划",
            "安排",
            "总结",
            "声明",
            "启事",
            "简报",
            "述职报告",
        ],
    },
    {
        "id": "regulation",
        "label": "规章类文书",
        "doc_types": [
            "章程",
            "条例",
            "办法",
            "规定",
            "细则",
            "守则",
            "制度",
        ],
    },
    {
        "id": "meeting",
        "label": "会议类文书",
        "doc_types": [
            "讲话稿",
            "演讲词",
            "开幕词",
            "闭幕词",
            "会议记录",
            "心得体会",
        ],
    },
    {
        "id": "economic",
        "label": "经济类文书",
        "doc_types": [
            "市场调查报告",
            "商业计划书",
            "可行性分析报告",
            "经济合同",
            "广告文案",
            "招标书",
            "投标书",
            "清算报告",
            "破产申请书",
        ],
    },
    {
        "id": "trade",
        "label": "贸易类文书",
        "doc_types": [
            "合作意向书",
            "询价函",
            "报价函",
            "订购函",
            "催款函",
            "索赔函",
            "理赔函",
        ],
    },
    {
        "id": "legal",
        "label": "法律类文书",
        "doc_types": [
            "起诉状",
            "上诉状",
            "申诉状",
            "答辩状",
            "委托书",
            "担保书",
        ],
    },
    {
        "id": "letters",
        "label": "书信类文书",
        "doc_types": [
            "证明信",
            "介绍信",
            "推荐信",
            "感谢信",
            "公开信",
            "慰问信",
            "表扬信",
            "批评信",
            "倡议书",
        ],
    },
    {
        "id": "notes",
        "label": "条据类文书",
        "doc_types": [
            "留言条",
            "请假条",
            "借条",
            "收条",
            "欠条",
            "发条",
            "领条",
        ],
    },
    {
        "id": "etiquette",
        "label": "礼仪类文书",
        "doc_types": [
            "贺信（电）",
            "邀请书",
            "颁奖词",
            "欢迎词",
            "欢送词",
            "祝酒词",
            "答谢词",
            "讣告",
            "悼词",
        ],
    },
    {
        "id": "fallback",
        "label": "其他",
        "doc_types": [OTHER_DOC_TYPE],
    },
]

_all_doc_types = [doc_type for group in DOC_TYPE_GROUPS for doc_type in group["doc_types"]]
if OTHER_DOC_TYPE not in _all_doc_types:
    _all_doc_types.append(OTHER_DOC_TYPE)

CANONICAL_DOC_TYPES: Final[tuple[str, ...]] = tuple(_all_doc_types)
CANONICAL_DOC_TYPE_SET: Final[frozenset[str]] = frozenset(CANONICAL_DOC_TYPES)

# Internal-only aliases for normalization in LLM classification results.
DOC_TYPE_ALIASES: Final[dict[str, str]] = {
    "纪要": "会议纪要",
    "讲话": "讲话稿",
    "讲话材料": "讲话稿",
    "心得": "心得体会",
    "体会": "心得体会",
    "贺信": "贺信（电）",
    "贺电": "贺信（电）",
    "邀请函": "邀请书",
    "欢迎辞": "欢迎词",
    "欢送辞": "欢送词",
    "感谢函": "感谢信",
    "公开函": "公开信",
}

DOC_TYPE_TO_GROUP: Final[dict[str, str]] = {}
for _group in DOC_TYPE_GROUPS:
    for _doc_type in _group["doc_types"]:
        DOC_TYPE_TO_GROUP[_doc_type] = str(_group["label"])

DOC_TYPE_TO_SLUG: Final[dict[str, str]] = {}
for _idx, _doc_type in enumerate(CANONICAL_DOC_TYPES, start=1):
    DOC_TYPE_TO_SLUG[_doc_type] = f"doc_type_{_idx:03d}"

DOC_TYPE_CHOICES_TEXT: Final[str] = "|".join(CANONICAL_DOC_TYPES)


def is_canonical_doc_type(value: str | None) -> bool:
    if not value:
        return False
    return value.strip() in CANONICAL_DOC_TYPE_SET


def normalize_doc_type(value: str | None) -> str | None:
    """Normalize known aliases to canonical doc types."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in CANONICAL_DOC_TYPE_SET:
        return cleaned
    return DOC_TYPE_ALIASES.get(cleaned)


def get_all_doc_types() -> list[str]:
    return list(CANONICAL_DOC_TYPES)
