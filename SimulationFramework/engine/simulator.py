"""Simulation engine lifecycle orchestrator."""

from __future__ import annotations

import enum
import random
import threading
import time
from typing import Any, Mapping, Sequence

from agents.base import Agent
from data.logger import SimulationLogger
from environment.base import Environment
from evolution.base import EvolutionStrategy


class SimulatorState(str, enum.Enum):
    """Execution control states for generation stepping."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    STOPPED = "stopped"


class SimulatorExecutionError(RuntimeError):
    """Raised when one simulator lifecycle phase fails."""


class Simulator:
    """Orchestrates generation-based evolutionary simulations.

    The simulator is intentionally generic: it only coordinates data flow
    between agents, environments, and evolution strategies. It does not embed
    domain-specific simulation logic.
    """

    def __init__(
        self,
        environment: Environment,
        population: list[Agent],
        evolution_strategy: EvolutionStrategy,
        seed: int | None = None,
        logger: SimulationLogger | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize simulator dependencies and deterministic state."""
        self.environment = environment
        self.population = list(population)
        self.evolution_strategy = evolution_strategy

        self.seed = seed
        self.rng = random.Random(seed)

        self.logger = logger
        self.config = dict(config or {})
        self.experiment_id: str | None = None
        if self.logger is not None:
            safe_seed = int(seed if seed is not None else 0)
            self.experiment_id = self.logger.start_experiment(
                config=self.config,
                seed=safe_seed,
                metadata={"simulator_seed": safe_seed, "simulator_version": "0.1.0"},
            )

        self.generation_index: int = 0
        self.last_generation_metrics: dict[str, Any] | None = None

        self._state = SimulatorState.IDLE
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._step_request_event = threading.Event()
        self._step_ack_event = threading.Event()

    def run_generation(self) -> None:
        """Run one full evolutionary generation lifecycle.

        Lifecycle:
          1) environment observations for each agent,
          2) agent decision pass,
          3) environment transition via actions,
          4) fitness + metric computation,
          5) evolution to next population,
          6) metrics publication for logger hook.
        """
        agent_ids = [str(getattr(agent, "agent_id", "") or f"agent_{idx}") for idx, agent in enumerate(self.population)]

        # 1) Collect environment observations in stable population order.
        raw_observations = self._safe_call(
            "environment.get_observations",
            self.environment.get_observations,
            agent_ids,
        )
        observations: list[Any] = []
        for agent, agent_id in zip(self.population, agent_ids):
            env_state = raw_observations.get(agent_id)
            try:
                observations.append(agent.observe(env_state))
            except Exception as exc:
                raise SimulatorExecutionError(f"Agent '{agent_id}' observe failed: {exc}") from exc

        # 2) Collect actions from all agents.
        actions: dict[str, Any] = {}
        for agent, agent_id, observation in zip(self.population, agent_ids, observations):
            try:
                actions[agent_id] = agent.act(observation)
            except Exception as exc:
                raise SimulatorExecutionError(f"Agent '{agent_id}' act failed: {exc}") from exc

        # 3) Apply actions to update environment state.
        transition = self._safe_call(
            "environment.apply_actions",
            self.environment.apply_actions,
            actions,
        )

        # 4) Evaluate fitness and compute generation metrics.
        fitness_map = self._safe_call(
            "environment.evaluate_fitness",
            self.environment.evaluate_fitness,
            agent_ids,
        )
        if not fitness_map:
            rewards = transition.get("rewards") if isinstance(transition, Mapping) else None
            if isinstance(rewards, Mapping):
                fitness_map = {agent_id: float(rewards.get(agent_id, 0.0)) for agent_id in agent_ids}
            else:
                fitness_map = {agent_id: float(self.rng.random()) for agent_id in agent_ids}

        fitnesses = [float(fitness_map.get(agent_id, 0.0)) for agent_id in agent_ids]

        # 5) Evolve next population with deterministic RNG injection.
        try:
            next_population = self.evolution_strategy.evolve(self.population, fitnesses, rng=self.rng)
        except TypeError:
            try:
                next_population = self.evolution_strategy.evolve(self.population, fitnesses)
            except Exception as exc:
                raise SimulatorExecutionError(f"evolution_strategy.evolve failed: {exc}") from exc
        except Exception as exc:
            raise SimulatorExecutionError(f"evolution_strategy.evolve failed: {exc}") from exc

        if len(next_population) != len(self.population):
            raise ValueError("Evolution strategy must preserve population size.")
        self.population = list(next_population)

        # 6) Update metrics for logging layer.
        self.last_generation_metrics = self._compute_metrics(
            fitnesses=fitnesses,
            transition=transition,
            population=self.population,
        )

    def _compute_metrics(
        self,
        fitnesses: Sequence[float],
        transition: Mapping[str, Any] | Any,
        population: Sequence[Agent],
    ) -> dict[str, float]:
        """Compute dynamic generation metrics from current lifecycle outputs."""
        metrics: dict[str, float] = {}
        if fitnesses:
            metrics["mean_fitness"] = float(sum(fitnesses) / len(fitnesses))
            metrics["max_fitness"] = float(max(fitnesses))
        else:
            metrics["mean_fitness"] = 0.0
            metrics["max_fitness"] = 0.0

        metrics["diversity"] = float(self._compute_genome_diversity(list(population)))
        metrics["mutation_stats"] = float(getattr(self.evolution_strategy, "last_mutation_ratio", 0.0))

        if isinstance(transition, Mapping):
            dynamic_metrics = transition.get("metrics")
            if isinstance(dynamic_metrics, Mapping):
                for key, value in dynamic_metrics.items():
                    try:
                        metrics[str(key)] = float(value)
                    except (TypeError, ValueError):
                        continue
        return metrics

    def _compute_genome_diversity(self, population: list[Agent]) -> float:
        """Compute mean pairwise genome distance for diversity tracking."""
        if len(population) < 2:
            return 0.0

        genomes = [agent.get_genome() for agent in population]
        total = 0.0
        pairs = 0
        for i in range(len(genomes)):
            for j in range(i + 1, len(genomes)):
                total += float(genomes[i].distance(genomes[j]))
                pairs += 1
        return total / pairs if pairs else 0.0

    def control_state(self) -> str:
        """Return current execution control state."""
        with self._state_lock:
            return str(self._state.value)

    def set_running(self) -> None:
        """Set simulator to running state."""
        with self._state_lock:
            if self._state != SimulatorState.STOPPED:
                self._state = SimulatorState.RUNNING

    def pause(self) -> None:
        """Pause execution in controlled run mode."""
        with self._state_lock:
            if self._state in {SimulatorState.RUNNING, SimulatorState.STEPPING}:
                self._state = SimulatorState.PAUSED

    def resume(self) -> None:
        """Resume execution in controlled run mode."""
        with self._state_lock:
            if self._state == SimulatorState.PAUSED:
                self._state = SimulatorState.RUNNING
        self._step_request_event.set()

    def stop(self) -> None:
        """Stop execution in controlled run mode."""
        self._stop_event.set()
        with self._state_lock:
            self._state = SimulatorState.STOPPED
        self._step_request_event.set()
        self._step_ack_event.set()

    def request_step_once(self, timeout: float | None = None) -> bool:
        """Request exactly one generation step and wait for acknowledgment."""
        with self._state_lock:
            if self._state == SimulatorState.STOPPED:
                return False
            self._state = SimulatorState.STEPPING
            self._step_ack_event.clear()
            self._step_request_event.set()
        if timeout is None:
            return True
        return bool(self._step_ack_event.wait(timeout=max(0.0, float(timeout))))

    def run_controlled(self, generations: int, poll_interval: float = 0.01) -> None:
        """Run generation loop honoring RUNNING/PAUSED/STEPPING state machine."""
        if generations < 0:
            raise ValueError("generations must be non-negative")
        poll = max(0.001, float(poll_interval))

        self._stop_event.clear()
        with self._state_lock:
            if self._state in {SimulatorState.IDLE, SimulatorState.PAUSED, SimulatorState.STOPPED}:
                self._state = SimulatorState.RUNNING

        generation_index = int(self.generation_index)
        while generation_index < generations and not self._stop_event.is_set():
            with self._state_lock:
                state = self._state

            if state == SimulatorState.PAUSED:
                self._step_request_event.wait(timeout=poll)
                self._step_request_event.clear()
                continue

            if state not in {SimulatorState.RUNNING, SimulatorState.STEPPING}:
                time.sleep(poll)
                continue

            self.generation_index = generation_index
            self.run_generation()
            self.on_generation_end(generation_index)
            generation_index += 1

            if state == SimulatorState.STEPPING:
                with self._state_lock:
                    if self._state == SimulatorState.STEPPING:
                        self._state = SimulatorState.PAUSED
                self._step_ack_event.set()

        with self._state_lock:
            if self._state != SimulatorState.STOPPED:
                self._state = SimulatorState.IDLE

    def run(self, generations: int) -> None:
        """Run the simulation loop for a fixed number of generations."""
        if generations < 0:
            raise ValueError("generations must be non-negative")

        self._stop_event.clear()
        with self._state_lock:
            self._state = SimulatorState.RUNNING

        try:
            for generation_index in range(generations):
                if self._stop_event.is_set():
                    break
                self.generation_index = generation_index
                self.run_generation()
                self.on_generation_end(generation_index)
        finally:
            with self._state_lock:
                if self._state != SimulatorState.STOPPED:
                    self._state = SimulatorState.IDLE

    def on_generation_end(self, generation_index: int) -> None:
        """Persist metrics for a completed generation if logger is configured."""
        if self.logger is None or self.experiment_id is None:
            return

        raw_metrics = self.last_generation_metrics or {}
        safe_metrics = {
            "mean_fitness": float(raw_metrics.get("mean_fitness", 0.0)),
            "max_fitness": float(raw_metrics.get("max_fitness", 0.0)),
            "diversity": float(raw_metrics.get("diversity", 0.0)),
            "mutation_stats": float(raw_metrics.get("mutation_stats", 0.0)),
        }
        self._safe_call(
            "logger.log_metrics",
            self.logger.log_metrics,
            experiment_id=self.experiment_id,
            generation_index=generation_index,
            metrics=safe_metrics,
        )

    @staticmethod
    def _safe_call(label: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            raise SimulatorExecutionError(f"{label} failed: {exc}") from exc
