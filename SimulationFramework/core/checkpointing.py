"""Checkpoint contracts for deterministic replay/time-travel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CHECKPOINT_SCHEMA_VERSION = "v1"


@dataclass(frozen=True)
class Checkpoint:
    """Immutable simulation checkpoint payload."""

    generation_index: int
    step_index: int
    population_state: Any
    environment_state: Any
    metrics: dict[str, float]
    rng_state: dict[str, Any]
    timestamp: float
    schema_version: str = CHECKPOINT_SCHEMA_VERSION
