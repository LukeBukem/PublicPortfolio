"""Behavior and integration tests for wandering_agents_adv plugin."""

from __future__ import annotations

import random

import pytest

from core.config_loader import load_config
from core.live_plugin_session import _normalize_render_state
from core.simulator import Simulator
from simulations.wandering_agents_adv.sim import WanderingAgentsAdvancedSimulation
from simulations.wandering_agents_adv.agents import WanderingAgent
from simulations.wandering_agents_adv.environment import RoomConfig, WanderingRoomEnvironment


def _room_config(**overrides: object) -> RoomConfig:
    defaults = {
        "room_width": 12,
        "room_height": 12,
        "initial_agents": 1,
        "max_hunger": 10,
        "move_distance": 3,
        "food_hunger_gain": 3,
        "hunger_decay_per_step": 1,
        "food_spawn_per_step": 0,
        "food_spawn_divisor": 2,
        "mating_hunger_fraction": 0.5,
        "mating_min_hunger": 5,
        "mating_hunger_cost": 2,
        "offspring_deviation_pct": 0.2,
        "initial_agreeable_min": 0.0,
        "initial_agreeable_max": 1.0,
        "initial_aggression_min": 0.0,
        "initial_aggression_max": 1.0,
        "max_population": 200,
    }
    defaults.update(overrides)
    return RoomConfig(**defaults)


def _agent(
    *,
    agent_id: str,
    x: int,
    y: int,
    move_distance: int = 3,
    hunger: int = 10,
    max_hunger: int = 10,
    hands: int = 0,
    agreeable: float = 0.5,
    aggression: float = 0.5,
) -> WanderingAgent:
    return WanderingAgent(
        agent_id=agent_id,
        x=x,
        y=y,
        move_distance=move_distance,
        hunger=hunger,
        max_hunger=max_hunger,
        hands=hands,
        agreeable=agreeable,
        aggression=aggression,
        alive=True,
        age=0,
    )


def test_hunger_decay_then_consumption_from_hands() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=1, move_distance=1, hunger_decay_per_step=1, food_hunger_gain=3),
        rng=random.Random(11),
    )
    env.reset()
    agent = env.agents[0]
    agent.hunger = 6
    agent.hands = 1

    env.step()

    assert agent.hunger == 8
    assert agent.hands == 0


def test_step_uses_full_move_distance_budget_when_no_other_actions() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=1, move_distance=4, hunger_decay_per_step=0, food_spawn_per_step=0),
        rng=random.Random(7),
    )
    env.reset()
    move_calls = 0
    original_move = env._move_one_step

    def _wrapped_move(agent: WanderingAgent) -> None:
        nonlocal move_calls
        move_calls += 1
        original_move(agent)

    env._move_one_step = _wrapped_move  # type: ignore[method-assign]
    env.step()

    assert move_calls == 4


def test_move_falls_back_to_random_when_target_is_current_position() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=1, move_distance=1, hunger_decay_per_step=0, food_spawn_per_step=0),
        rng=random.Random(7),
    )
    env.reset()
    agent = env.agents[0]
    start = (agent.x, agent.y)

    env._pick_movement_target = lambda _agent: (start[0], start[1])  # type: ignore[method-assign]
    env._move_one_step(agent)

    if env.config.room_width > 1 or env.config.room_height > 1:
        assert (agent.x, agent.y) != start


def test_mating_produces_child_with_expected_inheritance() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(
            initial_agents=0,
            hunger_decay_per_step=0,
            food_spawn_per_step=0,
            offspring_deviation_pct=0.0,
        ),
        rng=random.Random(3),
    )
    env.reset()
    env.agents = [
        _agent(agent_id="agent_0", x=3, y=3, move_distance=4, hunger=9, agreeable=0.2, aggression=0.8),
        _agent(agent_id="agent_1", x=4, y=3, move_distance=6, hunger=9, agreeable=0.8, aggression=0.2),
    ]
    env.next_agent_index = 2

    env.step()

    assert len(env.agents) == 3
    child = next(agent for agent in env.agents if agent.agent_id == "agent_2")
    assert child.move_distance == 5
    assert child.agreeable == pytest.approx(0.5)
    assert child.aggression == pytest.approx(0.5)
    assert env.agents[0].hunger == 7
    assert env.agents[1].hunger == 7


def test_mating_is_blocked_below_minimum_hunger() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=0, hunger_decay_per_step=0, food_spawn_per_step=0, mating_min_hunger=5),
        rng=random.Random(3),
    )
    env.reset()
    env.agents = [
        _agent(agent_id="agent_0", x=1, y=1, hunger=4),
        _agent(agent_id="agent_1", x=2, y=1, hunger=4),
    ]
    env.next_agent_index = 2

    env.step()

    assert len(env.agents) == 2


def test_agent_mates_at_most_once_per_turn() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=0, hunger_decay_per_step=0, food_spawn_per_step=0, move_distance=8),
        rng=random.Random(3),
    )
    env.reset()
    env.agents = [
        _agent(agent_id="agent_0", x=2, y=2, move_distance=8, hunger=9),
        _agent(agent_id="agent_1", x=3, y=2, move_distance=8, hunger=9),
        _agent(agent_id="agent_2", x=2, y=3, move_distance=8, hunger=9),
    ]
    env.next_agent_index = 3

    env.step()

    births = [agent for agent in env.agents if agent.agent_id.startswith("agent_3")]
    assert len(births) <= 1
    assert len(env.agents) == 4


