"""Experiment manager panel for selecting and editing experiment configs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from configs.loader import ExperimentConfig
from core.stack_map import load_stack_config

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import (
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover
    class Signal:  # type: ignore[override]
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, *_args: object, **_kwargs: object) -> None:
            pass

    QWidget = object  # type: ignore


class ExperimentPanel(QWidget):
    """Displays available experiment configs and emits run requests."""

    run_requested = Signal(object)

    def __init__(self, config_dir: str = "configs") -> None:
        super().__init__()
        self.config_dir = Path(config_dir)
        self._loaded_config: ExperimentConfig | None = None
        self._loaded_plugin: dict[str, Any] | None = None
        self._loaded_plugin_path: str | None = None
        self._loaded_path: str | None = None

        if QWidget is object:
            return

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.config_select = QComboBox()
        self.refresh_btn = QPushButton("Refresh Configs")
        self.load_btn = QPushButton("Load")

        self.population = QLineEdit("50")
        self.generations = QLineEdit("100")
        self.mutation_rate = QLineEdit("0.05")
        self.seed = QLineEdit("42")
        self.environment = QLineEdit("dummy")

        config_controls = QHBoxLayout()
        config_controls.addWidget(self.config_select)
        config_controls.addWidget(self.refresh_btn)
        config_controls.addWidget(self.load_btn)

        form.addRow("Experiment config", config_controls)
        form.addRow("Population size", self.population)
        form.addRow("Generations / Steps", self.generations)
        form.addRow("Mutation rate", self.mutation_rate)
        form.addRow("Seed", self.seed)
        form.addRow("Environment", self.environment)

        actions = QHBoxLayout()
        self.run_btn = QPushButton("Run Selected Experiment")
        actions.addWidget(self.run_btn)

        self.status = QLabel("Select a config and load it.")

        root.addLayout(form)
        root.addLayout(actions)
        root.addWidget(self.status)

        self.refresh_btn.clicked.connect(self.refresh_configs)
        self.load_btn.clicked.connect(self.load_selected)
        self.config_select.currentTextChanged.connect(self._invalidate_loaded_cache)
        self.run_btn.clicked.connect(self.emit_run_request)

        self.refresh_configs()

    def refresh_configs(self) -> None:
        if QWidget is object:
            return
        self.config_select.clear()
        files = sorted(list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.json")))
        for path in files:
            self.config_select.addItem(str(path))
        self.status.setText(f"Found {len(files)} config file(s).")

    def load_selected(self) -> bool:
        if QWidget is object:
            return False
        path = self.config_select.currentText().strip()
        if not path:
            self.status.setText("No config selected.")
            return False
        self._loaded_plugin = None
        self._loaded_plugin_path = None
        self._loaded_config = None
        self._loaded_path = None

        try:
            stack_name, payload = load_stack_config(path)
        except Exception as exc:
            self.status.setText(f"Failed to load config: {exc}")
            return False

        if stack_name == "generation":
            cfg = payload
            if not isinstance(cfg, ExperimentConfig):
                self.status.setText("Generation config loader returned invalid payload.")
                return False
            self._loaded_config = cfg
            self._loaded_path = path
            self.population.setText(str(cfg.population_size))
            self.generations.setText(str(cfg.generations))
            self.mutation_rate.setText(str(cfg.mutation_rate))
            self.seed.setText(str(cfg.seed))
            self.environment.setText(str(cfg.environment))
            self.status.setText(f"Loaded legacy config {path}")
            return True

        plugin_config = payload
        if not isinstance(plugin_config, dict):
            self.status.setText("Plugin config loader returned invalid payload.")
            return False

        self._loaded_plugin = plugin_config
        self._loaded_plugin_path = path
        self._loaded_path = path

        evolution = plugin_config.get("evolution_config", {})
        evolution_map = dict(evolution) if isinstance(evolution, dict) else {}
        self.population.setText(str(int(evolution_map.get("population_size", 0))))
        self.generations.setText("200")
        self.mutation_rate.setText(str(float(evolution_map.get("mutation_rate", 0.0))))
        self.seed.setText(str(int(plugin_config.get("seed", evolution_map.get("random_seed", 0)))))
        self.environment.setText(str(plugin_config.get("simulation", "")))
        self.status.setText(
            f"Loaded plugin config {path}. The 'Generations / Steps' field controls runtime steps."
        )
        return True

    def build_config(self) -> ExperimentConfig:
        extras = {}
        if self._loaded_config is not None:
            extras.update(self._loaded_config.extras)
        extras["environment"] = self.environment.text().strip()
        return ExperimentConfig(
            population_size=int(self.population.text()),
            generations=int(self.generations.text()),
            mutation_rate=float(self.mutation_rate.text()),
            environment=str(self.environment.text().strip()),
            seed=int(self.seed.text()),
            extras=extras,
        )

    def build_run_request(self) -> object:
        """Build run payload for legacy or plugin runtime path."""
        if self._loaded_plugin is not None and self._loaded_plugin_path is not None:
            try:
                steps = max(1, int(self.generations.text()))
            except ValueError:
                steps = 200
            try:
                population_size = max(1, int(self.population.text()))
            except ValueError:
                population_size = 1
            try:
                mutation_rate = float(self.mutation_rate.text())
            except ValueError:
                mutation_rate = 0.0
            try:
                random_seed = int(self.seed.text())
            except ValueError:
                random_seed = 0
            params_overrides: dict[str, Any] = {}
            sim_cfg = self._loaded_plugin.get("simulation_config", {})
            sim_cfg_map = dict(sim_cfg) if isinstance(sim_cfg, dict) else {}
            for candidate in ("initial_agents", "num_agents", "population_size"):
                if candidate in sim_cfg_map:
                    params_overrides[candidate] = population_size
            return {
                "mode": "plugin",
                "config_path": self._loaded_plugin_path,
                "steps": steps,
                "runtime_overrides": {
                    "evolution": {
                        "population_size": population_size,
                        "mutation_rate": mutation_rate,
                        "random_seed": random_seed,
                    },
                    "params": params_overrides,
                },
            }
        return {"mode": "legacy", "config": self.build_config()}

    def emit_run_request(self) -> None:
        typed_values: dict[str, str] = {}
        if QWidget is not object:
            typed_values = {
                "population": self.population.text(),
                "generations": self.generations.text(),
                "mutation_rate": self.mutation_rate.text(),
                "seed": self.seed.text(),
                "environment": self.environment.text(),
            }
        selected_path = self.config_select.currentText().strip() if QWidget is not object else ""
        if selected_path and selected_path != (self._loaded_path or ""):
            if not self.load_selected():
                return
            if typed_values:
                self.population.setText(typed_values["population"])
                self.generations.setText(typed_values["generations"])
                self.mutation_rate.setText(typed_values["mutation_rate"])
                self.seed.setText(typed_values["seed"])
                self.environment.setText(typed_values["environment"])
        cfg = self.build_run_request()
        self.status.setText("Dispatching run request...")
        self.run_requested.emit(cfg)

    def _invalidate_loaded_cache(self, _path: str) -> None:
        self._loaded_plugin = None
        self._loaded_plugin_path = None
        self._loaded_config = None
        self._loaded_path = None
