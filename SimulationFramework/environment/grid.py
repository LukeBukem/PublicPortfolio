"""Simple pluggable grid-like numeric environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from environment.base import Environment


@dataclass
class GridEnvironment(Environment):
    """Toy numeric environment with target-matching rewards.

    Each agent chooses an integer action in [0, grid_size-1]. Reward is 1.0 when
    action equals per-agent target, else 0.0.
    """

    agent_ids: tuple[str, ...]
    grid_size: int = 5
    max_steps: int = 1
    _step: int = field(default=0, init=False)
    _targets: dict[str, int] = field(default_factory=dict, init=False)
    _last_rewards: dict[str, float] = field(default_factory=dict, init=False)

    def reset(self) -> Mapping[str, Any]:
        self._step = 0
        self._targets = {
            agent_id: index % self.grid_size for index, agent_id in enumerate(self.agent_ids)
        }
        self._last_rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        return {agent_id: self.observe(agent_id) for agent_id in self.agent_ids}

    def step(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        rewards: dict[str, float] = {}
        for agent_id in self.agent_ids:
            action = int(actions.get(agent_id, -1))
            rewards[agent_id] = 1.0 if action == self._targets[agent_id] else 0.0

        self._last_rewards = rewards
        self._step += 1
        done = self._step >= self.max_steps

        return {
            "observations": {agent_id: self.observe(agent_id) for agent_id in self.agent_ids},
            "rewards": rewards,
            "dones": {agent_id: done for agent_id in self.agent_ids},
            "step": self._step,
        }

    def observe(self, agent: str) -> Any:
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        return {
            "agent_id": agent,
            "action_space": list(range(self.grid_size)),
            "target_hint": self._targets.get(agent, 0),
            "step": self._step,
        }

    def get_observation(self, agent: str) -> Any:
        return self.observe(agent)

    def evaluate(self, agent: str) -> float:
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        return float(self._last_rewards.get(agent, 0.0))
