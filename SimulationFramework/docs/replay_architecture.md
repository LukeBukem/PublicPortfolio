# Deterministic Replay & Time-Travel Architecture

## Replay pipeline

```text
Simulator (deterministic RNG)
  -> Checkpoint builder (core/checkpointing.py)
  -> CheckpointStore.save(...) [atomic write]
  -> persisted checkpoint files

ReplayEngine
  -> load nearest checkpoint
  -> restore simulator + RNG state
  -> deterministic fast-forward to target generation
  -> provide render state for UI/analysis
```

## Determinism guarantees

- All runtime randomness comes from `core/deterministic_rng.DeterministicRNG`.
- Checkpoints persist RNG state snapshots.
- Replays restore RNG state and re-step deterministically from checkpoint.

## Checkpoint payload (v1)

```json
{
  "generation_index": 0,
  "step_index": 100,
  "population_state": [...],
  "environment_state": {...},
  "metrics": {"mean_agent_x_position": 4.5, "step_count": 100.0},
  "rng_state": {"seed": 1234, "python_rng_state": "..."},
  "timestamp": 1730000000.0,
  "schema_version": "v1"
}
```

## Time-travel algorithm

1. Build list of checkpoint files.
2. Binary-search nearest checkpoint <= target generation.
3. Load + restore simulator state.
4. Fast-forward `target - checkpoint.step_index` steps.
5. Return render state.

## Performance considerations

- Atomic writes use temp-file + rename.
- Checkpoints are sharded by generation to avoid directory collapse.
- Replay can skip from sparse checkpoints without replaying entire history.
- Optional in-memory LRU cache stores recently used replay states.
