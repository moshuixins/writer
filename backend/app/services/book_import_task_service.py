from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.database import SessionLocal
from app.errors import logger
from app.models.book_import_task import BookImportTask


class BookImportTaskTracker:
    def __init__(self, ttl_seconds: int = 24 * 3600):
        self._ttl_seconds = ttl_seconds
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._active_task_id: str | None = None

    def _now(self) -> float:
        return time.time()

    def _dt_from_ts(self, value: float | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    def _ts_from_dt(self, value: datetime | None) -> float | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    def _task_from_row(self, row: BookImportTask) -> dict[str, Any]:
        return {
            "task_id": row.task_id,
            "status": row.status,
            "stage": row.stage,
            "message": row.message or "",
            "rebuild": bool(row.rebuild),
            "account_id": int(row.account_id or 1),
            "started_ts": self._ts_from_dt(row.started_at) or self._now(),
            "updated_ts": self._ts_from_dt(row.updated_at) or self._now(),
            "finished_ts": self._ts_from_dt(row.finished_at),
            "total_files": int(row.total_files or 0),
            "completed_files": int(row.completed_files or 0),
            "failed_files": int(row.failed_files or 0),
            "partial_files": int(row.partial_files or 0),
            "skipped_files": int(row.skipped_files or 0),
            "running_file": row.running_file or "",
            "total_chunks": int(row.total_chunks or 0),
            "completed_chunks": int(row.completed_chunks or 0),
            "ocr_used_files": int(row.ocr_used_files or 0),
            "ocr_pages": int(row.ocr_pages or 0),
            "file_results": list(row.file_results or []),
            "selected_files": list(row.selected_files or []),
        }

    def _load_db_task(self, task_id: str) -> dict[str, Any] | None:
        db = SessionLocal()
        try:
            row = db.query(BookImportTask).filter(BookImportTask.task_id == task_id).first()
            if row is None:
                return None
            return self._task_from_row(row)
        finally:
            db.close()

    def _load_db_active_task(self) -> dict[str, Any] | None:
        db = SessionLocal()
        try:
            row = (
                db.query(BookImportTask)
                .filter(BookImportTask.status.in_(["pending", "running"]))
                .order_by(BookImportTask.updated_at.desc(), BookImportTask.id.desc())
                .first()
            )
            if row is None:
                return None
            return self._task_from_row(row)
        finally:
            db.close()

    def _load_db_recoverable_task_ids(self) -> list[str]:
        db = SessionLocal()
        try:
            rows = (
                db.query(BookImportTask.task_id)
                .filter(BookImportTask.status.in_(["pending", "running", "interrupted"]))
                .order_by(BookImportTask.started_at.asc(), BookImportTask.id.asc())
                .all()
            )
            return [str(task_id) for (task_id,) in rows if str(task_id).strip()]
        finally:
            db.close()

    def _persist_task(self, task: dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            row = db.query(BookImportTask).filter(BookImportTask.task_id == task["task_id"]).first()
            if row is None:
                row = BookImportTask(task_id=task["task_id"], account_id=int(task.get("account_id", 1) or 1))
                db.add(row)
            row.account_id = int(task.get("account_id", 1) or 1)
            row.status = str(task.get("status", "pending") or "pending")
            row.stage = str(task.get("stage", "") or "")
            row.message = str(task.get("message", "") or "")
            row.rebuild = bool(task.get("rebuild", False))
            row.total_files = int(task.get("total_files", 0) or 0)
            row.completed_files = int(task.get("completed_files", 0) or 0)
            row.failed_files = int(task.get("failed_files", 0) or 0)
            row.partial_files = int(task.get("partial_files", 0) or 0)
            row.skipped_files = int(task.get("skipped_files", 0) or 0)
            row.running_file = str(task.get("running_file", "") or "")
            row.total_chunks = int(task.get("total_chunks", 0) or 0)
            row.completed_chunks = int(task.get("completed_chunks", 0) or 0)
            row.ocr_used_files = int(task.get("ocr_used_files", 0) or 0)
            row.ocr_pages = int(task.get("ocr_pages", 0) or 0)
            row.file_results = list(task.get("file_results", []))
            row.selected_files = list(task.get("selected_files", []))
            row.started_at = self._dt_from_ts(task.get("started_ts")) or datetime.now(timezone.utc)
            row.updated_at = self._dt_from_ts(task.get("updated_ts")) or datetime.now(timezone.utc)
            row.finished_at = self._dt_from_ts(task.get("finished_ts"))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("Book import task persistence failed: task_id=%s err=%s", task.get("task_id"), e)
        finally:
            db.close()

    def _prune_locked(self, now: float) -> None:
        expired = [
            task_id
            for task_id, task in self._tasks.items()
            if now - float(task.get("updated_ts", now)) > self._ttl_seconds
        ]
        for task_id in expired:
            self._tasks.pop(task_id, None)
            if self._active_task_id == task_id:
                self._active_task_id = None

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
            "selected_files": list(task.get("selected_files", [])),
        }

    def reserve_slot(self, task_id: str, *, account_id: int) -> tuple[bool, str | None]:
        del account_id
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            active_id = self._active_task_id
            if active_id:
                active = self._tasks.get(active_id) or self._load_db_task(active_id)
                if active and active.get("status") in {"pending", "running"}:
                    return False, active_id
                self._active_task_id = None

            db_active = self._load_db_active_task()
            if db_active is not None and db_active["task_id"] != task_id:
                self._active_task_id = db_active["task_id"]
                self._tasks[db_active["task_id"]] = db_active
                return False, db_active["task_id"]

            self._active_task_id = task_id
            return True, None

    def claim_task(self, task_id: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            active_id = self._active_task_id
            if active_id and active_id != task_id:
                active = self._tasks.get(active_id) or self._load_db_task(active_id)
                if active and active.get("status") in {"pending", "running"}:
                    return None
                self._active_task_id = None

            task = self._tasks.get(task_id) or self._load_db_task(task_id)
            if not task:
                return None
            if task.get("status") == "interrupted":
                task["status"] = "pending"
                task["stage"] = "等待恢复"
                task["message"] = task.get("message") or "准备恢复执行"
                task["finished_ts"] = None
                task["updated_ts"] = now
                self._persist_task(task)
            self._active_task_id = task_id
            self._tasks[task_id] = task
            return self._format(task)

    def create_task(
        self,
        task_id: str,
        *,
        total_files: int,
        rebuild: bool = False,
        account_id: int = 1,
        selected_files: list[str] | None = None,
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
                "total_files": int(total_files or 0),
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
                "selected_files": list(selected_files or []),
            }
            self._tasks[task_id] = task
            self._persist_task(task)
            return self._format(task)

    def restart(
        self,
        task_id: str,
        *,
        total_files: int,
        selected_files: list[str] | None = None,
        stage: str = "准备导入",
        message: str = "任务已启动",
    ) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            task = self._tasks.get(task_id) or self._load_db_task(task_id)
            if not task:
                return None
            task["status"] = "running"
            task["stage"] = stage
            task["message"] = message
            task["updated_ts"] = now
            task["finished_ts"] = None
            task["total_files"] = int(total_files or 0)
            task["completed_files"] = 0
            task["failed_files"] = 0
            task["partial_files"] = 0
            task["skipped_files"] = 0
            task["running_file"] = ""
            task["total_chunks"] = 0
            task["completed_chunks"] = 0
            task["ocr_used_files"] = 0
            task["ocr_pages"] = 0
            task["file_results"] = []
            if selected_files is not None:
                task["selected_files"] = list(selected_files)
            self._active_task_id = task_id
            self._tasks[task_id] = task
            self._persist_task(task)
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
            task = self._tasks.get(task_id) or self._load_db_task(task_id)
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
            self._tasks[task_id] = task
            self._persist_task(task)
            return self._format(task)

    def _release_slot_locked(self, task_id: str) -> None:
        if self._active_task_id == task_id:
            self._active_task_id = None

    def finish(self, task_id: str, *, status: str = "completed", message: str = "") -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            task = self._tasks.get(task_id) or self._load_db_task(task_id)
            if not task:
                return None
            task["status"] = status
            task["stage"] = "已完成" if status == "completed" else "已结束"
            task["message"] = message
            task["running_file"] = ""
            task["finished_ts"] = now
            task["updated_ts"] = now
            self._tasks[task_id] = task
            self._persist_task(task)
            self._release_slot_locked(task_id)
            return self._format(task)

    def fail(self, task_id: str, message: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            task = self._tasks.get(task_id) or self._load_db_task(task_id)
            if not task:
                return None
            task["status"] = "failed"
            task["stage"] = "执行失败"
            task["message"] = message
            task["running_file"] = ""
            task["finished_ts"] = now
            task["updated_ts"] = now
            self._tasks[task_id] = task
            self._persist_task(task)
            self._release_slot_locked(task_id)
            return self._format(task)

    def get(self, task_id: str) -> dict[str, Any] | None:
        now = self._now()
        with self._lock:
            self._prune_locked(now)
            task = self._tasks.get(task_id)
            if task is None:
                task = self._load_db_task(task_id)
                if task is None:
                    return None
                self._tasks[task_id] = task
            return self._format(task)

    def get_state(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                task = self._load_db_task(task_id)
                if task is None:
                    return None
                self._tasks[task_id] = task
            return dict(task)

    def list_recoverable_task_ids(self) -> list[str]:
        task_ids = self._load_db_recoverable_task_ids()
        with self._lock:
            for task_id in task_ids:
                if task_id not in self._tasks:
                    task = self._load_db_task(task_id)
                    if task is not None:
                        self._tasks[task_id] = task
            return task_ids


book_import_task_tracker = BookImportTaskTracker()
