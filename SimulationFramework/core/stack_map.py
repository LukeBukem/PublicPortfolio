"""Stack descriptors and config routing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configs.loader import ConfigLoader, ExperimentConfig
from core.config_loader import ConfigValidationError, load_config as load_plugin_config


@dataclass(frozen=True)
class StackDescriptor:
    """Human-readable stack map entry."""

    name: str
    purpose: str
    entrypoints: tuple[str, ...]
    config_loader: str


STACKS: dict[str, StackDescriptor] = {
    "generation": StackDescriptor(
        name="generation",
        purpose="Deterministic generation-based evolution with SQLite metrics logging.",
        entrypoints=("main.py", "cli/main.py", "gui/app.py"),
        config_loader="configs.loader.ConfigLoader",
    ),
    "plugin": StackDescriptor(
        name="plugin",
        purpose="Plugin/runtime stack for replay, checkpointing, and render streaming.",
        entrypoints=("core/simulator.py", "ui_desktop/app.py"),
        config_loader="core.config_loader.load_config",
    ),
}


class StackConfigLoadError(ValueError):
    """Raised when a config cannot be mapped to either stack."""


def describe_stacks() -> dict[str, StackDescriptor]:
    """Return immutable stack descriptor map."""
    return dict(STACKS)


def load_stack_config(path: str | Path) -> tuple[str, Any]:
    """Load a config and return (stack_name, parsed_config)."""
    config_path = str(path)
    gen_error: Exception | None = None
    plugin_error: Exception | None = None

    try:
        return "generation", ConfigLoader.load(config_path)
    except Exception as exc:
        gen_error = exc

    try:
        return "plugin", load_plugin_config(config_path)
    except Exception as exc:
        plugin_error = exc

    raise StackConfigLoadError(
        f"Config '{config_path}' did not match generation or plugin schemas. "
        f"generation_error={gen_error!r}; plugin_error={plugin_error!r}"
    )


def validate_plugin_stack_config(path: str | Path) -> dict[str, Any]:
    """Validate config explicitly against plugin stack loader."""
    try:
        return load_plugin_config(str(path))
    except ConfigValidationError:
        raise
