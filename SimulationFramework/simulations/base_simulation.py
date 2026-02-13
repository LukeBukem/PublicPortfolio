"""Base simulation plugin contract."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any


class Simulation(ABC):
    """Abstract simulation plugin interface.

    All simulation state must be instance-local. The core engine communicates
    with plugins only through this contract.
    """

    def __init__(self, params: dict[str, Any], rng: random.Random) -> None:
        """Store plugin parameters and RNG.

        Args:
            params: Plugin-specific validated parameters.
            rng: Deterministic RNG owned by the simulator.
        """
        self.params = params
        self.rng = rng

    @abstractmethod
    def reset(self) -> None:
        """Initialize world state and agents."""

    @abstractmethod
    def step(self) -> None:
        """Advance the simulation by one tick."""

    @abstractmethod
    def get_metrics(self) -> dict[str, float]:
        """Return scalar metrics for logging."""

    @abstractmethod
    def get_render_state(self) -> dict[str, Any]:
        """Return JSON-serializable world state (data only)."""

    @abstractmethod
    def close(self) -> None:
        """Release plugin resources."""
