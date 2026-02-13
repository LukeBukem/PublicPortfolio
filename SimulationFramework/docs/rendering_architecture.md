# Rendering & Streaming Architecture

## Pipeline

```text
Simulator
  -> simulation renderer_adapter.build_render_state(simulator)
  -> EventBus.publish("render_state", RenderState)
  -> state_serializer.serialize_state(RenderState)
  -> RenderStateServer.broadcast(...)
  -> WebSocket clients (UI)
```

## Data Flow

1. `core/simulator.py` runs plugin steps.
2. A simulation-specific adapter (`simulations/<name>/renderer_adapter.py`) maps internal state to `RenderState`.
3. `core/event_bus.py` publishes render events without blocking simulator loop.
4. `streaming/state_serializer.py` converts state to deterministic JSON bytes.
5. `streaming/websocket_server.py` broadcasts frames to subscribed clients.

## Example JSON frame

```json
{
  "generation_index": 0,
  "step_index": 12,
  "agents": [
    {"id": "0", "position": [3.0, 7.0], "velocity": null, "genome_summary": {}, "fitness": null, "alive": true}
  ],
  "environment": {
    "bounds": [50, 50],
    "obstacles": [],
    "resources": [],
    "metadata": {"simulation": "example_sim"}
  },
  "metrics": {"mean_agent_x_position": 24.5, "step_count": 12.0},
  "timestamp": 1730000000.0
}
```

## Performance Notes

- Serialization is O(n_agents) and deterministic (`sort_keys=True`).
- Frame size guard rejects payloads above ~10MB.
- Websocket server uses bounded per-client queues and drops stale frames on lag.
- FPS throttle prevents oversending (default max 30 FPS).
- Simulation can run headless with event bus/streaming disabled.
