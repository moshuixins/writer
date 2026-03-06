from __future__ import annotations

import threading
import time
from typing import Any


class UploadProgressTracker:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl_seconds = ttl_seconds
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.time()

    def _prune_locked(self, now: float) -> None:
        expired = [
            task_id
            for task_id, task in self._tasks.items()
            if now - float(task.get("updated_ts", now)) > self._ttl_seconds
        ]
        for task_id in expired:
            self._tasks.pop(task_id, None)

    def update(
        self,
        task_id: str,
        *,
        account_id: int = 1,
        parse_progress: int | None = None,
        status: str | None = None,
        stage: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = self._tasks.get(
                task_id,
                {
                    "task_id": task_id,
                    "account_id": int(account_id or 1),
                    "status": "pending",
                    "stage": "等待解析",
                    "message": "",
                    "parse_progress": 0,
                    "updated_ts": now,
                },
            )

            if "account_id" not in task:
                task["account_id"] = int(account_id or 1)
            if parse_progress is not None:
                task["parse_progress"] = max(0, min(100, int(parse_progress)))
            if status is not None:
                task["status"] = status
            if stage is not None:
                task["stage"] = stage
            if message is not None:
                task["message"] = message
            task["updated_ts"] = now
            self._tasks[task_id] = task
            return self._format(task)

    def complete(self, task_id: str, stage: str = "解析完成") -> dict[str, Any]:
        return self.update(
            task_id,
            parse_progress=100,
            status="completed",
            stage=stage,
            message="ok",
        )

    def fail(self, task_id: str, message: str = "failed") -> dict[str, Any]:
        return self.update(
            task_id,
            status="failed",
            stage="解析失败",
            message=message,
        )

    def get(self, task_id: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = self._tasks.get(task_id)
            if not task:
                return None
            return self._format(task)

    def _format(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": task["task_id"],
            "account_id": task.get("account_id", 1),
            "status": task["status"],
            "stage": task["stage"],
            "message": task.get("message", ""),
            "parse_progress": task.get("parse_progress", 0),
            "updated_at": int(task.get("updated_ts", self._now()) * 1000),
        }


upload_progress_tracker = UploadProgressTracker()
