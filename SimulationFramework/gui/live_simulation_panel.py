"""Live simulation control and real-time rendering panel."""

from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class RenderCanvas(QWidget):
    """Generic canvas for rendering engine-agnostic agent state."""

    def __init__(self) -> None:
        super().__init__()
        self._state: dict[str, Any] = {"agents": [], "environment": {"bounds": [1, 1]}}
        self._hide_dead_agents = False

    def set_state(self, state: dict[str, Any]) -> None:
        self._state = state
        if QWidget is not object:
            self.update()

    def set_hide_dead_agents(self, enabled: bool) -> None:
        self._hide_dead_agents = bool(enabled)
        if QWidget is not object:
            self.update()

    def paintEvent(self, _event: Any) -> None:  # type: ignore[override]
        if QWidget is object:
            return
        painter = QPainter(self)
        if self._is_wandering_payload():
            self._draw_wandering_frame(painter)
        else:
            self._draw_generic_frame(painter)

        painter.end()

    def _draw_generic_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        agents = self._state.get("agents", [])
        env = self._state.get("environment", {})
        bounds = env.get("bounds", [1, 1])
        max_x = max(float(bounds[0]), 1.0)
        max_y = max(float(bounds[1]), 1.0)

        w = float(self.width())
        h = float(self.height())

        # highlight first agent as top-performer placeholder overlay hook.
        draw_index = 0
        for agent in agents:
            if self._hide_dead_agents and not bool(agent.get("alive", True)):
                continue
            pos = agent.get("position", [0, 0])
            x = float(pos[0]) / max_x * w
            y = float(pos[1]) / max_y * h
            color = QColor(255, 190, 80) if draw_index == 0 else QColor(80, 180, 255)
            painter.setBrush(color)
            painter.setPen(color)
            painter.drawEllipse(int(x), int(y), 5, 5)
            draw_index += 1

    def _draw_wandering_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor(248, 248, 248))
        room_w = max(1, int(self._state.get("room_width", 1)))
        room_h = max(1, int(self._state.get("room_height", 1)))
        cell_w = max(1.0, float(self.width()) / float(room_w))
        cell_h = max(1.0, float(self.height()) / float(room_h))

        painter.setPen(QColor(220, 220, 220))
        for gx in range(room_w + 1):
            x = int(gx * cell_w)
            painter.drawLine(x, 0, x, self.height())
        for gy in range(room_h + 1):
            y = int(gy * cell_h)
            painter.drawLine(0, y, self.width(), y)

        foods = list(self._state.get("food", []))
        painter.setPen(QColor(0, 120, 0))
        painter.setBrush(QColor(40, 180, 40))
        for food in foods:
            if not isinstance(food, dict):
                continue
            x = int(food.get("x", 0))
            y = int(food.get("y", 0))
            center_x = int((x + 0.5) * cell_w)
            center_y = int((y + 0.5) * cell_h)
            radius = max(2, int(min(cell_w, cell_h) * 0.28))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        agents = list(self._state.get("agents", []))
        for raw in agents:
            if not isinstance(raw, dict):
                continue
            if self._hide_dead_agents and not bool(raw.get("alive", True)):
                continue
            pos = raw.get("position")
            if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                continue
            ax = int(pos[0])
            ay = int(pos[1])
            left = int(ax * cell_w + max(1, cell_w * 0.15))
            top = int(ay * cell_h + max(1, cell_h * 0.15))
            side = max(3, int(min(cell_w, cell_h) * 0.7))
            alive = bool(raw.get("alive", True))
            if alive:
                painter.setPen(QColor(180, 30, 30))
                painter.setBrush(QColor(220, 40, 40))
            else:
                painter.setPen(QColor(120, 120, 120))
                painter.setBrush(QColor(180, 180, 180))
            painter.drawRect(left, top, side, side)

    def _is_wandering_payload(self) -> bool:
        if not isinstance(self._state.get("room_width"), (int, float)):
            return False
        if not isinstance(self._state.get("room_height"), (int, float)):
            return False
        if not isinstance(self._state.get("food"), list):
            return False
        agents = self._state.get("agents", [])
        return isinstance(agents, list)


class LiveSimulationPanel(QWidget):
    """Provides start/pause/resume/stop/reset controls and live render widget."""

    SPEED_PRESETS = {
        "Slow": 0.5,
        "Normal": 1.0,
        "Fast": 3.0,
        "Instant": 100.0,
    }

    def __init__(self) -> None:
        super().__init__()
        self.on_start = None
        self.on_pause = None
        self.on_resume = None
        self.on_step = None
        self.on_stop = None
        self.on_reset = None
        self.on_speed = None

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        controls = QHBoxLayout()

        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.step_btn = QPushButton("Step")
        self.stop_btn = QPushButton("Stop")
        self.reset_btn = QPushButton("Reset")

        self.speed = QComboBox()
        self.speed.addItems(list(self.SPEED_PRESETS.keys()))
        self.speed.setCurrentText("Normal")
        self.hide_dead = QCheckBox("Hide dead agents")

        controls.addWidget(self.start_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.resume_btn)
        controls.addWidget(self.step_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.reset_btn)
        controls.addWidget(QLabel("Speed"))
        controls.addWidget(self.speed)
        controls.addWidget(self.hide_dead)

        self.status = QLabel("Generation: 0 / 0")
        self.canvas = RenderCanvas()
        self.canvas.setMinimumHeight(300)

        root.addLayout(controls)
        root.addWidget(self.status)
        root.addWidget(self.canvas)

        self.start_btn.clicked.connect(lambda: self.on_start and self.on_start())
        self.pause_btn.clicked.connect(lambda: self.on_pause and self.on_pause())
        self.resume_btn.clicked.connect(lambda: self.on_resume and self.on_resume())
        self.step_btn.clicked.connect(lambda: self.on_step and self.on_step())
        self.stop_btn.clicked.connect(lambda: self.on_stop and self.on_stop())
        self.reset_btn.clicked.connect(lambda: self.on_reset and self.on_reset())
        self.speed.currentTextChanged.connect(self._on_speed_change)
        self.hide_dead.toggled.connect(self.canvas.set_hide_dead_agents)

    def _on_speed_change(self, label: str) -> None:
        if self.on_speed:
            self.on_speed(float(self.SPEED_PRESETS.get(label, 1.0)))

    def update_generation(self, generation: int, total: int, status: str | None = None) -> None:
        if QWidget is object:
            return
        suffix = f" ({status})" if status else ""
        self.status.setText(f"Generation: {generation + 1} / {total}{suffix}")

    def update_render_state(self, state: dict[str, Any]) -> None:
        if QWidget is object:
            return
        self.canvas.set_state(state)
