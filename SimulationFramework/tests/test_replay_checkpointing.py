"""Tests for deterministic RNG, checkpointing, and replay engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.deterministic_rng import DeterministicRNG
from core.replay import ReplayEngine
from core.simulator import Simulator
from data.checkpoint_store import CheckpointSchemaError, CheckpointStore


def _config_text(seed: int = 123, checkpoint_interval: int = 2) -> str:
    return (
        "simulation: example_sim\n"
        "params:\n"
        "  world_size: 12\n"
        "  num_agents: 4\n"
        "evolution:\n"
        "  population_size: 20\n"
        "  mutation_rate: 0.1\n"
        "  crossover_rate: 0.7\n"
        "  elite_fraction: 0.1\n"
        f"  random_seed: {seed}\n"
        "logging:\n"
        "  log_interval: 1\n"
        f"  checkpoint_interval: {checkpoint_interval}\n"
        "  experiment_name: replay_test\n"
    )


def test_rng_deterministic_reproduction() -> None:
    rng_a = DeterministicRNG(42)
    rng_b = DeterministicRNG(42)

    vals_a = [rng_a.python_rng.random() for _ in range(5)]
    vals_b = [rng_b.python_rng.random() for _ in range(5)]
    assert vals_a == vals_b

    snap = rng_a.snapshot()
    rng_a.python_rng.random()
    rng_a.restore(snap)
    assert rng_a.snapshot()["python_rng_state"] == snap["python_rng_state"]


def test_save_load_checkpoint_identical_state(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(_config_text(), encoding="utf-8")

    store = CheckpointStore()
    sim = Simulator(cfg, checkpoint_store=store, experiment_dir=tmp_path / "exp")
    metrics = sim.run(steps=4)

    checkpoints = store.list_checkpoints(tmp_path / "exp")
    assert checkpoints
    cp = store.load(checkpoints[-1])

    assert cp.step_index == 4
    assert cp.metrics == metrics[-1]


def test_replay_forward_equals_original_metrics(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(_config_text(seed=999), encoding="utf-8")

    store = CheckpointStore()
    exp_dir = tmp_path / "exp"

    sim = Simulator(cfg, checkpoint_store=store, experiment_dir=exp_dir)
    original_metrics = sim.run(steps=6)

    replay = ReplayEngine(cfg, exp_dir, checkpoint_store=store)
    replay.jump_to_generation(6)

    assert replay.current_metrics == original_metrics[-1]


def test_replay_backward_restores_prior_generation_state(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(_config_text(seed=321), encoding="utf-8")

    store = CheckpointStore()
    exp_dir = tmp_path / "exp"

    sim = Simulator(cfg, checkpoint_store=store, experiment_dir=exp_dir)
    sim.run(steps=6)

    replay = ReplayEngine(cfg, exp_dir, checkpoint_store=store)
    replay.jump_to_generation(6)
    state_at_6 = replay.get_render_state()

    replay.step_backward(2)
    state_at_4 = replay.get_render_state()

    assert state_at_4 != state_at_6
    assert replay.current_step_index == 4


def test_schema_version_mismatch_error(tmp_path) -> None:
    store = CheckpointStore()
    path = tmp_path / "bad.chk"
    path.write_text(
        '{"generation_index":0,"step_index":0,"population_state":{},"environment_state":{},"metrics":{},"rng_state":{},"timestamp":0.0,"schema_version":"v999"}',
        encoding="utf-8",
    )

    with pytest.raises(CheckpointSchemaError, match="schema mismatch"):
        store.load(path)
