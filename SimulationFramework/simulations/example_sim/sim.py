"""Example simulation plugin implementation."""

from __future__ import annotations

import random
from typing import Any

from simulations.base_simulation import Simulation


class ExampleSimulation(Simulation):
    """Toy grid world where agents wander randomly."""

    def __init__(self, params: dict[str, Any], rng: random.Random) -> None:
        super().__init__(params=params, rng=rng)
        self.world_size = int(params["world_size"])
        self.num_agents = int(params["num_agents"])
        self.step_count = 0
        self.agents: list[dict[str, float | int]] = []

    def reset(self) -> None:
        self.step_count = 0
        self.agents = [
            {
                "id": i,
                "x": float(self.rng.randrange(self.world_size)),
                "y": float(self.rng.randrange(self.world_size)),
            }
            for i in range(self.num_agents)
        ]

    def step(self) -> None:
        for agent in self.agents:
            dx = self.rng.choice([-1.0, 0.0, 1.0])
            dy = self.rng.choice([-1.0, 0.0, 1.0])
            agent["x"] = max(0.0, min(float(self.world_size - 1), float(agent["x"]) + dx))
            agent["y"] = max(0.0, min(float(self.world_size - 1), float(agent["y"]) + dy))
        self.step_count += 1

    def get_metrics(self) -> dict[str, float]:
        mean_x = (
            sum(float(agent["x"]) for agent in self.agents) / float(len(self.agents))
            if self.agents
            else 0.0
        )
        return {
            "mean_agent_x_position": mean_x,
            "step_count": float(self.step_count),
        }

    def get_render_state(self) -> dict[str, Any]:
        return {
            "agents": [{"id": int(a["id"]), "x": float(a["x"]), "y": float(a["y"])} for a in self.agents],
            "world_size": int(self.world_size),
            "step": int(self.step_count),
        }


    def export_state(self) -> dict[str, Any]:
        """Export simulation state for checkpointing."""
        return {
            "population_state": [{"id": int(a["id"]), "x": float(a["x"]), "y": float(a["y"])} for a in self.agents],
            "environment_state": {"world_size": int(self.world_size)},
            "step_count": int(self.step_count),
        }

    def import_state(self, state: dict[str, Any]) -> None:
        """Restore simulation state from checkpoint payload."""
        self.agents = [
            {"id": int(a["id"]), "x": float(a["x"]), "y": float(a["y"])}
            for a in list(state.get("population_state", []))
        ]
        self.step_count = int(state.get("step_count", state.get("step_index", 0)))
        env_state = dict(state.get("environment_state", {}))
        if "world_size" in env_state:
            self.world_size = int(env_state["world_size"])

    def close(self) -> None:
        self.agents = []


SIMULATION_NAME = "example_sim"
SimulationClass = ExampleSimulation
