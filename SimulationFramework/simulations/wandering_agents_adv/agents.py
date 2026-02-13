"""Agent model for wandering_agents_adv plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WanderingAgent:
    """Single agent state for the wandering room simulation."""

    agent_id: str
    x: int
    y: int
    move_distance: int
    hunger: int
    max_hunger: int
    hands: int
    agreeable: float
    aggression: float
    alive: bool = True
    age: int = 0

    def can_mate(self, min_hunger: int, hunger_fraction: float) -> bool:
        """Return true when this agent is eligible to mate this turn."""
        if not self.alive:
            return False
        if self.hunger < int(min_hunger):
            return False
        return float(self.hunger) > float(self.max_hunger) * float(hunger_fraction)

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent state for render/export."""
        return {
            "id": self.agent_id,
            "x": int(self.x),
            "y": int(self.y),
            "position": [int(self.x), int(self.y)],
            "MoveDistance": int(self.move_distance),
            "Hunger": int(self.hunger),
            "MaxHunger": int(self.max_hunger),
            "Hands": int(self.hands),
            "Agreeable": float(self.agreeable),
            "Aggression": float(self.aggression),
            "alive": bool(self.alive),
            "age": int(self.age),
        }
