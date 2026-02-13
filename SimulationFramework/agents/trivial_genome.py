"""Minimal concrete genome used by the vertical slice demo."""

from __future__ import annotations

from dataclasses import dataclass

from agents.genome import Genome


@dataclass(frozen=True)
class TrivialGenome(Genome):
    """Genome with a single scalar parameter.

    This implementation exists only to validate interface wiring in a simple,
    deterministic setup.
    """

    value: float

    def crossover(self, other: Genome) -> "TrivialGenome":
        """Create offspring by averaging scalar values."""
        if not isinstance(other, TrivialGenome):
            raise TypeError("TrivialGenome crossover requires another TrivialGenome.")
        return TrivialGenome(value=(self.value + other.value) / 2.0)

    def mutate(self, rate: float) -> "TrivialGenome":
        """Return a new genome shifted by a deterministic amount."""
        return TrivialGenome(value=self.value + rate)

    def distance(self, other: Genome) -> float:
        """Absolute distance between scalar values."""
        if not isinstance(other, TrivialGenome):
            raise TypeError("TrivialGenome distance requires another TrivialGenome.")
        return abs(self.value - other.value)
