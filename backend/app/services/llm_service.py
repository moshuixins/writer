from __future__ import annotations

import asyncio
import time
from typing import Generator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from app.config import get_settings
from app.errors import LLMError, logger

settings = get_settings()

MAX_RETRIES = 2
RETRY_DELAY = 1.0


class LLMService:
    """LLM 调用封装，包含重试和统一异常。"""

    def __init__(self, temperature: float = 0.3):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=temperature,
            request_timeout=60,
            max_retries=0,
        )

    def invoke(self, prompt: str) -> str:
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm.invoke(prompt)
                content = response.content
                if not content or not str(content).strip():
                    logger.warning("LLM returned empty response, attempt %d", attempt + 1)
                    raise LLMError(detail="LLM returned empty content")
                return str(content)
            except LLMError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        logger.error("LLM call exhausted all retries: %s", last_error)
        raise LLMError(detail=str(last_error))

    def invoke_messages(self, messages: list[BaseMessage]) -> str:
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm.invoke(messages)
                content = response.content
                if not content or not str(content).strip():
                    logger.warning("LLM returned empty response, attempt %d", attempt + 1)
                    raise LLMError(detail="LLM returned empty content")
                return str(content)
            except LLMError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        logger.error("LLM call exhausted all retries: %s", last_error)
        raise LLMError(detail=str(last_error))

    async def invoke_async(self, prompt: str) -> str:
        return await asyncio.to_thread(self.invoke, prompt)

    async def invoke_messages_async(self, messages: list[BaseMessage]) -> str:
        return await asyncio.to_thread(self.invoke_messages, messages)

    def stream(self, prompt: str) -> Generator[str, None, None]:
        try:
            for chunk in self.llm.stream(prompt):
                if chunk.content:
                    yield str(chunk.content)
        except Exception as e:
            logger.error("LLM stream error: %s", e)
            raise LLMError(detail=str(e))

    def stream_messages(self, messages: list[BaseMessage]) -> Generator[str, None, None]:
        try:
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield str(chunk.content)
        except Exception as e:
            logger.error("LLM stream error: %s", e)
            raise LLMError(detail=str(e))
