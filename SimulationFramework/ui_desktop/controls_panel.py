"""Playback and simulation-control panel."""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtWidgets import (
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class ControlsPanel(QWidget):
    """User controls for play/pause/step/jump/speed/mode."""

    def __init__(self) -> None:
        super().__init__()
        self.on_play: Callable[[], None] | None = None
        self.on_pause: Callable[[], None] | None = None
        self.on_step_forward: Callable[[], None] | None = None
        self.on_step_backward: Callable[[], None] | None = None
        self.on_jump: Callable[[int], None] | None = None
        self.on_speed_change: Callable[[int], None] | None = None
        self.on_mode_change: Callable[[str], None] | None = None

        if QWidget is object:
            return

        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()

        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.back_btn = QPushButton("Step -")
        self.forward_btn = QPushButton("Step +")

        buttons.addWidget(self.play_btn)
        buttons.addWidget(self.pause_btn)
        buttons.addWidget(self.back_btn)
        buttons.addWidget(self.forward_btn)

        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(0, 10_000_000)
        self.jump_btn = QPushButton("Jump")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1", "10", "100"])

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["live", "replay"])

        form = QFormLayout()
        form.addRow(QLabel("Jump generation"), self.jump_spin)
        form.addRow(self.jump_btn)
        form.addRow(QLabel("Speed"), self.speed_combo)
        form.addRow(QLabel("Mode"), self.mode_combo)

        layout.addLayout(buttons)
        layout.addLayout(form)

        self.play_btn.clicked.connect(lambda: self.on_play and self.on_play())
        self.pause_btn.clicked.connect(lambda: self.on_pause and self.on_pause())
        self.forward_btn.clicked.connect(lambda: self.on_step_forward and self.on_step_forward())
        self.back_btn.clicked.connect(lambda: self.on_step_backward and self.on_step_backward())
        self.jump_btn.clicked.connect(lambda: self.on_jump and self.on_jump(self.jump_spin.value()))
        self.speed_combo.currentTextChanged.connect(
            lambda txt: self.on_speed_change and self.on_speed_change(int(txt))
        )
        self.mode_combo.currentTextChanged.connect(
            lambda mode: self.on_mode_change and self.on_mode_change(mode)
        )
