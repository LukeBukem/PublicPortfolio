"""Simulation runner interface contract for orchestration-facing consumers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RunMetadata:
    """Metadata for a completed or running simulation instance."""

    run_id: str
    experiment_id: str
    status: str
    seed: int
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Metrics:
    """Dynamic metrics container with per-generation series support."""

    run_id: str
    summary: dict[str, float] = field(default_factory=dict)
    series: dict[str, list[float]] = field(default_factory=dict)


@dataclass(slots=True)
class ReplayStream:
    """Engine-agnostic replay frame stream."""

    run_id: str
    frames: list[dict[str, Any]] = field(default_factory=list)


class SimulationRunnerAPI(ABC):
    """Boundary layer the GUI must consume for all run/metrics/replay access."""

    @abstractmethod
    def run_experiment(self, manifest_path: str) -> None:
        """Dispatch an experiment described by manifest_path."""

    @abstractmethod
    def list_runs(self) -> list[RunMetadata]:
        """List known runs from the configured persistence layer."""

    @abstractmethod
    def get_metrics(self, run_id: str) -> Metrics:
        """Load normalized metrics for a run from the data layer."""

    @abstractmethod
    def get_replay(self, run_id: str) -> ReplayStream:
        """Load replay frames for a run via replay loader abstraction."""
