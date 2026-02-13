"""SQLite-backed experiment metadata and per-generation metrics logging."""

from __future__ import annotations

import hashlib
import json
import platform
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class GenerationMetrics:
    """Structured per-generation metrics payload."""

    generation_index: int
    mean_fitness: float = 0.0
    max_fitness: float = 0.0
    diversity: float = 0.0
    mutation_stats: float = 0.0


class SimulationLogger:
    """Persist experiment metadata and per-generation metrics in SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self.connection.close()

    def _ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS experiment_metadata (
                experiment_id TEXT PRIMARY KEY,
                config_hash TEXT NOT NULL,
                seed INTEGER NOT NULL,
                config_json TEXT NOT NULL,
                runtime_metadata TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS generation_metrics (
                experiment_id TEXT NOT NULL,
                generation_index INTEGER NOT NULL,
                mean_fitness REAL NOT NULL,
                max_fitness REAL NOT NULL,
                diversity REAL NOT NULL,
                mutation_stats REAL NOT NULL,
                PRIMARY KEY (experiment_id, generation_index),
                FOREIGN KEY (experiment_id)
                    REFERENCES experiment_metadata (experiment_id)
                    ON DELETE CASCADE
            );
            """
        )
        self.connection.commit()

    def start_experiment(self, config: Mapping[str, Any], seed: int, metadata: Mapping[str, Any] | None = None) -> str:
        config_json = json.dumps(dict(config), sort_keys=True)
        runtime_metadata = {"python_version": platform.python_version(), "platform": platform.platform()}
        if metadata:
            runtime_metadata.update(dict(metadata))
        metadata_json = json.dumps(runtime_metadata, sort_keys=True)
        config_hash = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
        deterministic_key = hashlib.sha256(f"{config_hash}:{seed}".encode("utf-8")).hexdigest()
        run_nonce = str(time.time_ns())
        experiment_id = hashlib.sha256(f"{deterministic_key}:{run_nonce}".encode("utf-8")).hexdigest()[:16]
        runtime_metadata["deterministic_key"] = deterministic_key
        metadata_json = json.dumps(runtime_metadata, sort_keys=True)

        self.connection.execute(
            """
            INSERT OR IGNORE INTO experiment_metadata (
                experiment_id, config_hash, seed, config_json, runtime_metadata
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (experiment_id, config_hash, seed, config_json, metadata_json),
        )
        self.connection.commit()
        return experiment_id

    def log_metrics(self, experiment_id: str, generation_index: int, metrics: Mapping[str, float]) -> None:
        row = GenerationMetrics(
            generation_index=generation_index,
            mean_fitness=float(metrics.get("mean_fitness", 0.0)),
            max_fitness=float(metrics.get("max_fitness", 0.0)),
            diversity=float(metrics.get("diversity", 0.0)),
            mutation_stats=float(metrics.get("mutation_stats", 0.0)),
        )
        self.connection.execute(
            """
            INSERT OR REPLACE INTO generation_metrics (
                experiment_id,
                generation_index,
                mean_fitness,
                max_fitness,
                diversity,
                mutation_stats
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                row.generation_index,
                row.mean_fitness,
                row.max_fitness,
                row.diversity,
                row.mutation_stats,
            ),
        )
        self.connection.commit()

    def fetch_metrics(self, experiment_id: str) -> list[dict[str, float]]:
        """Return ordered generation metrics for plotting/analysis."""
        rows = self.connection.execute(
            """
            SELECT generation_index, mean_fitness, max_fitness, diversity, mutation_stats
            FROM generation_metrics
            WHERE experiment_id = ?
            ORDER BY generation_index ASC
            """,
            (experiment_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_experiment_id(self) -> str | None:
        """Return most recently created experiment id, if any."""
        row = self.connection.execute(
            """
            SELECT experiment_id
            FROM experiment_metadata
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """
        ).fetchone()
        return str(row[0]) if row is not None else None
