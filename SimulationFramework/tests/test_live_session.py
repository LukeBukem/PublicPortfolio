from __future__ import annotations

import time

from configs.loader import ExperimentConfig
from core.live_session import LiveSimulationSession


def test_live_session_emits_updates_and_completion(tmp_path) -> None:
    updates: list[dict] = []

    cfg = ExperimentConfig(
        population_size=50,
        generations=6,
        mutation_rate=0.05,
        environment="dummy",
        seed=123,
    )
    session = LiveSimulationSession(
        config=cfg,
        on_update=lambda payload: updates.append(payload),
        db_path=tmp_path / "live.db",
    )
    session.set_speed(100.0)
    session.start()
    session.join(timeout=5)

    generation_events = [u for u in updates if u.get("event") == "generation"]
    complete_events = [u for u in updates if u.get("event") == "complete"]

    assert len(generation_events) == 6
    assert complete_events
    assert all("metrics" in event for event in generation_events)


def test_live_session_pause_resume_and_stop(tmp_path) -> None:
    updates: list[dict] = []

    cfg = ExperimentConfig(
        population_size=50,
        generations=50,
        mutation_rate=0.05,
        environment="dummy",
        seed=5,
    )
    session = LiveSimulationSession(
        config=cfg,
        on_update=lambda payload: updates.append(payload),
        db_path=tmp_path / "live2.db",
    )
    session.set_speed(20.0)
    session.start()
    time.sleep(0.1)
    session.pause()

    paused_count = len([u for u in updates if u.get("event") == "generation"])
    time.sleep(0.1)
    paused_count_after = len([u for u in updates if u.get("event") == "generation"])
    assert paused_count_after <= paused_count + 1

    session.resume()
    time.sleep(0.1)
    session.stop()
    session.join(timeout=3)

    complete_events = [u for u in updates if u.get("event") == "complete"]
    assert complete_events
