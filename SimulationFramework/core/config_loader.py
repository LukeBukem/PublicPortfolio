"""Top-level config loading and validation for plugin-driven simulator."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Mapping

from core.plugin_registry import get_simulation_class
from core.schema_validator import SchemaValidationError, validate_simulation_params


class ConfigValidationError(ValueError):
    """Raised when runtime config fails validation."""


_REQUIRED_TOP_LEVEL = {"simulation", "params", "evolution", "logging"}
_REQUIRED_EVOLUTION = {
    "population_size": int,
    "mutation_rate": float,
    "crossover_rate": float,
    "elite_fraction": float,
    "random_seed": int,
}
_REQUIRED_LOGGING = {
    "log_interval": int,
    "checkpoint_interval": int,
    "experiment_name": str,
}


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse minimal YAML subset used by project configs."""
    result: dict[str, Any] = {}
    current_top: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if indent == 0:
            if value == "":
                result[key] = {}
                current_top = key
            else:
                result[key] = _coerce_scalar(value)
                current_top = None
        else:
            if current_top is None or not isinstance(result.get(current_top), dict):
                raise ConfigValidationError("Invalid YAML structure in config file.")
            result[current_top][key] = _coerce_scalar(value)

    return result


def _load_yaml_or_raise(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigValidationError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    except ModuleNotFoundError:
        payload = _parse_simple_yaml(text)
    except Exception as exc:
        raise ConfigValidationError(f"Failed to parse YAML config '{path}': {exc}") from exc

    if not isinstance(payload, Mapping):
        raise ConfigValidationError("Top-level config must be a mapping.")
    return dict(payload)


def _validate_section(
    section_name: str,
    section_value: Any,
    required_fields: Mapping[str, type[Any]],
) -> dict[str, Any]:
    if not isinstance(section_value, Mapping):
        raise ConfigValidationError(f"Section '{section_name}' must be a mapping.")

    section = dict(section_value)
    missing = [key for key in required_fields if key not in section]
    if missing:
        raise ConfigValidationError(
            f"Section '{section_name}' missing required field(s): {missing}."
        )

    extras = [key for key in section if key not in required_fields]
    if extras:
        raise ConfigValidationError(
            f"Section '{section_name}' has unknown field(s): {extras}."
        )

    for key, expected_type in required_fields.items():
        if type(section[key]) is not expected_type:
            raise ConfigValidationError(
                f"Field '{section_name}.{key}' expected {expected_type.__name__}, got {type(section[key]).__name__}."
            )

    return section


def load_config(path: str, strict: bool = True) -> dict[str, Any]:
    """Load and validate YAML runtime configuration.

    Returns normalized config with keys:
    - simulation
    - simulation_config
    - evolution_config
    - logging_config
    - seed
    """
    config = _load_yaml_or_raise(Path(path))

    missing_top = [key for key in _REQUIRED_TOP_LEVEL if key not in config]
    if missing_top:
        raise ConfigValidationError(
            f"Missing required top-level section(s): {missing_top}."
        )

    extras_top = [key for key in config if key not in _REQUIRED_TOP_LEVEL]
    if extras_top:
        raise ConfigValidationError(
            f"Unknown top-level field(s): {extras_top}."
        )

    simulation_name = config.get("simulation")
    if not isinstance(simulation_name, str) or not simulation_name:
        raise ConfigValidationError("Field 'simulation' must be a non-empty string.")

    # registry lookup for descriptive plugin errors
    get_simulation_class(simulation_name)

    evolution_config = _validate_section("evolution", config["evolution"], _REQUIRED_EVOLUTION)
    logging_config = _validate_section("logging", config["logging"], _REQUIRED_LOGGING)

    raw_params = config["params"]
    if not isinstance(raw_params, Mapping):
        raise ConfigValidationError("Section 'params' must be a mapping.")

    schema_module_name = f"simulations.{simulation_name}.config_schema"
    try:
        schema_module = importlib.import_module(schema_module_name)
    except Exception as exc:
        raise ConfigValidationError(
            f"Could not load schema for simulation '{simulation_name}' ({schema_module_name})."
        ) from exc

    try:
        simulation_params = validate_simulation_params(
            params=dict(raw_params),
            schema_module=schema_module,
            simulation_name=simulation_name,
            strict=strict,
        )
    except SchemaValidationError as exc:
        raise ConfigValidationError(str(exc)) from exc

    # Expose evolution mutation rate to plugin params so simulations can use it
    # as their internal variation rate without duplicating config values.
    if "mutation_rate" not in simulation_params:
        simulation_params["mutation_rate"] = float(evolution_config.get("mutation_rate", 0.0))

    seed = int(evolution_config.get("random_seed", 0))
    return {
        "simulation": simulation_name,
        "simulation_config": simulation_params,
        "evolution_config": evolution_config,
        "logging_config": logging_config,
        "seed": seed,
    }
