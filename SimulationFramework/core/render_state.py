"""Immutable render-state contracts for streaming and visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentState:
    """Simulation-agnostic agent snapshot."""

    id: str
    position: tuple[float, float] | tuple[int, int]
    velocity: tuple[float, float] | None = None
    genome_summary: dict[str, Any] = field(default_factory=dict)
    fitness: float | None = None
    alive: bool = True


@dataclass(frozen=True)
class EnvironmentState:
    """Simulation-agnostic environment snapshot."""

    bounds: tuple[int, int]
    obstacles: list[Any] = field(default_factory=list)
    resources: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderState:
    """Top-level immutable render frame emitted by simulator."""

    generation_index: int
    step_index: int
    agents: list[AgentState]
    environment: EnvironmentState
    metrics: dict[str, float]
    timestamp: float
