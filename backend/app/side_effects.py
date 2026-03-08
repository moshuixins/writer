from __future__ import annotations

import uuid
from typing import Any

from app.errors import logger


def new_error_id() -> str:
    return uuid.uuid4().hex[:12]


def format_side_effect_warning(message: str, error_id: str) -> str:
    return f"{message}（错误ID: {error_id}）"


def log_side_effect_failure(operation: str, error: Exception, **context: Any) -> str:
    error_id = new_error_id()
    safe_context = ' '.join(
        f"{key}={value}"
        for key, value in context.items()
        if value not in (None, '')
    )
    logger.warning(
        'External side effect degraded. error_id=%s operation=%s context=%s err=%s',
        error_id,
        operation,
        safe_context or '-',
        error,
    )
    return error_id


def collect_side_effect_warning(
    warnings: list[str],
    *,
    operation: str,
    public_message: str,
    error: Exception,
    **context: Any,
) -> str:
    error_id = log_side_effect_failure(operation, error, **context)
    warnings.append(format_side_effect_warning(public_message, error_id))
    return error_id
