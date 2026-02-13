"""Agent with simple action-choice logic for wandering environments."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Sequence

from agents.base import Agent
from agents.genome import Genome


@dataclass
class WanderAgent(Agent):
    """Agent that chooses actions from explicit action arrays.

    Selection policy:
    - With probability ``exploration_rate`` choose random action.
    - Otherwise choose deterministic preferred index derived from genome scalar.
    """

    genome: Genome
    rng: random.Random
    agent_id: str = ""
    exploration_rate: float = 0.1

    def act(self, observation: Any) -> int:
        if not isinstance(observation, dict) or "action_space" not in observation:
            raise ValueError("Observation must include 'action_space'.")
        action_space: Sequence[int] = observation["action_space"]
        if not action_space:
            raise ValueError("Action space must be non-empty.")

        if self.rng.random() < self.exploration_rate:
            return int(self.rng.choice(list(action_space)))

        genome = self.get_genome()
        scalar = float(getattr(genome, "value", 0.0))
        preferred_idx = int(abs(scalar) * 1000) % len(action_space)
        return int(action_space[preferred_idx])

    def get_genome(self) -> Genome:
        return self.genome

    def set_genome(self, genome: Genome) -> None:
        self.genome = genome
