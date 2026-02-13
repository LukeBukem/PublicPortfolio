"""Command-line entry points for running, batching, and plotting simulations."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Allow `python cli/main.py ...` execution from IDEs by adding repo root to sys.path.
if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from configs.loader import ConfigLoader, ExperimentConfig
from data.logger import SimulationLogger
from main import build_components
from visualization.plotting import plot_experiment


def _run_single(config: ExperimentConfig, db_path: Path) -> str:
    logger = SimulationLogger(db_path)
    experiment_id: str | None = None
    try:
        simulator = build_components(config=config, logger=logger)
        simulator.run(config.generations)
        experiment_id = simulator.experiment_id
    finally:
        logger.close()
    if experiment_id is None:
        raise RuntimeError("Expected experiment id when logger is configured.")
    return experiment_id


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evo")
    sub = parser.add_subparsers(dest="command", required=False)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--config", default="configs/example_experiment.yaml")
    run_cmd.add_argument("--db", default="simulation_metrics.db")

    batch_cmd = sub.add_parser("batch")
    batch_cmd.add_argument("--config", default="configs/example_batch.yaml")
    batch_cmd.add_argument("--db", default="simulation_metrics.db")

    plot_cmd = sub.add_parser("plot")
    plot_cmd.add_argument("--experiment", required=True)
    plot_cmd.add_argument("--db", default="simulation_metrics.db")
    plot_cmd.add_argument("--out", default="artifacts/metrics.png")

    gui_cmd = sub.add_parser("gui")
    gui_cmd.add_argument("--live")
    gui_cmd.add_argument("--replay")
    gui_cmd.add_argument("--config", default="configs/plugin_example.yaml")

    args = parser.parse_args(argv)

    if args.command is None:
        try:
            from gui.app import main as manager_main

            return int(manager_main())
        except Exception as exc:
            parser.print_help()
            raise RuntimeError(
                "No command provided. Default GUI launch failed. "
                "Install GUI deps with: pip install PySide6 pyqtgraph websockets "
                "or run headless with: python -m cli.main run --config configs/example_experiment.yaml"
            ) from exc

    if args.command == "run":
        config = ConfigLoader.load(args.config)
        exp_id = _run_single(config, Path(args.db))
        print(exp_id)
        return 0

    if args.command == "batch":
        configs = ConfigLoader.load_many(args.config)
        for config in configs:
            exp_id = _run_single(config, Path(args.db))
            print(exp_id)
        return 0

    if args.command == "plot":
        path = plot_experiment(args.db, args.experiment, args.out)
        print(path)
        return 0

    if args.command == "gui":
        if bool(args.live) or bool(args.replay):
            from ui_desktop.app import main as desktop_main

            forwarded: list[str] = []
            if args.live:
                forwarded.extend(["--live", str(args.live)])
            if args.replay:
                forwarded.extend(["--replay", str(args.replay)])
            if args.config:
                forwarded.extend(["--config", str(args.config)])
            return int(desktop_main(forwarded))

        from gui.app import main as manager_main

        return int(manager_main())

    return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
