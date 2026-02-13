from __future__ import annotations

import time

from configs.loader import ExperimentConfig
from core.experiment_coordinator import ExperimentCoordinator


def _cfg(seed: int, mutation_rate: float, environment: str = "dummy") -> ExperimentConfig:
    return ExperimentConfig(
        population_size=50,
        generations=8,
        mutation_rate=mutation_rate,
        environment=environment,
        seed=seed,
    )


def test_multi_experiment_live_updates_and_leaderboard(tmp_path) -> None:
    coord = ExperimentCoordinator(base_dir=tmp_path)
    ids = [
        coord.start_experiment(_cfg(1, 0.02), speed=80.0),
        coord.start_experiment(_cfg(2, 0.08), speed=80.0),
        coord.start_experiment(_cfg(3, 0.15), speed=80.0),
    ]

    time.sleep(0.15)
    rows_mid = coord.list_experiments()
    assert len(rows_mid) == 3
    assert any(row["status"] in {"running", "completed"} for row in rows_mid)

    coord.stop_all()
    time.sleep(0.1)
    rows = coord.list_experiments()
    assert len(rows) == 3

    leaderboard = coord.leaderboard(metric="max_fitness")
    assert len(leaderboard) == 3
    assert leaderboard[0]["max_fitness"] >= leaderboard[-1]["max_fitness"]


def test_comparison_overlay_and_exports_match_state(tmp_path) -> None:
    coord = ExperimentCoordinator(base_dir=tmp_path)
    exp_a = coord.start_experiment(_cfg(11, 0.03), speed=100.0)
    exp_b = coord.start_experiment(_cfg(22, 0.07), speed=100.0)

    time.sleep(0.5)
    coord.stop_all()

    overlay = coord.comparison([exp_a, exp_b], metric_keys=["mean_fitness", "diversity"])
    assert "runs" in overlay and "stats" in overlay
    assert set(overlay["runs"].keys()) == {exp_a, exp_b}
    assert "mean_fitness" in overlay["stats"]

    out = coord.export_experiment(exp_a, tmp_path / "exports")
    assert out["csv"].exists()
    assert out["json"].exists()

    history = coord.get_metrics_history(exp_a)
    assert history


def test_delete_experiment_removes_record_and_artifacts(tmp_path) -> None:
    coord = ExperimentCoordinator(base_dir=tmp_path)
    experiment_id = coord.start_plugin_experiment("configs/wandering_agents_adv.yaml", steps=20, speed=200.0)
    metrics_log = tmp_path / f"{experiment_id}_metrics.jsonl"

    time.sleep(0.25)
    assert any(row["experiment_id"] == experiment_id for row in coord.list_experiments())
    assert metrics_log.exists()

    deleted = coord.delete_experiment(experiment_id, delete_artifacts=True)

    assert deleted is True
    assert all(row["experiment_id"] != experiment_id for row in coord.list_experiments())
    assert not metrics_log.exists()


def test_start_plugin_experiment_applies_runtime_overrides(tmp_path) -> None:
    coord = ExperimentCoordinator(base_dir=tmp_path)
    experiment_id = coord.start_plugin_experiment(
        "configs/wandering_agents_adv.yaml",
        steps=1,
        speed=200.0,
        runtime_overrides={
            "evolution": {
                "population_size": 321,
                "mutation_rate": 0.33,
                "random_seed": 777,
            },
            "params": {
                "initial_agents": 10,
                "mating_min_hunger": 100,
                "hunger_decay_per_step": 0,
            },
        },
    )

    time.sleep(0.25)
    history = coord.get_metrics_history(experiment_id)
    rows = coord.list_experiments()
    coord.stop_all()
    row = next(r for r in rows if r["experiment_id"] == experiment_id)
    assert row["population_size"] == 321
    assert row["mutation_rate"] == 0.33
    assert row["seed"] == 777
    assert history
    assert history[-1]["population"] == 10.0


def test_pause_step_resume_state_transitions_are_reported(tmp_path) -> None:
    coord = ExperimentCoordinator(base_dir=tmp_path)
    experiment_id = coord.start_plugin_experiment(
        "configs/wandering_agents_adv.yaml",
        steps=40,
        speed=200.0,
        runtime_overrides={"params": {"initial_agents": 12}},
    )
    time.sleep(0.1)

    coord.pause_experiment(experiment_id)
    time.sleep(0.05)
    assert coord.is_experiment_paused(experiment_id) is True

    stepped = coord.step_experiment(experiment_id, timeout=2.0)
    assert stepped is True
    assert coord.is_experiment_paused(experiment_id) is True

    coord.resume_experiment(experiment_id)
    time.sleep(0.05)
    assert coord.is_experiment_paused(experiment_id) is False
    coord.stop_all()
