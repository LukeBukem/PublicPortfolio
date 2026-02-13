"""Metrics panel with real-time charting hooks."""

from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class MetricsPanel(QWidget):
    """Displays latest metrics and supports CSV export."""

    def __init__(self) -> None:
        super().__init__()
        self._latest: dict[str, float] = {}
        if QWidget is object:
            return
        layout = QVBoxLayout(self)
        self.label = QLabel("No metrics yet")
        layout.addWidget(self.label)

    def update_metrics(self, metrics: dict[str, float]) -> None:
        self._latest = metrics
        if QWidget is object:
            return
        lines = [f"{k}: {v:.4f}" for k, v in sorted(metrics.items())]
        self.label.setText("\n".join(lines) if lines else "No metrics yet")

    def export_csv(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = ["metric,value"] + [f"{k},{v}" for k, v in sorted(self._latest.items())]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
