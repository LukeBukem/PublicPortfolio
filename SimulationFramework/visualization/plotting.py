"""Plot utilities for persisted simulation metrics."""

from __future__ import annotations

from pathlib import Path

from data.logger import SimulationLogger


def plot_experiment(db_path: str | Path, experiment_id: str, output_path: str | Path) -> Path:
    """Render fitness/diversity curves for an experiment from SQLite logs.

    If matplotlib is unavailable, writes a plaintext summary to ``output_path``.
    """
    logger = SimulationLogger(db_path)
    rows = logger.fetch_metrics(experiment_id)
    logger.close()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib.pyplot as plt  # type: ignore

        generations = [int(row["generation_index"]) for row in rows]
        mean_fitness = [float(row["mean_fitness"]) for row in rows]
        max_fitness = [float(row["max_fitness"]) for row in rows]
        diversity = [float(row["diversity"]) for row in rows]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax1.plot(generations, mean_fitness, label="mean_fitness")
        ax1.plot(generations, max_fitness, label="max_fitness")
        ax1.set_ylabel("fitness")
        ax1.legend()

        ax2.plot(generations, diversity, label="diversity", color="tab:green")
        ax2.set_ylabel("diversity")
        ax2.set_xlabel("generation")
        ax2.legend()

        fig.tight_layout()
        fig.savefig(output)
        plt.close(fig)
    except ModuleNotFoundError:
        lines = ["generation_index,mean_fitness,max_fitness,diversity,mutation_stats"]
        for row in rows:
            lines.append(
                f"{row['generation_index']},{row['mean_fitness']},{row['max_fitness']},{row['diversity']},{row['mutation_stats']}"
            )
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return output
