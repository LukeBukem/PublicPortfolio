"""Coordinates multiple concurrent live experiments for GUI consumption."""

from __future__ import annotations

import csv
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from configs.loader import ExperimentConfig
from core.analytics import build_overlay, build_summary
from core.config_loader import load_config as load_plugin_config
from core.live_plugin_session import LivePluginSession
from core.live_session import LiveSimulationSession
from data.logger import SimulationLogger


@dataclass
class ExperimentRecord:
    """In-memory record for a live or completed experiment session."""

    experiment_id: str
    config: Any
    config_kind: str = "legacy"
    planned_steps: int = 0
    config_path: str | None = None
    runtime_config_path: str | None = None
    simulation_name: str | None = None
    metrics_db_path: str | None = None
    logger_experiment_id: str | None = None
    metrics_log_path: str | None = None
    last_error: str | None = None
    persisted_refresh_ts: float = 0.0
    status: str = "queued"
    metrics_history: list[dict[str, float]] = field(default_factory=list)
    latest_render_state: dict[str, Any] = field(default_factory=dict)


class ExperimentCoordinator:
    """Manages multiple `LiveSimulationSession` instances concurrently."""

    def __init__(self, base_dir: str | Path = "experiments") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._max_history_points = 4000
        self._lock = threading.Lock()
        self._records: dict[str, ExperimentRecord] = {}
        self._sessions: dict[str, Any] = {}

    def start_experiment(self, config: ExperimentConfig, speed: float = 1.0) -> str:
        experiment_id = f"live-{uuid4().hex[:8]}"
        db_path = self.base_dir / f"{experiment_id}.sqlite"
        record = ExperimentRecord(
            experiment_id=experiment_id,
            config=config,
            config_kind="legacy",
            planned_steps=int(config.generations),
            simulation_name=str(config.environment),
            metrics_db_path=str(db_path),
            status="running",
        )

        def on_update(payload: dict[str, Any]) -> None:
            self._on_session_update(experiment_id, payload)

        session = LiveSimulationSession(config=config, on_update=on_update, db_path=db_path)
        session.set_speed(speed)
        with self._lock:
            self._records[experiment_id] = record
            self._sessions[experiment_id] = session
        session.start()
        return experiment_id

    def start_plugin_experiment(
        self,
        config_path: str | Path,
        steps: int = 200,
        speed: float = 1.0,
        runtime_overrides: dict[str, Any] | None = None,
    ) -> str:
        """Start a plugin-backed live session using core simulator modules."""
        path = Path(config_path)
        plugin_config = load_plugin_config(str(path))
        merged_plugin_config = self._apply_plugin_runtime_overrides(plugin_config, runtime_overrides or {})
        simulation_name = str(plugin_config.get("simulation", "plugin"))
        experiment_id = f"plugin-{uuid4().hex[:8]}"
        runtime_config_path = self.base_dir / f"{experiment_id}_runtime.yaml"
        self._write_runtime_plugin_config(runtime_config_path, merged_plugin_config)
        record = ExperimentRecord(
            experiment_id=experiment_id,
            config=merged_plugin_config,
            config_kind="plugin",
            planned_steps=max(1, int(steps)),
            config_path=str(path),
            runtime_config_path=str(runtime_config_path),
            simulation_name=simulation_name,
            metrics_log_path=str(self.base_dir / f"{experiment_id}_metrics.jsonl"),
            status="running",
        )
        if record.metrics_log_path is not None:
            Path(record.metrics_log_path).write_text("", encoding="utf-8")

        def on_update(payload: dict[str, Any]) -> None:
            self._on_session_update(experiment_id, payload)

        session = LivePluginSession(
            config_path=runtime_config_path,
            steps=max(1, int(steps)),
            on_update=on_update,
        )
        session.set_speed(speed)
        with self._lock:
            self._records[experiment_id] = record
            self._sessions[experiment_id] = session
        session.start()
        return experiment_id

    def list_experiments(self) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._records.values())
        rows = []
        for rec in items:
            history = self._load_persisted_history(rec)
            summary = build_summary(history)
            if rec.config_kind == "legacy" and isinstance(rec.config, ExperimentConfig):
                rows.append(
                    {
                        "experiment_id": rec.experiment_id,
                        "status": rec.status,
                        "population_size": rec.config.population_size,
                        "generations": rec.config.generations,
                        "steps": rec.planned_steps,
                        "mutation_rate": rec.config.mutation_rate,
                        "environment": rec.config.environment,
                        "simulation": rec.simulation_name or rec.config.environment,
                        "seed": rec.config.seed,
                        "mode": "legacy",
                        "error": rec.last_error or "",
                        **summary,
                    }
                )
                continue

            plugin_config = rec.config if isinstance(rec.config, dict) else {}
            evolution = plugin_config.get("evolution_config", {})
            evolution_map = dict(evolution) if isinstance(evolution, dict) else {}
            rows.append(
                {
                    "experiment_id": rec.experiment_id,
                    "status": rec.status,
                    "population_size": int(evolution_map.get("population_size", 0)),
                    "generations": rec.planned_steps,
                    "steps": rec.planned_steps,
                    "mutation_rate": float(evolution_map.get("mutation_rate", 0.0)),
                    "environment": rec.simulation_name or "plugin",
                    "simulation": rec.simulation_name or "plugin",
                    "seed": int(plugin_config.get("seed", evolution_map.get("random_seed", 0))),
                    "mode": "plugin",
                    "config_path": rec.config_path or "",
                    "error": rec.last_error or "",
                    **summary,
                }
            )
        return rows

    def get_render_state(self, experiment_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._records.get(experiment_id)
            return dict(rec.latest_render_state) if rec is not None else {}

    def get_metrics_history(self, experiment_id: str) -> list[dict[str, float]]:
        with self._lock:
            rec = self._records.get(experiment_id)
        if rec is None:
            return []
        history = self._load_persisted_history(rec)
        return list(history)


    def pause_experiment(self, experiment_id: str) -> None:
        with self._lock:
            session = self._sessions.get(experiment_id)
            rec = self._records.get(experiment_id)
            if rec is not None and rec.status in {"running", "queued"}:
                rec.status = "paused"
        if session is not None:
            session.pause()

    def resume_experiment(self, experiment_id: str) -> None:
        with self._lock:
            session = self._sessions.get(experiment_id)
            rec = self._records.get(experiment_id)
            if rec is not None and rec.status == "paused":
                rec.status = "running"
        if session is not None:
            session.resume()

    def is_experiment_paused(self, experiment_id: str) -> bool:
        with self._lock:
            rec = self._records.get(experiment_id)
            if rec is not None and rec.status == "paused":
                return True
            session = self._sessions.get(experiment_id)
        return _session_pause_event_is_set(session)

    def set_experiment_speed(self, experiment_id: str, multiplier: float) -> None:
        with self._lock:
            session = self._sessions.get(experiment_id)
        if session is not None:
            session.set_speed(multiplier)

    def step_experiment(self, experiment_id: str, timeout: float = 2.0) -> bool:
        """Advance one step/generation for a paused experiment if supported."""
        with self._lock:
            session = self._sessions.get(experiment_id)
        if session is None or not hasattr(session, "step_once"):
            return False
        try:
            return bool(session.step_once(timeout=timeout))
        except Exception:
            return False

    def stop_experiment(self, experiment_id: str) -> None:
        with self._lock:
            session = self._sessions.get(experiment_id)
        if session is not None:
            session.stop()
            session.join(timeout=2)

    def delete_experiment(self, experiment_id: str, delete_artifacts: bool = True) -> bool:
        """Stop and remove one experiment record/session from coordinator state."""
        with self._lock:
            session = self._sessions.pop(experiment_id, None)
            rec = self._records.pop(experiment_id, None)

        if session is not None:
            try:
                session.stop()
            except Exception:
                pass
            try:
                session.join(timeout=2)
            except Exception:
                pass

        if rec is None:
            return False

        if delete_artifacts:
            self._delete_record_artifacts(rec)
        return True

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._sessions.keys())
        for experiment_id in ids:
            self.stop_experiment(experiment_id)

    def leaderboard(
        self,
        metric: str = "max_fitness",
        environment: str | None = None,
        mutation_range: tuple[float, float] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.list_experiments()
        filtered = []
        for row in rows:
            if environment and row.get("environment") != environment:
                continue
            if mutation_range is not None:
                lo, hi = mutation_range
                mr = float(row.get("mutation_rate", 0.0))
                if mr < lo or mr > hi:
                    continue
            filtered.append(row)
        return sorted(filtered, key=lambda r: float(r.get(metric, 0.0)), reverse=True)

    def comparison(self, experiment_ids: list[str], metric_keys: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            histories = {}
            for experiment_id in experiment_ids:
                rec = self._records.get(experiment_id)
                histories[experiment_id] = list(rec.metrics_history) if rec is not None else []
        return build_overlay(histories, metric_keys=metric_keys)

    def export_experiment(self, experiment_id: str, out_dir: str | Path) -> dict[str, Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        history = self.get_metrics_history(experiment_id)

        csv_path = out / f"{experiment_id}_metrics.csv"
        json_path = out / f"{experiment_id}_metrics.json"

        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            keys = sorted({k for row in history for k in row}) or ["mean_fitness", "max_fitness", "diversity", "mutation_stats"]
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(history)

        json_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        return {"csv": csv_path, "json": json_path}

    def _on_session_update(self, experiment_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            rec = self._records.get(experiment_id)
            if rec is None:
                return
            event = payload.get("event")
            if event == "generation":
                session = self._sessions.get(experiment_id)
                rec.status = "paused" if _session_pause_event_is_set(session) else "running"
                logger_experiment_id = payload.get("logger_experiment_id")
                if isinstance(logger_experiment_id, str) and logger_experiment_id:
                    rec.logger_experiment_id = logger_experiment_id
                metrics = payload.get("metrics", {})
                if isinstance(metrics, dict):
                    row = {k: float(v) for k, v in metrics.items() if _is_floatable(v)}
                    rec.metrics_history.append(row)
                    rec.persisted_refresh_ts = time.monotonic()
                    if len(rec.metrics_history) > self._max_history_points:
                        rec.metrics_history = rec.metrics_history[::2]
                    if rec.metrics_log_path:
                        try:
                            with Path(rec.metrics_log_path).open("a", encoding="utf-8") as fh:
                                fh.write(json.dumps(row, sort_keys=True) + "\n")
                        except Exception:
                            pass
                render_state = payload.get("render_state")
                if isinstance(render_state, dict) and render_state:
                    rec.latest_render_state = dict(render_state)
            elif event == "complete":
                rec.status = "stopped" if bool(payload.get("stopped", False)) else "completed"
            elif event == "error":
                rec.status = "failed"
                rec.last_error = str(payload.get("message", "unknown error"))
            elif event:
                rec.status = "running"

    def _load_persisted_history(self, rec: ExperimentRecord) -> list[dict[str, float]]:
        now = time.monotonic()
        if rec.status == "running" and rec.metrics_history and (now - rec.persisted_refresh_ts) < 0.5:
            return list(rec.metrics_history)

        if rec.config_kind == "legacy":
            if rec.metrics_db_path:
                logger: SimulationLogger | None = None
                try:
                    logger = SimulationLogger(rec.metrics_db_path)
                    experiment_id = rec.logger_experiment_id or logger.latest_experiment_id()
                    if not experiment_id:
                        return list(rec.metrics_history)
                    rec.logger_experiment_id = str(experiment_id)
                    rows = logger.fetch_metrics(str(experiment_id))
                    normalized: list[dict[str, float]] = []
                    for row in rows:
                        normalized.append(
                            {
                                k: float(v)
                                for k, v in row.items()
                                if k != "generation_index" and _is_floatable(v)
                            }
                        )
                    if normalized:
                        rec.metrics_history = list(normalized)
                        rec.persisted_refresh_ts = now
                        return normalized
                except Exception:
                    pass
                finally:
                    if logger is not None:
                        logger.close()
            return list(rec.metrics_history)

        if rec.metrics_log_path:
            path = Path(rec.metrics_log_path)
            if path.exists():
                try:
                    rows: list[dict[str, float]] = []
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        payload = json.loads(line)
                        if isinstance(payload, dict):
                            rows.append({k: float(v) for k, v in payload.items() if _is_floatable(v)})
                    if rows:
                        rec.metrics_history = list(rows)
                        rec.persisted_refresh_ts = now
                        return rows
                except Exception:
                    pass
        return list(rec.metrics_history)

    def _delete_record_artifacts(self, rec: ExperimentRecord) -> None:
        paths: list[Path] = []
        if rec.metrics_log_path:
            paths.append(Path(rec.metrics_log_path))
        if rec.runtime_config_path:
            paths.append(Path(rec.runtime_config_path))
        if rec.metrics_db_path:
            db_path = Path(rec.metrics_db_path)
            paths.extend([db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")])

        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

    @staticmethod
    def _apply_plugin_runtime_overrides(
        plugin_config: dict[str, Any],
        runtime_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(plugin_config)
        evolution = dict(merged.get("evolution_config", {}))
        sim_params = dict(merged.get("simulation_config", {}))
        override_evolution = runtime_overrides.get("evolution", {})
        override_params = runtime_overrides.get("params", {})
        if isinstance(override_evolution, dict):
            for key in ("population_size", "mutation_rate", "random_seed"):
                if key in override_evolution:
                    evolution[key] = override_evolution[key]
        if isinstance(override_params, dict):
            for key, value in override_params.items():
                if key in sim_params:
                    sim_params[key] = value
        if evolution:
            merged["evolution_config"] = evolution
            if "random_seed" in evolution:
                merged["seed"] = int(evolution["random_seed"])
        if sim_params:
            merged["simulation_config"] = sim_params
        return merged

    @staticmethod
    def _write_runtime_plugin_config(path: Path, config: dict[str, Any]) -> None:
        params = dict(config.get("simulation_config", {}))
        # Synthetic params injected by config loader should not be serialized back
        # into runtime config params because strict schema validation will reject them.
        params.pop("mutation_rate", None)
        payload = {
            "simulation": config.get("simulation", ""),
            "params": params,
            "evolution": config.get("evolution_config", {}),
            "logging": config.get("logging_config", {}),
        }
        try:
            import yaml  # type: ignore

            text = yaml.safe_dump(payload, sort_keys=False)
        except Exception:
            text = _dump_simple_yaml(payload)
        path.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8")


def _is_floatable(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _session_pause_event_is_set(session: Any) -> bool:
    if session is None:
        return False
    state = getattr(session, "_state", None)
    pause_event = getattr(state, "pause_event", None)
    if pause_event is None or not hasattr(pause_event, "is_set"):
        return False
    try:
        return bool(pause_event.is_set())
    except Exception:
        return False


def _dump_simple_yaml(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    def emit_map(mapping: dict[str, Any], indent: int) -> None:
        prefix = " " * indent
        for key, value in mapping.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                emit_map(value, indent + 2)
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")

    emit_map(payload, 0)
    return "\n".join(lines)


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\n", " ").strip()
    if not text:
        return "\"\""
    if any(ch in text for ch in [":", "#", "\"", "'"]):
        return f"\"{text.replace('\"', '\\\"')}\""
    return text
