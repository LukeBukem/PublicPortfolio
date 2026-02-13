"""RenderState serialization utilities."""

from __future__ import annotations

import dataclasses
import json
from typing import Any


MAX_FRAME_BYTES = 10 * 1024 * 1024


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def serialize_state(render_state: Any) -> bytes:
    """Serialize render state into deterministic JSON bytes."""
    payload = _to_jsonable(render_state)
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_FRAME_BYTES:
        raise ValueError(
            f"Serialized frame exceeds max size ({len(data)} bytes > {MAX_FRAME_BYTES})."
        )
    return data
