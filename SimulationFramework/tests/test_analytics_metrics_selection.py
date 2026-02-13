"""Tests for analytics metric key selection across stack types."""

from __future__ import annotations

from core.analytics import build_overlay, build_summary


def test_build_overlay_prefers_wandering_metrics_when_present() -> None:
    histories = {
        "run-a": [
            {"population": 10.0, "average_hunger": 7.2, "average_lifespan_turns": 3.0},
            {"population": 12.0, "average_hunger": 6.8, "average_lifespan_turns": 4.0},
        ],
        "run-b": [
            {"population": 8.0, "average_hunger": 7.9, "average_lifespan_turns": 2.0},
        ],
    }
    overlay = build_overlay(histories)

    assert "population" in overlay["stats"]
    assert "average_hunger" in overlay["stats"]
    assert "average_lifespan_turns" in overlay["stats"]
    assert "mean_fitness" not in overlay["stats"]


def test_build_summary_exposes_wandering_metrics_from_latest_row() -> None:
    history = [
        {"population": 5.0, "average_hunger": 8.0, "average_lifespan_turns": 1.0},
        {"population": 7.0, "average_hunger": 7.0, "average_lifespan_turns": 2.0},
    ]
    summary = build_summary(history)

    assert summary["population"] == 7.0
    assert summary["average_hunger"] == 7.0
    assert summary["average_lifespan_turns"] == 2.0
