"""Compatibility entrypoint for doc-type prompt routing."""

from app.prompts.writing_registry import get_prompt_set

__all__ = ["get_prompt_set"]

