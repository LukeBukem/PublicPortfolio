"""Tests for SQLite-backed experiment logger and simulator hook integration."""

from __future__ import annotations

import random
import sqlite3

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from data.logger import SimulationLogger
from engine.simulator import Simulator
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


def test_logger_persists_metadata_and_metrics(tmp_path) -> None:
    db_path = tmp_path / "metrics.db"
    logger = SimulationLogger(db_path)

    experiment_id = logger.start_experiment(
        config={"population_size": 2, "generations": 1, "mutation_rate": 0.1, "environment": "dummy"},
        seed=42,
    )
    logger.log_metrics(
        experiment_id=experiment_id,
        generation_index=0,
        metrics={"mean_fitness": 0.5, "max_fitness": 1.0, "diversity": 0.2, "mutation_stats": 0.1},
    )
    logger.close()

    conn = sqlite3.connect(db_path)
    metadata_count = conn.execute("SELECT COUNT(*) FROM experiment_metadata").fetchone()[0]
    metrics_count = conn.execute("SELECT COUNT(*) FROM generation_metrics").fetchone()[0]
    conn.close()

    assert metadata_count == 1
    assert metrics_count == 1


def test_simulator_on_generation_end_logs_placeholder_metrics(tmp_path) -> None:
    db_path = tmp_path / "sim.db"
    logger = SimulationLogger(db_path)

    rng_seed = 7
    simulator = Simulator(
        environment=DummyEnvironment(agent_ids=("agent_0",), max_steps=1),
        population=[RandomAgent(genome=TrivialGenome(value=0.1), rng=random.Random(rng_seed))],
        evolution_strategy=IdentityEvolutionStrategy(),
        seed=rng_seed,
        logger=logger,
        config={"population_size": 1, "generations": 1, "mutation_rate": 0.1, "environment": "dummy", "seed": 7},
    )

    simulator.last_generation_metrics = {"mean_fitness": 0.3, "max_fitness": 0.9}
    simulator.on_generation_end(0)
    logger.close()

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT mean_fitness, max_fitness, diversity, mutation_stats FROM generation_metrics"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == 0.3
    assert row[1] == 0.9
    assert row[2] == 0.0
    assert row[3] == 0.0
