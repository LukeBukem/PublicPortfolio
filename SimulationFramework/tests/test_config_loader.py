"""Tests for config loading and validation."""

from __future__ import annotations

import json

import pytest

from configs.loader import ConfigLoader


def test_load_json_config(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    payload = {
        "population_size": 10,
        "generations": 5,
        "mutation_rate": 0.1,
        "environment": "dummy",
        "seed": 1,
        "note": "demo",
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    config = ConfigLoader.load(config_path)

    assert config.population_size == 10
    assert config.get("note") == "demo"


def test_load_many_batch_json(tmp_path) -> None:
    config_path = tmp_path / "batch.json"
    payload = {
        "experiments": [
            {
                "population_size": 10,
                "generations": 5,
                "mutation_rate": 0.1,
                "environment": "dummy",
                "seed": 1,
            },
            {
                "population_size": 10,
                "generations": 6,
                "mutation_rate": 0.2,
                "environment": "dummy",
                "seed": 2,
            },
        ]
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    configs = ConfigLoader.load_many(config_path)

    assert len(configs) == 2
    assert configs[1].generations == 6


def test_invalid_config_missing_required_key(tmp_path) -> None:
    config_path = tmp_path / "invalid.json"
    payload = {
        "population_size": 10,
        "generations": 5,
        "mutation_rate": 0.1,
        "environment": "dummy",
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required config keys"):
        ConfigLoader.load(config_path)
