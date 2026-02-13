"""Main experiment manager desktop window composed from modular panels."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from configs.loader import ExperimentConfig
from core.experiment_coordinator import ExperimentCoordinator
from core.simulation_runner_api import SimulationRunnerAPI
from gui.comparison_panel import ComparisonPanel
from gui.experiment_panel import ExperimentPanel
from gui.experiments_table_panel import ExperimentsTablePanel
from gui.leaderboard_panel import LeaderboardPanel
from gui.live_simulation_panel import LiveSimulationPanel
from gui.metrics_panel import MetricsPanel
from gui.options_panel import OptionsPanel
from gui.wandering_agents_adv_panel import WanderingAgentsAdvPanel

LOGGER = logging.getLogger(__name__)

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMainWindow, QSplitter, QTabWidget, QWidget, QVBoxLayout
except ModuleNotFoundError:  # pragma: no cover
    QMainWindow = object  # type: ignore


class MainWindow(QMainWindow):
    """Coordinates panel interactions while preserving API-only data flow."""

    def __init__(self, runner: SimulationRunnerAPI) -> None:
        super().__init__()
        self.runner = runner
        self.coordinator = ExperimentCoordinator(base_dir="experiments")
        self._active_experiment_id: str | None = None
        self._metrics_bound_experiment_id: str | None = None
        self._metrics_last_signature: tuple[int, tuple[str, ...], tuple[tuple[str, float], ...]] | None = None
        self._analysis_pool = ThreadPoolExecutor(max_workers=2)

        self.experiment_panel = ExperimentPanel()
        self.experiments_table = ExperimentsTablePanel()
        self.live_panel = LiveSimulationPanel()
        self.metrics_panel = MetricsPanel()
        self.options_panel = OptionsPanel()
        self.leaderboard_panel = LeaderboardPanel()
        self.comparison_panel = ComparisonPanel()
        self.wandering_panel = WanderingAgentsAdvPanel()

        if QMainWindow is object:
            return

        self.setWindowTitle("Experiment Manager")

        experiments_container = QWidget()
        experiments_layout = QVBoxLayout(experiments_container)
        experiments_layout.addWidget(self.experiment_panel)
        experiments_layout.addWidget(self.experiments_table)

        live_container = QWidget()
        live_layout = QVBoxLayout(live_container)
        split = QSplitter()
        split.addWidget(self.live_panel)
        split.addWidget(self.metrics_panel)
        split.setSizes([700, 400])
        live_layout.addWidget(split)

        tabs = QTabWidget()
        tabs.addTab(experiments_container, "Experiments")
        tabs.addTab(live_container, "Live Run")
        tabs.addTab(self.leaderboard_panel, "Leaderboard")
        tabs.addTab(self.comparison_panel, "Comparison")
        tabs.addTab(self.wandering_panel, "Wandering Agents")
        tabs.addTab(self.options_panel, "Options")
        self.setCentralWidget(tabs)

        self.experiment_panel.run_requested.connect(self._start_experiment)

        self.experiments_table.view_metrics_requested.connect(self._select_for_metrics)
        self.experiments_table.render_requested.connect(self._select_for_render)
        self.experiments_table.stop_requested.connect(self._stop_selected)
        self.experiments_table.delete_requested.connect(self._delete_selected)
        self.experiments_table.export_requested.connect(self._export_selected)
        self.experiments_table.selected_experiment_changed.connect(self._select_active_experiment)

        self.live_panel.on_start = self._start_from_current_form
        self.live_panel.on_pause = self._pause_active
        self.live_panel.on_resume = self._resume_active
        self.live_panel.on_step = self._step_active
        self.live_panel.on_stop = self._stop_active
        self.live_panel.on_reset = self._reset_active
        self.live_panel.on_speed = self._set_active_speed

        self.wandering_panel.on_start = self._start_from_current_form
        self.wandering_panel.on_pause = self._pause_active
        self.wandering_panel.on_resume = self._resume_active
        self.wandering_panel.on_step = self._step_active
        self.wandering_panel.on_stop = self._stop_active
        self.options_panel.on_speed_changed = self._set_active_speed

        self.comparison_panel.compare_btn.clicked.connect(self._compute_comparison_async)
        self.comparison_panel.export_btn.clicked.connect(self.comparison_panel.export_overlay)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_live_views)
        self._refresh_timer.start(200)

    def _start_from_current_form(self) -> None:
        self.experiment_panel.emit_run_request()

    def _start_experiment(self, request: object) -> None:
        try:
            if isinstance(request, ExperimentConfig):
                experiment_id = self.coordinator.start_experiment(request)
            elif isinstance(request, dict):
                mode = str(request.get("mode", "legacy"))
                if mode == "plugin":
                    config_path = str(request.get("config_path", "")).strip()
                    steps = int(request.get("steps", 200))
                    runtime_overrides = request.get("runtime_overrides", {})
                    experiment_id = self.coordinator.start_plugin_experiment(
                        config_path=config_path,
                        steps=steps,
                        runtime_overrides=runtime_overrides if isinstance(runtime_overrides, dict) else None,
                    )
                else:
                    config = request.get("config")
                    if not isinstance(config, ExperimentConfig):
                        raise ValueError("Legacy run request missing ExperimentConfig payload.")
                    experiment_id = self.coordinator.start_experiment(config)
            else:
                raise ValueError("Unsupported run request payload.")
        except Exception as exc:
            LOGGER.exception("Failed to start experiment: %s", exc)
            self.experiment_panel.status.setText(f"Failed to start experiment: {exc}")
            return

        self._active_experiment_id = experiment_id
        self._metrics_bound_experiment_id = None
        self._metrics_last_signature = None
        self.metrics_panel.set_history([])
        LOGGER.info("Started experiment %s", experiment_id)

    def _pause_active(self) -> None:
        if self._active_experiment_id:
            self.coordinator.pause_experiment(self._active_experiment_id)

    def _resume_active(self) -> None:
        if self._active_experiment_id:
            self.coordinator.resume_experiment(self._active_experiment_id)

    def _step_active(self) -> None:
        if self._active_experiment_id:
            experiment_id = self._active_experiment_id
            was_paused = self.coordinator.is_experiment_paused(experiment_id)
            if not was_paused:
                self.coordinator.pause_experiment(experiment_id)
            ok = self.coordinator.step_experiment(experiment_id, timeout=5.0)
            if not ok:
                self.experiment_panel.status.setText("Step request timed out or is unsupported for this run.")
            elif not was_paused:
                self.coordinator.resume_experiment(experiment_id)

    def _stop_active(self) -> None:
        if self._active_experiment_id:
            self.coordinator.stop_experiment(self._active_experiment_id)

    def _reset_active(self) -> None:
        self._stop_active()
        self._start_from_current_form()

    def _set_active_speed(self, multiplier: float) -> None:
        self.options_panel.set_speed(multiplier)
        if self._active_experiment_id:
            self.coordinator.set_experiment_speed(self._active_experiment_id, multiplier)

    def _select_for_metrics(self, experiment_ids: list[str]) -> None:
        if not experiment_ids:
            return
        self._active_experiment_id = experiment_ids[0]

    def _select_for_render(self, experiment_ids: list[str]) -> None:
        if not experiment_ids:
            return
        self._active_experiment_id = experiment_ids[0]

    def _select_active_experiment(self, experiment_id: str) -> None:
        normalized = str(experiment_id).strip()
        if not normalized:
            return
        if normalized == self._active_experiment_id:
            return
        self._active_experiment_id = normalized
        self._metrics_bound_experiment_id = None
        self._metrics_last_signature = None

    def _export_selected(self, experiment_ids: list[str]) -> None:
        for experiment_id in experiment_ids:
            self.coordinator.export_experiment(experiment_id, Path("experiments") / "exports")

    def _stop_selected(self, experiment_ids: list[str]) -> None:
        for experiment_id in experiment_ids:
            self.coordinator.stop_experiment(experiment_id)

    def _delete_selected(self, experiment_ids: list[str]) -> None:
        for experiment_id in experiment_ids:
            deleted = self.coordinator.delete_experiment(experiment_id, delete_artifacts=True)
            if deleted and experiment_id == self._active_experiment_id:
                self._active_experiment_id = None
                self._metrics_bound_experiment_id = None
                self._metrics_last_signature = None
                self.metrics_panel.set_history([])
                self.wandering_panel.update_state({}, simulation_name=None)

    def _compute_comparison_async(self) -> None:
        experiment_ids = self.comparison_panel.selected_experiment_ids()
        metric_keys = self.comparison_panel.selected_metric_keys()
        if not experiment_ids:
            return

        def job() -> dict:
            return self.coordinator.comparison(experiment_ids, metric_keys=metric_keys)

        future = self._analysis_pool.submit(job)

        def on_done(done) -> None:
            try:
                overlay = done.result()
            except Exception as exc:
                LOGGER.exception("Comparison compute failed: %s", exc)
                return

            if QMainWindow is object:
                self.comparison_panel.show_overlay(overlay)
                return

            QTimer.singleShot(0, lambda value=overlay: self.comparison_panel.show_overlay(value))

        future.add_done_callback(on_done)

    def _refresh_live_views(self) -> None:
        rows = self.coordinator.list_experiments()
        self.experiments_table.update_rows(rows)
        self.leaderboard_panel.update_rows(rows)
        self.comparison_panel.update_experiments(rows)

        if self._active_experiment_id:
            state = self.coordinator.get_render_state(self._active_experiment_id)
            history = self.coordinator.get_metrics_history(self._active_experiment_id)
            active_row = next((r for r in rows if r.get("experiment_id") == self._active_experiment_id), None)
            if isinstance(active_row, dict):
                active_sim = str(active_row.get("simulation", state.get("simulation", "")))
            else:
                active_sim = str(state.get("simulation", ""))
            self.live_panel.update_render_state(state)
            self.wandering_panel.update_state(state, simulation_name=active_sim)
            if history:
                generation = len(history) - 1
                total = int(
                    next(
                        (
                            r.get("steps", r.get("generations", generation + 1))
                            for r in rows
                            if r.get("experiment_id") == self._active_experiment_id
                        ),
                        generation + 1,
                    )
                )
                row_status = str(active_row.get("status", "")) if isinstance(active_row, dict) else ""
                self.live_panel.update_generation(generation, total, status=row_status if row_status else None)
                latest_row = history[-1] if isinstance(history[-1], dict) else {}
                latest_items = tuple(sorted((str(k), float(v)) for k, v in latest_row.items() if _is_floatable(v)))
                signature = (
                    len(history),
                    tuple(sorted(str(k) for k in latest_row.keys())),
                    latest_items,
                )
                if self._metrics_bound_experiment_id != self._active_experiment_id or signature != self._metrics_last_signature:
                    self.metrics_panel.set_history(list(history))
                    self._metrics_bound_experiment_id = self._active_experiment_id
                    self._metrics_last_signature = signature
            else:
                if self._metrics_bound_experiment_id != self._active_experiment_id and self.metrics_panel.history:
                    self.metrics_panel.set_history([])
                self._metrics_bound_experiment_id = self._active_experiment_id
                self._metrics_last_signature = None

    def closeEvent(self, event):  # type: ignore[override]
        self.coordinator.stop_all()
        self._analysis_pool.shutdown(wait=False)
        return super().closeEvent(event)


def _is_floatable(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
