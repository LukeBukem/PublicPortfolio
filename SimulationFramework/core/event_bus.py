"""Thread-safe non-blocking pub/sub event bus."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Semaphore
from typing import Any, Callable


Callback = Callable[[Any], None]


class EventBus:
    """Minimal non-blocking event bus.

    Callbacks execute in a worker pool so publish() does not block simulation.
    """

    def __init__(self, max_workers: int = 4, max_pending: int = 2048) -> None:
        self._subs: dict[str, list[Callback]] = defaultdict(list)
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._pending = Semaphore(max(1, int(max_pending)))

    def subscribe(self, event_type: str, callback: Callback) -> None:
        with self._lock:
            self._subs[event_type].append(callback)

    def publish(self, event_type: str, payload: Any) -> None:
        with self._lock:
            callbacks = list(self._subs.get(event_type, []))
        for callback in callbacks:
            if not self._pending.acquire(blocking=False):
                continue
            future = self._executor.submit(self._safe_invoke, callback, payload)
            future.add_done_callback(lambda _f: self._pending.release())

    def close(self) -> None:
        self._executor.shutdown(wait=True)

    @staticmethod
    def _safe_invoke(callback: Callback, payload: Any) -> None:
        try:
            callback(payload)
        except Exception:
            return
