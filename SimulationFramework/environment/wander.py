"""2D wandering-squares environment with explicit discrete actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from environment.base import Environment

# Discrete action set shared by wandering environments/agents.
ACTION_STAY = 0
ACTION_UP = 1
ACTION_DOWN = 2
ACTION_LEFT = 3
ACTION_RIGHT = 4
ACTION_SPACE: tuple[int, ...] = (
    ACTION_STAY,
    ACTION_UP,
    ACTION_DOWN,
    ACTION_LEFT,
    ACTION_RIGHT,
)


@dataclass
class WanderEnvironment(Environment):
    """Environment where square agents move on a bounded 2D grid.

    Each agent starts at a deterministic coordinate based on index. Reward is
    negative Manhattan distance to the grid center after the move (scaled to
    [-1, 0]) so higher is better as agents approach the center.
    """

    agent_ids: tuple[str, ...]
    width: int = 10
    height: int = 10
    max_steps: int = 25
    _step: int = field(default=0, init=False)
    _positions: dict[str, tuple[int, int]] = field(default_factory=dict, init=False)
    _last_rewards: dict[str, float] = field(default_factory=dict, init=False)

    def reset(self) -> Mapping[str, Any]:
        """Reset positions and return initial per-agent observations."""
        self._step = 0
        self._positions = {
            agent_id: (index % self.width, index % self.height)
            for index, agent_id in enumerate(self.agent_ids)
        }
        self._last_rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        return {agent_id: self.observe(agent_id) for agent_id in self.agent_ids}

    def step(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        """Apply actions, update positions, and return transition payload."""
        for agent_id in self.agent_ids:
            action = int(actions.get(agent_id, ACTION_STAY))
            x, y = self._positions[agent_id]
            if action == ACTION_UP:
                y = max(0, y - 1)
            elif action == ACTION_DOWN:
                y = min(self.height - 1, y + 1)
            elif action == ACTION_LEFT:
                x = max(0, x - 1)
            elif action == ACTION_RIGHT:
                x = min(self.width - 1, x + 1)
            self._positions[agent_id] = (x, y)

        self._step += 1
        center_x, center_y = self.width // 2, self.height // 2
        max_dist = max(center_x + center_y, 1)
        self._last_rewards = {}
        for agent_id, (x, y) in self._positions.items():
            dist = abs(x - center_x) + abs(y - center_y)
            self._last_rewards[agent_id] = -float(dist) / float(max_dist)

        done = self._step >= self.max_steps
        return {
            "observations": {agent_id: self.observe(agent_id) for agent_id in self.agent_ids},
            "rewards": dict(self._last_rewards),
            "dones": {agent_id: done for agent_id in self.agent_ids},
            "step": self._step,
        }

    def observe(self, agent: str) -> Any:
        """Return observation including position and explicit action space."""
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        x, y = self._positions[agent]
        return {
            "agent_id": agent,
            "position": (x, y),
            "grid_size": (self.width, self.height),
            "action_space": list(ACTION_SPACE),
            "step": self._step,
        }

    def get_observation(self, agent: str) -> Any:
        """Compatibility alias used by simulator."""
        return self.observe(agent)

    def evaluate(self, agent: str) -> float:
        """Return latest reward as current fitness estimate for ``agent``."""
        if agent not in self.agent_ids:
            raise KeyError(f"Unknown agent id: {agent}")
        return float(self._last_rewards.get(agent, 0.0))
