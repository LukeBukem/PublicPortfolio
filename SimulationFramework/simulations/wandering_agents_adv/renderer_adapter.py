"""Render adapter for wandering_agents_adv plugin."""

from __future__ import annotations

import time
from typing import Any

from core.render_state import AgentState, EnvironmentState, RenderState


def build_render_state(simulator: object) -> RenderState:
    """Build generic RenderState while preserving plugin-specific metadata."""
    sim = getattr(simulator, "sim")
    raw = sim.get_render_state()
    metrics = sim.get_metrics()

    agents_raw = list(raw.get("agents", [])) if isinstance(raw, dict) else []
    food_raw = list(raw.get("food", [])) if isinstance(raw, dict) else []
    room_width = int(raw.get("room_width", 50)) if isinstance(raw, dict) else 50
    room_height = int(raw.get("room_height", 50)) if isinstance(raw, dict) else 50

    agents = []
    for idx, agent in enumerate(agents_raw):
        if not isinstance(agent, dict):
            continue
        pos = agent.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            x = float(pos[0])
            y = float(pos[1])
        else:
            x = float(agent.get("x", idx))
            y = float(agent.get("y", 0))
        agents.append(
            AgentState(
                id=str(agent.get("id", f"agent_{idx}")),
                position=(x, y),
                velocity=None,
                genome_summary={},
                fitness=None,
                alive=bool(agent.get("alive", True)),
            )
        )

    env_state = EnvironmentState(
        bounds=(room_width, room_height),
        obstacles=[],
        resources=[],
        metadata={
            "simulation": "wandering_agents_adv",
            "food": food_raw,
            "agents_full": agents_raw,
        },
    )

    return RenderState(
        generation_index=int(getattr(simulator, "generation_index", 0)),
        step_index=int(getattr(simulator, "step_index", raw.get("step", 0) if isinstance(raw, dict) else 0)),
        agents=agents,
        environment=env_state,
        metrics={k: float(v) for k, v in metrics.items() if _is_floatable(v)},
        timestamp=float(time.time()),
    )


def _is_floatable(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
