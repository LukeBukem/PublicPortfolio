from __future__ import annotations

import random

from agents.base import Agent
from agents.trivial_genome import TrivialGenome
from configs.loader import ExperimentConfig
from engine.component_registry import (
    available_agent_factories,
    available_environment_factories,
    available_evolution_factories,
    create_agent,
    create_environment,
    create_evolution,
)
from environment.base import Environment
from evolution.base import EvolutionStrategy


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        population_size=4,
        generations=2,
        mutation_rate=0.1,
        environment="dummy",
        seed=123,
        extras={"evolution_strategy": "ga"},
    )


def test_default_factories_registered() -> None:
    assert "random" in available_agent_factories()
    assert "dummy" in available_environment_factories()
    assert "ga" in available_evolution_factories()


def test_create_environment_agent_evolution() -> None:
    config = _config()
    agent_ids = tuple(f"agent_{i}" for i in range(config.population_size))

    env = create_environment("dummy", agent_ids, config)
    assert isinstance(env, Environment)

    genome = TrivialGenome(value=0.5)
    agent = create_agent("random", "agent_0", genome, random.Random(1), config)
    assert isinstance(agent, Agent)

    evo = create_evolution("ga", config)
    assert isinstance(evo, EvolutionStrategy)
