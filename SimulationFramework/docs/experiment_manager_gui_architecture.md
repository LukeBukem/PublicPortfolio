# Experiment Manager Desktop GUI Architecture

This desktop module is a **thin orchestration layer** that controls simulation execution, rendering, and analytics without embedding simulation business logic in widgets.

## Architecture map (ASCII UML-style)

```text
+----------------------------------------+
| gui/main_window.py                     |
| - wires panel signals                  |
| - routes background updates            |
+-----------------+----------------------+
                  |
      +-----------+------------+------------------------------+
      | GUI Panels                                            |
      |-------------------------------------------------------|
      | experiment_panel          (load/edit config)          |
      | experiments_table_panel   (multi-exp table + actions) |
      | live_simulation_panel     (start/pause/stop/render)   |
      | metrics_panel             (live metrics + export)      |
      | leaderboard_panel         (rank/filter/sort)           |
      | comparison_panel          (overlays + mean±std)        |
      | playback_panel            (replay controls)            |
      +-----------+------------+------------------------------+
                  |
                  v
+-----------------+----------------------+      +-----------------------------+
| core/experiment_coordinator.py         |----->| core/live_session.py        |
| - manages many concurrent sessions     |      | - one background run loop   |
| - keeps in-memory experiment records   |      | - emits generation updates  |
| - leaderboard/comparison/export APIs   |      +--------------+--------------+
+-----------------+----------------------+                     |
                  |                                            v
                  |                                 +----------+--------------+
                  +-------------------------------->| engine/simulator.py     |
                                                    +-------------------------+
```

## Runtime behavior

- Multiple experiments can run concurrently through `ExperimentCoordinator.start_experiment`.
- `MainWindow` refreshes table/leaderboard/comparison views on a timer, so running experiments appear live.
- Leaderboard and comparison analytics are performed in coordinator/analytics modules, not in widget code.
- Simulation control operations (pause/resume/stop/speed) are routed through coordinator methods.

## Key capabilities

- **Multi-experiment table** with sort/filter and contextual actions (View Metrics, Render Simulation, Export Data).
- **Live leaderboard** sortable by configurable metric and filterable by environment.
- **Comparison overlays** for selected runs with mean±std envelopes.
- **Derived analytics** including improvement rate, peak generation, mutation impact, and diversity trend.
- **Export** of full per-experiment datasets to CSV and JSON.

## Extension points

- Add new metrics: emit from simulator metrics payload; analytics/GUI consume dynamic keys.
- Add new renderers: customize `LiveSimulationSession` render-state builder or attach environment-specific adapters.
- Add experiment types: provide compatible `ExperimentConfig` + simulator build path; coordinator remains unchanged.
- Add advanced visualizers: register richer plotting widgets in comparison/metrics panels without changing orchestration services.

## Non-developer usage

1. Launch GUI: `python -m gui.app`
2. **Experiments** tab:
   - load a config from `configs/`
   - adjust population/generations/mutation/seed/environment
   - click **Run Selected Experiment** (repeat to run multiple concurrently)
3. Use experiment table actions:
   - **View Metrics** to focus analytics
   - **Render Simulation** to focus live render
   - **Export Data** for CSV/JSON output
4. **Leaderboard** tab: sort by metric and filter by environment.
5. **Comparison** tab: multi-select experiments, choose metric toggles, compare overlays.

## Constraints honored

- No simulation logic in GUI widgets.
- No GUI-thread blocking run loop for simulation or heavy comparisons.
- No hardcoded single experiment/agent/environment flow.
- No global mutable state shared outside coordinator/session instances.
