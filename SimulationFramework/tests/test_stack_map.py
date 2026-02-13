from __future__ import annotations

import pytest

from core.stack_map import StackConfigLoadError, load_stack_config


def test_load_stack_config_generation(tmp_path) -> None:
    path = tmp_path / "gen.yaml"
    path.write_text(
        "\n".join(
            [
                "population_size: 10",
                "generations: 5",
                "mutation_rate: 0.1",
                "environment: dummy",
                "seed: 7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stack, payload = load_stack_config(path)
    assert stack == "generation"
    assert int(payload.population_size) == 10


def test_load_stack_config_plugin(tmp_path) -> None:
    path = tmp_path / "plugin.yaml"
    path.write_text(
        "\n".join(
            [
                "simulation: example_sim",
                "params:",
                "  world_size: 12",
                "  num_agents: 4",
                "evolution:",
                "  population_size: 20",
                "  mutation_rate: 0.1",
                "  crossover_rate: 0.7",
                "  elite_fraction: 0.1",
                "  random_seed: 123",
                "logging:",
                "  log_interval: 1",
                "  checkpoint_interval: 10",
                "  experiment_name: test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stack, payload = load_stack_config(path)
    assert stack == "plugin"
    assert payload["simulation"] == "example_sim"


def test_load_stack_config_invalid(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("not_a_valid_stack: true\n", encoding="utf-8")
    with pytest.raises(StackConfigLoadError):
        load_stack_config(path)
