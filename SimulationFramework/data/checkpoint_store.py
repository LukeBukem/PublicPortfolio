"""Persistent checkpoint storage with atomic writes."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from core.checkpointing import CHECKPOINT_SCHEMA_VERSION, Checkpoint


class CheckpointSchemaError(ValueError):
    """Raised for incompatible or unknown checkpoint schema versions."""


class CheckpointStore:
    """Save/load/list checkpoints without simulator dependencies."""

    def save(self, checkpoint: Checkpoint, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        payload = asdict(checkpoint)
        tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        tmp_path.replace(path)

    def load(self, path: Path) -> Checkpoint:
        payload = json.loads(path.read_text(encoding="utf-8"))
        version = payload.get("schema_version")
        if version != CHECKPOINT_SCHEMA_VERSION:
            raise CheckpointSchemaError(
                f"Checkpoint schema mismatch: expected {CHECKPOINT_SCHEMA_VERSION}, got {version}."
            )
        return Checkpoint(**payload)

    def list_checkpoints(self, experiment_dir: Path) -> list[Path]:
        base = experiment_dir / "checkpoints"
        if not base.exists():
            return []
        # hierarchical safe traversal
        files = [p for p in base.rglob("*.chk") if p.is_file()]
        return sorted(files)

    def checkpoint_path(self, experiment_dir: Path, generation_index: int) -> Path:
        shard = generation_index // 1000
        return experiment_dir / "checkpoints" / f"shard_{shard:06d}" / f"gen_{generation_index:08d}.chk"
