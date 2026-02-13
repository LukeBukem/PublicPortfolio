"""Minimal vertical slice orchestration using concrete interface implementations."""

from __future__ import annotations

import random
from dataclasses import dataclass

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


@dataclass
class SliceResult:
    """Container for one minimal generation result."""

    fitness: list[float]
    next_population_size: int


def run_minimal_vertical_slice(seed: int = 42) -> SliceResult:
    """Execute one simple deterministic generation using concrete components."""
    rng = random.Random(seed)
    agent_ids = ("agent_0", "agent_1")

    environment = DummyEnvironment(agent_ids=agent_ids, max_steps=1)
    population = [
        RandomAgent(genome=TrivialGenome(value=0.1), rng=rng),
        RandomAgent(genome=TrivialGenome(value=0.2), rng=rng),
    ]
    evolution = IdentityEvolutionStrategy()

    observations = environment.reset()
    actions = {
        agent_id: agent.act(observations[agent_id])
        for agent_id, agent in zip(agent_ids, population)
    }
    transition = environment.step(actions)
    fitness = [transition["rewards"][agent_id] for agent_id in agent_ids]
    next_population = evolution.evolve(population, fitness)

    return SliceResult(fitness=fitness, next_population_size=len(next_population))
