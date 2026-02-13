"""RenderState websocket streaming server and broadcaster."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from streaming.state_serializer import serialize_state


@dataclass
class _Client:
    websocket: Any
    mode: str = "full_state"
    queue: asyncio.Queue[bytes] = field(default_factory=lambda: asyncio.Queue(maxsize=1))


class RenderStateServer:
    """Broadcast render frames to websocket clients with backpressure control."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, max_fps: int = 30) -> None:
        self.host = host
        self.port = port
        self.max_fps = max(1, max_fps)
        self._min_interval = 1.0 / self.max_fps
        self._last_broadcast = 0.0
        self._clients: list[_Client] = []
        self._server = None

    async def start(self) -> None:
        """Start websocket listener."""
        try:
            import websockets  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "websockets package is required to start RenderStateServer."
            ) from exc

        async def _handler(ws: Any) -> None:
            mode = "full_state"
            try:
                first_msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                if isinstance(first_msg, str):
                    try:
                        payload = json.loads(first_msg)
                        mode = payload.get("mode", "full_state")
                    except Exception:
                        mode = "full_state"
            except Exception:
                mode = "full_state"

            client = _Client(websocket=ws, mode=mode)
            self._clients.append(client)
            sender = asyncio.create_task(self._sender_loop(client))
            try:
                await ws.wait_closed()
            finally:
                if client in self._clients:
                    self._clients.remove(client)
                sender.cancel()

        self._server = await websockets.serve(_handler, self.host, self.port)

    async def stop(self) -> None:
        """Stop listener and disconnect clients."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _sender_loop(self, client: _Client) -> None:
        while True:
            frame = await client.queue.get()
            try:
                await client.websocket.send(frame)
            except Exception:
                return

    async def broadcast(self, render_state: Any) -> None:
        """Broadcast frame to clients, dropping stale frames on backpressure."""
        now = time.monotonic()
        if (now - self._last_broadcast) < self._min_interval:
            return
        self._last_broadcast = now

        for client in list(self._clients):
            filtered = self._apply_filter(render_state, client.mode)
            frame = serialize_state(filtered)
            if client.queue.full():
                try:
                    client.queue.get_nowait()
                except Exception:
                    pass
            try:
                client.queue.put_nowait(frame)
            except Exception:
                continue

    def _apply_filter(self, render_state: Any, mode: str) -> Any:
        if mode == "metrics_only":
            return {
                "generation_index": getattr(render_state, "generation_index", 0),
                "step_index": getattr(render_state, "step_index", 0),
                "metrics": getattr(render_state, "metrics", {}),
                "timestamp": getattr(render_state, "timestamp", 0.0),
            }
        if mode == "agent_positions_only":
            agents = getattr(render_state, "agents", [])
            return {
                "generation_index": getattr(render_state, "generation_index", 0),
                "step_index": getattr(render_state, "step_index", 0),
                "agents": [
                    {"id": getattr(a, "id", None), "position": getattr(a, "position", None)}
                    for a in agents
                ],
                "timestamp": getattr(render_state, "timestamp", 0.0),
            }
        return render_state
