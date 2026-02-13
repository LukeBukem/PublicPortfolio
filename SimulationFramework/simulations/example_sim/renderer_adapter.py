"""Render-state adapter for example_sim plugin."""

from __future__ import annotations

import time

from core.render_state import AgentState, EnvironmentState, RenderState


def build_render_state(simulator: object) -> RenderState:
    """Map example simulation runtime objects into core RenderState."""
    sim = getattr(simulator, "sim")
    metrics = sim.get_metrics()

    agents = [
        AgentState(
            id=str(agent["id"]),
            position=(float(agent["x"]), float(agent["y"])),
            velocity=None,
            genome_summary={},
            fitness=None,
            alive=True,
        )
        for agent in sim.agents
    ]

    env_state = EnvironmentState(
        bounds=(int(sim.world_size), int(sim.world_size)),
        obstacles=[],
        resources=[],
        metadata={"simulation": "example_sim"},
    )

    return RenderState(
        generation_index=int(getattr(simulator, "generation_index", 0)),
        step_index=int(getattr(simulator, "step_index", 0)),
        agents=agents,
        environment=env_state,
        metrics={k: float(v) for k, v in metrics.items()},
        timestamp=float(time.time()),
    )
