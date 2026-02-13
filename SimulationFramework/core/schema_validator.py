"""Schema validation utilities for simulation plugin parameters."""

from __future__ import annotations

import warnings
from typing import Any, Mapping


class SchemaValidationError(ValueError):
    """Raised when simulation params fail schema validation."""


def _type_name(tp: type[Any]) -> str:
    return tp.__name__


def validate_simulation_params(
    params: dict[str, Any],
    schema_module: Any,
    simulation_name: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Validate simulation params against plugin schema.

    Applies defaults, validates required fields and exact types, and handles
    unknown parameters as warnings or errors depending on ``strict``.
    """
    required: Mapping[str, type[Any]] = getattr(schema_module, "REQUIRED_PARAMS", {})
    defaults: Mapping[str, Any] = getattr(schema_module, "DEFAULTS", {})
    optional: Mapping[str, type[Any]] = getattr(schema_module, "OPTIONAL_PARAMS", {})

    if not isinstance(required, Mapping) or not isinstance(defaults, Mapping) or not isinstance(optional, Mapping):
        raise SchemaValidationError(
            f"Simulation '{simulation_name}' schema must define REQUIRED_PARAMS, DEFAULTS, OPTIONAL_PARAMS mappings."
        )

    merged = dict(defaults)
    merged.update(params)

    for key, expected_type in required.items():
        if key not in merged:
            raise SchemaValidationError(
                f"Simulation '{simulation_name}' missing required parameter '{key}'."
            )
        if type(merged[key]) is not expected_type:
            raise SchemaValidationError(
                f"Parameter '{key}' expected {_type_name(expected_type)}, got {type(merged[key]).__name__}."
            )

    for key, expected_type in optional.items():
        if key in merged and type(merged[key]) is not expected_type:
            raise SchemaValidationError(
                f"Parameter '{key}' expected {_type_name(expected_type)}, got {type(merged[key]).__name__}."
            )

    allowed = set(required) | set(optional) | set(defaults)
    extras = [key for key in merged if key not in allowed]
    if extras:
        message = (
            f"Unknown parameter(s) {extras} for simulation '{simulation_name}'."
        )
        if strict:
            raise SchemaValidationError(message)
        warnings.warn(message, stacklevel=2)

    return merged
