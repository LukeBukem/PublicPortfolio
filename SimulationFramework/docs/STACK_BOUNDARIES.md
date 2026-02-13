# Stack Boundaries and Module Map

This project intentionally keeps two compatible stacks.

## Generation stack

Purpose:
- deterministic generation-based evolution
- SQLite metrics logging and plotting
- experiment manager live sessions

Primary modules:
- `engine/`
- `agents/`
- `environment/`
- `evolution/`
- `configs/loader.py`
- `main.py`
- `cli/main.py` (`run`, `batch`, `plot`)
- `gui/`

Config schema:
- loaded by `configs.loader.ConfigLoader`
- requires `population_size`, `generations`, `mutation_rate`, `environment`, `seed`

## Plugin/runtime stack

Purpose:
- plugin simulation discovery
- checkpointing/replay/time-travel
- render-state streaming
- desktop replay/live viewer

Primary modules:
- `core/plugin_registry.py`
- `core/config_loader.py`
- `core/simulator.py`
- `simulations/`
- `streaming/`
- `core/replay.py`
- `ui_desktop/`

Config schema:
- loaded by `core.config_loader.load_config`
- requires top-level sections `simulation`, `params`, `evolution`, `logging`

## Shared stack map utilities

- `core/stack_map.py` provides:
  - stack descriptors (`describe_stacks`)
  - config routing (`load_stack_config`)

GUI config loading now uses `load_stack_config` so users can select either config format from one panel.

## Extension points

Generation stack:
- Register new factories in `engine/component_registry.py` for:
  - agents
  - environments
  - evolution strategies

Plugin/runtime stack:
- Add plugin package under `simulations/<name>/` with:
  - `sim.py`
  - `config_schema.py`
  - optional `renderer_adapter.py`

## Non-goals

- Stacks are not merged into one simulator.
- Backward compatibility is preserved for existing CLI commands and config files.
