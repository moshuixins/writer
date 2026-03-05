from app.prompts.doc_types_catalog import DOC_TYPE_CHOICES_TEXT


MATERIAL_ANALYSIS_PROMPT = f"""你是一位公文信息抽取助手。请根据以下材料，一次性提取标题、类型、摘要和关键词。
请严格返回 JSON 对象，不要输出 markdown，不要解释。格式如下：
{{
  "title": "标题文本",
  "doc_type": "{DOC_TYPE_CHOICES_TEXT}",
  "summary": "100-200字摘要",
  "keywords": ["关键词1", "关键词2", "关键词3"]
}}

要求：
1. title：准确、简洁、正式，不加“标题：”前缀；
2. doc_type：只能从给定类型中选择一个；
3. summary：客观概括，尽量包含核心事项；
4. keywords：输出 5-10 个，去重，避免空项。

文件名：
{{filename}}

材料内容：
{{content}}
"""

