"""Tests for modular simulation plugin architecture."""

from __future__ import annotations

import pytest

from core.config_loader import ConfigValidationError, load_config
from core.plugin_registry import (
    SimulationPluginNotFoundError,
    discover_simulations,
    get_simulation_class,
)
from core.simulator import Simulator


def _valid_config_yaml() -> str:
    return (
        "simulation: example_sim\n"
        "params:\n"
        "  world_size: 12\n"
        "  num_agents: 4\n"
        "evolution:\n"
        "  population_size: 20\n"
        "  mutation_rate: 0.1\n"
        "  crossover_rate: 0.7\n"
        "  elite_fraction: 0.1\n"
        "  random_seed: 123\n"
        "logging:\n"
        "  log_interval: 1\n"
        "  checkpoint_interval: 10\n"
        "  experiment_name: baseline\n"
    )


def test_plugin_discovery_finds_example_sim() -> None:
    discovered = discover_simulations()
    assert "example_sim" in discovered


def test_simulator_runs_example_sim_for_10_steps(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_valid_config_yaml(), encoding="utf-8")

    simulator = Simulator(config_path)
    metrics = simulator.run(steps=10)

    assert len(metrics) == 10
    assert "mean_agent_x_position" in metrics[-1]
    assert "step_count" in metrics[-1]
    assert metrics[-1]["step_count"] == 10.0


def test_invalid_config_triggers_schema_error(tmp_path) -> None:
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        _valid_config_yaml().replace("world_size: 12", "world_size: wrong_type"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="expected int"):
        load_config(str(config_path))


def test_missing_plugin_raises_registry_error() -> None:
    with pytest.raises(SimulationPluginNotFoundError, match="Available simulations"):
        get_simulation_class("definitely_missing_sim")


def test_extra_param_strict_mode_errors(tmp_path) -> None:
    config_path = tmp_path / "extra.yaml"
    config_path.write_text(
        _valid_config_yaml().replace("num_agents: 4", "num_agents: 4\n  foo_bar: 1"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="Unknown parameter"):
        load_config(str(config_path), strict=True)


def test_extra_param_non_strict_warns(tmp_path) -> None:
    config_path = tmp_path / "extra_warn.yaml"
    config_path.write_text(
        _valid_config_yaml().replace("num_agents: 4", "num_agents: 4\n  foo_bar: 1"),
        encoding="utf-8",
    )

    with pytest.warns(UserWarning, match="Unknown parameter"):
        config = load_config(str(config_path), strict=False)
    assert config["simulation"] == "example_sim"
