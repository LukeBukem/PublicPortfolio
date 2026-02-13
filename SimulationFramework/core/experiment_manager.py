"""Experiment manager orchestrator implementing SimulationRunner API."""

from __future__ import annotations

import itertools
import json
import logging
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.metrics_store import MetricsStore
from core.replay_loader import ReplayLoader
from core.simulation_runner_api import Metrics, ReplayStream, RunMetadata, SimulationRunnerAPI
from workers.simulation_worker import execute_run

LOGGER = logging.getLogger(__name__)


class ExperimentManager(SimulationRunnerAPI):
    """Thin orchestration service for manifest-driven experiment sweeps."""

    def __init__(self, store: MetricsStore, replay_loader: ReplayLoader, max_workers: int = 2) -> None:
        self.store = store
        self.replay_loader = replay_loader
        self.max_workers = max(1, max_workers)

    def run_experiment(self, manifest_path: str) -> None:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        experiment_id = manifest.get("experiment_id", str(uuid4()))
        self.store.save_experiment(experiment_id, manifest)

        tasks = self._expand_manifest_tasks(experiment_id, manifest)
        if not tasks:
            LOGGER.warning("No tasks generated for manifest %s", manifest_path)
            return

        for task in tasks:
            self.store.upsert_run(
                RunMetadata(
                    run_id=task["run_id"],
                    experiment_id=experiment_id,
                    status="queued",
                    seed=int(task["seed"]),
                    parameters=task["parameters"],
                )
            )

        with ProcessPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(execute_run, task): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                run_id = task["run_id"]
                try:
                    result = future.result()
                except Exception as exc:
                    LOGGER.exception("Worker failed for run %s: %s", run_id, exc)
                    result = {
                        "run_id": run_id,
                        "seed": int(task["seed"]),
                        "summary": {"error": 1.0},
                        "series": {},
                        "status": "failed",
                    }
                run_id = task["run_id"]
                self.store.upsert_run(
                    RunMetadata(
                        run_id=run_id,
                        experiment_id=experiment_id,
                        status=result["status"],
                        seed=int(result["seed"]),
                        parameters=task["parameters"],
                    )
                )
                self.store.save_metrics(
                    Metrics(run_id=run_id, summary=result["summary"], series=result["series"])
                )

    def list_runs(self) -> list[RunMetadata]:
        return self.store.list_runs()

    def get_metrics(self, run_id: str) -> Metrics:
        return self.store.get_metrics(run_id)

    def get_replay(self, run_id: str) -> ReplayStream:
        return self.replay_loader.get_replay(run_id)

    def _expand_manifest_tasks(self, experiment_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        sweep = manifest.get("sweep", {})
        output_dir = manifest.get("output_dir", "experiments")
        base_seed = int(manifest.get("base_seed", 42))
        seed_strategy = manifest.get("seed_strategy", "incremental")
        runs_per_param_set = int(manifest.get("runs_per_param_set", 1))
        generations = int(manifest.get("generations", 20))

        param_grid = sweep.get("grid", {})
        random_samples = int(sweep.get("random_samples", 0))
        random_space = sweep.get("random_space", {})

        grid_sets = self._grid_parameter_sets(param_grid)
        sampled_sets = self._sample_parameter_sets(random_space, random_samples, base_seed)
        param_sets = grid_sets + sampled_sets

        tasks: list[dict[str, Any]] = []
        counter = 0
        for params in param_sets:
            for repeat in range(runs_per_param_set):
                counter += 1
                run_id = f"{experiment_id}-run-{counter:04d}"
                seed = self._resolve_seed(seed_strategy, base_seed, counter, repeat)
                tasks.append(
                    {
                        "run_id": run_id,
                        "seed": seed,
                        "parameters": params,
                        "output_dir": output_dir,
                        "generations": generations,
                        "config_path": manifest.get("config_path"),
                    }
                )
        return tasks

    @staticmethod
    def _grid_parameter_sets(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
        if not grid:
            return [{}]
        keys = sorted(grid)
        values = [grid[k] for k in keys]
        combos = itertools.product(*values)
        return [dict(zip(keys, combo, strict=False)) for combo in combos]

    @staticmethod
    def _sample_parameter_sets(random_space: dict[str, dict[str, float]], n: int, seed: int) -> list[dict[str, Any]]:
        if n <= 0 or not random_space:
            return []
        rng = random.Random(seed)
        samples: list[dict[str, Any]] = []
        for _ in range(n):
            row = {}
            for key, bounds in random_space.items():
                lo = float(bounds.get("min", 0.0))
                hi = float(bounds.get("max", 1.0))
                row[key] = rng.uniform(lo, hi)
            samples.append(row)
        return samples

    @staticmethod
    def _resolve_seed(strategy: str, base_seed: int, counter: int, repeat: int) -> int:
        if strategy == "fixed":
            return base_seed
        if strategy == "random":
            return random.SystemRandom().randint(0, 2**31 - 1)
        return base_seed + counter + repeat
