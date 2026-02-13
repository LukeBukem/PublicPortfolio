"""Dedicated GUI tab for wandering_agents_adv simulation state inspection."""

from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover
    QWidget = object  # type: ignore


class _RoomCanvas(QWidget):
    """Grid renderer for agent/food room state."""

    def __init__(self) -> None:
        super().__init__()
        self._state: dict[str, Any] = {}
        self._selected_agent_id: str | None = None
        self.on_agent_click = None

    def set_state(self, state: dict[str, Any], selected_agent_id: str | None) -> None:
        self._state = dict(state)
        self._selected_agent_id = selected_agent_id
        if QWidget is not object:
            self.update()

    def mousePressEvent(self, event: Any) -> None:  # type: ignore[override]
        if QWidget is object:
            return
        if event.button() != Qt.LeftButton:
            return

        room_w = max(1, int(self._state.get("room_width", 1)))
        room_h = max(1, int(self._state.get("room_height", 1)))
        agents = list(self._state.get("agents", []))
        if not agents:
            return

        cell_w = max(1.0, float(self.width()) / float(room_w))
        cell_h = max(1.0, float(self.height()) / float(room_h))
        grid_x = int(event.position().x() // cell_w)
        grid_y = int(event.position().y() // cell_h)

        picked_id: str | None = None
        for raw in agents:
            if not isinstance(raw, dict):
                continue
            pos = raw.get("position")
            if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                continue
            ax = int(pos[0])
            ay = int(pos[1])
            if ax == grid_x and ay == grid_y:
                picked_id = str(raw.get("id", ""))
                break

        if picked_id and self.on_agent_click is not None:
            self.on_agent_click(picked_id)

    def paintEvent(self, _event: Any) -> None:  # type: ignore[override]
        if QWidget is object:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(248, 248, 248))

        room_w = max(1, int(self._state.get("room_width", 1)))
        room_h = max(1, int(self._state.get("room_height", 1)))
        cell_w = max(1.0, float(self.width()) / float(room_w))
        cell_h = max(1.0, float(self.height()) / float(room_h))

        grid_pen = QPen(QColor(220, 220, 220))
        painter.setPen(grid_pen)
        for gx in range(room_w + 1):
            x = int(gx * cell_w)
            painter.drawLine(x, 0, x, self.height())
        for gy in range(room_h + 1):
            y = int(gy * cell_h)
            painter.drawLine(0, y, self.width(), y)

        foods = list(self._state.get("food", []))
        painter.setPen(QPen(QColor(0, 120, 0)))
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
            pos = raw.get("position")
            if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                continue
            ax = int(pos[0])
            ay = int(pos[1])

            left = int(ax * cell_w + max(1, cell_w * 0.15))
            top = int(ay * cell_h + max(1, cell_h * 0.15))
            side = max(3, int(min(cell_w, cell_h) * 0.7))
            agent_id = str(raw.get("id", ""))
            alive = bool(raw.get("alive", True))

            if alive:
                painter.setPen(QPen(QColor(180, 30, 30)))
                painter.setBrush(QColor(220, 40, 40))
            else:
                painter.setPen(QPen(QColor(120, 120, 120)))
                painter.setBrush(QColor(180, 180, 180))
            painter.drawRect(left, top, side, side)

            if self._selected_agent_id and agent_id == self._selected_agent_id:
                painter.setPen(QPen(QColor(255, 200, 0), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(left - 2, top - 2, side + 4, side + 4)

            hands = raw.get("Hands", 0)
            if isinstance(hands, (int, float)) and int(hands) > 0:
                painter.setPen(QPen(QColor(0, 0, 0)))
                painter.drawText(left, top + side + 10, "F")

        painter.end()


class WanderingAgentsAdvPanel(QWidget):
    """Tab panel for wandering_agents_adv frame-by-frame rendering and inspection."""

    def __init__(self) -> None:
        super().__init__()
        self._state: dict[str, Any] = {}
        self._selected_agent_id: str | None = None
        self.on_start = None
        self.on_pause = None
        self.on_resume = None
        self.on_step = None
        self.on_stop = None

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.step_btn = QPushButton("Step")
        self.stop_btn = QPushButton("Stop")
        controls.addWidget(self.start_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.resume_btn)
        controls.addWidget(self.step_btn)
        controls.addWidget(self.stop_btn)
        self.title = QLabel("Wandering Agents Advanced")
        self.status = QLabel("Load and run wandering_agents_adv to view this tab.")
        self.canvas = _RoomCanvas()
        self.canvas.setMinimumHeight(420)
        self.canvas.on_agent_click = self._select_agent

        self.agent_details = QTextEdit()
        self.agent_details.setReadOnly(True)
        self.agent_details.setPlaceholderText("Click an agent to inspect variables.")

        root.addWidget(self.title)
        root.addLayout(controls)
        root.addWidget(self.status)
        root.addWidget(self.canvas)
        root.addWidget(self.agent_details)

        self.start_btn.clicked.connect(lambda: self.on_start and self.on_start())
        self.pause_btn.clicked.connect(lambda: self.on_pause and self.on_pause())
        self.resume_btn.clicked.connect(lambda: self.on_resume and self.on_resume())
        self.step_btn.clicked.connect(lambda: self.on_step and self.on_step())
        self.stop_btn.clicked.connect(lambda: self.on_stop and self.on_stop())

    def update_state(self, state: dict[str, Any], simulation_name: str | None) -> None:
        self._state = dict(state)
        state_sim = str(state.get("simulation", "")) if isinstance(state, dict) else ""
        looks_like_wandering = self._is_wandering_payload(state)
        is_target = (
            str(simulation_name or "") == "wandering_agents_adv"
            or state_sim == "wandering_agents_adv"
            or looks_like_wandering
        )
        if QWidget is object:
            return

        if not is_target:
            self.status.setText("Active experiment is not wandering_agents_adv.")
            self.canvas.set_state({}, self._selected_agent_id)
            self.agent_details.setPlainText("")
            return

        step = int(state.get("step", 0))
        room_w = int(state.get("room_width", 0))
        room_h = int(state.get("room_height", 0))
        food_count = len(list(state.get("food", [])))
        agents = list(state.get("agents", []))
        agent_count = len(agents)
        alive_count = sum(1 for item in agents if isinstance(item, dict) and bool(item.get("alive", True)))
        self.status.setText(
            f"Turn {step} | Room {room_w}x{room_h} | Agents {alive_count}/{agent_count} alive | Food {food_count}"
        )
        self.canvas.set_state(state, self._selected_agent_id)
        self._refresh_details()

    def _select_agent(self, agent_id: str) -> None:
        self._selected_agent_id = agent_id
        if QWidget is not object:
            self.canvas.set_state(self._state, self._selected_agent_id)
        self._refresh_details()

    def _refresh_details(self) -> None:
        if QWidget is object:
            return
        if not self._selected_agent_id:
            self.agent_details.setPlainText("")
            return

        for raw in list(self._state.get("agents", [])):
            if not isinstance(raw, dict):
                continue
            if str(raw.get("id", "")) != self._selected_agent_id:
                continue
            lines = [
                f"id: {raw.get('id')}",
                f"Hunger: {raw.get('Hunger')}",
                f"Hands: {raw.get('Hands')}",
                f"MoveDistance: {raw.get('MoveDistance')}",
                f"Agreeable: {raw.get('Agreeable')}",
                f"Aggression: {raw.get('Aggression')}",
                f"alive: {raw.get('alive')}",
                f"position: {raw.get('position')}",
            ]
            self.agent_details.setPlainText("\n".join(lines))
            return

        self.agent_details.setPlainText("Selected agent not found in current frame.")

    @staticmethod
    def _is_wandering_payload(state: dict[str, Any]) -> bool:
        if not isinstance(state, dict):
            return False
        if not isinstance(state.get("room_width"), (int, float)) or not isinstance(state.get("room_height"), (int, float)):
            return False
        agents = state.get("agents", [])
        if not isinstance(agents, list):
            agents = []
        if any(
            isinstance(agent, dict) and any(key in agent for key in ("Hunger", "Hands", "MoveDistance"))
            for agent in agents
        ):
            return True
        return isinstance(state.get("food"), list)
