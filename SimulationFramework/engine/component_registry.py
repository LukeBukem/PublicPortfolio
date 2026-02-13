"""Factories/registries for generation-stack components."""

from __future__ import annotations

import random
from typing import Callable

from agents.base import Agent
from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from agents.wander_agent import WanderAgent
from configs.loader import ExperimentConfig
from environment.base import Environment
from environment.dummy import DummyEnvironment
from environment.grid import GridEnvironment
from environment.wander import WanderEnvironment
from evolution.base import EvolutionStrategy
from evolution.ga import GeneticEvolutionStrategy
from evolution.trivial import IdentityEvolutionStrategy


AgentFactory = Callable[[str, TrivialGenome, random.Random, ExperimentConfig], Agent]
EnvironmentFactory = Callable[[tuple[str, ...], ExperimentConfig], Environment]
EvolutionFactory = Callable[[ExperimentConfig], EvolutionStrategy]


_AGENT_FACTORIES: dict[str, AgentFactory] = {}
_ENVIRONMENT_FACTORIES: dict[str, EnvironmentFactory] = {}
_EVOLUTION_FACTORIES: dict[str, EvolutionFactory] = {}


def register_agent_factory(name: str, factory: AgentFactory) -> None:
    _AGENT_FACTORIES[str(name)] = factory


def register_environment_factory(name: str, factory: EnvironmentFactory) -> None:
    _ENVIRONMENT_FACTORIES[str(name)] = factory


def register_evolution_factory(name: str, factory: EvolutionFactory) -> None:
    _EVOLUTION_FACTORIES[str(name)] = factory


def available_agent_factories() -> list[str]:
    return sorted(_AGENT_FACTORIES)


def available_environment_factories() -> list[str]:
    return sorted(_ENVIRONMENT_FACTORIES)


def available_evolution_factories() -> list[str]:
    return sorted(_EVOLUTION_FACTORIES)


def create_agent(
    name: str,
    agent_id: str,
    genome: TrivialGenome,
    rng: random.Random,
    config: ExperimentConfig,
) -> Agent:
    factory = _AGENT_FACTORIES.get(str(name))
    if factory is None:
        available = ", ".join(available_agent_factories()) or "<none>"
        raise ValueError(f"Unknown agent factory '{name}'. Available: {available}")
    return factory(agent_id, genome, rng, config)


def create_environment(name: str, agent_ids: tuple[str, ...], config: ExperimentConfig) -> Environment:
    factory = _ENVIRONMENT_FACTORIES.get(str(name))
    if factory is None:
        available = ", ".join(available_environment_factories()) or "<none>"
        raise ValueError(f"Unknown environment factory '{name}'. Available: {available}")
    return factory(agent_ids, config)


def create_evolution(name: str, config: ExperimentConfig) -> EvolutionStrategy:
    factory = _EVOLUTION_FACTORIES.get(str(name))
    if factory is None:
        available = ", ".join(available_evolution_factories()) or "<none>"
        raise ValueError(f"Unknown evolution factory '{name}'. Available: {available}")
    return factory(config)


def _random_agent_factory(
    agent_id: str,
    genome: TrivialGenome,
    rng: random.Random,
    _config: ExperimentConfig,
) -> Agent:
    return RandomAgent(genome=genome, rng=rng, agent_id=agent_id)


def _wander_agent_factory(
    agent_id: str,
    genome: TrivialGenome,
    rng: random.Random,
    config: ExperimentConfig,
) -> Agent:
    return WanderAgent(
        genome=genome,
        rng=rng,
        agent_id=agent_id,
        exploration_rate=float(config.get("exploration_rate", 0.1)),
    )


def _dummy_environment_factory(agent_ids: tuple[str, ...], config: ExperimentConfig) -> Environment:
    return DummyEnvironment(
        agent_ids=agent_ids,
        max_steps=int(config.get("max_steps", 1)),
    )


def _grid_environment_factory(agent_ids: tuple[str, ...], config: ExperimentConfig) -> Environment:
    return GridEnvironment(
        agent_ids=agent_ids,
        grid_size=int(config.get("grid_size", 5)),
        max_steps=int(config.get("max_steps", 1)),
    )


def _wander_environment_factory(agent_ids: tuple[str, ...], config: ExperimentConfig) -> Environment:
    return WanderEnvironment(
        agent_ids=agent_ids,
        width=int(config.get("width", 10)),
        height=int(config.get("height", 10)),
        max_steps=int(config.get("max_steps", 25)),
    )


def _identity_evolution_factory(_config: ExperimentConfig) -> EvolutionStrategy:
    return IdentityEvolutionStrategy()


def _ga_evolution_factory(config: ExperimentConfig) -> EvolutionStrategy:
    return GeneticEvolutionStrategy(
        mutation_rate=float(config.mutation_rate),
        tournament_size=int(config.get("tournament_size", 3)),
    )


def _register_defaults() -> None:
    if _AGENT_FACTORIES:
        return
    register_agent_factory("random", _random_agent_factory)
    register_agent_factory("wander", _wander_agent_factory)

    register_environment_factory("dummy", _dummy_environment_factory)
    register_environment_factory("grid", _grid_environment_factory)
    register_environment_factory("wander", _wander_environment_factory)

    register_evolution_factory("identity", _identity_evolution_factory)
    register_evolution_factory("ga", _ga_evolution_factory)


_register_defaults()