def test_food_spawn_defaults_to_floor_alive_div_2() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(
            initial_agents=4,
            hunger_decay_per_step=0,
            food_spawn_per_step=-1,
            food_spawn_divisor=2,
            mating_min_hunger=11,
        ),
        rng=random.Random(19),
    )
    env.reset()
    env.food_counts.clear()

    env.step()

    assert sum(env.food_counts.values()) == 2


def test_metrics_include_population_hunger_and_lifespan() -> None:
    env = WanderingRoomEnvironment(
        config=_room_config(initial_agents=3, hunger_decay_per_step=0, food_spawn_per_step=0, mating_min_hunger=11),
        rng=random.Random(23),
    )
    env.reset()
    env.step()
    metrics = env.get_metrics()

    assert "population" in metrics
    assert "average_hunger" in metrics
    assert "average_lifespan_turns" in metrics
    assert metrics["population"] == 3.0
    assert metrics["average_hunger"] >= 0.0
    assert metrics["average_lifespan_turns"] >= 1.0


def test_visible_entities_reports_all_other_agents_and_food() -> None:
    env = WanderingRoomEnvironment(config=_room_config(initial_agents=0), rng=random.Random(5))
    env.reset()
    observer = _agent(agent_id="agent_0", x=0, y=0)
    env.agents = [
        observer,
        _agent(agent_id="agent_1", x=5, y=5),
        _agent(agent_id="agent_2", x=2, y=1),
    ]
    env.food_counts[(1, 1)] = 2
    env.food_counts[(6, 0)] = 1

    visible = env.visible_entities(observer)

    seen_ids = {item["id"] for item in visible["visible_agents"]}
    seen_food = {(item["x"], item["y"], item["count"]) for item in visible["visible_food"]}
    assert seen_ids == {"agent_1", "agent_2"}
    assert seen_food == {(1, 1, 2), (6, 0, 1)}


def test_render_normalization_recovers_plugin_metadata_fields() -> None:
    payload = {
        "step_index": 9,
        "agents": [{"id": "agent_0", "position": [1.0, 1.0], "alive": True}],
        "environment": {
            "bounds": [50, 40],
            "metadata": {
                "simulation": "wandering_agents_adv",
                "food": [{"x": 3, "y": 4, "count": 2}],
                "agents_full": [
                    {
                        "id": "agent_0",
                        "position": [1, 1],
                        "Hunger": 9,
                        "Hands": 1,
                        "MoveDistance": 5,
                        "Agreeable": 0.4,
                        "Aggression": 0.6,
                        "alive": True,
                    }
                ],
            },
        },
    }

    normalized = _normalize_render_state(payload)

    assert normalized["step"] == 9
    assert normalized["room_width"] == 50
    assert normalized["room_height"] == 40
    assert normalized["simulation"] == "wandering_agents_adv"
    assert normalized["food"][0]["count"] == 2
    assert normalized["agents"][0]["Hunger"] == 9
    assert normalized["agents"][0]["Hands"] == 1


def test_simulator_is_deterministic_for_same_seed(tmp_path) -> None:
    config_path = tmp_path / "wandering.yaml"
    config_path.write_text(
        (
            "simulation: wandering_agents_adv\n"
            "params:\n"
            "  room_width: 20\n"
            "  room_height: 20\n"
            "  initial_agents: 12\n"
            "  max_hunger: 10\n"
            "  move_distance: 3\n"
            "  food_hunger_gain: 3\n"
            "  hunger_decay_per_step: 1\n"
            "  food_spawn_per_step: -1\n"
            "  food_spawn_divisor: 2\n"
            "  mating_hunger_fraction: 0.5\n"
            "  mating_min_hunger: 5\n"
            "  mating_hunger_cost: 2\n"
            "  offspring_deviation_pct: 0.2\n"
            "  initial_agreeable_min: 0.0\n"
            "  initial_agreeable_max: 1.0\n"
            "  initial_aggression_min: 0.0\n"
            "  initial_aggression_max: 1.0\n"
            "  max_population: 150\n"
            "evolution:\n"
            "  population_size: 50\n"
            "  mutation_rate: 0.1\n"
            "  crossover_rate: 0.7\n"
            "  elite_fraction: 0.1\n"
            "  random_seed: 321\n"
            "logging:\n"
            "  log_interval: 1\n"
            "  checkpoint_interval: 20\n"
            "  experiment_name: det_test\n"
        ),
        encoding="utf-8",
    )

    sim_a = Simulator(config_path)
    sim_b = Simulator(config_path)
    metrics_a = sim_a.run(steps=6)
    metrics_b = sim_b.run(steps=6)

    assert metrics_a == metrics_b


def test_mutation_rate_is_used_as_variation_rate(tmp_path) -> None:
    config_path = tmp_path / "wandering_mutation.yaml"
    config_path.write_text(
        (
            "simulation: wandering_agents_adv\n"
            "params:\n"
            "  initial_agents: 6\n"
            "  offspring_deviation_pct: 0.05\n"
            "evolution:\n"
            "  population_size: 20\n"
            "  mutation_rate: 0.2\n"
            "  crossover_rate: 0.7\n"
            "  elite_fraction: 0.1\n"
            "  random_seed: 77\n"
            "logging:\n"
            "  log_interval: 1\n"
            "  checkpoint_interval: 10\n"
            "  experiment_name: mutation_variation\n"
        ),
        encoding="utf-8",
    )

    loaded = load_config(str(config_path))
    params = loaded["simulation_config"]
    sim = WanderingAgentsAdvancedSimulation(params=params, rng=random.Random(77))

    assert params["mutation_rate"] == pytest.approx(0.2)
    assert sim.room_config.offspring_deviation_pct == pytest.approx(0.2)
