"""Live leaderboard panel for ranking experiments by configurable metrics."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

try:
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class LeaderboardPanel(QWidget):
    """Displays sortable experiment leaderboard with environment filtering."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict[str, Any]] = []

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.metric_sort = QComboBox()
        self.metric_sort.addItems(
            [
                "population",
                "average_hunger",
                "average_lifespan_turns",
                "max_fitness",
                "mean_fitness",
                "diversity",
                "mutation_stats",
            ]
        )
        self.environment_filter = QLineEdit()
        self.text_filter = QLineEdit()
        self.export_btn = QPushButton("Export Leaderboard CSV")

        controls.addWidget(QLabel("Sort metric"))
        controls.addWidget(self.metric_sort)
        controls.addWidget(QLabel("Environment filter"))
        controls.addWidget(self.environment_filter)
        controls.addWidget(QLabel("Search"))
        controls.addWidget(self.text_filter)
        controls.addWidget(self.export_btn)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["experiment_id"])
        self.table.setSortingEnabled(True)

        root.addLayout(controls)
        root.addWidget(self.table)

        self.metric_sort.currentTextChanged.connect(lambda _x: self._render())
        self.environment_filter.textChanged.connect(lambda _x: self._render())
        self.text_filter.textChanged.connect(lambda _x: self._render())
        self.export_btn.clicked.connect(self.export_csv)

    def update_rows(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows)
        self._render()

    def _render(self) -> None:
        if QWidget is object:
            return

        rows = list(self._rows)
        env = self.environment_filter.text().strip().lower()
        text = self.text_filter.text().strip().lower()
        metric = self.metric_sort.currentText().strip() or "max_fitness"

        filtered = []
        for row in rows:
            if env and str(row.get("environment", "")).lower() != env:
                continue
            if text and text not in str(row).lower():
                continue
            filtered.append(row)

        filtered.sort(key=lambda r: float(r.get(metric, 0.0)), reverse=True)

        columns = sorted({k for row in filtered for k in row.keys()}) or ["experiment_id"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(filtered))

        for i, row in enumerate(filtered):
            for j, col in enumerate(columns):
                self.table.setItem(i, j, QTableWidgetItem(str(row.get(col, ""))))

    def export_csv(self) -> None:
        if not self._rows:
            return
        out = Path("experiments") / "leaderboard_live.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        columns = sorted({k for row in self._rows for k in row.keys()})
        with out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows(self._rows)
