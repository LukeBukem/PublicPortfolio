"""Minimal deterministic dummy environment for simulator lifecycle testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from environment.base import Environment


@dataclass
class DummyEnvironment(Environment):
    """Simple two-action environment keyed by agent id.

    Agents receive reward 1.0 when selecting action ``1`` and 0.0 otherwise.
    """

    agent_ids: tuple[str, ...]
    max_steps: int = 1
    _step: int = field(default=0, init=False)
    _last_rewards: dict[str, float] = field(default_factory=dict, init=False)

    def reset(self) -> Mapping[str, Any]:
        """Reset step counter and return initial observations."""
        self._step = 0
        self._last_rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        return self.get_observations(self.agent_ids)

    def step(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        """Apply one step and return standard transition payload."""
        return self.apply_actions(actions)

    def observe(self, agent: str) -> Any:
        """Return a minimal observation compatible with ``RandomAgent``."""
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        return {"agent_id": agent, "action_space": [0, 1], "step": self._step}

    def get_observation(self, agent: str) -> Any:
        """Compatibility alias for environments exposing ``get_observation``."""
        return self.observe(agent)

    def get_observations(self, agent_ids: Sequence[str]) -> dict[str, Any]:
        """Return observations for all requested agents."""
        return {agent_id: self.observe(agent_id) for agent_id in agent_ids}

    def apply_actions(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        """Apply actions, update rewards, and return transition data."""
        rewards = {
            agent_id: 1.0 if int(actions.get(agent_id, 0)) == 1 else 0.0
            for agent_id in self.agent_ids
        }
        self._last_rewards = rewards
        self._step += 1
        done = self._step >= self.max_steps
        observations = self.get_observations(self.agent_ids)
        dones = {agent_id: done for agent_id in self.agent_ids}
        return {
            "observations": observations,
            "rewards": rewards,
            "dones": dones,
            "step": self._step,
        }

    def evaluate(self, agent: str) -> float:
        """Compatibility function returning latest reward for one agent."""
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        return float(self._last_rewards.get(agent, 0.0))

    def evaluate_fitness(self, agent_ids: Sequence[str]) -> dict[str, float]:
        """Return latest reward values as fitness map for requested agents."""
        return {agent_id: float(self._last_rewards.get(agent_id, 0.0)) for agent_id in agent_ids}
