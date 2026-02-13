# Plugin Behavior Guide (Plugin Stack)

This guide is for behavior implemented inside simulation plugins in `simulations/<name>/sim.py`.

## Target path

Use this guide when your simulation is started with `core.Simulator` and config files like `configs/plugin_example.yaml`.

## 1) Create plugin package

```text
simulations/
  my_plugin/
    __init__.py
    sim.py
    config_schema.py
    renderer_adapter.py  # optional
```

## 2) Implement behavior in `sim.py`

Your behavior lives inside `Simulation.step()` and the plugin's per-agent state.

Example skeleton:

```python
from __future__ import annotations

import random
from typing import Any

from simulations.base_simulation import Simulation


class MyPluginSimulation(Simulation):
    def __init__(self, params: dict[str, Any], rng: random.Random) -> None:
        super().__init__(params=params, rng=rng)
        self.world_size = int(params["world_size"])
        self.num_agents = int(params["num_agents"])
        self.step_count = 0
        self.agents: list[dict[str, float | int]] = []

    def reset(self) -> None:
        self.step_count = 0
        self.agents = [
            {"id": i, "x": float(self.rng.randrange(self.world_size)), "y": float(self.rng.randrange(self.world_size))}
            for i in range(self.num_agents)
        ]

    def step(self) -> None:
        for agent in self.agents:
            # Replace this with your behavior logic.
            agent["x"] = max(0.0, min(float(self.world_size - 1), float(agent["x"]) + self.rng.choice([-1.0, 0.0, 1.0])))
            agent["y"] = max(0.0, min(float(self.world_size - 1), float(agent["y"]) + self.rng.choice([-1.0, 0.0, 1.0])))
        self.step_count += 1

    def get_metrics(self) -> dict[str, float]:
        return {"step_count": float(self.step_count)}

    def get_render_state(self) -> dict[str, Any]:
        return {"agents": self.agents, "world_size": self.world_size, "step": self.step_count}

    def close(self) -> None:
        self.agents = []


SIMULATION_NAME = "my_plugin"
SimulationClass = MyPluginSimulation
```

## 3) Define plugin schema in `config_schema.py`

```python
REQUIRED_PARAMS = {
    "world_size": int,
    "num_agents": int,
}

DEFAULTS = {
    "world_size": 20,
    "num_agents": 30,
}

OPTIONAL_PARAMS = {
    "exploration_rate": float,
}
```

## 4) Create runtime config

Create `configs/my_plugin.yaml`:

```yaml
simulation: my_plugin

params:
  world_size: 40
  num_agents: 80

evolution:
  population_size: 200
  mutation_rate: 0.02
  crossover_rate: 0.70
  elite_fraction: 0.05
  random_seed: 1234

logging:
  log_interval: 10
  checkpoint_interval: 25
  experiment_name: my_plugin_run
```

## 5) Run plugin simulation

```bash
python -c "from pathlib import Path; from core.simulator import Simulator; from data.checkpoint_store import CheckpointStore; sim=Simulator('configs/my_plugin.yaml', checkpoint_store=CheckpointStore(), experiment_dir=Path('experiments/my_plugin_run')); result=sim.run(steps=100); print(result[-1])"
```

## 6) Optional replay and render adapter

Replay:

```bash
python -m ui_desktop.app --replay experiments/my_plugin_run --config configs/my_plugin.yaml
```

If you need structured UI rendering, add `renderer_adapter.py` with `build_render_state(simulator)`.

## 7) Behavior checklist

- Keep all plugin state inside the simulation instance.
- Use `self.rng` for deterministic behavior.
- Return numeric metrics (`dict[str, float]`) from `get_metrics()`.
- Keep render state JSON-serializable.
- Add tests similar to `tests/test_plugin_architecture.py`.

