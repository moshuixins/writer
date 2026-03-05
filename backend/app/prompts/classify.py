"""Doc type classification prompt using canonical 79+1 taxonomy."""

from app.prompts.doc_types_catalog import DOC_TYPE_CHOICES_TEXT


CLASSIFY_PROMPT = f"""你是一位文种分类专家。请根据材料内容判断其文种。

可选文种（只能输出其中一个）：
{DOC_TYPE_CHOICES_TEXT}

要求：
1. 仅返回文种名称，不要返回解释；
2. 返回值必须来自可选文种列表；
3. 无法判断时返回“其他”。

材料内容：
{{content}}
"""
