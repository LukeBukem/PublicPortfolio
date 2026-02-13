# Evolution-Simulation Code Review & Contributor Guide

## Executive Summary

This repository currently contains **two complementary simulation stacks**:

1. **Generation-based evolutionary stack** (used by CLI `evo run/batch/plot` and desktop Experiment Manager):
   - `engine/` + `agents/` + `environment/` + `evolution/` + `configs/loader.py` + `main.py`.
2. **Plugin runtime stack** (used for simulation plugin architecture, render streaming, replay/checkpointing):
   - `core/` + `simulations/` + `streaming/` + `data/checkpoint_store.py` + `core/config_loader.py`.

The design intent is modular and extensible, with deterministic behavior as a first-class requirement. The code is generally well-factored around interfaces, with extensive tests across lifecycle, CLI, plugin loading, replay/checkpointing, GUI backend coordination, and rendering serialization.

---

## High-Level File Structure (by responsibility)

- `agents/`: agent + genome interfaces and baseline concrete agents (`RandomAgent`, `WanderAgent`).
- `environment/`: environment interface plus concrete environments (`dummy`, `grid`, `wander`).
- `evolution/`: strategy interface + implementations (`identity`, GA).
- `engine/`: generation-loop simulator orchestration.
- `main.py`: object graph wiring for generation-based stack.
- `configs/loader.py`: experiment config loader for generation-based stack.
- `data/logger.py`: SQLite experiment metadata + generation metrics.
- `cli/main.py`: command wrapper around `main.build_components` and plotting.
- `visualization/plotting.py`: experiment plotting from persisted SQLite metrics.

- `core/plugin_registry.py`: runtime plugin discovery (`simulations.<name>`).
- `core/config_loader.py`: strict schema-validated plugin runtime config loader.
- `core/simulator.py`: plugin-driven step loop, event publishing, checkpoint emission.
- `core/checkpointing.py`, `data/checkpoint_store.py`, `core/replay.py`, `core/replay_loader.py`: deterministic replay infrastructure.
- `streaming/`: render-state serialization + websocket broadcasting.
- `simulations/base_simulation.py` + `simulations/example_sim/`: simulation plugin contract + sample plugin.

- `core/experiment_coordinator.py`, `core/live_session.py`, `gui/`, `ui_desktop/`: GUI orchestration and live-session management.
- `tests/`: broad unit/integration coverage for CLI, plugin runtime, lifecycle controls, replay, rendering, config handling, and GUI backend services.

---

## Scope, Contracts, and Module Boundaries

### 1) Agent, Environment, Evolution interfaces

The architecture is correctly contract-driven:

- `agents.base.Agent` defines `act`, `get_genome`, `set_genome`; `observe` has a safe passthrough default.
- `environment.base.Environment` defines `reset`, `step`, `observe`, with convenience wrappers (`get_observations`, `apply_actions`) and optional `evaluate_fitness`.
- `evolution.base.EvolutionStrategy` defines one core method: `evolve(population, fitness)` with explicit invariants.

**Practical consequence:** new behavior should be implemented at concrete class level without changing simulator orchestration logic.

### 2) Two config systems (important)

There are two distinct loaders with different schemas:

- `configs/loader.py` handles simple experiment configs (`population_size`, `generations`, `mutation_rate`, etc.) for the generation stack.
- `core/config_loader.py` handles plugin-runtime configs (`simulation`, `params`, `evolution`, `logging`) with schema-driven validation.

**Contributor caution:** do not mix these schemas; pick the stack first, then the matching loader.

### 3) Two simulator implementations (intentional but easy to confuse)

- `engine/simulator.py`: generation-level lifecycle (observe → act → apply actions → fitness → evolve → log metrics).
- `core/simulator.py`: plugin step-loop runtime with event bus + checkpoints + replay support.

**Contributor caution:** if you are building evolutionary behavior, modify the `engine` path; if building plugin/stream/replay capabilities, modify the `core` path.

---

## Behavior & Data Flow

### Generation-based run path

1. CLI loads config using `configs/loader.py`.
2. `main.build_components` wires environment, initial population, and evolution strategy.
3. `engine.Simulator.run` iterates generations, updating population each generation.
4. `data.SimulationLogger` persists experiment metadata and per-generation metrics.
5. `visualization.plotting` reads DB and emits chart artifacts.

### Plugin-runtime path

