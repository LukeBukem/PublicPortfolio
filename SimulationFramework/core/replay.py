"""Deterministic replay and time-travel engine."""

from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path
from typing import Any

from core.simulator import Simulator
from data.checkpoint_store import CheckpointStore


class ReplayEngine:
    """Replay engine that restores checkpoints and scrubs timeline."""

    def __init__(
        self,
        config_path: str | Path,
        experiment_dir: Path,
        checkpoint_store: CheckpointStore | None = None,
        cache_size: int = 16,
    ) -> None:
        self.config_path = Path(config_path)
        self.experiment_dir = Path(experiment_dir)
        self.store = checkpoint_store or CheckpointStore()
        self.simulator = Simulator(self.config_path)

        self._cache_size = max(1, cache_size)
        self._state_cache: OrderedDict[int, Any] = OrderedDict()
        self._metrics_cache: OrderedDict[int, dict[str, float]] = OrderedDict()
        self._checkpoints = self.store.list_checkpoints(self.experiment_dir)
        self._checkpoint_index: list[tuple[int, Path]] = self._build_checkpoint_index(self._checkpoints)
        self.current_step_index = 0
        self.current_metrics: dict[str, float] = {}

        self.simulator.sim.reset()

    def load_checkpoint(self, path: str | Path) -> None:
        cp = self.store.load(Path(path))
        self.simulator.sim.reset()
        self.simulator.restore_from_checkpoint(cp)
        self.current_step_index = int(cp.step_index)
        self.current_metrics = dict(cp.metrics)
        self._cache_put(
            self.current_step_index,
            self.simulator.sim.get_render_state(),
            self.current_metrics,
        )

    def _cache_put(self, step_index: int, state: Any, metrics: dict[str, float]) -> None:
        self._state_cache[step_index] = state
        self._metrics_cache[step_index] = dict(metrics)
        self._state_cache.move_to_end(step_index)
        self._metrics_cache.move_to_end(step_index)
        while len(self._state_cache) > self._cache_size:
            self._state_cache.popitem(last=False)
        while len(self._metrics_cache) > self._cache_size:
            self._metrics_cache.popitem(last=False)

    def _nearest_checkpoint_for_step(self, step_index: int) -> Path | None:
        if not self._checkpoint_index:
            return None
        indices = [idx for idx, _path in self._checkpoint_index]
        pos = bisect_right(indices, step_index) - 1
        if pos < 0:
            return None
        return self._checkpoint_index[pos][1]

    def step_forward(self, n_steps: int) -> None:
        for _ in range(max(0, n_steps)):
            self.simulator.sim.step()
            self.current_step_index += 1
            self.simulator.step_index = self.current_step_index
            self.current_metrics = dict(self.simulator.sim.get_metrics())
            self._cache_put(
                self.current_step_index,
                self.simulator.sim.get_render_state(),
                self.current_metrics,
            )

    def step_backward(self, n_steps: int) -> None:
        target = max(0, self.current_step_index - max(0, n_steps))
        self.jump_to_generation(target)

    def jump_to_generation(self, gen_index: int) -> None:
        target = max(0, gen_index)
        if target in self._state_cache:
            self.current_step_index = target
            self.current_metrics = dict(self._metrics_cache.get(target, {}))
            return

        checkpoint_path = self._nearest_checkpoint_for_step(target)
        if checkpoint_path is None:
            self.simulator.sim.reset()
            self.current_step_index = 0
            self.current_metrics = {}
        else:
            self.load_checkpoint(checkpoint_path)

        delta = target - self.current_step_index
        if delta > 0:
            self.step_forward(delta)

    def jump_to_step(self, step_index: int) -> None:
        """Alias for timeline APIs that reason in steps rather than generations."""
        self.jump_to_generation(step_index)

    def get_render_state(self) -> Any:
        if self.current_step_index in self._state_cache:
            return self._state_cache[self.current_step_index]

        if getattr(self.simulator, "_render_adapter", None) is not None:
            return self.simulator._render_adapter(self.simulator)  # type: ignore[attr-defined]
        return self.simulator.sim.get_render_state()

    def _build_checkpoint_index(self, checkpoints: list[Path]) -> list[tuple[int, Path]]:
        indexed: list[tuple[int, Path]] = []
        for path in checkpoints:
            name = path.stem
            if name.startswith("gen_"):
                try:
                    indexed.append((int(name.replace("gen_", "")), path))
                    continue
                except ValueError:
                    pass
            try:
                indexed.append((int(self.store.load(path).step_index), path))
            except Exception:
                continue
        indexed.sort(key=lambda pair: pair[0])
        return indexed
