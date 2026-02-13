"""Tests for Simulator.run_generation orchestration behavior."""

from __future__ import annotations

import random
import sqlite3

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from data.logger import SimulationLogger
from engine.simulator import Simulator
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


def _build_simulator(db_path, seed: int) -> Simulator:
    logger = SimulationLogger(db_path)
    population = [
        RandomAgent(genome=TrivialGenome(value=0.1), rng=random.Random(seed)),
        RandomAgent(genome=TrivialGenome(value=0.2), rng=random.Random(seed + 1)),
    ]
    return Simulator(
        environment=DummyEnvironment(agent_ids=("agent_0", "agent_1"), max_steps=1),
        population=population,
        evolution_strategy=IdentityEvolutionStrategy(),
        seed=seed,
        logger=logger,
        config={
            "population_size": 2,
            "generations": 1,
            "mutation_rate": 0.1,
            "environment": "dummy",
            "seed": seed,
        },
    )


def test_run_generation_updates_metrics_and_logs(tmp_path) -> None:
    db_path = tmp_path / "run_gen.db"
    simulator = _build_simulator(db_path, seed=10)

    simulator.run_generation()
    simulator.on_generation_end(simulator.generation_index)
    experiment_id = simulator.experiment_id
    assert experiment_id is not None
    assert simulator.last_generation_metrics is not None
    assert "mean_fitness" in simulator.last_generation_metrics
    assert "max_fitness" in simulator.last_generation_metrics

    simulator.logger.close()  # type: ignore[union-attr]

    conn = sqlite3.connect(db_path)
    logged_rows = conn.execute("SELECT COUNT(*) FROM generation_metrics").fetchone()[0]
    conn.close()

    assert logged_rows == 1