1. `core/config_loader.load_config` validates runtime config + simulation params schema.
2. `core/plugin_registry` resolves simulation class from `simulations/` packages.
3. `core.Simulator.run` executes step loop and emits render/checkpoint events.
4. `streaming` serializes/broadcasts render state.
5. Replay/checkpoint modules enable deterministic restore and fast-forward.

---

## Constraints and Invariants You Must Preserve

1. **Determinism:** seed-driven behavior is expected in both stacks.
2. **Population size invariance:** evolution outputs must match input population length.
3. **Metric robustness:** simulator guards against missing fitness by fallback paths (rewards or RNG default).
4. **Persistence contract:** SQLite schema in `data/logger.py` is relied on by CLI plotting and tests.
5. **Plugin contract:** each simulation plugin must expose `SIMULATION_NAME` and `SimulationClass`, and class must satisfy `Simulation` interface.
6. **Render payload discipline:** render states should remain JSON-serializable and bounded in size.
7. **Thread-safety in live sessions:** coordinator/session interactions are lock + event based; avoid GUI-thread blocking code.

---

## Strengths Observed in the Codebase

- Clean interface-first decomposition in core simulation primitives.
- Good use of deterministic RNG patterns and replay architecture.
- CLI is a thin wrapper over reusable runtime components.
- Plugin discovery and schema validation are explicit and test-backed.
- Live experiment coordination keeps orchestration out of GUI widgets.
- Tests cover many integration seams, reducing regression risk.

---

## Risks / Complexity Hotspots

1. **Dual-stack conceptual overhead**: contributors can accidentally edit the wrong simulator/config path.
2. **Documentation drift risk**: `FILE_STRUCTURE.md` is outdated versus real repository shape.
3. **Split UI packages (`gui/` and `ui_desktop/`)**: likely historical layering that can confuse ownership boundaries.
4. **Error handling asymmetry**: plugin runtime wraps failures in `SimulatorRuntimeError`; generation stack uses more direct exceptions.

---

## How to Safely Add New Features

### A) Add a new environment (generation stack)

1. Implement `Environment` methods in `environment/<new_env>.py`.
2. Add selection branch in `main.build_components`.
3. Ensure observations and fitness map are deterministic under seed.
4. Add tests in `tests/` for reset/step/fitness behavior and simulator integration.

### B) Add a new agent/genome behavior

1. Extend `Genome` and/or concrete genome classes.
2. Implement an `Agent` subclass using explicit `act` behavior.
3. Ensure compatibility with evolution strategy mutation/crossover expectations.
4. Add coverage for deterministic actions under fixed RNG.

### C) Add a new evolution strategy

1. Implement `EvolutionStrategy.evolve` in `evolution/<strategy>.py`.
2. Preserve population length and deterministic RNG usage.
3. Add wiring in `main.build_components` via config key.
4. Add tests for selection/mutation correctness and mutation ratio metrics.

### D) Add a new plugin simulation (plugin stack)

1. Create `simulations/<sim_name>/` package with:
   - `sim.py` exposing `SIMULATION_NAME` and `SimulationClass`.
   - `config_schema.py` with required/default/optional params.
   - Optional `renderer_adapter.py` for richer render state mapping.
2. Keep plugin state instance-local; avoid global mutable state.
3. Add plugin config-loader + simulator run tests mirroring `test_plugin_architecture.py`.

### E) Add new metrics end-to-end

1. Emit metric in simulator/plugin output.
2. Ensure persistence path stores/retrieves metric (or dynamic payload where supported).
3. Surface in analytics/coordinator overlays.
4. Add plotting/GUI display usage only through persisted metrics flow, not hidden in-memory coupling.

---

## Recommended Refactoring Roadmap (low-risk)

1. Add a top-level architecture map clarifying **which entrypoints use which stack**.
2. Refresh `FILE_STRUCTURE.md` to match current tree.
3. Introduce a shared naming convention doc for "generation stack" vs "plugin stack".
4. Add a short contributor checklist in README for adding env/agent/evolution/plugin modules.

---

## Quick Mental Model for New Contributors

If your feature is about **evolution over generations and SQLite metrics for `evo run`**, work in:
- `configs/loader.py` + `main.py` + `engine/` + `environment/` + `agents/` + `evolution/`.

If your feature is about **simulation plugins, streaming, replay/checkpoints, render events**, work in:
- `core/` + `simulations/` + `streaming/` + replay/checkpoint modules.

This distinction alone prevents most onboarding mistakes in this repository.
