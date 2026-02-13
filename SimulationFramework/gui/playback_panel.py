"""Playback panel for replay stream visualization and transport controls."""

from __future__ import annotations

from typing import Any

from core.simulation_runner_api import SimulationRunnerAPI

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSlider,
        QSpinBox,
        QVBoxLayout,
        QWidget,
    )
    from PySide6.QtCore import Qt
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class PlaybackPanel(QWidget):
    """Frame-by-frame replay controller with non-blocking timer-driven updates."""

    def __init__(self, runner: SimulationRunnerAPI) -> None:
        super().__init__()
        self.runner = runner
        self._frames: list[dict[str, Any]] = []
        self._index = 0

        if QWidget is object:
            return

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)

        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.speed = QSpinBox()
        self.speed.setRange(1, 120)
        self.speed.setValue(24)

        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(QLabel("FPS"))
        controls.addWidget(self.speed)

        self.canvas = QLabel("No replay loaded")
        root.addLayout(controls)
        root.addWidget(self.seek_slider)
        root.addWidget(self.canvas)

        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
        self.seek_slider.valueChanged.connect(self.seek)

    def load_run(self, run_id: str) -> None:
        replay = self.runner.get_replay(run_id)
        self._frames = replay.frames
        self._index = 0
        if QWidget is object:
            return
        self.seek_slider.setRange(0, max(0, len(self._frames) - 1))
        self._render_current_frame()

    def play(self) -> None:
        if QWidget is object:
            return
        interval = int(1000 / max(1, self.speed.value()))
        self.timer.start(interval)

    def pause(self) -> None:
        if QWidget is object:
            return
        self.timer.stop()

    def seek(self, index: int) -> None:
        self._index = max(0, min(index, len(self._frames) - 1 if self._frames else 0))
        if QWidget is not object:
            self._render_current_frame()

    def _advance(self) -> None:
        if not self._frames:
            return
        self._index = (self._index + 1) % len(self._frames)
        self.seek_slider.setValue(self._index)
        self._render_current_frame()

    def _render_current_frame(self) -> None:
        if not self._frames:
            self.canvas.setText("No replay frames")
            return
        frame = self._frames[self._index]
        self.canvas.setText(f"Frame {self._index}: agents={len(frame.get('agents', []))}")
