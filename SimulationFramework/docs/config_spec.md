# Config Specification

This document defines the runtime config format for the plugin-driven simulator.

## Top-level structure

```yaml
simulation: <simulation_name>

params:
  <param_name>: <value>
  ...

evolution:
  population_size: int
  mutation_rate: float
  crossover_rate: float
  elite_fraction: float
  random_seed: int

logging:
  log_interval: int
  checkpoint_interval: int
  experiment_name: str
```

## Validation rules

- `simulation` must resolve through the plugin registry.
- `params` are validated against `simulations/<name>/config_schema.py`.
- `DEFAULTS` are applied before validation.
- Unknown params fail in strict mode; can warn in non-strict mode.
- `evolution` and `logging` sections are required and strictly typed.

## Simulation schema format

Each plugin must provide `config_schema.py` with:

```python
REQUIRED_PARAMS = {
    "world_size": int,
    "num_agents": int,
}

DEFAULTS = {
    "world_size": 10,
    "num_agents": 5,
}

OPTIONAL_PARAMS = {
    "food_spawn_rate": float,
}
```

## Example config (example_sim)

```yaml
simulation: example_sim

params:
  world_size: 25
  num_agents: 50

evolution:
  population_size: 200
  mutation_rate: 0.02
  crossover_rate: 0.7
  elite_fraction: 0.05
  random_seed: 1234

logging:
  log_interval: 10
  checkpoint_interval: 100
  experiment_name: "baseline_test"
```

## Multiple simulations (illustrative)

A second plugin can define different params without core changes:

```yaml
simulation: maze_world
params:
  map_size: 64
  obstacle_density: 0.2
# evolution/logging sections unchanged
```

Only `simulations/maze_world/config_schema.py` needs to define the schema.
