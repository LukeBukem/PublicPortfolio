"""Async websocket ingestion client for live render-state streams."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Callable


class WebSocketRenderClient:
    """Background websocket client that feeds decoded frames to callbacks."""

    def __init__(self, endpoint: str, mode: str = "full_state") -> None:
        self.endpoint = endpoint
        self.mode = mode
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        asyncio.run(self._consume())

    async def _consume(self) -> None:
        try:
            import websockets  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("websockets dependency is required for live mode") from exc

        async with websockets.connect(self.endpoint) as ws:
            await ws.send(json.dumps({"mode": self.mode}))
            while not self._stop.is_set():
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                if isinstance(msg, bytes):
                    payload = json.loads(msg.decode("utf-8"))
                else:
                    payload = json.loads(msg)
                for cb in list(self._callbacks):
                    cb(payload)
