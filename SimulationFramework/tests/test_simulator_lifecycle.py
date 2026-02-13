"""Lifecycle and determinism checks for engine.simulator.Simulator."""

from __future__ import annotations

import random

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from data.logger import SimulationLogger
from engine.simulator import Simulator
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


def _build(seed: int, db_path: str) -> Simulator:
    logger = SimulationLogger(db_path)
    population = [
        RandomAgent(genome=TrivialGenome(value=i / 4.0), rng=random.Random(seed + i), agent_id=f"agent_{i}")
        for i in range(4)
    ]
    env = DummyEnvironment(agent_ids=tuple(a.agent_id for a in population), max_steps=50)
    env.reset()
    return Simulator(
        environment=env,
        population=population,
        evolution_strategy=IdentityEvolutionStrategy(),
        seed=seed,
        logger=logger,
        config={"population_size": 4, "environment": "dummy", "seed": seed},
    )


def test_simulator_runs_multiple_generations_and_logs_metrics(tmp_path) -> None:
    sim = _build(seed=13, db_path=str(tmp_path / "metrics_a.db"))
    sim.run(6)

    assert sim.experiment_id is not None
    rows = sim.logger.fetch_metrics(sim.experiment_id)  # type: ignore[union-attr]
    sim.logger.close()  # type: ignore[union-attr]

    assert len(rows) == 6
    mean_values = [float(row["mean_fitness"]) for row in rows]
    assert len(set(mean_values)) > 1


def test_simulator_is_deterministic_with_same_seed(tmp_path) -> None:
    sim_a = _build(seed=21, db_path=str(tmp_path / "metrics_b.db"))
    sim_b = _build(seed=21, db_path=str(tmp_path / "metrics_c.db"))

    sim_a.run(5)
    sim_b.run(5)

    exp_a = sim_a.experiment_id
    exp_b = sim_b.experiment_id
    assert exp_a is not None and exp_b is not None

    rows_a = sim_a.logger.fetch_metrics(exp_a)  # type: ignore[union-attr]
    rows_b = sim_b.logger.fetch_metrics(exp_b)  # type: ignore[union-attr]
    sim_a.logger.close()  # type: ignore[union-attr]
    sim_b.logger.close()  # type: ignore[union-attr]

    assert rows_a == rows_b
