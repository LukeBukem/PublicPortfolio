"""Live metrics visualization panel with optional plotting backend."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

try:
    from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class MetricsPanel(QWidget):
    """Tracks and visualizes key generation metrics in real-time."""

    _PREFERRED_METRIC_ORDER = (
        "population",
        "average_hunger",
        "average_lifespan_turns",
        "mean_fitness",
        "max_fitness",
        "diversity",
        "mutation_stats",
        "step_count",
    )
    _LABEL_OVERRIDES = {
        "population": "population",
        "average_hunger": "average hunger",
        "average_lifespan_turns": "average lifespan (in turns)",
        "mean_fitness": "mean fitness",
        "max_fitness": "max fitness",
        "mutation_stats": "mutation stats",
        "step_count": "step",
    }
    _PLOT_COLORS = ("#ff6b6b", "#4ecdc4", "#1a535c", "#ffe66d", "#2b2d42", "#118ab2")

    def __init__(self) -> None:
        super().__init__()
        self.history: list[dict[str, float]] = []
        self._plot_backend = None
        self._metric_keys: list[str] = []
        self._curves: dict[str, Any] = {}
        self._metric_enabled: dict[str, bool] = {}
        self._metric_checkboxes: dict[str, Any] = {}

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        actions = QHBoxLayout()
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_png_btn = QPushButton("Export Plot")
        actions.addWidget(self.export_csv_btn)
        actions.addWidget(self.export_png_btn)

        self.label = QLabel("No metrics yet")
        root.addLayout(actions)
        root.addWidget(self.label)
        self.metric_checks = QWidget()
        self.metric_checks_layout = QHBoxLayout(self.metric_checks)
        self.metric_checks_layout.setContentsMargins(0, 0, 0, 0)
        self.metric_checks_layout.setSpacing(10)
        root.addWidget(QLabel("Visible metrics"))
        root.addWidget(self.metric_checks)

        self.export_csv_btn.clicked.connect(self.export_csv)
        self.export_png_btn.clicked.connect(self.export_plot)

        # optional plotting backend
        try:
            import pyqtgraph as pg  # type: ignore

            self._plot_backend = "pyqtgraph"
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.addLegend()
            root.addWidget(self.plot_widget)
        except Exception:
            self._plot_backend = None

    def set_history(self, history: list[dict[str, float]]) -> None:
        """Replace complete metric history and refresh visuals."""
        normalized: list[dict[str, float]] = []
        for row in history:
            if not isinstance(row, dict):
                continue
            normalized.append({str(k): float(v) for k, v in row.items() if _is_floatable(v)})
        self.history = normalized
        if self.history:
            self._sync_metric_controls()
            self._refresh_from_last()
            return
        self._metric_keys = []
        self._curves = {}
        self._metric_enabled = {}
        self._metric_checkboxes = {}
        if QWidget is not object:
            self.label.setText("No metrics yet")
            self._clear_metric_controls()
            if self._plot_backend == "pyqtgraph":
                self.plot_widget.clear()

    def add_metrics(self, metrics: dict[str, Any]) -> None:
        row = {str(k): float(v) for k, v in metrics.items() if _is_floatable(v)}
        if not row:
            return
        self.history.append(row)
        if QWidget is not object:
            known = set(self._metric_enabled.keys())
            if set(self._all_metric_keys()) != known:
                self._sync_metric_controls()
        self._refresh_from_last()

    def _refresh_from_last(self) -> None:
        if QWidget is object or not self.history:
            return
        display_keys = self._selected_metric_keys()
        if not display_keys:
            self.label.setText("No metrics selected.")
            if self._plot_backend == "pyqtgraph":
                self.plot_widget.clear()
                self._metric_keys = []
                self._curves = {}
            return
        row = self.history[-1]
        parts = [f"{self._label_for_metric(k)}: {row.get(k, 0.0):.4f}" for k in display_keys]
        if len(parts) > 6:
            self.label.setText(" | ".join(parts[:6]) + f" | +{len(parts) - 6} more")
        else:
            self.label.setText(" | ".join(parts))
        if self._plot_backend == "pyqtgraph":
            self._ensure_plot_curves(display_keys)
            x = list(range(len(self.history)))
            for key in self._metric_keys:
                curve = self._curves.get(key)
                if curve is None:
                    continue
                curve.setData(x, [float(r.get(key, 0.0)) for r in self.history])

    def _select_display_keys(self) -> list[str]:
        if not self.history:
            return []
        latest = self.history[-1]
        if not latest:
            return []
        available = set(latest.keys())
        wandering_core = ["population", "average_hunger", "average_lifespan_turns"]
        if any(key in available for key in wandering_core):
            selected = [key for key in wandering_core if key in available]
            if selected:
                return selected
        preferred = [key for key in self._PREFERRED_METRIC_ORDER if key in available]
        if preferred:
            return preferred
        non_event_keys = [k for k in sorted(available) if not str(k).startswith("event_")]
        return non_event_keys or sorted(available)

    def _all_metric_keys(self) -> list[str]:
        available = {str(k) for row in self.history for k in row.keys()}
        preferred = [key for key in self._PREFERRED_METRIC_ORDER if key in available]
        remaining = [key for key in sorted(available) if key not in preferred]
        return preferred + remaining

    def _sync_metric_controls(self) -> None:
        if QWidget is object:
            return
        keys = self._all_metric_keys()
        if not keys:
            self._clear_metric_controls()
            return

        previous_enabled = dict(self._metric_enabled)
        self._metric_enabled = {}
        self._metric_checkboxes = {}
        self._clear_metric_controls()
        default_keys = set(self._select_display_keys())
        for key in keys:
            if key in previous_enabled:
                enabled = bool(previous_enabled[key])
            else:
                enabled = key in default_keys or (key not in default_keys and not key.startswith("event_"))
            self._metric_enabled[key] = enabled
            checkbox = QCheckBox(self._label_for_metric(key))
            checkbox.setChecked(enabled)
            checkbox.toggled.connect(lambda checked, metric_key=key: self._on_metric_toggled(metric_key, checked))
            self.metric_checks_layout.addWidget(checkbox)
            self._metric_checkboxes[key] = checkbox
        self.metric_checks_layout.addStretch(1)

    def _clear_metric_controls(self) -> None:
        if QWidget is object:
            return
        while self.metric_checks_layout.count():
            item = self.metric_checks_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _selected_metric_keys(self) -> list[str]:
        keys = self._all_metric_keys()
        return [key for key in keys if self._metric_enabled.get(key, False)]

    def _on_metric_toggled(self, key: str, checked: bool) -> None:
        self._metric_enabled[str(key)] = bool(checked)
        self._refresh_from_last()

    def _label_for_metric(self, key: str) -> str:
        if key in self._LABEL_OVERRIDES:
            return self._LABEL_OVERRIDES[key]
        return str(key).replace("_", " ").strip().lower()

    def _ensure_plot_curves(self, keys: list[str]) -> None:
        if self._plot_backend != "pyqtgraph":
            return
        if self._metric_keys == keys and self._curves:
            return

        self.plot_widget.clear()
        self._curves = {}
        self._metric_keys = list(keys)
        if not self._metric_keys:
            return
        for index, key in enumerate(self._metric_keys):
            color = self._PLOT_COLORS[index % len(self._PLOT_COLORS)]
            self._curves[key] = self.plot_widget.plot(
                name=self._label_for_metric(key),
                pen=color,
            )

    def export_csv(self) -> None:
        if not self.history:
            if QWidget is not object:
                self.label.setText("No metrics to export.")
            return
        out = Path("experiments") / "live_metrics.csv"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            columns = sorted({k for row in self.history for k in row.keys()})
            with out.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                writer.writerows(self.history)
            if QWidget is not object:
                self.label.setText(f"Exported CSV: {out}")
        except Exception as exc:
            if QWidget is not object:
                self.label.setText(f"CSV export failed: {exc}")

    def export_plot(self) -> None:
        if QWidget is object:
            return
        if self._plot_backend == "pyqtgraph":
            try:
                import pyqtgraph as pg  # type: ignore
                from pyqtgraph.exporters import ImageExporter  # type: ignore

                exporter = ImageExporter(self.plot_widget.plotItem)
                out = Path("experiments") / "live_metrics.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                exporter.export(str(out))
                self.label.setText(f"Exported plot: {out}")
            except Exception:
                self.label.setText("Plot export failed.")


def _is_floatable(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
