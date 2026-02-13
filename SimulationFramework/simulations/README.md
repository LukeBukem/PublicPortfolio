# Simulation Plugin Guide

This folder contains plugin simulations loaded by `core/plugin_registry.py`.

## Plugin package layout

Create `simulations/<your_sim_name>/` with:

```text
simulations/
  your_sim_name/
    __init__.py
    sim.py
    config_schema.py
    renderer_adapter.py   # optional
```

## Required exports

### `sim.py`
- Define a class that subclasses `simulations.base_simulation.Simulation`
- Export:
  - `SIMULATION_NAME = "your_sim_name"`
  - `SimulationClass = YourSimulation`

### `config_schema.py`
Export all three mappings:
- `REQUIRED_PARAMS`
- `DEFAULTS`
- `OPTIONAL_PARAMS`

Example:

```python
REQUIRED_PARAMS = {
    "world_size": int,
    "num_agents": int,
}

DEFAULTS = {
    "world_size": 20,
    "num_agents": 50,
}

OPTIONAL_PARAMS = {
    "food_spawn_rate": float,
}
```

### `__init__.py`
Re-export symbols from `sim.py`:

```python
from .sim import SIMULATION_NAME, SimulationClass
```

## Start a new plugin simulation (exact steps)

### 1) Create a runtime config
Create `configs/my_plugin_run.yaml`:

```yaml
simulation: your_sim_name

params:
  world_size: 30
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

### 2) Validate + run the plugin

```bash
python -c "from pathlib import Path; from core.simulator import Simulator; from data.checkpoint_store import CheckpointStore; sim=Simulator('configs/my_plugin_run.yaml', checkpoint_store=CheckpointStore(), experiment_dir=Path('experiments/my_plugin_run')); metrics=sim.run(steps=120); print(metrics[-1])"
```

### 3) Replay checkpoints in desktop UI

```bash
python -m ui_desktop.app --replay experiments/my_plugin_run --config configs/my_plugin_run.yaml
```

## Optional renderer adapter

If you add `renderer_adapter.py`, expose:

```python
def build_render_state(simulator):
    ...
```

When present, `core/simulator.py` loads it automatically and publishes adapted render frames.

## Important constraints

- Keep all state instance-local in your simulation class (no globals).
- Keep `SIMULATION_NAME` unique.
- Ensure `get_render_state()` returns JSON-serializable data.
- Keep behavior deterministic for the same seed/config when possible.

## Behavior authoring

For behavior-focused implementation patterns, see `docs/PLUGIN_BEHAVIOR_GUIDE.md`.
For full world/agent/reproduction design workflow, see `docs/NEW_SIMULATION_DETAILED_GUIDE.md`.

## Concrete reference: `wandering_agents_adv`

Use `simulations/wandering_agents_adv/` as a complete example of:
- room/grid world state and per-step emission
- deterministic agent logic (`Eat > Pickup > Mate > Move`)
- hunger, inventory (`Hands`), and inheritable trait stats
- reproduction with configurable deviation
- dedicated GUI tab (`gui/wandering_agents_adv_panel.py`) using emitted JSON state

Starter config:
- `configs/wandering_agents_adv.yaml`

## Run wandering_agents_adv tests

From repository root:

```bash
python -m pytest tests/test_wandering_agents_adv_plugin.py -q
```

Optional GUI test (requires `PySide6`):

```bash
python -m pytest tests/test_wandering_agents_adv_gui.py -q
```

Focused live control regression test:

```bash
python -m pytest tests/test_experiment_coordinator.py -k pause_step_resume -q
```

