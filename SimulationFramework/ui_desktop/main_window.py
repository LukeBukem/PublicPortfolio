"""Desktop dashboard main window (MVVM-oriented composition)."""

from __future__ import annotations

from typing import Any

from ui_desktop.controls_panel import ControlsPanel
from ui_desktop.metrics_panel import MetricsPanel
from ui_desktop.models.render_state_model import RenderStateModel
from ui_desktop.render_viewport import RenderViewport
from ui_desktop.timeline_panel import TimelinePanel

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover
    QMainWindow = object  # type: ignore


class MainWindow(QMainWindow):
    """Main dashboard layout: controls | viewport+timeline | metrics."""

    def __init__(self, model: RenderStateModel, data_client: Any) -> None:
        super().__init__()
        self.model = model
        self.data_client = data_client
        self.setWindowTitle("Evolution Simulation Dashboard")
        self.resize(1400, 900)

        self.viewport = RenderViewport()
        self.controls = ControlsPanel()
        self.metrics = MetricsPanel()
        self.timeline = TimelinePanel()

        if QMainWindow is object:
            return

        center = QWidget()
        root = QHBoxLayout(center)

        middle_col = QVBoxLayout()
        middle_col.addWidget(self.viewport, stretch=9)
        middle_col.addWidget(self.timeline, stretch=1)

        root.addWidget(self.controls, stretch=2)
        root.addLayout(middle_col, stretch=7)
        root.addWidget(self.metrics, stretch=2)
        self.setCentralWidget(center)

        self.model.subscribe(self._on_model_update)
        self.data_client.subscribe(self.model.update_state)

        self.controls.on_step_forward = lambda: getattr(self.data_client, "step_forward", lambda *_: None)(1)
        self.controls.on_step_backward = lambda: getattr(self.data_client, "step_backward", lambda *_: None)(1)
        self.controls.on_jump = lambda g: getattr(self.data_client, "jump_to_generation", lambda *_: None)(g)
        self.timeline.on_jump = lambda g: getattr(self.data_client, "jump_to_generation", lambda *_: None)(g)

        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: None)

    def _on_model_update(self, state: dict[str, Any]) -> None:
        self.viewport.set_render_state(state)
        self.metrics.update_metrics(state.get("metrics", {}))
        step = int(state.get("step_index", 0))
        self.timeline.set_range(max(step, 1_000))
        self.timeline.set_generation(step)
