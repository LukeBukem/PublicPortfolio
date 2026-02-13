"""Agent interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agents.genome import Genome


class Agent(ABC):
    """Abstract decision-making entity controlled by a genome.

    Agents encapsulate policy behavior and genome ownership but remain decoupled
    from selection and population-level evolution logic.
    """

    def observe(self, environment_state: Any) -> Any:
        """Transform environment state into an agent-specific observation.

        Default behavior is pass-through so existing agents remain compatible.
        Subclasses may override to implement richer perception pipelines.
        """
        return environment_state

    @abstractmethod
    def act(self, observation: Any) -> Any:
        """Produce an action from the given observation.

        Args:
            observation (Any): Environment-provided observation object.

        Returns:
            Any: Action compatible with the environment interface.

        Invariants:
            - Must not mutate external observation objects unexpectedly.
            - Deterministic behavior should be achievable under fixed state.
        """

    def mutate(self) -> None:
        """Optional in-place mutation hook.

        Evolution strategies generally mutate genomes directly; this hook exists
        as an extension point for agent implementations that keep additional
        mutable controller state.
        """

    @abstractmethod
    def get_genome(self) -> Genome:
        """Return the genome currently associated with this agent.

        Returns:
            Genome: Agent genome instance.

        Invariants:
            - Returned genome should represent the agent's active parameters.
        """

    @abstractmethod
    def set_genome(self, genome: Genome) -> None:
        """Replace the agent's active genome.

        Args:
            genome (Genome): Genome instance to assign.

        Returns:
            None

        Invariants:
            - Assignment must preserve agent-genome consistency constraints.
            - Method should not perform population-level evolution.
        """
