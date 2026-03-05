"""Writing guides for canonical document types."""

from __future__ import annotations

from typing import Final

from app.prompts.doc_types_catalog import DOC_TYPE_GROUPS, OTHER_DOC_TYPE, normalize_doc_type


GROUP_GUIDE_TEMPLATES: Final[dict[str, dict[str, object]]] = {
    "公务类文书": {
        "definition": "用于机关单位履职、部署、请示、答复和通报等正式公务场景。",
        "structure": [
            "标题：发文机关+事由+文种，避免口号式标题",
            "主送对象：按行文关系准确填写",
            "正文：按“缘由-事项-要求/结语”组织，层级清晰",
            "结尾：使用规范公务语句，避免口语化表达",
        ],
        "tone": "正式、准确、权威，避免情绪化与夸饰语。",
        "common_errors": "文种混用、主送对象错误、结构缺段、语气失衡。",
    },
    "事务类文书": {
        "definition": "用于单位日常工作安排、回顾总结、公告说明等事务管理场景。",
        "structure": [
            "标题：直接点明事项与文种",
            "正文：背景/目的、具体安排或复盘、后续要求",
            "关键项：时间、责任人、执行路径、完成标准",
        ],
        "tone": "清晰、务实、可执行。",
        "common_errors": "空泛描述多、可执行信息不足、缺少时间与责任约束。",
    },
    "规章类文书": {
        "definition": "用于制度建设、规则发布、流程规范与执行约束。",
        "structure": [
            "标题：对象+事项+文种",
            "条款：适用范围、职责分工、流程标准、责任追究",
            "术语：定义清楚，避免歧义",
        ],
        "tone": "规范、严谨、可落地，措辞避免模糊。",
        "common_errors": "条款交叉冲突、责任边界不清、操作标准不完整。",
    },
    "会议类文书": {
        "definition": "用于会议发言、主持、记录与会务总结场景。",
        "structure": [
            "开场：对象称谓+会议目的",
            "主体：按议题或层次展开，逻辑递进",
            "结尾：凝练收束，明确后续行动",
        ],
        "tone": "庄重且易听懂，兼顾现场表达与书面规范。",
        "common_errors": "口号堆砌、逻辑跳跃、与会议主题脱节。",
    },
    "经济类文书": {
        "definition": "用于经营管理、项目论证、投融资及合同交易等经济活动。",
        "structure": [
            "问题与目标：定义清楚并可量化",
            "数据与论证：引用可信来源，结论可复核",
            "方案与风险：给出可执行路径与风险应对",
        ],
        "tone": "客观、审慎、数据驱动。",
        "common_errors": "数据来源不明、结论先行、风险分析缺失。",
    },
    "贸易类文书": {
        "definition": "用于商务往来、交易磋商、索赔理赔与付款催收等场景。",
        "structure": [
            "交易背景：时间、标的、双方关系",
            "核心诉求：金额、数量、期限、责任",
            "附件与证据：编号完整、引用明确",
        ],
        "tone": "礼貌、专业、边界清晰。",
        "common_errors": "诉求不明确、证据不足、责任归属描述含糊。",
    },
    "法律类文书": {
        "definition": "用于诉讼、申诉、答辩、授权担保等法律事务。",
        "structure": [
            "当事人信息：准确完整",
            "事实与理由：按时间线与证据链展开",
            "请求事项：明确、可裁判、可执行",
        ],
        "tone": "中性、严谨、证据导向。",
        "common_errors": "事实与观点混杂、法条援引失当、请求不清。",
    },
    "书信类文书": {
        "definition": "用于单位或个人之间的沟通、证明、倡议、致谢与批评表扬。",
        "structure": [
            "称谓：对象准确、礼貌得体",
            "正文：缘由-主体-结语",
            "落款：署名、日期完整",
        ],
        "tone": "真诚、得体、边界明确。",
        "common_errors": "称谓失当、情绪化表达、信息不完整。",
    },
    "条据类文书": {
        "definition": "用于简短书面凭据、留言、借还、请假等高频场景。",
        "structure": [
            "核心要素：时间、事项、金额/数量、双方身份",
            "责任界定：条件、期限、违约说明（如适用）",
            "签署信息：署名与日期完整",
        ],
        "tone": "简明、明确、可核对。",
        "common_errors": "关键要素缺失、金额和时间表达不规范。",
    },
    "礼仪类文书": {
        "definition": "用于礼仪交往、欢迎欢送、颁奖致辞、吊唁悼念等场景。",
        "structure": [
            "开场：对象与场景对应",
            "主体：赞誉/祝愿/追思等围绕主题展开",
            "结尾：礼貌收束，情感分寸适当",
        ],
        "tone": "庄重、真诚、克制。",
        "common_errors": "套话过多、情感失衡、与场景不匹配。",
    },
}


DOC_TYPE_GUIDES: dict[str, dict[str, object]] = {}
for group in DOC_TYPE_GROUPS:
    label = str(group["label"])
    template = GROUP_GUIDE_TEMPLATES.get(label)
    if not template:
        continue
    for doc_type in group["doc_types"]:
        DOC_TYPE_GUIDES[str(doc_type)] = {
            "definition": f"文种：{doc_type}。{template['definition']}",
            "structure": list(template["structure"]),
            "tone": template["tone"],
            "common_errors": template["common_errors"],
        }

DOC_TYPE_GUIDES[OTHER_DOC_TYPE] = {
    "definition": "当无法准确判断文种时使用的兜底类型。",
    "structure": [
        "先明确写作目标、对象、场景",
        "再按“背景-事项-要求-结语”组织内容",
        "保持层级清晰、信息完整",
    ],
    "tone": "正式、客观、准确。",
    "common_errors": "文种不明确导致结构混乱、要素缺失。",
}


def get_doc_type_guide(doc_type: str) -> str:
    """Get the writing guide text for a canonical doc type."""
    normalized = normalize_doc_type(doc_type) or doc_type
    guide = DOC_TYPE_GUIDES.get(normalized, DOC_TYPE_GUIDES[OTHER_DOC_TYPE])

    lines = [f"【{normalized}写作规范】"]
    lines.append(f"定义：{guide['definition']}")
    lines.append("结构要求：")
    for item in guide["structure"]:
        lines.append(f"  - {item}")
    lines.append(f"语气要求：{guide['tone']}")
    lines.append(f"常见问题：{guide['common_errors']}")
    return "\n".join(lines)
