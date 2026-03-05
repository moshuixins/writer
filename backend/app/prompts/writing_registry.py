"""Prompt registry for canonical document types."""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module

from app.prompts.doc_types_catalog import DOC_TYPE_TO_SLUG, OTHER_DOC_TYPE, normalize_doc_type


PromptSet = dict[str, str]


@lru_cache(maxsize=256)
def _load_prompt_set(doc_type: str) -> PromptSet:
    slug = DOC_TYPE_TO_SLUG.get(doc_type, DOC_TYPE_TO_SLUG[OTHER_DOC_TYPE])
    module = import_module(f"app.prompts.writing_types.{slug}")
    prompt_set = getattr(module, "PROMPT_SET", None)
    if not isinstance(prompt_set, dict):
        raise ValueError(f"PROMPT_SET missing for doc_type={doc_type}")
    required = {"guidance", "generate", "edit", "review"}
    if not required.issubset(prompt_set.keys()):
        missing = required - set(prompt_set.keys())
        raise ValueError(f"Prompt set incomplete for doc_type={doc_type}, missing={sorted(missing)}")
    return prompt_set


def get_prompt_set(doc_type: str | None) -> PromptSet:
    normalized = normalize_doc_type(doc_type) or OTHER_DOC_TYPE
    return _load_prompt_set(normalized)

