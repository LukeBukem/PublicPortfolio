"""Tests for desktop GUI data/transport architecture."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ui_desktop.models.render_state_model import RenderStateModel
from ui_desktop.replay_client import ReplayRenderClient
from ui_desktop.timeline_panel import TimelinePanel
from ui_desktop.websocket_client import WebSocketRenderClient


def _config_text() -> str:
    return (
        "simulation: example_sim\n"
        "params:\n"
        "  world_size: 10\n"
        "  num_agents: 5\n"
        "evolution:\n"
        "  population_size: 20\n"
        "  mutation_rate: 0.1\n"
        "  crossover_rate: 0.7\n"
        "  elite_fraction: 0.1\n"
        "  random_seed: 123\n"
        "logging:\n"
        "  log_interval: 1\n"
        "  checkpoint_interval: 2\n"
        "  experiment_name: ui_test\n"
    )


def test_render_state_model_update_propagation() -> None:
    model = RenderStateModel(history_size=8)
    seen: list[int] = []

    model.subscribe(lambda s: seen.append(int(s.get("step_index", -1))))
    model.update_state({"step_index": 1, "agents": []})
    model.update_state({"step_index": 2, "agents": []})

    assert seen == [1, 2]
    assert model.latest() is not None


def test_replay_client_loads_and_emits_frames(tmp_path) -> None:
    from core.simulator import Simulator
    from data.checkpoint_store import CheckpointStore

    config = tmp_path / "cfg.yaml"
    config.write_text(_config_text(), encoding="utf-8")

    store = CheckpointStore()
    exp_dir = tmp_path / "exp"
    sim = Simulator(config, checkpoint_store=store, experiment_dir=exp_dir)
    sim.run(steps=4)

    client = ReplayRenderClient(config_path=config, experiment_dir=exp_dir)
    frames: list[dict] = []
    client.subscribe(lambda s: frames.append(s))
    client.jump_to_generation(4)

    assert frames
    step_value = frames[-1].get("step_index", frames[-1].get("step", 0))
    assert int(step_value) == 4


def test_timeline_scrubber_jump_callback_correctness() -> None:
    timeline = TimelinePanel()
    captured: list[int] = []
    timeline.on_jump = lambda g: captured.append(g)

    if hasattr(timeline, "_handle_change"):
        timeline._handle_change(7)  # type: ignore[attr-defined]
    assert captured == [7]


def test_websocket_client_connects_and_receives_frames() -> None:
    websockets = pytest.importorskip("websockets")

    async def handler(ws):
        await ws.recv()  # consume subscription message
        await ws.send(json.dumps({"step_index": 3, "agents": []}))
        await asyncio.sleep(0.1)

    async def _run() -> None:
        server = await websockets.serve(handler, "127.0.0.1", 9876)
        try:
            client = WebSocketRenderClient("ws://127.0.0.1:9876", mode="full_state")
            received: list[dict] = []
            client.subscribe(lambda payload: received.append(payload))
            client.start()
            await asyncio.sleep(0.3)
            client.stop()

            assert received
            assert int(received[-1]["step_index"]) == 3
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(_run())


def test_render_viewport_can_handle_10k_agents_without_crash() -> None:
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    from ui_desktop.render_viewport import RenderViewport

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    viewport = RenderViewport()
    state = {
        "agents": [{"id": str(i), "position": [i % 100, i // 100], "fitness": 0.5, "alive": True} for i in range(10_000)],
        "environment": {"bounds": [100, 100]},
    }
    viewport.set_render_state(state)
    viewport.resize(320, 240)
    viewport.show()
    app.processEvents()
    viewport.close()
