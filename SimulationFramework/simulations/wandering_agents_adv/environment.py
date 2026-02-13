"""Environment and turn-resolution logic for wandering_agents_adv."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from simulations.wandering_agents_adv.agents import WanderingAgent


@dataclass(frozen=True)
class RoomConfig:
    """Runtime parameters for wandering room simulation."""

    room_width: int
    room_height: int
    initial_agents: int
    max_hunger: int
    move_distance: int
    food_hunger_gain: int
    hunger_decay_per_step: int
    food_spawn_per_step: int
    food_spawn_divisor: int
    mating_hunger_fraction: float
    mating_min_hunger: int
    mating_hunger_cost: int
    offspring_deviation_pct: float
    initial_agreeable_min: float
    initial_agreeable_max: float
    initial_aggression_min: float
    initial_aggression_max: float
    max_population: int


class WanderingRoomEnvironment:
    """Square-room environment with food, mating, and deterministic movement."""

    def __init__(self, config: RoomConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.step_count = 0
        self.next_agent_index = 0
        self.agents: list[WanderingAgent] = []
        self.food_counts: dict[tuple[int, int], int] = defaultdict(int)
        self._last_metrics: dict[str, float] = {}
        self._last_events: dict[str, int] = {}

    def reset(self) -> None:
        """Reset world state to initial deterministic setup."""
        self.step_count = 0
        self.next_agent_index = 0
        self.agents = []
        self.food_counts = defaultdict(int)
        self._last_metrics = {}
        self._last_events = {}

        for _ in range(max(0, int(self.config.initial_agents))):
            self.agents.append(self._create_initial_agent())

    def step(self) -> None:
        """Advance one world turn with deterministic priority-based behavior."""
        self.step_count += 1
        births: list[WanderingAgent] = []
        mated_this_step: set[str] = set()
        events = {"ate": 0, "picked": 0, "mated": 0, "births": 0, "deaths": 0}

        alive_agents = [agent for agent in self.agents if agent.alive]
        alive_agents.sort(key=lambda agent: agent.agent_id)

        for agent in alive_agents:
            self._decrement_hunger(agent)
            if not agent.alive:
                events["deaths"] += 1
                continue

            actions_remaining = max(1, int(agent.move_distance))
            mated_this_turn = False
            while actions_remaining > 0 and agent.alive:
                performed = False
                if self._eat_if_possible(agent):
                    events["ate"] += 1
                    performed = True
                elif self._pickup_if_possible(agent):
                    events["picked"] += 1
                    performed = True
                else:
                    child = None
                    if not mated_this_turn:
                        child = self._attempt_mate(agent, mated_this_step)
                    if child is not None:
                        births.append(child)
                        events["mated"] += 1
                        events["births"] += 1
                        mated_this_turn = True
                        performed = True
                        actions_remaining -= 1
                        break
                    else:
                        self._move_one_step(agent)
                        performed = True

                if performed:
                    actions_remaining -= 1

            agent.age += 1

        if births:
            remaining = max(0, int(self.config.max_population) - len(self.agents))
            if remaining > 0:
                self.agents.extend(births[:remaining])

        self._spawn_food()
        self._last_events = dict(events)
        self._last_metrics = self._compute_metrics()

    def visible_entities(self, agent: WanderingAgent) -> dict[str, Any]:
        """Return line-of-sight entities for one agent (no obstacles)."""
        others = [
            {"id": other.agent_id, "x": int(other.x), "y": int(other.y)}
            for other in self.agents
            if other.alive and other.agent_id != agent.agent_id
        ]
        foods = [{"x": int(x), "y": int(y), "count": int(count)} for (x, y), count in self.food_counts.items() if count > 0]
        return {
            "visible_agents": others,
            "visible_food": foods,
        }

    def get_metrics(self) -> dict[str, float]:
        """Return latest scalar metrics."""
        if not self._last_metrics:
            self._last_metrics = self._compute_metrics()
        payload = dict(self._last_metrics)
        for key, value in self._last_events.items():
            payload[f"event_{key}"] = float(value)
        return payload

    def get_render_state(self) -> dict[str, Any]:
        """Return full JSON-serializable room state."""
        return {
            "simulation": "wandering_agents_adv",
            "step": int(self.step_count),
            "room_width": int(self.config.room_width),
            "room_height": int(self.config.room_height),
            "food": [
                {"x": int(x), "y": int(y), "count": int(count)}
                for (x, y), count in sorted(self.food_counts.items(), key=lambda row: (row[0][1], row[0][0]))
                if count > 0
            ],
            "agents": [agent.to_dict() for agent in sorted(self.agents, key=lambda a: a.agent_id)],
        }

    def export_state(self) -> dict[str, Any]:
        """Export checkpoint-compatible state."""
        render = self.get_render_state()
        return {
            "population_state": render["agents"],
            "environment_state": {
                "food": render["food"],
                "room_width": render["room_width"],
                "room_height": render["room_height"],
                "step": render["step"],
                "next_agent_index": int(self.next_agent_index),
            },
            "step_count": int(self.step_count),
        }

    def import_state(self, state: dict[str, Any]) -> None:
        """Restore state exported by export_state()."""
        population = list(state.get("population_state", []))
        environment = dict(state.get("environment_state", {}))
        self.agents = []
        for item in population:
            if not isinstance(item, dict):
                continue
            self.agents.append(
                WanderingAgent(
                    agent_id=str(item.get("id", f"agent_{len(self.agents)}")),
                    x=int(item.get("x", item.get("position", [0, 0])[0] if isinstance(item.get("position"), list) else 0)),
                    y=int(item.get("y", item.get("position", [0, 0])[1] if isinstance(item.get("position"), list) else 0)),
                    move_distance=max(1, int(item.get("MoveDistance", self.config.move_distance))),
                    hunger=max(0, int(item.get("Hunger", self.config.max_hunger))),
                    max_hunger=max(1, int(item.get("MaxHunger", self.config.max_hunger))),
                    hands=max(0, min(1, int(item.get("Hands", 0)))),
                    agreeable=float(item.get("Agreeable", 0.5)),
                    aggression=float(item.get("Aggression", 0.5)),
                    alive=bool(item.get("alive", True)),
                    age=int(item.get("age", 0)),
                )
            )

        self.food_counts = defaultdict(int)
        for food in list(environment.get("food", [])):
            if not isinstance(food, dict):
                continue
            key = (int(food.get("x", 0)), int(food.get("y", 0)))
            self.food_counts[key] += max(0, int(food.get("count", 1)))

        self.step_count = int(state.get("step_count", state.get("step_index", environment.get("step", 0))))
        self.next_agent_index = int(environment.get("next_agent_index", len(self.agents)))
        self._last_metrics = self._compute_metrics()

    def _create_initial_agent(self) -> WanderingAgent:
        agent = WanderingAgent(
            agent_id=f"agent_{self.next_agent_index}",
            x=self.rng.randrange(self.config.room_width),
            y=self.rng.randrange(self.config.room_height),
            move_distance=max(1, int(self.config.move_distance)),
            hunger=int(self.config.max_hunger),
            max_hunger=int(self.config.max_hunger),
            hands=0,
            agreeable=self.rng.uniform(self.config.initial_agreeable_min, self.config.initial_agreeable_max),
            aggression=self.rng.uniform(self.config.initial_aggression_min, self.config.initial_aggression_max),
            alive=True,
            age=0,
        )
        self.next_agent_index += 1
        return agent

    def _decrement_hunger(self, agent: WanderingAgent) -> None:
        agent.hunger = max(0, int(agent.hunger - self.config.hunger_decay_per_step))
        if agent.hunger <= 0:
            agent.alive = False

    def _eat_if_possible(self, agent: WanderingAgent) -> bool:
        if agent.hands <= 0:
            return False
        if agent.hunger >= agent.max_hunger:
            return False
        agent.hands = 0
        agent.hunger = min(agent.max_hunger, agent.hunger + self.config.food_hunger_gain)
        return True

    def _pickup_if_possible(self, agent: WanderingAgent) -> bool:
        if agent.hands >= 1:
            return False
        key = (agent.x, agent.y)
        if self.food_counts.get(key, 0) <= 0:
            return False
        self.food_counts[key] -= 1
        if self.food_counts[key] <= 0:
            self.food_counts.pop(key, None)
        agent.hands = 1
        return True

    def _attempt_mate(self, agent: WanderingAgent, mated_this_step: set[str]) -> WanderingAgent | None:
        if agent.agent_id in mated_this_step:
            return None
        if not agent.can_mate(self.config.mating_min_hunger, self.config.mating_hunger_fraction):
            return None

        partners = []
        for candidate in self.agents:
            if not candidate.alive or candidate.agent_id == agent.agent_id:
                continue
            if candidate.agent_id in mated_this_step:
                continue
            if not candidate.can_mate(self.config.mating_min_hunger, self.config.mating_hunger_fraction):
                continue
            if max(abs(candidate.x - agent.x), abs(candidate.y - agent.y)) <= 1:
                partners.append(candidate)

        if not partners:
            return None
        partners.sort(key=lambda c: c.agent_id)
        partner = partners[0]

        if agent.hunger < self.config.mating_min_hunger or partner.hunger < self.config.mating_min_hunger:
            return None

        mated_this_step.add(agent.agent_id)
        mated_this_step.add(partner.agent_id)
        agent.hunger = max(0, agent.hunger - self.config.mating_hunger_cost)
        partner.hunger = max(0, partner.hunger - self.config.mating_hunger_cost)
        if agent.hunger <= 0:
            agent.alive = False
        if partner.hunger <= 0:
            partner.alive = False

        child_move = self._inherit_with_deviation(agent.move_distance, partner.move_distance)
        child_agreeable = self._inherit_with_deviation(agent.agreeable, partner.agreeable)
        child_aggression = self._inherit_with_deviation(agent.aggression, partner.aggression)

        child = WanderingAgent(
            agent_id=f"agent_{self.next_agent_index}",
            x=int(agent.x),
            y=int(agent.y),
            move_distance=max(1, int(round(child_move))),
            hunger=int(self.config.max_hunger),
            max_hunger=int(self.config.max_hunger),
            hands=0,
            agreeable=float(max(0.0, min(1.0, child_agreeable))),
            aggression=float(max(0.0, min(1.0, child_aggression))),
            alive=True,
            age=0,
        )
        self.next_agent_index += 1
        return child

    def _move_one_step(self, agent: WanderingAgent) -> None:
        target = self._pick_movement_target(agent)
        dx = 0
        dy = 0
        if target is not None:
            tx, ty = target
            if tx > agent.x:
                dx = 1
            elif tx < agent.x:
                dx = -1
            elif ty > agent.y:
                dy = 1
            elif ty < agent.y:
                dy = -1
            else:
                dx, dy = self._random_movement_delta(agent)
        else:
            dx, dy = self._random_movement_delta(agent)

        new_x = max(0, min(self.config.room_width - 1, agent.x + dx))
        new_y = max(0, min(self.config.room_height - 1, agent.y + dy))
        agent.x = int(new_x)
        agent.y = int(new_y)

    def _random_movement_delta(self, agent: WanderingAgent) -> tuple[int, int]:
        options = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self.rng.shuffle(options)
        for dx, dy in options:
            new_x = max(0, min(self.config.room_width - 1, agent.x + dx))
            new_y = max(0, min(self.config.room_height - 1, agent.y + dy))
            if new_x != agent.x or new_y != agent.y:
                return dx, dy
        return (0, 0)

    def _pick_movement_target(self, agent: WanderingAgent) -> tuple[int, int] | None:
        if self.food_counts and (agent.hands <= 0 or agent.hunger < int(agent.max_hunger * 0.8)):
            return self._nearest_food_position(agent.x, agent.y)

        if agent.can_mate(self.config.mating_min_hunger, self.config.mating_hunger_fraction):
            mate_target = self._nearest_mate_candidate(agent)
            if mate_target is not None:
                return mate_target

        return None

    def _nearest_food_position(self, x: int, y: int) -> tuple[int, int] | None:
        best: tuple[int, int] | None = None
        best_dist = math.inf
        for (fx, fy), count in self.food_counts.items():
            if count <= 0:
                continue
            dist = abs(fx - x) + abs(fy - y)
            if dist < best_dist:
                best_dist = dist
                best = (fx, fy)
        return best

    def _nearest_mate_candidate(self, agent: WanderingAgent) -> tuple[int, int] | None:
        best: WanderingAgent | None = None
        best_dist = math.inf
        for other in self.agents:
            if not other.alive or other.agent_id == agent.agent_id:
                continue
            if not other.can_mate(self.config.mating_min_hunger, self.config.mating_hunger_fraction):
                continue
            dist = abs(other.x - agent.x) + abs(other.y - agent.y)
            if dist < best_dist:
                best_dist = dist
                best = other
        if best is None:
            return None
        return (best.x, best.y)

    def _spawn_food(self) -> None:
        alive_count = sum(1 for agent in self.agents if agent.alive)
        if self.config.food_spawn_per_step >= 0:
            spawn_count = int(self.config.food_spawn_per_step)
        else:
            divisor = max(1, int(self.config.food_spawn_divisor))
            spawn_count = alive_count // divisor
        spawn_count = max(0, int(spawn_count))

        for _ in range(spawn_count):
            x = self.rng.randrange(self.config.room_width)
            y = self.rng.randrange(self.config.room_height)
            self.food_counts[(x, y)] += 1

    def _inherit_with_deviation(self, value_a: float, value_b: float) -> float:
        avg = (float(value_a) + float(value_b)) / 2.0
        deviation = self.rng.uniform(-self.config.offspring_deviation_pct, self.config.offspring_deviation_pct)
        return avg * (1.0 + deviation)

    def _compute_metrics(self) -> dict[str, float]:
        alive = [agent for agent in self.agents if agent.alive]
        mean_hunger = float(sum(agent.hunger for agent in alive) / len(alive)) if alive else 0.0
        avg_lifespan_turns = float(sum(agent.age for agent in self.agents) / len(self.agents)) if self.agents else 0.0
        mean_agreeable = float(sum(agent.agreeable for agent in alive) / len(alive)) if alive else 0.0
        mean_aggression = float(sum(agent.aggression for agent in alive) / len(alive)) if alive else 0.0
        food_total = float(sum(self.food_counts.values()))
        held_food = float(sum(agent.hands for agent in alive))
        return {
            "population": float(len(alive)),
            "average_hunger": mean_hunger,
            "average_lifespan_turns": avg_lifespan_turns,
            "population_alive": float(len(alive)),
            "population_total": float(len(self.agents)),
            "mean_hunger": mean_hunger,
            "mean_agreeable": mean_agreeable,
            "mean_aggression": mean_aggression,
            "food_count": food_total,
            "food_held": held_food,
            "step_count": float(self.step_count),
        }
