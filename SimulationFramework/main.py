"""Simple simulation runner for local validation."""

from __future__ import annotations

import random
from pathlib import Path

from agents.trivial_genome import TrivialGenome
from configs.loader import ConfigLoader, ExperimentConfig
from data.logger import SimulationLogger
from engine.component_registry import create_agent, create_environment, create_evolution
from engine.simulator import Simulator


def _build_population(config: ExperimentConfig) -> list:
    """Create deterministic population with selected agent behavior."""
    population_size = config.population_size
    seed = config.seed
    agent_type = str(config.get("agent_type", "random"))

    population: list = []
    for index in range(population_size):
        genome = TrivialGenome(value=float(index) / max(population_size, 1))
        rng = random.Random(seed + index)
        agent_id = f"agent_{index}"
        population.append(create_agent(agent_type, agent_id, genome, rng, config))
    return population


def build_components(config: ExperimentConfig, logger: SimulationLogger | None = None) -> Simulator:
    """Build a simulator from experiment configuration."""
    agent_ids = tuple(f"agent_{index}" for index in range(config.population_size))

    environment = create_environment(config.environment, agent_ids, config)
    environment.reset()

    strategy_name = str(config.get("evolution_strategy", "identity"))
    evolution_strategy = create_evolution(strategy_name, config)

    return Simulator(
        environment=environment,
        population=_build_population(config),
        evolution_strategy=evolution_strategy,
        seed=config.seed,
        logger=logger,
        config=config.to_dict(),
    )


def main(config_path: str = "configs/example_experiment.yaml") -> None:
    """Load config, build components, and run the simulator."""
    config = ConfigLoader.load(config_path)
    logger = SimulationLogger(Path("simulation_metrics.db"))
    simulator = build_components(config=config, logger=logger)

    early_stop_threshold = config.get("early_stop_max_fitness", None)
    if early_stop_threshold is None:
        simulator.run(config.generations)
    else:
        threshold = float(early_stop_threshold)
        for generation_index in range(config.generations):
            simulator.generation_index = generation_index
            simulator.run_generation()
            simulator.on_generation_end(generation_index)
            max_fitness = float((simulator.last_generation_metrics or {}).get("max_fitness", 0.0))
            if max_fitness >= threshold:
                break

    logger.close()


if __name__ == "__main__":
    main()
