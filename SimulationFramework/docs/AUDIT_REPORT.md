# Comprehensive Audit Report

Date: 2026-02-13  
Scope reviewed: `engine/`, `core/`, `agents/`, `environment/`, `evolution/`, `simulations/`, `streaming/`, `gui/`, `ui_desktop/`, `data/`, `configs/`

## Summary

The codebase is modular and test-oriented, but had several high-impact risks:

- stack boundary confusion (dual config loaders and dual simulators)
- missing factory/registry extension points in generation wiring
- GUI callback thread-safety hazards
- determinism bug in named RNG streams
- incomplete step-once control path and weak live-session error isolation
- manifest run orchestration always relying on mock worker behavior

Most high-severity issues listed below are now addressed.

## Findings

1. High - Non-stable named RNG seed derivation  
Location: `core/deterministic_rng.py`  
Issue: `hash((seed, name))` is process-salted and not stable across runs.  
Fix: replaced with deterministic SHA256 seed derivation.  
Status: Fixed.

2. High - GUI thread safety risk when updating comparison view  
Location: `gui/main_window.py`  
Issue: background future callback updated Qt widget from worker thread.  
Fix: marshaled update through `QTimer.singleShot(0, ...)` on UI loop.  
Status: Fixed.

3. High - No deterministic step-once acknowledgment API in generation simulator  
Location: `engine/simulator.py`  
Issue: missing RUNNING/PAUSED/STEPPING control state machine for step-based control.  
Fix: added control state machine, `request_step_once`, `run_controlled`, stop/pause/resume semantics, and step ACK event.  
Status: Fixed.

4. High - Generation stack wiring hardcoded in `main.py`  
Location: `main.py`  
Issue: environment/agent/evolution selection required editing core wiring.  
Fix: introduced factory/registry module (`engine/component_registry.py`) and switched `main.py` to registry-driven creation.  
Status: Fixed.

5. Medium - Live session callback failures could crash session loops  
Location: `core/live_session.py`, `core/live_plugin_session.py`  
Issue: callback exceptions were not isolated.  
Fix: added safe emit wrappers + explicit error events for run failures.  
Status: Fixed.

6. Medium - High-frequency update pressure could bloat history/UI workload  
Location: `core/live_session.py`, `core/live_plugin_session.py`, `core/experiment_coordinator.py`  
Issue: unbounded metric history growth and unthrottled update emission risked lag.  
Fix: throttled emit rate, bounded in-memory history with downsampling, persisted plugin metrics to jsonl.  
Status: Fixed.

7. Medium - Event bus could queue unbounded pending callbacks under load  
Location: `core/event_bus.py`  
Issue: ThreadPool executor task queue can grow unbounded.  
Fix: added semaphore-based pending-task cap (`max_pending`) and safe callback invocation.  
Status: Fixed.

8. Medium - Manifest orchestration did not tolerate worker failures  
Location: `core/experiment_manager.py`  
Issue: one worker exception could abort whole sweep result handling.  
Fix: per-future exception handling and failed run status persistence.  
Status: Fixed.

9. Medium - Manifest `config_path` ignored for worker execution  
Location: `core/experiment_manager.py`, `workers/simulation_worker.py`  
Issue: runs always used mock/stub worker logic.  
Fix: task now forwards `config_path`; worker executes real plugin simulation when provided, with fallback compatibility outputs.  
Status: Fixed (with compatibility fallback).

10. Medium - Replay cache did not keep metrics synchronized on cache hit  
Location: `core/replay.py`  
Issue: `current_metrics` became stale when state came from cache.  
Fix: added metrics cache and synchronized updates; added step alias API.  
Status: Fixed.

11. Medium - GUI metrics plot assumed fixed metric keys  
Location: `gui/metrics_panel.py`  
Issue: plugin metrics could miss expected keys and break plotting paths.  
Fix: dynamic metric normalization + safe defaulting for missing keys + export success/failure feedback.  
Status: Fixed.

12. Medium - Stack config routing duplicated/implicit  
Location: `gui/experiment_panel.py`  
Issue: ambiguous config detection and weak boundary messaging.  
Fix: introduced `core/stack_map.py` and routed GUI config loading through stack-aware helper.  
Status: Fixed.

13. Medium - CLI run path could leak logger on exceptions  
Location: `cli/main.py`  
Issue: logger close not guaranteed in error paths.  
Fix: `try/finally` around single-run execution.  
Status: Fixed.

14. Low - GUI dependency visibility incomplete in runtime deps  
Location: `requirements.txt`, `pyproject.toml`  
Issue: desktop GUI/stream deps not listed by default.  
Fix: added `PySide6`, `pyqtgraph`, `websockets`.  
Status: Fixed.

## Remaining Risks / Follow-up

1. Worker behavior duality remains by design  
- `workers/simulation_worker.py` still supports mock fallback when no `config_path` is provided, to preserve existing tests/workflows.

2. Metric persistence model differs by stack  
- generation live sessions use SQLite (`data/logger.py`), plugin live sessions currently persist JSONL in coordinator.
- a unified typed metrics backend could simplify cross-stack analytics.

3. `ui_desktop` and `gui` are still separate UIs  
- separation is preserved for backward compatibility; long-term convergence can reduce maintenance overhead.

## Test Coverage Added

- `tests/test_component_registry.py`
- `tests/test_stack_map.py`
- `tests/test_engine_simulator_control.py`

These focus on new factory/registry path, stack config routing, control-state stepping, and deterministic named RNG streams.
