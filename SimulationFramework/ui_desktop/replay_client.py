"""Replay ingestion client for local checkpoint-driven playback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.replay import ReplayEngine


class ReplayRenderClient:
    """Thin adapter around ReplayEngine for UI consumption."""

    def __init__(self, config_path: str | Path, experiment_dir: str | Path) -> None:
        self.engine = ReplayEngine(config_path=config_path, experiment_dir=Path(experiment_dir))
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def jump_to_generation(self, generation: int) -> None:
        self.engine.jump_to_generation(generation)
        self._emit()

    def step_forward(self, n_steps: int = 1) -> None:
        self.engine.step_forward(n_steps)
        self._emit()

    def step_backward(self, n_steps: int = 1) -> None:
        self.engine.step_backward(n_steps)
        self._emit()

    def current_state(self) -> dict[str, Any]:
        state = self.engine.get_render_state()
        if isinstance(state, dict):
            return state
        return {
            "generation_index": getattr(state, "generation_index", 0),
            "step_index": getattr(state, "step_index", 0),
            "agents": [
                {
                    "id": getattr(a, "id", ""),
                    "position": list(getattr(a, "position", (0, 0))),
                    "fitness": getattr(a, "fitness", None),
                    "alive": getattr(a, "alive", True),
                }
                for a in getattr(state, "agents", [])
            ],
            "environment": {
                "bounds": list(getattr(getattr(state, "environment", {}), "bounds", (0, 0))),
                "metadata": getattr(getattr(state, "environment", {}), "metadata", {}),
            },
            "metrics": getattr(state, "metrics", {}),
            "timestamp": getattr(state, "timestamp", 0.0),
        }

    def _emit(self) -> None:
        payload = self.current_state()
        for cb in list(self._callbacks):
            cb(payload)
