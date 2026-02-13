"""Background live simulation session orchestration for desktop GUI consumption."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from configs.loader import ExperimentConfig
from data.logger import SimulationLogger
from main import build_components


SessionCallback = Callable[[dict[str, Any]], None]


@dataclass
class SessionControlState:
    """Mutable thread-safe control state for a running live session."""

    stop_event: threading.Event
    pause_event: threading.Event
    step_event: threading.Event
    step_ack_event: threading.Event
    speed_multiplier: float = 1.0
    min_emit_interval: float = 1.0 / 30.0


class LiveSimulationSession:
    """Runs simulator generations in a background thread and emits updates.

    This class isolates lifecycle orchestration from GUI widgets. The GUI should
    subscribe to callbacks and should not call simulator internals directly.
    """

    def __init__(
        self,
        config: ExperimentConfig,
        on_update: SessionCallback,
        on_complete: SessionCallback | None = None,
        db_path: str | Path = "experiments/live_session_metrics.db",
    ) -> None:
        self.config = config
        self.on_update = on_update
        self.on_complete = on_complete
        self.db_path = Path(db_path)
        self._thread: threading.Thread | None = None
        self._state = SessionControlState(
            stop_event=threading.Event(),
            pause_event=threading.Event(),
            step_event=threading.Event(),
            step_ack_event=threading.Event(),
        )

    def start(self) -> None:
        """Start session in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._state.stop_event.clear()
        self._state.pause_event.clear()
        self._state.step_event.clear()
        self._state.step_ack_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Request session stop."""
        self._state.stop_event.set()
        self._state.pause_event.clear()
        self._state.step_event.set()
        self._state.step_ack_event.set()

    def pause(self) -> None:
        """Pause generation stepping."""
        self._state.pause_event.set()

    def resume(self) -> None:
        """Resume generation stepping."""
        self._state.pause_event.clear()
        self._state.step_event.set()

    def set_speed(self, multiplier: float) -> None:
        """Adjust session speed multiplier."""
        self._state.speed_multiplier = max(0.01, float(multiplier))

    def step_once(self, timeout: float = 2.0) -> bool:
        """Advance exactly one generation while paused and wait for ack."""
        self._state.pause_event.set()
        self._state.step_ack_event.clear()
        self._state.step_event.set()
        return bool(self._state.step_ack_event.wait(timeout=max(0.01, float(timeout))))

    def join(self, timeout: float | None = None) -> None:
        """Join worker thread for deterministic tests/shutdown."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger = SimulationLogger(self.db_path)
        simulator = build_components(self.config, logger=logger)

        total_generations = int(self.config.generations)
        last_emit = 0.0
        try:
            for generation in range(total_generations):
                if self._state.stop_event.is_set():
                    break

                step_mode = False
                while self._state.pause_event.is_set() and not self._state.stop_event.is_set():
                    if self._state.step_event.is_set():
                        self._state.step_event.clear()
                        step_mode = True
                        break
                    time.sleep(0.02)
                if self._state.stop_event.is_set():
                    break

                try:
                    simulator.generation_index = generation
                    simulator.run_generation()
                    simulator.on_generation_end(generation)
                except Exception as exc:
                    self._safe_emit(
                        {
                            "event": "error",
                            "generation": generation,
                            "message": str(exc),
                        }
                    )
                    break

                payload = {
                    "event": "generation",
                    "generation": generation,
                    "total_generations": total_generations,
                    "logger_experiment_id": simulator.experiment_id,
                    "metrics": dict(simulator.last_generation_metrics or {}),
                    "render_state": self._build_render_state(simulator),
                }
                now = time.monotonic()
                should_emit = step_mode or (now - last_emit) >= max(0.001, self._state.min_emit_interval)
                if should_emit or generation == total_generations - 1:
                    self._safe_emit(payload)
                    last_emit = now
                else:
                    self._safe_emit(
                        {
                            "event": "generation",
                            "generation": generation,
                            "total_generations": total_generations,
                            "logger_experiment_id": simulator.experiment_id,
                            "metrics": dict(simulator.last_generation_metrics or {}),
                        }
                    )
                if step_mode:
                    self._state.step_ack_event.set()

                if not step_mode:
                    delay = 0.05 / max(0.01, self._state.speed_multiplier)
                    time.sleep(delay)

            completion = {
                "event": "complete",
                "stopped": self._state.stop_event.is_set(),
                "total_generations": total_generations,
            }
            if self.on_complete is not None:
                try:
                    self.on_complete(completion)
                except Exception:
                    pass
            else:
                self._safe_emit(completion)
        finally:
            logger.close()

    def _safe_emit(self, payload: dict[str, Any]) -> None:
        try:
            self.on_update(payload)
        except Exception:
            pass

    @staticmethod
    def _build_render_state(simulator: Any) -> dict[str, Any]:
        """Build a generic render state from environment observations."""
        population = list(getattr(simulator, "population", []))
        agent_ids = [str(getattr(agent, "agent_id", f"agent_{idx}")) for idx, agent in enumerate(population)]
        env = getattr(simulator, "environment", None)

        observations: dict[str, Any] = {}
        if env is not None and hasattr(env, "get_observations"):
            try:
                observations = dict(env.get_observations(agent_ids))
            except Exception:
                observations = {}

        agents: list[dict[str, Any]] = []
        for idx, agent in enumerate(population):
            agent_id = agent_ids[idx]
            obs = observations.get(agent_id, {}) if isinstance(observations, dict) else {}
            if isinstance(obs, dict):
                pos = obs.get("position", (idx, 0))
            else:
                pos = (idx, 0)
            x, y = pos if isinstance(pos, (tuple, list)) and len(pos) >= 2 else (idx, 0)
            agents.append({"id": agent_id, "position": [float(x), float(y)], "observation": obs})

        bounds = [max(len(agents), 1), max(len(agents), 1)]
        if observations:
            first = next(iter(observations.values()))
            if isinstance(first, dict) and "grid_size" in first:
                grid = first.get("grid_size")
                if isinstance(grid, (tuple, list)) and len(grid) >= 2:
                    bounds = [float(grid[0]), float(grid[1])]

        return {
            "agents": agents,
            "environment": {"bounds": bounds},
        }
