"""Dynamic simulation plugin discovery and lookup."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Type

from simulations.base_simulation import Simulation
import simulations

_DISCOVERED: dict[str, Type[Simulation]] | None = None


class SimulationPluginNotFoundError(LookupError):
    """Raised when requested simulation plugin cannot be resolved."""


def discover_simulations() -> dict[str, Type[Simulation]]:
    """Discover simulation plugins from the ``simulations`` package."""
    global _DISCOVERED
    if _DISCOVERED is not None:
        return dict(_DISCOVERED)

    discovered: dict[str, Type[Simulation]] = {}
    for module_info in pkgutil.iter_modules(simulations.__path__):
        if not module_info.ispkg:
            continue
        package_name = module_info.name
        if package_name.startswith("_"):
            continue

        plugin_module = None
        try:
            plugin_module = importlib.import_module(f"simulations.{package_name}")
        except Exception:
            plugin_module = None

        if plugin_module is None or not hasattr(plugin_module, "SIMULATION_NAME"):
            try:
                plugin_module = importlib.import_module(f"simulations.{package_name}.sim")
            except Exception:
                continue

        sim_name = getattr(plugin_module, "SIMULATION_NAME", None)
        sim_class = getattr(plugin_module, "SimulationClass", None)
        if isinstance(sim_name, str) and isinstance(sim_class, type) and issubclass(sim_class, Simulation):
            discovered[sim_name] = sim_class

    _DISCOVERED = discovered
    return dict(discovered)


def get_simulation_class(name: str) -> Type[Simulation]:
    """Return simulation class by name or raise descriptive error."""
    discovered = discover_simulations()
    if name in discovered:
        return discovered[name]

    available = ", ".join(sorted(discovered.keys())) or "<none>"
    raise SimulationPluginNotFoundError(
        f"Simulation plugin '{name}' not found. Available simulations: {available}"
    )
