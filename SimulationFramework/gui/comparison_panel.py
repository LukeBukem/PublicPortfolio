"""Experiment comparison panel with overlay and summary analytics views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from PySide6.QtWidgets import (
        QCheckBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class ComparisonPanel(QWidget):
    """Compares multiple experiment runs using overlay metric payloads."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict[str, Any]] = []
        self._overlay: dict[str, Any] = {}

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        self.run_list = QListWidget()
        self.run_list.setSelectionMode(QListWidget.MultiSelection)

        toggles = QHBoxLayout()
        self.population_chk = QCheckBox("population")
        self.avg_hunger_chk = QCheckBox("average_hunger")
        self.avg_lifespan_chk = QCheckBox("average_lifespan_turns")
        self.mean_fit_chk = QCheckBox("mean_fitness")
        self.max_fit_chk = QCheckBox("max_fitness")
        self.div_chk = QCheckBox("diversity")
        self.mut_chk = QCheckBox("mutation_stats")
        for chk in [
            self.population_chk,
            self.avg_hunger_chk,
            self.avg_lifespan_chk,
            self.mean_fit_chk,
            self.max_fit_chk,
            self.div_chk,
            self.mut_chk,
        ]:
            chk.setChecked(chk in {self.population_chk, self.avg_hunger_chk, self.avg_lifespan_chk})
            toggles.addWidget(chk)

        self.compare_btn = QPushButton("Compare Selected")
        self.export_btn = QPushButton("Export Comparison JSON")
        actions = QHBoxLayout()
        actions.addWidget(self.compare_btn)
        actions.addWidget(self.export_btn)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setPlaceholderText("Comparison overlays and mean±std summaries appear here.")

        root.addWidget(QLabel("Select experiments to compare"))
        root.addWidget(self.run_list)
        root.addLayout(toggles)
        root.addLayout(actions)
        root.addWidget(self.summary)

    def update_experiments(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows)
        if QWidget is object:
            return
        self.run_list.clear()
        for row in self._rows:
            self.run_list.addItem(str(row.get("experiment_id", "")))

    def selected_experiment_ids(self) -> list[str]:
        if QWidget is object:
            return [str(r.get("experiment_id", "")) for r in self._rows[:2]]
        return [item.text() for item in self.run_list.selectedItems()]

    def selected_metric_keys(self) -> list[str]:
        checks = [
            ("population", self.population_chk),
            ("average_hunger", self.avg_hunger_chk),
            ("average_lifespan_turns", self.avg_lifespan_chk),
            ("mean_fitness", self.mean_fit_chk),
            ("max_fitness", self.max_fit_chk),
            ("diversity", self.div_chk),
            ("mutation_stats", self.mut_chk),
        ]
        if QWidget is object:
            return [name for name, _ in checks]
        return [name for name, chk in checks if chk.isChecked()]

    def show_overlay(self, overlay: dict[str, Any]) -> None:
        self._overlay = overlay
        if QWidget is object:
            return
        self.summary.setPlainText(json.dumps(overlay, indent=2)[:20000])

    def export_overlay(self) -> Path | None:
        if not self._overlay:
            return None
        out = Path("experiments") / "comparison_overlay.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self._overlay, indent=2), encoding="utf-8")
        return out
