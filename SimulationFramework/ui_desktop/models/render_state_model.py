"""Thread-safe UI model for render-state propagation and history buffering."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any, Callable


Subscriber = Callable[[dict[str, Any]], None]


class RenderStateModel:
    """Holds latest render state and notifies UI subscribers."""

    def __init__(self, history_size: int = 256) -> None:
        self._lock = Lock()
        self._latest: dict[str, Any] | None = None
        self._history: deque[dict[str, Any]] = deque(maxlen=max(1, history_size))
        self._subscribers: list[Subscriber] = []

    def subscribe(self, callback: Subscriber) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def update_state(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._latest = state
            self._history.append(state)
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(state)

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return self._latest

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def downsampled_agents(self, max_agents: int = 1000) -> list[dict[str, Any]]:
        state = self.latest() or {}
        agents = list(state.get("agents", []))
        if len(agents) <= max_agents:
            return agents
        stride = max(1, len(agents) // max_agents)
        return agents[::stride]
