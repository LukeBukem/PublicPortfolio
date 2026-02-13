# Evolution Simulation

This repository has two runnable simulation stacks.

- Generation stack: `engine/`, `agents/`, `environment/`, `evolution/`, `main.py`, `cli/main.py`
- Plugin stack: `core/`, `simulations/`, `streaming/`, replay/checkpoint modules

Use the generation stack for `evo run/batch/plot`. Use the plugin stack for dynamic simulation plugins, replay checkpoints, and render streaming.

## 1) Environment setup (once)

### Windows PowerShell
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Optional tools used by docs/tests/GUI:
```bash
pip install pytest PySide6 pyqtgraph websockets
```

## 2) Start a new simulation (generation stack, recommended)

### Step A: Create a new config file
Create `configs/my_new_simulation.yaml`:

```yaml
population_size: 80
generations: 30
mutation_rate: 0.05
environment: wander
seed: 42

evolution_strategy: ga
agent_type: wander

tournament_size: 3
width: 16
height: 16
max_steps: 30
exploration_rate: 0.1
```

Required keys are:
- `population_size`
- `generations`
- `mutation_rate`
- `environment` (`dummy`, `grid`, or `wander`)
- `seed`

### Step B: Run the simulation
```bash
python -m cli.main run --config configs/my_new_simulation.yaml --db simulation_metrics.db
```

The command prints an experiment id. Keep it.

### Step C: Plot metrics for that run
```bash
python -m cli.main plot --experiment <EXPERIMENT_ID> --db simulation_metrics.db --out artifacts/my_new_simulation.png
```

### Step D: Run multiple new simulations (batch)
Create `configs/my_batch.yaml`:

```yaml
experiments:
  - population_size: 80
    generations: 20
    mutation_rate: 0.05
    environment: wander
    seed: 100
    evolution_strategy: ga
    agent_type: wander
    width: 12
    height: 12
    max_steps: 25
  - population_size: 80
    generations: 20
    mutation_rate: 0.10
    environment: wander
    seed: 101
    evolution_strategy: ga
    agent_type: wander
    width: 16
    height: 16
    max_steps: 25
```

Run:
```bash
python -m cli.main batch --config configs/my_batch.yaml --db simulation_metrics.db
```

## 3) Start a new simulation (plugin stack)

This path uses plugin configs like `configs/plugin_example.yaml` and plugins under `simulations/`.
The advanced wandering-room simulation in this repository uses `configs/wandering_agents_adv.yaml`.

### Step A: Create/update plugin runtime config
Example `configs/my_plugin_run.yaml`:

```yaml
simulation: example_sim

params:
  world_size: 30
  num_agents: 60

evolution:
  population_size: 200
  mutation_rate: 0.02
  crossover_rate: 0.70
  elite_fraction: 0.05
  random_seed: 1234

logging:
  log_interval: 10
  checkpoint_interval: 25
  experiment_name: my_plugin_run
```

### Step B: Run plugin simulation with checkpoint output
```bash
python -c "from pathlib import Path; from core.simulator import Simulator; from data.checkpoint_store import CheckpointStore; sim=Simulator('configs/my_plugin_run.yaml', checkpoint_store=CheckpointStore(), experiment_dir=Path('experiments/my_plugin_run')); result=sim.run(steps=100); print(result[-1])"
```

This writes checkpoints under `experiments/my_plugin_run/checkpoints/`.

### Step C: Open replay desktop UI for that run
```bash
python -m ui_desktop.app --replay experiments/my_plugin_run --config configs/my_plugin_run.yaml
```

### Step D: Run the built-in wandering room plugin in the Experiment Manager GUI

```bash
python -m cli.main gui
```

Then in the GUI:
- load `configs/wandering_agents_adv.yaml`
- click `Run Selected Experiment`
- open the `Wandering Agents` tab for per-step grid rendering and agent inspection
- in `Live Run -> Metrics`, the primary wandering metrics are:
  - `population`
  - `average_hunger`
  - `average_lifespan_turns`
- use `Stop Selected` / `Delete Selected` in the Experiments table to stop or remove runs

For `wandering_agents_adv`, offspring variation uses `evolution.mutation_rate` (for example `0.2` = +/-20%).

## 4) GUI entrypoints

- Launch from normal CLI flow:
```bash
python -m cli.main gui
```

- Experiment manager GUI (generation stack live sessions):
```bash
python -m gui.app
```

- Desktop replay/live UI (plugin stack):
```bash
python -m ui_desktop.app --replay experiments/my_plugin_run --config configs/my_plugin_run.yaml
```

or

```bash
python -m ui_desktop.app --live ws://127.0.0.1:8765
```

## 5) Create new behaviors

Use these guides:

- Generation-stack agent behavior guide: `docs/AGENT_BEHAVIOR_GUIDE.md`
- Plugin-stack behavior guide: `docs/PLUGIN_BEHAVIOR_GUIDE.md`
- Full new-simulation guide (world + behavior + reproduction): `docs/NEW_SIMULATION_DETAILED_GUIDE.md`
- Stack boundaries and config map: `docs/STACK_BOUNDARIES.md`
- Full audit report and remediation status: `docs/AUDIT_REPORT.md`

## 6) Fast sanity check

```bash
python -m cli.main run --config configs/example_experiment.yaml --db simulation_metrics.db
```

If that succeeds and prints an experiment id, the default simulation path is working.

## 7) Run wandering_agents_adv tests (exact commands)

From the repository root with your virtual environment activated:

```bash
python -m pytest tests/test_wandering_agents_adv_plugin.py -q
```

Optional GUI test (requires `PySide6`):

```bash
python -m pytest tests/test_wandering_agents_adv_gui.py -q
```

If you want a focused live-session behavior check for pause/step/resume:

```bash
python -m pytest tests/test_experiment_coordinator.py -k pause_step_resume -q
```

## 8) Run wandering_agents_adv in the GUI

```bash
python -m cli.main gui
```

Then:
- Load `configs/wandering_agents_adv.yaml`
- Click `Run Selected Experiment`
- Open `Live Run` for global render + metrics
- Open `Wandering Agents` for per-agent click inspection
- In `Live Run`, use `Hide dead agents` to filter dead-agent squares
- In `Live Run -> Metrics`, toggle checkbox series to add/remove plotted metrics

Note: the `Playback` tab is intentionally disabled in this build.

