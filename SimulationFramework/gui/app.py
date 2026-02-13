"""Desktop entrypoint for experiment manager GUI."""

from __future__ import annotations

import logging
import sys

from core.experiment_manager import ExperimentManager
from core.metrics_store import MetricsStore
from core.replay_loader import ReplayLoader
from gui.main_window import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "PySide6 is required for gui.app. Install with: pip install PySide6 pyqtgraph websockets"
        ) from exc

    app = QApplication(sys.argv)
    store = MetricsStore("experiments/metrics.sqlite")
    replay_loader = ReplayLoader("experiments")
    runner = ExperimentManager(store=store, replay_loader=replay_loader, max_workers=2)
    window = MainWindow(runner)
    window.resize(1200, 800)
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
