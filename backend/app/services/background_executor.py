from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Iterator, TypeVar

T = TypeVar('T')
_ITERATION_DONE = object()


def _next_or_done(iterator: Iterator[T]) -> T | object:
    try:
        return next(iterator)
    except StopIteration:
        return _ITERATION_DONE


class BackgroundExecutor:
    def __init__(self, *, max_workers: int, thread_name_prefix: str):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        self._lock = threading.Lock()
        self._closed = False

    async def run(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_running_loop()
        call = partial(fn, *args, **kwargs)
        return await loop.run_in_executor(self._executor, call)

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
        call = partial(fn, *args, **kwargs)
        with self._lock:
            if self._closed:
                raise RuntimeError('executor is shut down')
            return self._executor.submit(call)

    async def iterate_sync_generator(self, gen: Iterator[str]):
        iterator = iter(gen)
        try:
            while True:
                item = await self.run(_next_or_done, iterator)
                if item is _ITERATION_DONE:
                    break
                yield str(item)
        finally:
            close = getattr(iterator, 'close', None)
            if callable(close):
                await self.run(close)

    def shutdown(self, *, wait: bool = False, cancel_futures: bool = False) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)


chat_stream_executor = BackgroundExecutor(max_workers=4, thread_name_prefix='chat-stream')


def shutdown_background_executors(*, wait: bool = False, cancel_futures: bool = False) -> None:
    chat_stream_executor.shutdown(wait=wait, cancel_futures=cancel_futures)
