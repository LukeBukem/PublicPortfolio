"""Configuration loading and validation utilities for simulation experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


_REQUIRED_KEYS: tuple[str, ...] = (
    "population_size",
    "generations",
    "mutation_rate",
    "environment",
    "seed",
)


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated experiment configuration container.

    Provides typed field access for required parameters and dictionary-style
    access for extensible optional parameters.
    """

    population_size: int
    generations: int
    mutation_rate: float
    environment: str
    seed: int
    extras: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a configuration value by key.

        Args:
            key: Configuration key name.
            default: Value to return if key does not exist.

        Returns:
            Value associated with ``key`` or ``default``.
        """
        if hasattr(self, key):
            return getattr(self, key)
        return self.extras.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Return a full dictionary view of the configuration."""
        payload = {
            "population_size": self.population_size,
            "generations": self.generations,
            "mutation_rate": self.mutation_rate,
            "environment": self.environment,
            "seed": self.seed,
        }
        payload.update(self.extras)
        return payload


class ConfigLoader:
    """Load and validate experiment configuration files (YAML or JSON)."""

    @staticmethod
    def load(path: str | Path) -> ExperimentConfig:
        """Load a single experiment config from ``path``.

        Args:
            path: Path to a YAML or JSON config file.

        Returns:
            A validated ``ExperimentConfig`` instance.
        """
        payload = _read_config_payload(path)
        if not isinstance(payload, Mapping):
            raise ValueError("Single config file must contain a mapping object.")
        return _validate_and_build(payload)

    @staticmethod
    def load_many(path: str | Path) -> list[ExperimentConfig]:
        """Load one or many experiment configs from ``path``.

        Supports:
            - top-level mapping for single experiment
            - top-level list of mappings
            - top-level mapping with an ``experiments`` list
        """
        payload = _read_config_payload(path)

        if isinstance(payload, list):
            return [_validate_and_build(item) for item in payload]

        if isinstance(payload, Mapping) and "experiments" in payload:
            experiments = payload["experiments"]
            if not isinstance(experiments, list):
                raise ValueError("'experiments' must be a list of mappings.")
            return [_validate_and_build(item) for item in experiments]

        if isinstance(payload, Mapping):
            return [_validate_and_build(payload)]

        raise ValueError("Unsupported config file structure.")


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def _parse_simple_yaml(text: str) -> Any:
    """Parse minimal YAML subset used by local config files."""
    root_map: dict[str, Any] = {}
    root_list: list[Any] | None = None
    current_top: str | None = None
    current_list_item: dict[str, Any] | None = None

    lines = text.splitlines()
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.startswith("- "):
            if root_list is None:
                root_list = []
            item_text = stripped[2:].strip()
            if ":" in item_text:
                key, value = item_text.split(":", 1)
                item = {key.strip(): _coerce_scalar(value.strip())}
            else:
                item = _coerce_scalar(item_text)
            root_list.append(item)
            current_top = None
            current_list_item = item if isinstance(item, dict) else None
            continue

        if indent == 0:
            if ":" not in stripped:
                raise ValueError("Invalid YAML structure in config file.")
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                root_map[key] = {}
                current_top = key
                current_list_item = None
            else:
                root_map[key] = _coerce_scalar(value)
                current_top = None
                current_list_item = None
            continue

        if current_top is None:
            if root_list is not None and current_list_item is not None and indent >= 2:
                if ":" not in stripped:
                    raise ValueError("Invalid YAML structure in list item.")
                key, value = stripped.split(":", 1)
                current_list_item[key.strip()] = _coerce_scalar(value.strip())
                continue
            raise ValueError("Invalid YAML indentation in config file.")

        if indent == 2 and stripped.startswith("- "):
            if not isinstance(root_map.get(current_top), list):
                root_map[current_top] = []
            item_text = stripped[2:].strip()
            if ":" in item_text:
                key, value = item_text.split(":", 1)
                item = {key.strip(): _coerce_scalar(value.strip())}
            elif item_text:
                item = _coerce_scalar(item_text)
            else:
                item = {}
            root_map[current_top].append(item)
            current_list_item = item if isinstance(item, dict) else None
            continue

        if indent == 2:
            if ":" not in stripped:
                raise ValueError("Invalid YAML mapping entry.")
            if isinstance(root_map.get(current_top), dict):
                key, value = stripped.split(":", 1)
                root_map[current_top][key.strip()] = _coerce_scalar(value.strip())
                current_list_item = None
                continue
            raise ValueError("Invalid YAML section type.")

        if indent >= 4:
            section = root_map.get(current_top)
            if not isinstance(section, list) or current_list_item is None:
                raise ValueError("Invalid YAML list indentation.")
            if ":" not in stripped:
                raise ValueError("Invalid YAML list mapping entry.")
            key, value = stripped.split(":", 1)
            current_list_item[key.strip()] = _coerce_scalar(value.strip())
            continue

        raise ValueError("Unsupported YAML structure.")

    if root_list is not None and not root_map:
        return root_list
    return root_map


def _read_config_payload(path: str | Path) -> Any:
    """Read raw config payload from JSON or YAML file."""
    config_path = Path(path)
    suffix = config_path.suffix.lower()
    content = config_path.read_text(encoding="utf-8")

    if suffix == ".json":
        return json.loads(content)

    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            _ = exc
            return _parse_simple_yaml(content)
        return yaml.safe_load(content)

    raise ValueError(f"Unsupported config extension: {suffix}")


def _validate_and_build(payload: Mapping[str, Any]) -> ExperimentConfig:
    """Validate raw mapping and build ``ExperimentConfig``."""
    missing = [key for key in _REQUIRED_KEYS if key not in payload]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    population_size = int(payload["population_size"])
    generations = int(payload["generations"])
    mutation_rate = float(payload["mutation_rate"])
    environment = str(payload["environment"])
    seed = int(payload["seed"])

    if population_size <= 0:
        raise ValueError("population_size must be > 0")
    if generations < 0:
        raise ValueError("generations must be >= 0")
    if not 0.0 <= mutation_rate <= 1.0:
        raise ValueError("mutation_rate must be in [0.0, 1.0]")
    if not environment:
        raise ValueError("environment must be non-empty")

    extras = {k: v for k, v in payload.items() if k not in _REQUIRED_KEYS}

    return ExperimentConfig(
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
        environment=environment,
        seed=seed,
        extras=extras,
    )
