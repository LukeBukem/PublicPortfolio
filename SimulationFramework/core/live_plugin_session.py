"""Background plugin simulation session orchestration for GUI consumption."""

from __future__ import annotations

import dataclasses
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from core.simulator import Simulator


SessionCallback = Callable[[dict[str, Any]], None]


@dataclasses.dataclass
class PluginSessionControlState:
    """Mutable thread-safe control state for a plugin-backed live session."""

    stop_event: threading.Event
    pause_event: threading.Event
    step_event: threading.Event
    step_ack_event: threading.Event
    speed_multiplier: float = 1.0
    min_emit_interval: float = 1.0 / 30.0


class LivePluginSession:
    """Runs plugin simulator steps in a background thread and emits updates."""

    def __init__(
        self,
        config_path: str | Path,
        steps: int,
        on_update: SessionCallback,
        on_complete: SessionCallback | None = None,
    ) -> None:
        self.config_path = str(config_path)
        self.steps = max(1, int(steps))
        self.on_update = on_update
        self.on_complete = on_complete
        self._thread: threading.Thread | None = None
        self._state = PluginSessionControlState(
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
        """Pause step execution."""
        self._state.pause_event.set()

    def resume(self) -> None:
        """Resume step execution."""
        self._state.pause_event.clear()
        self._state.step_event.set()

    def set_speed(self, multiplier: float) -> None:
        """Adjust session speed multiplier."""
        self._state.speed_multiplier = max(0.01, float(multiplier))

    def step_once(self, timeout: float = 2.0) -> bool:
        """Advance exactly one plugin step while paused and wait for ack."""
        self._state.pause_event.set()
        self._state.step_ack_event.clear()
        self._state.step_event.set()
        return bool(self._state.step_ack_event.wait(timeout=max(0.01, float(timeout))))

    def join(self, timeout: float | None = None) -> None:
        """Join worker thread for deterministic tests/shutdown."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        simulator = Simulator(self.config_path)
        last_emit = 0.0
        try:
            simulator.sim.reset()
            for step in range(self.steps):
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
                    simulator.step_index = step + 1
                    simulator.sim.step()
                except Exception as exc:
                    self._safe_emit(
                        {
                            "event": "error",
                            "generation": step,
                            "message": str(exc),
                        }
                    )
                    break

                try:
                    metrics = _normalize_metrics(simulator.sim.get_metrics())
                except Exception as exc:
                    self._safe_emit(
                        {
                            "event": "error",
                            "generation": step,
                            "message": f"metrics collection failed: {exc}",
                        }
                    )
                    metrics = {}

                try:
                    render_state = _normalize_render_state(_build_raw_render_state(simulator))
                except Exception as exc:
                    self._safe_emit(
                        {
                            "event": "error",
                            "generation": step,
                            "message": f"render state normalization failed: {exc}",
                        }
                    )
                    render_state = {}

                payload = {
                    "event": "generation",
                    "generation": step,
                    "total_generations": self.steps,
                    "metrics": metrics,
                    "render_state": render_state,
                }
                now = time.monotonic()
                self._safe_emit(payload)
                last_emit = now
                if step_mode:
                    self._state.step_ack_event.set()

                if not step_mode:
                    delay = 0.05 / max(0.01, self._state.speed_multiplier)
                    time.sleep(delay)

            completion = {
                "event": "complete",
                "stopped": self._state.stop_event.is_set(),
                "total_generations": self.steps,
            }
            if self.on_complete is not None:
                try:
                    self.on_complete(completion)
                except Exception:
                    pass
            else:
                self._safe_emit(completion)
        finally:
            try:
                simulator.sim.close()
            except Exception:
                pass

    def _safe_emit(self, payload: dict[str, Any]) -> None:
        try:
            self.on_update(payload)
        except Exception:
            pass


def _build_raw_render_state(simulator: Simulator) -> Any:
    adapter = getattr(simulator, "_render_adapter", None)
    if callable(adapter):
        return adapter(simulator)
    return simulator.sim.get_render_state()


def _normalize_metrics(metrics: Any) -> dict[str, float]:
    if not isinstance(metrics, Mapping):
        return {}
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            normalized[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_render_state(state: Any) -> dict[str, Any]:
    state_map = _to_mapping(state)
    env_payload = _to_mapping(state_map.get("environment", {}))
    metadata = _to_mapping(env_payload.get("metadata", {}))

    agents_payload = state_map.get("agents", [])
    metadata_agents = metadata.get("agents_full", [])

    bounds = [1.0, 1.0]
    raw_bounds = env_payload.get("bounds")
    if isinstance(raw_bounds, (list, tuple)) and len(raw_bounds) >= 2:
        bounds = [float(raw_bounds[0]), float(raw_bounds[1])]
    elif all(isinstance(state_map.get(key), (int, float)) for key in ("room_width", "room_height")):
        bounds = [float(state_map["room_width"]), float(state_map["room_height"])]
    elif "world_size" in state_map:
        try:
            world_size = float(state_map["world_size"])
            bounds = [world_size, world_size]
        except (TypeError, ValueError):
            bounds = [1.0, 1.0]

    normalized_agents = _normalize_agent_rows(metadata_agents) or _normalize_agent_rows(agents_payload)
    environment: dict[str, Any] = {"bounds": bounds}
    if metadata:
        environment["metadata"] = dict(metadata)

    normalized_state: dict[str, Any] = {
        "agents": normalized_agents,
        "environment": environment,
    }
    if "step" in state_map and isinstance(state_map["step"], (int, float)):
        normalized_state["step"] = int(state_map["step"])
    elif "step_index" in state_map and isinstance(state_map["step_index"], (int, float)):
        normalized_state["step"] = int(state_map["step_index"])

    room_width = _coerce_int(state_map.get("room_width"))
    room_height = _coerce_int(state_map.get("room_height"))
    if room_width is None and len(bounds) >= 2:
        room_width = _coerce_int(bounds[0])
    if room_height is None and len(bounds) >= 2:
        room_height = _coerce_int(bounds[1])
    if room_width is not None:
        normalized_state["room_width"] = room_width
    if room_height is not None:
        normalized_state["room_height"] = room_height

    simulation_name = state_map.get("simulation")
    if not isinstance(simulation_name, str):
        simulation_name = metadata.get("simulation")
    if isinstance(simulation_name, str):
        normalized_state["simulation"] = simulation_name

    normalized_food = _normalize_food_rows(state_map.get("food"))
    if not normalized_food:
        normalized_food = _normalize_food_rows(metadata.get("food"))
    if normalized_food:
        normalized_state["food"] = normalized_food

    return normalized_state


def _to_mapping(value: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(value):
        converted = dataclasses.asdict(value)
        if isinstance(converted, dict):
            return converted
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_agent_rows(raw_agents: Any) -> list[dict[str, Any]]:
    normalized_agents: list[dict[str, Any]] = []
    if not isinstance(raw_agents, list):
        return normalized_agents

    for index, raw_agent in enumerate(raw_agents):
        agent_map = _to_mapping(raw_agent)
        if not agent_map:
            continue

        position = agent_map.get("position")
        if isinstance(position, (list, tuple)) and len(position) >= 2:
            try:
                x = float(position[0])
                y = float(position[1])
            except (TypeError, ValueError):
                x = float(index)
                y = 0.0
        elif "x" in agent_map and "y" in agent_map:
            try:
                x = float(agent_map["x"])
                y = float(agent_map["y"])
            except (TypeError, ValueError):
                x = float(index)
                y = 0.0
        else:
            x = float(index)
            y = 0.0

        normalized = {
            "id": str(agent_map.get("id", f"agent_{index}")),
            "position": [x, y],
            "alive": bool(agent_map.get("alive", True)),
        }

        # Preserve simulation-specific scalar fields for inspection tabs.
        for key, value in agent_map.items():
            if key in {"id", "position", "alive"}:
                continue
            if isinstance(value, (str, bool, int, float)):
                normalized[str(key)] = value

        fitness_value = agent_map.get("fitness")
        if isinstance(fitness_value, (float, int)):
            normalized["fitness"] = float(fitness_value)

        normalized_agents.append(normalized)

    return normalized_agents


def _normalize_food_rows(raw_food: Any) -> list[dict[str, int]]:
    normalized: list[dict[str, int]] = []
    if not isinstance(raw_food, list):
        return normalized

    for item in raw_food:
        item_map = _to_mapping(item)
        if not item_map:
            continue
        x_val = item_map.get("x")
        y_val = item_map.get("y")
        if not isinstance(x_val, (int, float)) or not isinstance(y_val, (int, float)):
            continue
        food_item = {"x": int(x_val), "y": int(y_val)}
        if isinstance(item_map.get("count"), (int, float)):
            food_item["count"] = int(item_map["count"])
        normalized.append(food_item)

    return normalized


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None
