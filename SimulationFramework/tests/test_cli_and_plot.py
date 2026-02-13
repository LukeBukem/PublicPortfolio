"""Tests for CLI run/batch/plot flow."""

from __future__ import annotations

from pathlib import Path

from cli.main import run_cli


def test_cli_run_and_plot(tmp_path) -> None:
    db_path = tmp_path / "sim.db"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "population_size": 4,
          "generations": 2,
          "mutation_rate": 0.1,
          "environment": "grid",
          "seed": 7,
          "evolution_strategy": "ga"
        }
        """,
        encoding="utf-8",
    )

    assert run_cli(["run", "--config", str(config_path), "--db", str(db_path)]) == 0

    out_path = tmp_path / "plot.png"
    # use latest exp id by reading print from cli is not captured; run plot by choosing latest in logger via CLI not exposed.
    # execute batch run to ensure DB has records, then fetch latest id through direct logger helper.
    from data.logger import SimulationLogger

    logger = SimulationLogger(db_path)
    exp_id = logger.latest_experiment_id()
    logger.close()
    assert exp_id is not None

    assert run_cli(["plot", "--experiment", exp_id, "--db", str(db_path), "--out", str(out_path)]) == 0
    assert Path(out_path).exists()
