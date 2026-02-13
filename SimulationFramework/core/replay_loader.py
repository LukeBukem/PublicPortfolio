"""Replay loading abstraction for engine-agnostic playback frames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.simulation_runner_api import ReplayStream


class ReplayLoader:
    """Loads serialized replay frames without coupling to simulation internals."""

    def __init__(self, base_output_dir: str | Path) -> None:
        self.base_output_dir = Path(base_output_dir)

    def get_replay(self, run_id: str) -> ReplayStream:
        replay_path = self.base_output_dir / run_id / "replay_frames.json"
        if not replay_path.exists():
            return ReplayStream(run_id=run_id, frames=[])
        payload: list[dict[str, Any]] = json.loads(replay_path.read_text(encoding="utf-8"))
        return ReplayStream(run_id=run_id, frames=payload)
