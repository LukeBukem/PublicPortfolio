from __future__ import annotations

from pathlib import Path

from core.live_plugin_session import LivePluginSession


def _wandering_config_text() -> str:
    return (
        "simulation: wandering_agents_adv\n"
        "params:\n"
        "  room_width: 20\n"
        "  room_height: 20\n"
        "  initial_agents: 8\n"
        "evolution:\n"
        "  population_size: 50\n"
        "  mutation_rate: 0.2\n"
        "  crossover_rate: 0.7\n"
        "  elite_fraction: 0.1\n"
        "  random_seed: 99\n"
        "logging:\n"
        "  log_interval: 1\n"
        "  checkpoint_interval: 10\n"
        "  experiment_name: live_plugin_test\n"
    )


def test_live_plugin_session_emits_render_state_each_generation(tmp_path: Path) -> None:
    cfg = tmp_path / "wandering.yaml"
    cfg.write_text(_wandering_config_text(), encoding="utf-8")
    updates: list[dict] = []

    session = LivePluginSession(
        config_path=cfg,
        steps=6,
        on_update=lambda payload: updates.append(payload),
    )
    session.set_speed(200.0)
    session.start()
    session.join(timeout=5)

    generations = [u for u in updates if u.get("event") == "generation"]
    assert len(generations) == 6
    assert all("render_state" in event for event in generations)


def test_live_plugin_session_reports_render_errors_without_silent_crash(tmp_path: Path) -> None:
    import core.live_plugin_session as lps

    cfg = tmp_path / "wandering.yaml"
    cfg.write_text(_wandering_config_text(), encoding="utf-8")
    updates: list[dict] = []

    original = lps._build_raw_render_state

    def _boom(_simulator):
        raise RuntimeError("boom")

    lps._build_raw_render_state = _boom
    try:
        session = LivePluginSession(
            config_path=cfg,
            steps=3,
            on_update=lambda payload: updates.append(payload),
        )
        session.set_speed(200.0)
        session.start()
        session.join(timeout=5)
    finally:
        lps._build_raw_render_state = original

    error_events = [u for u in updates if u.get("event") == "error"]
    generation_events = [u for u in updates if u.get("event") == "generation"]
    assert error_events
    assert generation_events
    assert any("render state normalization failed" in str(u.get("message", "")) for u in error_events)
