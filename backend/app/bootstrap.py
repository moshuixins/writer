from __future__ import annotations

import threading

import app.models  # noqa: F401

from app.database import Base, engine
from app.errors import logger
from app.schema_bootstrap import ensure_account_schema

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def ensure_runtime_ready(force: bool = False) -> None:
    """Initialize tables and schema patches exactly once per process.

    The project previously executed schema creation during module import, which made
    startup side effects hard to reason about in tests and CLI entrypoints. Runtime
    bootstrap is now explicit and reusable.
    """
    global _bootstrapped

    with _bootstrap_lock:
        if _bootstrapped and not force:
            return
        Base.metadata.create_all(bind=engine)
        ensure_account_schema(engine)
        _bootstrapped = True
        logger.info("Runtime bootstrap completed")

