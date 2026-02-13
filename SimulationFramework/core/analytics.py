"""Experiment analytics utilities decoupled from GUI widgets."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any


@dataclass(slots=True)
class LeaderboardRow:
    """Leaderboard row with dynamic metrics and metadata."""

    experiment_id: str
    status: str
    environment: str
    parameters: dict[str, Any]
    summary: dict[str, float]


def build_summary(metrics_history: list[dict[str, float]]) -> dict[str, float]:
    """Build aggregate and derived metrics from generation-level history."""
    if not metrics_history:
        return {
            "mean_fitness": 0.0,
            "max_fitness": 0.0,
            "diversity": 0.0,
            "mutation_stats": 0.0,
            "fitness_improvement_rate": 0.0,
            "peak_generation": 0.0,
            "avg_mutation_impact": 0.0,
            "diversity_trend": 0.0,
            "population": 0.0,
            "average_hunger": 0.0,
            "average_lifespan_turns": 0.0,
        }

    means = [float(m.get("mean_fitness", 0.0)) for m in metrics_history]
    maxes = [float(m.get("max_fitness", 0.0)) for m in metrics_history]
    diversities = [float(m.get("diversity", 0.0)) for m in metrics_history]
    mutations = [float(m.get("mutation_stats", 0.0)) for m in metrics_history]

    first = means[0] if means else 0.0
    last = means[-1] if means else 0.0
    improvement = (last - first) / max(len(means) - 1, 1)
    peak_index = float(max(range(len(maxes)), key=lambda i: maxes[i])) if maxes else 0.0
    diversity_trend = (diversities[-1] - diversities[0]) / max(len(diversities) - 1, 1) if diversities else 0.0

    summary = {
        "mean_fitness": float(mean(means)),
        "max_fitness": float(max(maxes) if maxes else 0.0),
        "diversity": float(mean(diversities) if diversities else 0.0),
        "mutation_stats": float(mean(mutations) if mutations else 0.0),
        "fitness_improvement_rate": float(improvement),
        "peak_generation": float(peak_index),
        "avg_mutation_impact": float(mean(mutations) if mutations else 0.0),
        "diversity_trend": float(diversity_trend),
    }
    latest = metrics_history[-1]
    if "population" in latest:
        summary["population"] = float(latest.get("population", 0.0))
    if "average_hunger" in latest:
        summary["average_hunger"] = float(latest.get("average_hunger", 0.0))
    if "average_lifespan_turns" in latest:
        summary["average_lifespan_turns"] = float(latest.get("average_lifespan_turns", 0.0))
    return summary


def build_overlay(
    histories: dict[str, list[dict[str, float]]],
    metric_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Create per-run overlay series plus mean/std envelopes."""
    if metric_keys:
        keys = list(metric_keys)
    else:
        observed = {key for history in histories.values() for row in history for key in row.keys()}
        if {"population", "average_hunger", "average_lifespan_turns"} & observed:
            keys = ["population", "average_hunger", "average_lifespan_turns"]
        else:
            keys = ["mean_fitness", "max_fitness", "diversity", "mutation_stats"]
    overlay: dict[str, Any] = {"runs": {}, "stats": {}}

    for run_id, history in histories.items():
        overlay["runs"][run_id] = {
            key: [float(row.get(key, 0.0)) for row in history]
            for key in keys
        }

    for key in keys:
        max_len = max((len(data.get(key, [])) for data in overlay["runs"].values()), default=0)
        means: list[float] = []
        stds: list[float] = []
        for idx in range(max_len):
            values = [data[key][idx] for data in overlay["runs"].values() if idx < len(data[key])]
            if not values:
                means.append(0.0)
                stds.append(0.0)
            else:
                means.append(float(mean(values)))
                stds.append(float(pstdev(values) if len(values) > 1 else 0.0))
        overlay["stats"][key] = {"mean": means, "std": stds}

    return overlay
