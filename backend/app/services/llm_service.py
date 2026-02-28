import time
from typing import Generator
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.errors import LLMError, logger

settings = get_settings()

MAX_RETRIES = 2
RETRY_DELAY = 1.0


class LLMService:
    """LLM调用封装，含错误处理和重试"""

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
        """调用LLM并返回文本结果，含重试和错误处理"""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm.invoke(prompt)
                content = response.content
                if not content or not content.strip():
                    logger.warning("LLM returned empty response, attempt %d", attempt + 1)
                    raise LLMError(detail="LLM返回了空内容")
                return content
            except LLMError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        logger.error("LLM call exhausted all retries: %s", last_error)
        raise LLMError(detail=str(last_error))

    def stream(self, prompt: str) -> Generator[str, None, None]:
        """流式调用LLM，逐块yield文本"""
        try:
            for chunk in self.llm.stream(prompt):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error("LLM stream error: %s", e)
            raise LLMError(detail=str(e))
