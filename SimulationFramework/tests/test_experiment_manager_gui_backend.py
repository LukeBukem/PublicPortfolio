from __future__ import annotations

import json
from pathlib import Path

from core.experiment_manager import ExperimentManager
from core.metrics_store import MetricsStore
from core.replay_loader import ReplayLoader


def test_experiment_manager_runs_manifest_and_persists_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "experiments"
    manifest = {
        "experiment_id": "exp-test",
        "output_dir": str(output_dir),
        "runs_per_param_set": 1,
        "seed_strategy": "fixed",
        "base_seed": 7,
        "generations": 5,
        "sweep": {"grid": {"mutation_rate": [0.1, 0.2]}, "random_samples": 0, "random_space": {}},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    store = MetricsStore(tmp_path / "metrics.sqlite")
    loader = ReplayLoader(output_dir)
    manager = ExperimentManager(store=store, replay_loader=loader, max_workers=1)

    manager.run_experiment(str(manifest_path))

    runs = manager.list_runs()
    assert len(runs) == 2
    assert all(run.status == "completed" for run in runs)

    metrics = manager.get_metrics(runs[0].run_id)
    assert "fitness_score" in metrics.summary
    assert "fitness" in metrics.series

    replay = manager.get_replay(runs[0].run_id)
    assert len(replay.frames) > 0


def test_metrics_store_dynamic_schema_roundtrip(tmp_path: Path) -> None:
    from core.simulation_runner_api import Metrics, RunMetadata

    store = MetricsStore(tmp_path / "metrics.sqlite")
    store.upsert_run(
        RunMetadata(
            run_id="run-1",
            experiment_id="exp-1",
            status="completed",
            seed=11,
            parameters={"alpha": 0.1},
        )
    )
    store.save_metrics(Metrics(run_id="run-1", summary={"custom_metric": 1.23}, series={"loss": [1.0, 0.5]}))

    loaded = store.get_metrics("run-1")
    assert loaded.summary["custom_metric"] == 1.23
    assert loaded.series["loss"] == [1.0, 0.5]
