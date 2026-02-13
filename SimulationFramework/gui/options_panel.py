"""Global options panel for runtime controls."""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class OptionsPanel(QWidget):
    """Runtime controls shared across live simulation views."""

    def __init__(self) -> None:
        super().__init__()
        self.on_speed_changed: Callable[[float], None] | None = None
        self._updating = False

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("Turn Speed"))

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)      # 0.1x
        self.speed_slider.setMaximum(2000)   # 200x
        self.speed_slider.setValue(10)       # 1.0x
        self.speed_slider.setTickInterval(10)

        self.speed_label = QLabel("1.0x")
        row.addWidget(self.speed_slider)
        row.addWidget(self.speed_label)

        root.addLayout(row)
        root.addStretch(1)

        self.speed_slider.valueChanged.connect(self._on_slider_change)

    def _on_slider_change(self, value: int) -> None:
        speed = max(0.1, float(value) / 10.0)
        if QWidget is not object:
            self.speed_label.setText(f"{speed:.1f}x")
        if not self._updating and self.on_speed_changed is not None:
            self.on_speed_changed(speed)

    def set_speed(self, speed: float) -> None:
        if QWidget is object:
            return
        slider_value = max(self.speed_slider.minimum(), min(self.speed_slider.maximum(), int(round(speed * 10.0))))
        self._updating = True
        try:
            self.speed_slider.setValue(slider_value)
            self.speed_label.setText(f"{float(slider_value) / 10.0:.1f}x")
        finally:
            self._updating = False
