"""Tests for wandering-squares simulation components."""

from __future__ import annotations

import random

from agents.trivial_genome import TrivialGenome
from agents.wander_agent import WanderAgent
from configs.loader import ExperimentConfig
from main import build_components
from environment.wander import ACTION_SPACE, WanderEnvironment


def test_wander_environment_action_space_and_step() -> None:
    env = WanderEnvironment(agent_ids=("agent_0",), width=6, height=6, max_steps=2)
    env.reset()
    obs = env.observe("agent_0")
    assert tuple(obs["action_space"]) == ACTION_SPACE

    transition = env.step({"agent_0": ACTION_SPACE[1]})
    assert "rewards" in transition
    assert "agent_0" in transition["rewards"]


def test_wander_agent_selects_action_from_observation_array() -> None:
    agent = WanderAgent(
        genome=TrivialGenome(value=0.37),
        rng=random.Random(3),
        agent_id="agent_0",
        exploration_rate=0.0,
    )
    action = agent.act({"action_space": list(ACTION_SPACE)})
    assert action in ACTION_SPACE


def test_build_components_supports_wander_end_to_end() -> None:
    config = ExperimentConfig(
        population_size=5,
        generations=2,
        mutation_rate=0.05,
        environment="wander",
        seed=11,
        extras={"evolution_strategy": "ga", "agent_type": "wander", "width": 8, "height": 8},
    )
    simulator = build_components(config)
    simulator.run_generation()
    assert simulator.last_generation_metrics is not None
