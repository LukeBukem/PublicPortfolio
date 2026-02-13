"""Core simulator that orchestrates plugins without simulation-specific logic."""

from __future__ import annotations

import importlib
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from core.checkpointing import Checkpoint
from core.config_loader import load_config
from core.deterministic_rng import DeterministicRNG
from core.plugin_registry import get_simulation_class
from data.checkpoint_store import CheckpointStore


class SimulatorRuntimeError(RuntimeError):
    """Raised when a simulation plugin fails during execution."""


class Simulator:
    """Plugin-driven simulator runtime."""

    def __init__(
        self,
        config_path: str | Path,
        event_bus: object | None = None,
        checkpoint_store: CheckpointStore | None = None,
        experiment_dir: Path | None = None,
    ) -> None:
        config = load_config(str(config_path))
        self.config = config

        self.simulation_name = str(config["simulation"])
        self.simulation_config = dict(config["simulation_config"])
        self.evolution_config = dict(config["evolution_config"])
        self.logging_config = dict(config["logging_config"])

        self.seed = int(config["seed"])
        self.rng = DeterministicRNG(self.seed)
        self.event_bus = event_bus

        self.generation_index = 0
        self.step_index = 0

        self.checkpoint_store = checkpoint_store
        self.experiment_dir = experiment_dir
        self._checkpoint_interval = int(self.logging_config.get("checkpoint_interval", 0))
        self._checkpoint_executor = ThreadPoolExecutor(max_workers=1) if checkpoint_store else None

        simulation_class = get_simulation_class(self.simulation_name)
        try:
            self.sim = simulation_class(params=self.simulation_config, rng=self.rng.python_rng)
        except Exception as exc:
            raise SimulatorRuntimeError(
                f"Failed to initialize simulation plugin '{self.simulation_name}': {exc}"
            ) from exc

        self._render_adapter = None
        try:
            adapter_module = importlib.import_module(
                f"simulations.{self.simulation_name}.renderer_adapter"
            )
            self._render_adapter = getattr(adapter_module, "build_render_state", None)
        except Exception:
            self._render_adapter = None

    def _emit_render_state(self) -> None:
        if self.event_bus is None or self._render_adapter is None:
            return
        state = self._render_adapter(self)
        self.event_bus.publish("render_state", state)

    def _build_checkpoint(self, metrics: dict[str, float]) -> Checkpoint:
        if hasattr(self.sim, "export_state"):
            sim_state = self.sim.export_state()  # type: ignore[attr-defined]
            population_state = sim_state.get("population_state")
            environment_state = sim_state.get("environment_state")
        else:
            render = self.sim.get_render_state()
            population_state = render.get("agents") if isinstance(render, dict) else None
            environment_state = render.get("environment") if isinstance(render, dict) else render

        return Checkpoint(
            generation_index=int(self.generation_index),
            step_index=int(self.step_index),
            population_state=population_state,
            environment_state=environment_state,
            metrics={k: float(v) for k, v in metrics.items()},
            rng_state=self.rng.snapshot(),
            timestamp=float(time.time()),
        )

    def _emit_checkpoint(self, metrics: dict[str, float]) -> None:
        if self.checkpoint_store is None or self.experiment_dir is None:
            return
        if self._checkpoint_interval <= 0:
            return
        if self.step_index % self._checkpoint_interval != 0:
            return

        checkpoint = self._build_checkpoint(metrics)
        path = self.checkpoint_store.checkpoint_path(self.experiment_dir, self.step_index)

        if self._checkpoint_executor is None:
            return
        self._checkpoint_executor.submit(self.checkpoint_store.save, checkpoint, path)
        if self.event_bus is not None:
            self.event_bus.publish("checkpoint_saved", {"path": str(path), "step_index": self.step_index})

    def run(self, steps: int = 10) -> list[dict[str, float]]:
        """Run plugin for a fixed number of steps and collect metrics."""
        metrics: list[dict[str, float]] = []
        try:
            self.sim.reset()
            for step in range(steps):
                self.step_index = step + 1
                self.sim.step()
                metric = self.sim.get_metrics()
                metrics.append(metric)
                _ = self.sim.get_render_state()
                self._emit_render_state()
                self._emit_checkpoint(metric)

            if self.event_bus is not None:
                self.event_bus.publish(
                    "generation_end",
                    {"generation_index": self.generation_index, "step_index": self.step_index},
                )
        except Exception as exc:
            raise SimulatorRuntimeError(
                f"Simulation plugin '{self.simulation_name}' crashed during run: {exc}"
            ) from exc
        finally:
            try:
                self.sim.close()
            except Exception as exc:
                raise SimulatorRuntimeError(
                    f"Simulation plugin '{self.simulation_name}' failed during close: {exc}"
                ) from exc
            if self._checkpoint_executor is not None:
                self._checkpoint_executor.shutdown(wait=True)

        if self.event_bus is not None:
            self.event_bus.publish(
                "simulation_end",
                {"generation_index": self.generation_index, "step_index": self.step_index},
            )

        return metrics

    def restore_from_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Restore simulator/plugin state from checkpoint."""
        self.generation_index = int(checkpoint.generation_index)
        self.step_index = int(checkpoint.step_index)
        self.rng.restore(dict(checkpoint.rng_state))

        if hasattr(self.sim, "import_state"):
            self.sim.import_state(  # type: ignore[attr-defined]
                {
                    "population_state": checkpoint.population_state,
                    "environment_state": checkpoint.environment_state,
                    "step_index": checkpoint.step_index,
                    "generation_index": checkpoint.generation_index,
                }
            )
