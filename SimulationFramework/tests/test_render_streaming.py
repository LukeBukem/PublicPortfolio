"""Tests for render-state API and streaming layer."""

from __future__ import annotations

import asyncio
import json
import threading
import time

from core.event_bus import EventBus
from core.render_state import AgentState, EnvironmentState, RenderState
from core.simulator import Simulator
from simulations.example_sim.renderer_adapter import build_render_state
from streaming.state_serializer import serialize_state
from streaming.websocket_server import RenderStateServer


def _example_state() -> RenderState:
    return RenderState(
        generation_index=0,
        step_index=1,
        agents=[AgentState(id="a1", position=(1, 2), velocity=None, genome_summary={}, fitness=1.0, alive=True)],
        environment=EnvironmentState(bounds=(10, 10), obstacles=[], resources=[], metadata={}),
        metrics={"mean": 1.0},
        timestamp=123.0,
    )


def test_render_state_serialization_works() -> None:
    data = serialize_state(_example_state())
    parsed = json.loads(data.decode("utf-8"))
    assert parsed["generation_index"] == 0
    assert parsed["agents"][0]["id"] == "a1"


def test_event_bus_dispatches_non_blocking() -> None:
    bus = EventBus(max_workers=2)
    received: list[int] = []
    lock = threading.Lock()

    def _cb(payload: dict[str, int]) -> None:
        with lock:
            received.append(payload["v"])

    bus.subscribe("render_state", _cb)
    bus.publish("render_state", {"v": 1})
    time.sleep(0.05)
    bus.close()
    assert received == [1]


def test_adapter_produces_valid_render_state(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        """
simulation: example_sim
params:
  world_size: 10
  num_agents: 3
evolution:
  population_size: 20
  mutation_rate: 0.1
  crossover_rate: 0.7
  elite_fraction: 0.1
  random_seed: 42
logging:
  log_interval: 1
  checkpoint_interval: 10
  experiment_name: test
""".strip()
        + "\n",
        encoding="utf-8",
    )
    sim = Simulator(cfg)
    sim.sim.reset()
    sim.sim.step()
    sim.step_index = 1
    state = build_render_state(sim)
    assert isinstance(state, RenderState)
    assert state.step_index == 1


def test_simulator_emits_render_events(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        """
simulation: example_sim
params:
  world_size: 10
  num_agents: 3
evolution:
  population_size: 20
  mutation_rate: 0.1
  crossover_rate: 0.7
  elite_fraction: 0.1
  random_seed: 42
logging:
  log_interval: 1
  checkpoint_interval: 10
  experiment_name: test
""".strip()
        + "\n",
        encoding="utf-8",
    )

    bus = EventBus(max_workers=2)
    got: list[RenderState] = []

    def _on_state(payload: RenderState) -> None:
        got.append(payload)

    bus.subscribe("render_state", _on_state)
    sim = Simulator(cfg, event_bus=bus)
    sim.run(steps=3)
    time.sleep(0.05)
    bus.close()
    assert len(got) == 3


class _DummyWS:
    def __init__(self) -> None:
        self.frames: list[bytes] = []

    async def send(self, frame: bytes) -> None:
        self.frames.append(frame)


def test_websocket_server_sends_frames() -> None:
    async def _run() -> None:
        server = RenderStateServer(max_fps=60)
        dummy = _DummyWS()
        from streaming.websocket_server import _Client  # local helper

        client = _Client(websocket=dummy, mode="metrics_only")
        server._clients.append(client)

        sender_task = asyncio.create_task(server._sender_loop(client))
        await server.broadcast(_example_state())
        await asyncio.sleep(0.05)
        sender_task.cancel()

        assert len(dummy.frames) == 1
        payload = json.loads(dummy.frames[0].decode("utf-8"))
        assert "metrics" in payload
        assert "agents" not in payload

    asyncio.run(_run())
