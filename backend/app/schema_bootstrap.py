from __future__ import annotations

from sqlalchemy.engine import Engine

from app.runtime_bootstrap_tasks import (
    bootstrap_rbac as _bootstrap_rbac,
    ensure_initial_admin as _ensure_initial_admin,
    mark_interrupted_book_tasks as _mark_interrupted_book_tasks,
    run_runtime_bootstrap_tasks,
)
from app.schema_patch import apply_account_schema_patch


def ensure_account_schema(engine: Engine, run_post_schema_tasks: bool = True) -> None:
    apply_account_schema_patch(engine)
    if run_post_schema_tasks:
        run_runtime_bootstrap_tasks()
