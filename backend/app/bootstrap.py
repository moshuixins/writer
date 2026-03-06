from __future__ import annotations

import threading

from app.errors import logger
from app.migration import run_database_migrations
from app.runtime_bootstrap_tasks import run_runtime_bootstrap_tasks

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def ensure_runtime_ready(force: bool = False) -> None:
    """Run schema migrations and runtime bootstrap tasks exactly once per process."""
    global _bootstrapped

    with _bootstrap_lock:
        if _bootstrapped and not force:
            return
        run_database_migrations(allow_legacy_bootstrap=True)
        run_runtime_bootstrap_tasks()
        _bootstrapped = True
        logger.info('Runtime bootstrap completed')
