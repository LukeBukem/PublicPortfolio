"""GPU render viewport for large-agent visualization."""

from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPainter, QWheelEvent
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except ModuleNotFoundError:  # pragma: no cover - runtime dependency in desktop mode
    QOpenGLWidget = object  # type: ignore
    QPainter = object  # type: ignore
    QColor = object  # type: ignore
    QPointF = object  # type: ignore
    QWheelEvent = object  # type: ignore


class RenderViewport(QOpenGLWidget):
    """OpenGL-capable viewport.

    Uses a lightweight painter path for compatibility in tests; designed to be
    upgraded to true VBO/instanced rendering backend without UI API changes.
    """

    def __init__(self) -> None:
        super().__init__()
        self._agents: list[dict[str, Any]] = []
        self._bounds = (1, 1)
        self._zoom = 1.0

    def set_render_state(self, state: dict[str, Any]) -> None:
        self._agents = state.get("agents", [])
        env = state.get("environment", {})
        self._bounds = tuple(env.get("bounds", [1, 1]))  # type: ignore[assignment]
        self.update()

    def set_3d_mode(self, enabled: bool) -> None:
        """Placeholder 2D/3D toggle hook."""
        _ = enabled

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        delta = event.angleDelta().y() / 120.0
        self._zoom = max(0.1, min(10.0, self._zoom * (1.1 ** delta)))
        self.update()

    def paintEvent(self, _event: Any) -> None:  # type: ignore[override]
        if not hasattr(QPainter, "__call__") and QPainter is object:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 18, 18))

        w, h = max(float(self._bounds[0]), 1.0), max(float(self._bounds[1]), 1.0)
        sx = self.width() / w * self._zoom
        sy = self.height() / h * self._zoom

        for agent in self._agents[:10000]:
            pos = agent.get("position", [0, 0])
            x, y = float(pos[0]), float(pos[1])
            fitness = agent.get("fitness", None)
            alive = bool(agent.get("alive", True))

            if not alive:
                color = QColor(120, 120, 120)
            elif isinstance(fitness, (int, float)):
                color = QColor(max(0, min(255, int(128 + fitness * 127))), 220, 120)
            else:
                color = QColor(80, 180, 255)

            painter.setPen(color)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x * sx, y * sy), 2.0, 2.0)

        painter.end()
