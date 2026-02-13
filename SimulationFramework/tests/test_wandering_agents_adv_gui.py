"""GUI tests for wandering_agents_adv panel."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _example_state() -> dict:
    return {
        "step": 4,
        "room_width": 10,
        "room_height": 10,
        "food": [{"x": 6, "y": 7, "count": 1}],
        "agents": [
            {
                "id": "agent_0",
                "position": [2, 3],
                "Hunger": 8,
                "Hands": 1,
                "MoveDistance": 5,
                "Agreeable": 0.35,
                "Aggression": 0.7,
                "alive": True,
            }
        ],
    }


def test_panel_click_selects_agent_and_shows_stats() -> None:
    QtCore = pytest.importorskip("PySide6.QtCore")
    QtTest = pytest.importorskip("PySide6.QtTest")
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    from gui.wandering_agents_adv_panel import WanderingAgentsAdvPanel

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    panel = WanderingAgentsAdvPanel()
    panel.resize(700, 700)
    panel.show()
    panel.update_state(_example_state(), simulation_name="wandering_agents_adv")
    app.processEvents()

    canvas = panel.canvas
    canvas.resize(500, 500)
    app.processEvents()
    cell_w = float(canvas.width()) / 10.0
    cell_h = float(canvas.height()) / 10.0
    click_pos = QtCore.QPoint(int((2.5) * cell_w), int((3.5) * cell_h))
    QtTest.QTest.mouseClick(canvas, QtCore.Qt.LeftButton, pos=click_pos)
    app.processEvents()

    details = panel.agent_details.toPlainText()
    assert "id: agent_0" in details
    assert "Hunger: 8" in details
    assert "Hands: 1" in details
    assert "MoveDistance: 5" in details

    panel.close()


def test_panel_shows_non_target_message_for_other_simulation() -> None:
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    from gui.wandering_agents_adv_panel import WanderingAgentsAdvPanel

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    panel = WanderingAgentsAdvPanel()
    panel.show()
    panel.update_state(_example_state(), simulation_name="example_sim")
    app.processEvents()

    assert "not wandering_agents_adv" in panel.status.text()
    assert panel.agent_details.toPlainText() == ""

    panel.close()


def test_panel_exposes_run_control_buttons() -> None:
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    from gui.wandering_agents_adv_panel import WanderingAgentsAdvPanel

    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    panel = WanderingAgentsAdvPanel()
    assert hasattr(panel, "start_btn")
    assert hasattr(panel, "pause_btn")
    assert hasattr(panel, "resume_btn")
    assert hasattr(panel, "step_btn")
    assert hasattr(panel, "stop_btn")
    panel.close()
