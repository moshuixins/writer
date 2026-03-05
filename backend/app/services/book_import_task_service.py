from __future__ import annotations

import threading
import time
from typing import Any


class BookImportTaskTracker:
    def __init__(self, ttl_seconds: int = 24 * 3600):
        self._ttl_seconds = ttl_seconds
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._active_task_by_account: dict[int, str] = {}

    def _now(self) -> float:
        return time.time()

    def _prune_locked(self, now: float) -> None:
        expired = [
            task_id
            for task_id, task in self._tasks.items()
            if now - float(task.get("updated_ts", now)) > self._ttl_seconds
        ]
        for task_id in expired:
            task = self._tasks.pop(task_id, None)
            if not task:
                continue
            account_id = int(task.get("account_id", 1))
            if self._active_task_by_account.get(account_id) == task_id:
                self._active_task_by_account.pop(account_id, None)

    def reserve_slot(self, task_id: str, *, account_id: int) -> tuple[bool, str | None]:
        """Reserve the per-account import slot.

        Returns (ok, active_task_id_when_conflict).
        """
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            acc = int(account_id or 1)
            active_id = self._active_task_by_account.get(acc)
            if active_id:
                active = self._tasks.get(active_id)
                if active and active.get("status") in {"pending", "running"}:
                    return False, active_id
                self._active_task_by_account.pop(acc, None)

            self._active_task_by_account[acc] = task_id
            return True, None

    @staticmethod
    def _safe_percent(numerator: int, denominator: int) -> int:
        if denominator <= 0:
            return 0
        return max(0, min(100, int(round(numerator * 100 / denominator))))

    def _format(self, task: dict[str, Any]) -> dict[str, Any]:
        file_progress = self._safe_percent(task["completed_files"], max(task["total_files"], 1))
        if int(task["total_chunks"]) <= 0:
            chunk_progress = file_progress
        else:
            chunk_progress = self._safe_percent(task["completed_chunks"], max(task["total_chunks"], 1))
        overall_progress = int(round(file_progress * 0.5 + chunk_progress * 0.5))
        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "stage": task["stage"],
            "message": task.get("message", ""),
            "rebuild": task.get("rebuild", False),
            "account_id": task.get("account_id", 1),
            "started_at": int(task.get("started_ts", 0) * 1000),
            "updated_at": int(task.get("updated_ts", 0) * 1000),
            "finished_at": int(task["finished_ts"] * 1000) if task.get("finished_ts") else None,
            "total_files": task["total_files"],
            "completed_files": task["completed_files"],
            "failed_files": task["failed_files"],
            "partial_files": task["partial_files"],
            "skipped_files": task["skipped_files"],
            "running_file": task.get("running_file", ""),
            "file_progress": file_progress,
            "total_chunks": task["total_chunks"],
            "completed_chunks": task["completed_chunks"],
            "chunk_progress": chunk_progress,
            "overall_progress": overall_progress,
            "ocr_used_files": task["ocr_used_files"],
            "ocr_pages": task["ocr_pages"],
            "file_results": list(task.get("file_results", [])),
        }

    def create_task(
        self,
        task_id: str,
        *,
        total_files: int,
        rebuild: bool = False,
        account_id: int = 1,
    ) -> dict[str, Any]:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = {
                "task_id": task_id,
                "status": "pending",
                "stage": "等待开始",
                "message": "",
                "rebuild": rebuild,
                "account_id": int(account_id or 1),
                "started_ts": now,
                "updated_ts": now,
                "finished_ts": None,
                "total_files": max(0, int(total_files)),
                "completed_files": 0,
                "failed_files": 0,
                "partial_files": 0,
                "skipped_files": 0,
                "running_file": "",
                "total_chunks": 0,
                "completed_chunks": 0,
                "ocr_used_files": 0,
                "ocr_pages": 0,
                "file_results": [],
            }
            self._tasks[task_id] = task
            return self._format(task)

    def update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        message: str | None = None,
        running_file: str | None = None,
        total_chunks_add: int = 0,
        completed_chunks_add: int = 0,
        ocr_used_files_add: int = 0,
        ocr_pages_add: int = 0,
        completed_files_add: int = 0,
        failed_files_add: int = 0,
        partial_files_add: int = 0,
        skipped_files_add: int = 0,
        file_result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = self._tasks.get(task_id)
            if not task:
                return None

            if status is not None:
                task["status"] = status
            if stage is not None:
                task["stage"] = stage
            if message is not None:
                task["message"] = message
            if running_file is not None:
                task["running_file"] = running_file

            task["total_chunks"] += max(0, int(total_chunks_add))
            task["completed_chunks"] += max(0, int(completed_chunks_add))
            task["ocr_used_files"] += max(0, int(ocr_used_files_add))
            task["ocr_pages"] += max(0, int(ocr_pages_add))
            task["completed_files"] += max(0, int(completed_files_add))
            task["failed_files"] += max(0, int(failed_files_add))
            task["partial_files"] += max(0, int(partial_files_add))
            task["skipped_files"] += max(0, int(skipped_files_add))

            if file_result:
                task["file_results"].append(file_result)

            task["updated_ts"] = now
            return self._format(task)

    def _release_slot_locked(self, task_id: str) -> None:
        for acc, active_id in list(self._active_task_by_account.items()):
            if active_id == task_id:
                self._active_task_by_account.pop(acc, None)

    def finish(self, task_id: str, *, status: str = "completed", message: str = "") -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task["status"] = status
            task["stage"] = "已完成" if status == "completed" else "已结束"
            task["message"] = message
            task["running_file"] = ""
            task["finished_ts"] = now
            task["updated_ts"] = now
            self._release_slot_locked(task_id)
            return self._format(task)

    def fail(self, task_id: str, message: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task["status"] = "failed"
            task["stage"] = "执行失败"
            task["message"] = message
            task["running_file"] = ""
            task["finished_ts"] = now
            task["updated_ts"] = now
            self._release_slot_locked(task_id)
            return self._format(task)

    def get(self, task_id: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = self._tasks.get(task_id)
            if not task:
                return None
            return self._format(task)


book_import_task_tracker = BookImportTaskTracker()
