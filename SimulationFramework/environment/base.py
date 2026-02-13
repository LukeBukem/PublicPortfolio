"""Environment contracts for evolutionary simulations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence


class Environment(ABC):
    """Abstract interface for simulation environments.

    Implementations coordinate world state transitions and observation access for
    one or more agents. Environments must support deterministic replay when
    initialized with equivalent configuration and random seed.
    """

    @abstractmethod
    def reset(self) -> Mapping[str, Any]:
        """Reset the environment to its initial state.

        Returns:
            Mapping[str, Any]: Initial observations keyed by agent identifier.

        Invariants:
            - Must fully reset internal episode state.
            - Must be deterministic under equivalent seed/configuration.
            - Must not perform external side effects.
        """

    @abstractmethod
    def step(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        """Advance environment state by one simulation step.

        Args:
            actions (Mapping[str, Any]): Action values keyed by agent identifier.

        Returns:
            Mapping[str, Any]: Step result payload. Implementations may include
                observations, rewards, done flags, and auxiliary metadata.

        Invariants:
            - Supports multi-agent action application in a single transition.
            - Must not mutate the provided ``actions`` mapping.
            - Deterministic under equivalent pre-step state and actions.
        """

    @abstractmethod
    def observe(self, agent: str) -> Any:
        """Return the current observation for a specific agent.

        Args:
            agent (str): Unique agent identifier.

        Returns:
            Any: Agent-specific observation object.

        Invariants:
            - Must not mutate environment state.
            - Returned observation reflects current environment state.
        """

    def get_observations(self, agent_ids: Sequence[str]) -> dict[str, Any]:
        """Return observations for all requested agents.

        Default implementation loops through ``observe`` for compatibility.
        """
        return {agent_id: self.observe(agent_id) for agent_id in agent_ids}

    def apply_actions(self, actions: Mapping[str, Any]) -> Mapping[str, Any]:
        """Apply batched actions and return transition payload.

        Default implementation delegates to ``step``.
        """
        return self.step(actions)

    def evaluate_fitness(self, agent_ids: Sequence[str]) -> dict[str, float]:
        """Return fitness for requested agents.

        Environments may override this to expose domain-specific fitness. The
        base implementation returns empty values so the simulator can derive
        fitness from transition rewards if needed.
        """
        _ = agent_ids
        return {}
