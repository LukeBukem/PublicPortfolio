"""Simple genetic algorithm evolution strategy."""

from __future__ import annotations

import copy
import random
from typing import Sequence

from agents.base import Agent
from agents.genome import Genome
from evolution.base import EvolutionStrategy


class GeneticEvolutionStrategy(EvolutionStrategy):
    """Tournament-selection GA with crossover + mutation."""

    def __init__(self, mutation_rate: float = 0.05, tournament_size: int = 3) -> None:
        self.mutation_rate = mutation_rate
        self.tournament_size = max(2, tournament_size)
        self.last_mutation_ratio: float = 0.0

    def evolve(
        self,
        population: Sequence[Agent],
        fitness: Sequence[float],
        rng: random.Random | None = None,
    ) -> list[Agent]:
        """Return next population with preserved size."""
        if len(population) != len(fitness):
            raise ValueError("Population and fitness lengths must match.")
        if not population:
            return []

        local_rng = rng or random.Random(0)
        next_population: list[Agent] = []
        mutation_count = 0

        while len(next_population) < len(population):
            parent_a = self._tournament_select(population, fitness, local_rng)
            parent_b = self._tournament_select(population, fitness, local_rng)

            genome_a = parent_a.get_genome()
            genome_b = parent_b.get_genome()
            child_genome = genome_a.crossover(genome_b)
            child_genome = child_genome.mutate(self.mutation_rate)
            mutation_count += 1

            child = copy.deepcopy(parent_a)
            child.set_genome(child_genome)
            next_population.append(child)

        self.last_mutation_ratio = float(mutation_count) / float(len(next_population)) if next_population else 0.0
        return next_population

    def _tournament_select(
        self,
        population: Sequence[Agent],
        fitness: Sequence[float],
        rng: random.Random,
    ) -> Agent:
        """Pick best fitness agent from a sampled subset."""
        indices = [rng.randrange(len(population)) for _ in range(self.tournament_size)]
        best_index = max(indices, key=lambda i: fitness[i])
        return population[best_index]
