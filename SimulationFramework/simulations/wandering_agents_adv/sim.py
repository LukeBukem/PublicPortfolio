"""Simulation plugin for wandering_agents_adv."""

from __future__ import annotations

import random
from typing import Any

from simulations.base_simulation import Simulation
from simulations.wandering_agents_adv.environment import RoomConfig, WanderingRoomEnvironment


class WanderingAgentsAdvancedSimulation(Simulation):
    """Room simulation with food collection, mating, and rich agent stats."""

    def __init__(self, params: dict[str, Any], rng: random.Random) -> None:
        super().__init__(params=params, rng=rng)
        variation_rate = float(params.get("mutation_rate", params.get("offspring_deviation_pct", 0.2)))
        self.room_config = RoomConfig(
            room_width=int(params.get("room_width", 50)),
            room_height=int(params.get("room_height", 50)),
            initial_agents=int(params.get("initial_agents", 20)),
            max_hunger=int(params.get("max_hunger", 10)),
            move_distance=int(params.get("move_distance", 5)),
            food_hunger_gain=int(params.get("food_hunger_gain", 3)),
            hunger_decay_per_step=int(params.get("hunger_decay_per_step", 1)),
            food_spawn_per_step=int(params.get("food_spawn_per_step", -1)),
            food_spawn_divisor=int(params.get("food_spawn_divisor", 2)),
            mating_hunger_fraction=float(params.get("mating_hunger_fraction", 0.5)),
            mating_min_hunger=int(params.get("mating_min_hunger", 5)),
            mating_hunger_cost=int(params.get("mating_hunger_cost", 2)),
            offspring_deviation_pct=float(max(0.0, variation_rate)),
            initial_agreeable_min=float(params.get("initial_agreeable_min", 0.0)),
            initial_agreeable_max=float(params.get("initial_agreeable_max", 1.0)),
            initial_aggression_min=float(params.get("initial_aggression_min", 0.0)),
            initial_aggression_max=float(params.get("initial_aggression_max", 1.0)),
            max_population=int(params.get("max_population", 500)),
        )
        self.environment = WanderingRoomEnvironment(config=self.room_config, rng=rng)

    def reset(self) -> None:
        self.environment.reset()

    def step(self) -> None:
        self.environment.step()

    def get_metrics(self) -> dict[str, float]:
        return self.environment.get_metrics()

    def get_render_state(self) -> dict[str, Any]:
        return self.environment.get_render_state()

    def export_state(self) -> dict[str, Any]:
        return self.environment.export_state()

    def import_state(self, state: dict[str, Any]) -> None:
        self.environment.import_state(state)

    def close(self) -> None:
        return None


SIMULATION_NAME = "wandering_agents_adv"
SimulationClass = WanderingAgentsAdvancedSimulation
