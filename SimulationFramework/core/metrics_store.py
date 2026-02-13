"""SQLite-backed metrics and metadata store for experiment manager UI."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from core.simulation_runner_api import Metrics, RunMetadata


class MetricsStore:
    """DAO for experiment/run metadata and dynamic metrics payloads."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    params_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
                );

                CREATE TABLE IF NOT EXISTS metrics (
                    run_id TEXT PRIMARY KEY,
                    summary_json TEXT NOT NULL,
                    series_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def save_experiment(self, experiment_id: str, manifest: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO experiments(experiment_id, manifest_json) VALUES(?, ?)",
                (experiment_id, json.dumps(manifest)),
            )

    def upsert_run(self, run: RunMetadata) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs(run_id, experiment_id, status, seed, params_json)
                VALUES(?, ?, ?, ?, ?)
                """,
                (run.run_id, run.experiment_id, run.status, run.seed, json.dumps(run.parameters)),
            )

    def save_metrics(self, metrics: Metrics) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metrics(run_id, summary_json, series_json) VALUES(?, ?, ?)",
                (metrics.run_id, json.dumps(metrics.summary), json.dumps(metrics.series)),
            )

    def list_runs(self) -> list[RunMetadata]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT run_id, experiment_id, status, seed, params_json FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [
            RunMetadata(
                run_id=row["run_id"],
                experiment_id=row["experiment_id"],
                status=row["status"],
                seed=int(row["seed"]),
                parameters=json.loads(row["params_json"]),
            )
            for row in rows
        ]

    def get_metrics(self, run_id: str) -> Metrics:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT summary_json, series_json FROM metrics WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return Metrics(run_id=run_id)
        return Metrics(
            run_id=run_id,
            summary=json.loads(row["summary_json"]),
            series=json.loads(row["series_json"]),
        )
