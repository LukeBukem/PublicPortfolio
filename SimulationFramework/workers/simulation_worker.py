"""Multiprocessing worker stub that emulates simulation execution outputs."""

from __future__ import annotations

import json
import logging
import random
import dataclasses
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def execute_run(task: dict[str, Any]) -> dict[str, Any]:
    """Execute a mock run and write standardized artifacts.

    This worker intentionally avoids simulation business logic. It only generates
    shape-compatible outputs expected by the Experiment Manager.
    """

    run_id = str(task["run_id"])
    output_dir = Path(task["output_dir"]) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    seed = int(task["seed"])
    generations = int(task.get("generations", 20))
    config_path = task.get("config_path")
    if isinstance(config_path, str) and config_path.strip():
        return _execute_plugin_run(task, output_dir, seed, generations, config_path.strip())

    rng = random.Random(seed)

    fitness = []
    diversity = []
    complexity = []
    for g in range(generations):
        fitness.append(0.5 + (g / max(1, generations)) + rng.random() * 0.05)
        diversity.append(max(0.0, 1.0 - g / max(1, generations) + rng.random() * 0.05))
        complexity.append(10 + g + rng.randint(0, 3))

    summary = {
        "fitness_score": float(max(fitness)),
        "diversity_score": float(sum(diversity) / len(diversity)),
        "convergence_time": float(generations),
        "genome_complexity": float(sum(complexity) / len(complexity)),
    }
    series = {
        "fitness": fitness,
        "diversity": diversity,
        "genome_complexity": complexity,
    }

    replay_frames = [
        {"frame": idx, "agents": [{"id": i, "position": [rng.random(), rng.random()]} for i in range(10)]}
        for idx in range(min(40, generations * 2))
    ]

    (output_dir / "metrics.json").write_text(
        json.dumps({"summary": summary, "series": series}, indent=2), encoding="utf-8"
    )
    (output_dir / "genome_snapshots.json").write_text(
        json.dumps({"run_id": run_id, "snapshots": []}, indent=2), encoding="utf-8"
    )
    (output_dir / "replay_frames.json").write_text(json.dumps(replay_frames), encoding="utf-8")
    (output_dir / "logs.txt").write_text(f"run_id={run_id}\nseed={seed}\n", encoding="utf-8")

    LOGGER.info("Completed mock run %s", run_id)
    return {
        "run_id": run_id,
        "seed": seed,
        "summary": summary,
        "series": series,
        "status": "completed",
    }


def _execute_plugin_run(
    task: dict[str, Any],
    output_dir: Path,
    seed: int,
    generations: int,
    config_path: str,
) -> dict[str, Any]:
    run_id = str(task["run_id"])
    replay_frames: list[dict[str, Any]] = []
    metrics_rows: list[dict[str, float]] = []
    logs = [f"run_id={run_id}", f"seed={seed}", f"config_path={config_path}"]
    try:
        from core.simulator import Simulator

        sim = Simulator(config_path)
        sim.sim.reset()
        for step in range(generations):
            sim.step_index = step + 1
            sim.sim.step()

            raw_metrics = sim.sim.get_metrics()
            metrics = {str(k): float(v) for k, v in dict(raw_metrics).items() if _is_floatable(v)}
            metrics_rows.append(metrics)

            replay_frames.append(
                {
                    "frame": step,
                    "agents": _extract_agents(sim.sim.get_render_state()),
                }
            )
        sim.sim.close()
    except Exception as exc:
        logs.append(f"error={exc}")
        (output_dir / "logs.txt").write_text("\n".join(logs) + "\n", encoding="utf-8")
        (output_dir / "metrics.json").write_text(
            json.dumps({"summary": {"error": 1.0}, "series": {}}, indent=2),
            encoding="utf-8",
        )
        (output_dir / "replay_frames.json").write_text(json.dumps([], indent=2), encoding="utf-8")
        return {
            "run_id": run_id,
            "seed": seed,
            "summary": {"error": 1.0},
            "series": {},
            "status": "failed",
        }

    series = _series_from_rows(metrics_rows)
    summary = _summary_from_rows(metrics_rows)

    # Keep compatibility keys expected by existing GUI/tests.
    summary.setdefault("fitness_score", float(summary.get("max_fitness", 0.0)))
    summary.setdefault("diversity_score", float(summary.get("diversity", 0.0)))
    summary.setdefault("convergence_time", float(generations))
    summary.setdefault("genome_complexity", float(len(metrics_rows)))
    if "fitness" not in series:
        base = [float(row.get("max_fitness", row.get("mean_fitness", 0.0))) for row in metrics_rows]
        series["fitness"] = base

    (output_dir / "metrics.json").write_text(
        json.dumps({"summary": summary, "series": series}, indent=2),
        encoding="utf-8",
    )
    (output_dir / "genome_snapshots.json").write_text(
        json.dumps({"run_id": run_id, "snapshots": []}, indent=2),
        encoding="utf-8",
    )
    (output_dir / "replay_frames.json").write_text(json.dumps(replay_frames), encoding="utf-8")
    (output_dir / "logs.txt").write_text("\n".join(logs) + "\n", encoding="utf-8")
    return {
        "run_id": run_id,
        "seed": seed,
        "summary": summary,
        "series": series,
        "status": "completed",
    }


def _series_from_rows(rows: list[dict[str, float]]) -> dict[str, list[float]]:
    keys = sorted({k for row in rows for k in row.keys()})
    return {key: [float(row.get(key, 0.0)) for row in rows] for key in keys}


def _summary_from_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    keys = sorted({k for row in rows for k in row.keys()})
    summary: dict[str, float] = {}
    for key in keys:
        vals = [float(row.get(key, 0.0)) for row in rows]
        if not vals:
            continue
        summary[key] = float(sum(vals) / len(vals))
        summary[f"{key}_max"] = float(max(vals))
    if "mean_fitness" in summary:
        summary["mean_fitness"] = float(summary["mean_fitness"])
    if "max_fitness_max" in summary:
        summary["max_fitness"] = float(summary["max_fitness_max"])
    return summary


def _extract_agents(state: Any) -> list[dict[str, Any]]:
    mapping = _to_mapping(state)
    agents = mapping.get("agents", [])
    if not isinstance(agents, list):
        return []

    extracted: list[dict[str, Any]] = []
    for idx, agent in enumerate(agents):
        a = _to_mapping(agent)
        if not a:
            continue
        pos = a.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2 and _is_floatable(pos[0]) and _is_floatable(pos[1]):
            position = [float(pos[0]), float(pos[1])]
        elif "x" in a and "y" in a and _is_floatable(a["x"]) and _is_floatable(a["y"]):
            position = [float(a["x"]), float(a["y"])]
        else:
            position = [float(idx), 0.0]
        extracted.append({"id": str(a.get("id", idx)), "position": position})
    return extracted


def _to_mapping(value: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(value):
        converted = dataclasses.asdict(value)
        if isinstance(converted, dict):
            return converted
        return {}
    if isinstance(value, dict):
        return dict(value)
    return {}


def _is_floatable(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
