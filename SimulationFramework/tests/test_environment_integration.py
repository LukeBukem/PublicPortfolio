"""Environment compatibility and simulator determinism checks."""

from __future__ import annotations

import random

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from engine.simulator import Simulator
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


def test_dummy_environment_supports_observe_step_evaluate() -> None:
    env = DummyEnvironment(agent_ids=("agent_0",), max_steps=1)
    env.reset()
    obs = env.get_observation("agent_0")
    assert "action_space" in obs

    env.step({"agent_0": 1})
    fitness = env.evaluate("agent_0")
    assert fitness == 1.0


def test_run_generation_is_deterministic_for_same_seed() -> None:
    def build(seed: int) -> Simulator:
        env = DummyEnvironment(agent_ids=("agent_0", "agent_1"), max_steps=1)
        env.reset()
        return Simulator(
            environment=env,
            population=[
                RandomAgent(genome=TrivialGenome(value=0.1), rng=random.Random(seed)),
                RandomAgent(genome=TrivialGenome(value=0.2), rng=random.Random(seed + 1)),
            ],
            evolution_strategy=IdentityEvolutionStrategy(),
            seed=seed,
        )

    sim_a = build(123)
    sim_b = build(123)

    sim_a.run_generation()
    sim_b.run_generation()

    assert sim_a.last_generation_metrics == sim_b.last_generation_metrics
