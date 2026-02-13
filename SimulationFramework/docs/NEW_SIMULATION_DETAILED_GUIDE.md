# New Simulation Guide (Detailed)

This guide covers how to build a new simulation, including world design, agent behavior, and reproduction behavior.

## 1) Choose your architecture path

- Use the generation stack when you want built-in evolution flow:
  - `agents/`, `environment/`, `evolution/`, `main.py`, `engine/simulator.py`
- Use the plugin stack when you want modular plugin simulations:
  - `simulations/<name>/`, `core/simulator.py`, `core/config_loader.py`

If you need direct control over world rules and rendering adapter contracts, plugin stack is usually the better long-term path.

## 2) World design checklist

Define these first:

1. State model
- What world state exists? Grid, resources, hazards, time, spatial bounds.
- What is per-agent state? Position, energy, inventory, alive/dead.

2. Transition rules
- How does one tick/step update world state?
- Which actions are legal?
- What are collision/resource/termination rules?

3. Observation contract
- What does each agent observe every step?
- Keep this stable and explicit. Avoid leaking hidden world internals by accident.

4. Reward or fitness contract
- In generation stack: environment should return rewards or `evaluate_fitness`.
- In plugin stack: expose numeric metrics and any per-agent scores you need for analysis.

5. Determinism
- For same seed and same config, transitions should be reproducible.
- Use provided RNG objects (`random.Random`) instead of global random state.

## 3) Agent behavior design checklist

Define behavior policy explicitly:

1. Input
- Observation shape and required keys.
- Validation behavior on malformed observations.

2. Output
- Action format (int, vector, structured command).
- Guaranteed to stay inside legal action space.

3. Strategy
- Reactive rules, stochastic exploration, memory/stateful policy, or genome-driven mapping.

4. Safety
- Always guard against empty action spaces.
- Raise clear exceptions for invalid input contracts.

## 4) Reproduction/evolution behavior checklist

### Generation stack (built-in evolution)

Use `EvolutionStrategy` implementations in `evolution/`.
Use `engine/component_registry.py` to register new agents/environments/strategies.

1. Selection
- Tournament, roulette, rank-based, elitist carry-over.

2. Crossover
- Parameter mixing, one-point/two-point, structure-aware merge.

3. Mutation
- Gaussian perturbation, random reset, probability schedules.

4. Invariants
- Output population size must match input size.
- Determinism for fixed RNG/seed.
- No hidden global mutable state.

### Plugin stack (plugin-owned dynamics)

`core/simulator.py` currently executes plugin `reset/step/get_metrics/get_render_state`; it does not run generic evolution operators for you. If reproduction is needed, implement it in plugin logic.

Recommended pattern:

1. Keep an internal population list in plugin state.
2. Compute fitness each step or episode.
3. Trigger reproduction on a cadence (every N steps/episodes).
4. Apply selection/crossover/mutation in plugin code.
5. Emit reproduction metrics (`offspring_count`, `survival_rate`, `mutation_ratio`) via `get_metrics()`.

## 5) Implementing a new plugin simulation

Create:

```text
simulations/
  my_sim/
    __init__.py
    sim.py
    config_schema.py
    renderer_adapter.py   # optional
```

### `sim.py`

Implement `Simulation` methods:

- `reset()`: initialize world + agents
- `step()`: apply world transition + behavior + optional reproduction cycle
- `get_metrics()`: return scalar metrics as `dict[str, float]`
- `get_render_state()`: return JSON-serializable frame
- `close()`: clean up

Export:

```python
SIMULATION_NAME = "my_sim"
SimulationClass = MySimulation
```

### `config_schema.py`

Provide:

```python
REQUIRED_PARAMS = {...}
DEFAULTS = {...}
OPTIONAL_PARAMS = {...}
```

## 6) Running your new simulation

Create config `configs/my_sim.yaml`:

```yaml
simulation: my_sim

params:
  world_size: 40
  num_agents: 80
  reproduction_interval: 20

evolution:
  population_size: 200
  mutation_rate: 0.02
  crossover_rate: 0.70
  elite_fraction: 0.05
  random_seed: 1234

logging:
  log_interval: 10
  checkpoint_interval: 25
  experiment_name: my_sim_run
```

Run:

```bash
python -c "from pathlib import Path; from core.simulator import Simulator; from data.checkpoint_store import CheckpointStore; sim=Simulator('configs/my_sim.yaml', checkpoint_store=CheckpointStore(), experiment_dir=Path('experiments/my_sim_run')); print(sim.run(steps=150)[-1])"
```

Replay in UI:

```bash
python -m ui_desktop.app --replay experiments/my_sim_run --config configs/my_sim.yaml
```

## 7) Integrating with GUI manager flow

`gui/experiment_panel.py` now supports loading plugin configs directly. When plugin config is loaded:

- the run request is routed as plugin mode
- coordinator starts `LivePluginSession`
- `Generations / Steps` field controls how many plugin steps run

Launch:

```bash
python -m cli.main gui
```

## 8) Testing checklist before shipping

1. Config validation
- invalid type in params fails with clear error
- unknown params behavior tested for strict/non-strict

2. Determinism
- same seed + same config => same metric sequence for fixed steps

3. Render stability
- `get_render_state()` always JSON-serializable
- agents always include positions or normalized fallback

4. Reproduction correctness
- population size/cadence rules honored
- mutation/crossover metrics sane and bounded

5. GUI run
- plugin config loads and starts from `gui.app`
- pause/resume/stop/speed controls work
