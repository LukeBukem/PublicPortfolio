"""Desktop app bootstrap for live and replay modes."""

from __future__ import annotations

import argparse
import sys

from ui_desktop.main_window import MainWindow
from ui_desktop.models.render_state_model import RenderStateModel
from ui_desktop.replay_client import ReplayRenderClient
from ui_desktop.websocket_client import WebSocketRenderClient


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evo-desktop")
    parser.add_argument("--live", help="WebSocket endpoint, e.g. ws://localhost:8765")
    parser.add_argument("--replay", help="Experiment directory for replay mode")
    parser.add_argument("--config", default="configs/plugin_example.yaml", help="Config path for replay mode")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if bool(args.live) == bool(args.replay):
        raise SystemExit("Choose exactly one mode: --live <ws://...> OR --replay <experiment_dir>")

    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "PySide6 is required to run desktop GUI. Install with: pip install PySide6 pyqtgraph websockets"
        ) from exc

    app = QApplication(sys.argv)
    model = RenderStateModel(history_size=512)

    if args.live:
        client = WebSocketRenderClient(endpoint=args.live)
        client.start()
    else:
        client = ReplayRenderClient(config_path=args.config, experiment_dir=args.replay)
        client.jump_to_generation(0)

    window = MainWindow(model=model, data_client=client)
    window.show()

    code = app.exec()
    if hasattr(client, "stop"):
        client.stop()
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
