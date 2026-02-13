"""Tests for GA strategy and high-level component builder."""

from __future__ import annotations

import random

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from configs.loader import ExperimentConfig
from main import build_components
from evolution.ga import GeneticEvolutionStrategy


def test_ga_strategy_preserves_population_size() -> None:
    strategy = GeneticEvolutionStrategy(mutation_rate=0.1, tournament_size=2)
    population = [
        RandomAgent(genome=TrivialGenome(value=0.0), rng=random.Random(1), agent_id="agent_0"),
        RandomAgent(genome=TrivialGenome(value=1.0), rng=random.Random(2), agent_id="agent_1"),
    ]
    fitness = [0.2, 0.8]

    next_population = strategy.evolve(population, fitness, rng=random.Random(10))

    assert len(next_population) == len(population)


def test_build_components_supports_grid_and_ga() -> None:
    config = ExperimentConfig(
        population_size=4,
        generations=3,
        mutation_rate=0.05,
        environment="grid",
        seed=42,
        extras={"evolution_strategy": "ga", "grid_size": 4, "tournament_size": 2},
    )

    simulator = build_components(config)
    simulator.run_generation()

    assert simulator.last_generation_metrics is not None
    assert "max_fitness" in simulator.last_generation_metrics
