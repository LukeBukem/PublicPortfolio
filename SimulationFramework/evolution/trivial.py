"""Minimal evolution strategy for the vertical slice demo."""

from __future__ import annotations

from typing import Sequence

from agents.base import Agent
from evolution.base import EvolutionStrategy


class IdentityEvolutionStrategy(EvolutionStrategy):
    """No-op strategy that preserves ordering and population size."""

    def evolve(self, population: Sequence[Agent], fitness: Sequence[float]) -> list[Agent]:
        """Return shallow-copied population after validating alignment."""
        if len(population) != len(fitness):
            raise ValueError("Population and fitness must have equal lengths.")
        return list(population)
