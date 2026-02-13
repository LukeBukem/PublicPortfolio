"""Panel listing all experiments with stable single-select and contextual actions."""

from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import (
        QAbstractItemView,
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
    class Signal:  # type: ignore[override]
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, *_args: object, **_kwargs: object) -> None:
            pass

    QWidget = object  # type: ignore


class ExperimentsTablePanel(QWidget):
    """Sortable/filterable experiment table with context actions."""

    view_metrics_requested = Signal(list)
    render_requested = Signal(list)
    export_requested = Signal(list)
    stop_requested = Signal(list)
    delete_requested = Signal(list)
    selected_experiment_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict[str, Any]] = []
        self._selected_experiment_id: str | None = None

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter experiments...")
        self.view_btn = QPushButton("View Metrics")
        self.render_btn = QPushButton("Render Simulation")
        self.stop_btn = QPushButton("Stop Selected")
        self.delete_btn = QPushButton("Delete Selected")
        self.export_btn = QPushButton("Export Data")

        controls.addWidget(QLabel("Experiments"))
        controls.addWidget(self.filter_input)
        controls.addWidget(self.view_btn)
        controls.addWidget(self.render_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.delete_btn)
        controls.addWidget(self.export_btn)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["experiment_id"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)

        root.addLayout(controls)
        root.addWidget(self.table)

        self.filter_input.textChanged.connect(lambda _x: self._render())
        self.view_btn.clicked.connect(lambda: self.view_metrics_requested.emit(self.selected_ids()))
        self.render_btn.clicked.connect(lambda: self.render_requested.emit(self.selected_ids()))
        self.stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.selected_ids()))
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.selected_ids()))
        self.export_btn.clicked.connect(lambda: self.export_requested.emit(self.selected_ids()))
        self.table.itemSelectionChanged.connect(self._emit_selected_experiment)

    def update_rows(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows)
        self._render()

    def selected_ids(self) -> list[str]:
        if QWidget is object:
            return [str(self._rows[0].get("experiment_id", ""))] if self._rows else []
        ids: list[str] = []
        rows = sorted(index.row() for index in self.table.selectionModel().selectedRows())
        for row_index in rows:
            index = self.table.model().index(row_index, 0)
            item = self.table.item(index.row(), 0)
            if item:
                ids.append(item.text())
        return ids

    def _render(self) -> None:
        if QWidget is object:
            return
        selected_ids = self.selected_ids()
        if selected_ids:
            self._selected_experiment_id = selected_ids[0]

        text = self.filter_input.text().strip().lower()
        rows = [r for r in self._rows if not text or text in str(r).lower()]

        columns = [
            "experiment_id",
            "status",
            "population_size",
            "generations",
            "mutation_rate",
            "environment",
            "seed",
        ]
        extra = sorted({k for row in rows for k in row.keys() if k not in columns})
        columns = columns + extra

        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(rows))
        selected_row_index: int | None = None
        for i, row in enumerate(rows):
            experiment_id = str(row.get("experiment_id", ""))
            if selected_row_index is None and experiment_id and experiment_id == self._selected_experiment_id:
                selected_row_index = i
            for j, col in enumerate(columns):
                self.table.setItem(i, j, QTableWidgetItem(str(row.get(col, ""))))
        if selected_row_index is not None:
            self.table.selectRow(selected_row_index)
        self.table.blockSignals(False)
        self.table.setSortingEnabled(sorting_enabled)
        self._emit_selected_experiment()

    def _emit_selected_experiment(self) -> None:
        if QWidget is object:
            return
        selected_ids = self.selected_ids()
        if not selected_ids:
            self._selected_experiment_id = None
            return
        selected_id = selected_ids[0]
        if selected_id == self._selected_experiment_id:
            return
        self._selected_experiment_id = selected_id
        self.selected_experiment_changed.emit(selected_id)
