from __future__ import annotations

import pytest


def test_options_panel_has_speed_slider() -> None:
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    from gui.options_panel import OptionsPanel

    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    panel = OptionsPanel()
    assert hasattr(panel, "speed_slider")
    assert panel.speed_slider.minimum() == 1
    assert panel.speed_slider.maximum() == 2000
    panel.close()
