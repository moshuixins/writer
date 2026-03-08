from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor

from app.database import SessionLocal
from app.errors import logger


class BookImportDispatcher:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='book-import')
        self._lock = threading.Lock()
        self._scheduled_task_ids: set[str] = set()
        self._futures: dict[str, Future[None]] = {}
        self._closed = False

    def dispatch(self, task_id: str, *, account_id: int) -> bool:
        with self._lock:
            if self._closed or task_id in self._scheduled_task_ids:
                return False
            future = self._executor.submit(self._run_task, task_id, int(account_id or 1))
            self._scheduled_task_ids.add(task_id)
            self._futures[task_id] = future
            future.add_done_callback(lambda completed, current_task_id=task_id: self._on_done(current_task_id, completed))
            return True

    def _run_task(self, task_id: str, account_id: int) -> None:
        from app.services.book_import_service import BookImportService

        db = SessionLocal()
        try:
            service = BookImportService(db, account_id=account_id)
            asyncio.run(service.execute_task(task_id))
        except Exception as exc:
            logger.exception('Book import dispatcher crashed. task_id=%s err=%s', task_id, exc)
        finally:
            db.close()

    def _on_done(self, task_id: str, future: Future[None]) -> None:
        error = None
        if future.cancelled():
            logger.info('Book import worker cancelled. task_id=%s', task_id)
        else:
            error = future.exception()
            if error is not None:
                logger.exception('Book import worker failed. task_id=%s err=%s', task_id, error)
        with self._lock:
            self._scheduled_task_ids.discard(task_id)
            self._futures.pop(task_id, None)
        self.resume_recoverable_tasks()

    def resume_recoverable_tasks(self) -> bool:
        from app.services.book_import_task_service import book_import_task_tracker

        with self._lock:
            if self._closed or any(not future.done() for future in self._futures.values()):
                return False

        for task_id in book_import_task_tracker.list_recoverable_task_ids():
            with self._lock:
                if self._closed or task_id in self._scheduled_task_ids:
                    continue
            task = book_import_task_tracker.get_state(task_id)
            if task is None:
                continue
            if str(task.get('status', '')) not in {'pending', 'running', 'interrupted'}:
                continue
            return self.dispatch(task_id, account_id=int(task.get('account_id', 1) or 1))
        return False

    def shutdown(self, *, wait: bool = False, cancel_futures: bool = False) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)


book_import_dispatcher = BookImportDispatcher()
