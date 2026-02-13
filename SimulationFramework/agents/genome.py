"""Genome contracts for evolutionary operators."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Genome(ABC):
    """Abstract genome representation used by evolutionary strategies.

    Implementations may represent parameter vectors, graph structures, or neural
    encodings, but must preserve deterministic semantics for crossover and
    mutation operations under controlled randomness.
    """

    @abstractmethod
    def crossover(self, other: "Genome") -> "Genome":
        """Create an offspring genome from this genome and ``other``.

        Args:
            other (Genome): The second parent genome.

        Returns:
            Genome: A newly created offspring genome.

        Invariants:
            - Must not mutate either parent genome.
            - Should validate compatibility of parent genome types/shapes.
        """

    @abstractmethod
    def mutate(self, rate: float) -> "Genome":
        """Create a mutated genome derived from this genome.

        Args:
            rate (float): Mutation intensity or probability parameter.

        Returns:
            Genome: A mutated genome instance.

        Invariants:
            - Must not mutate the original genome instance in place.
            - Behavior should be deterministic given equivalent RNG state.
        """

    @abstractmethod
    def distance(self, other: "Genome") -> float:
        """Measure distance between this genome and ``other``.

        Args:
            other (Genome): Genome to compare against.

        Returns:
            float: Non-negative distance metric value.

        Invariants:
            - Distance must be deterministic for equivalent inputs.
            - Distance must be non-negative.
        """
