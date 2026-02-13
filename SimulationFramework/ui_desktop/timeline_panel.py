"""Timeline scrubber for checkpoint-aware replay navigation."""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget
    from PySide6.QtCore import Qt
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class TimelinePanel(QWidget):
    """Generation timeline panel with jump callbacks."""

    def __init__(self) -> None:
        super().__init__()
        self.on_jump: Callable[[int], None] | None = None
        self._current_generation = 0
        if QWidget is object:
            self._max_generation = 0
            return

        layout = QHBoxLayout(self)
        self.label = QLabel("Generation: 0")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self._handle_change)

    def set_range(self, max_generation: int) -> None:
        if QWidget is object:
            self._max_generation = max_generation
            return
        self.slider.setRange(0, max(0, max_generation))

    def set_generation(self, generation: int) -> None:
        self._current_generation = generation
        if QWidget is object:
            return
        self.label.setText(f"Generation: {generation}")
        self.slider.blockSignals(True)
        self.slider.setValue(generation)
        self.slider.blockSignals(False)

    def _handle_change(self, generation: int) -> None:
        self._current_generation = generation
        if QWidget is not object:
            self.label.setText(f"Generation: {generation}")
        if self.on_jump:
            self.on_jump(generation)
