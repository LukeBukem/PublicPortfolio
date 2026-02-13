"""Evolution strategy contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from agents.base import Agent


class EvolutionStrategy(ABC):
    """Abstract interface for population evolution algorithms.

    Concrete strategies may include genetic algorithms, NEAT-like methods,
    CMA-ES, or hybrid approaches, provided they operate through explicit inputs
    and produce deterministic outcomes under equivalent conditions.
    """

    @abstractmethod
    def evolve(self, population: Sequence[Agent], fitness: Sequence[float]) -> list[Agent]:
        """Generate the next population from current agents and fitness values.

        Args:
            population (Sequence[Agent]): Current generation agents.
            fitness (Sequence[float]): Fitness scores aligned by index with
                ``population``.

        Returns:
            list[Agent]: Next generation population.

        Invariants:
            - Output population size must equal input population size.
            - Must not mutate input sequence containers in place.
            - Index alignment between ``population`` and ``fitness`` is required.
        """
