"""Random-action agent implementations."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Sequence

from agents.base import Agent
from agents.genome import Genome


@dataclass
class RandomAgent(Agent):
    """Agent that selects uniformly from an observation-provided action space."""

    genome: Genome
    rng: random.Random
    agent_id: str = ""

    def observe(self, environment_state: Any) -> Any:
        """Return environment state unchanged.

        This keeps the agent generic and compatible with multiple environment
        observation payloads while preserving the required API contract.
        """
        return environment_state

    def act(self, observation: Any) -> int:
        """Select an action index from ``observation['action_space']``."""
        if not isinstance(observation, dict) or "action_space" not in observation:
            raise ValueError("Observation must be a mapping with an 'action_space' key.")
        action_space: Sequence[int] = observation["action_space"]
        if not action_space:
            raise ValueError("Action space must be non-empty.")
        return int(self.rng.choice(list(action_space)))

    def get_genome(self) -> Genome:
        """Return current genome."""
        return self.genome

    def set_genome(self, genome: Genome) -> None:
        """Assign a new genome."""
        self.genome = genome
