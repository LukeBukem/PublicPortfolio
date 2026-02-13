# Easy Setup Guide (ZIP Download, No Git Needed)

This guide is for people who are **not technical** and who downloaded the project as a **ZIP file from GitHub**.

If you follow the steps exactly, you will be able to:
1. Open the project,
2. Install what it needs,
3. Run a test simulation,
4. Create a chart image,
5. Confirm everything is working.

---

## What you need before starting

Please make sure you have:

- A computer with internet access
- **Python 3.11 or newer** installed
- Permission to install software on your computer
- A terminal app:
  - **Windows:** PowerShell
  - **macOS:** Terminal
  - **Linux:** Terminal

> If you are unsure whether Python is installed, don’t worry—there is a step below to check.

---

## Step 1) Download the ZIP from GitHub

1. Open the project page on GitHub in your web browser.
2. Click the green **Code** button.
3. Click **Download ZIP**.
4. Wait for the ZIP file to finish downloading.

---

## Step 2) Extract (unzip) the project

1. Find the downloaded ZIP file (usually in your **Downloads** folder).
2. Right-click it and choose:
   - **Windows:** “Extract All…”
   - **macOS:** Double-click the ZIP file
   - **Linux:** “Extract Here” or equivalent
3. You should now have a normal folder named similar to:
   - `Evolution-Simulation-main`

---

## Step 3) Open a terminal in the project folder

### Windows (PowerShell)

1. Open the extracted project folder.
2. Click the folder path bar (at the top of File Explorer).
3. Type `powershell` and press Enter.
4. A PowerShell window opens in the correct folder.

### macOS

1. Open **Terminal**.
2. Type `cd ` (with a space after `cd`).
3. Drag the extracted folder into the Terminal window.
4. Press Enter.

### Linux

1. Open Terminal.
2. Use `cd` to move into the extracted folder, for example:
   ```bash
   cd ~/Downloads/Evolution-Simulation-main
   ```

---

## Step 4) Confirm you are in the correct folder

Run:

```bash
pwd
```

- You should see a path ending with your extracted project folder.

Then run:

```bash
ls
```

- You should see files such as `README.md`, `requirements.txt`, and folders like `cli`, `configs`, `tests`.

---

## Step 5) Check Python is installed and version is correct

Try one of these commands:

```bash
python --version
```

If that does not work, try:

```bash
python3 --version
```

On Windows, if needed, try:

```powershell
py --version
```

You need Python **3.11+**.

---

## Step 6) Create a virtual environment (safe project container)

This keeps project packages separate from the rest of your system.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

After activation, you should see `(.venv)` at the start of the terminal line.

---

## Step 7) Upgrade pip (recommended)

Run:

```bash
python -m pip install --upgrade pip
```

---

## Step 8) Install project dependencies

Run:

```bash
pip install -r requirements.txt
```

Optional (recommended): install local CLI command:

```bash
pip install -e .
```

This lets you run `evo ...` directly.

---

## Step 9) Run one simulation (first success check)

Run:

```bash
python -m cli.main run --config configs/example_experiment.json --db simulation_metrics.db
```

What to expect:
- The command finishes without an error.
- It prints a long experiment ID (letters/numbers).

Keep this ID—you’ll use it in the next step.

---

## Step 10) Generate a chart image from the simulation

Replace `<EXPERIMENT_ID>` with the long ID from Step 9:

```bash
python -m cli.main plot --experiment <EXPERIMENT_ID> --db simulation_metrics.db --out artifacts/metrics.png
```

Now open this file:

- `artifacts/metrics.png`

If it opens, your simulation + plotting pipeline works.

---

## Step 11) (Optional) Run a batch of experiments

Run:

```bash
python -m cli.main batch --config configs/example_batch.yaml --db simulation_metrics.db
```

This runs multiple experiment configurations.

---

## Step 12) Run test suite (health check)

Run:

```bash
PYTHONPATH=. pytest -q
```

On Windows PowerShell, run:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

Passing tests confirm your local setup is healthy.

---

## Step 13) Run the wandering_agents_adv test set

Run the plugin behavior tests:

```bash
python -m pytest tests/test_wandering_agents_adv_plugin.py -q
```

Run the GUI panel test (only if `PySide6` is installed):

```bash
python -m pytest tests/test_wandering_agents_adv_gui.py -q
```

Run the live pause/step/resume regression test:

```bash
python -m pytest tests/test_experiment_coordinator.py -k pause_step_resume -q
```

---

## Step 14) Run the wandering_agents_adv simulation in the GUI

Start the app:

```bash
python -m cli.main gui
```

In the app:
1. Select `configs/wandering_agents_adv.yaml`
2. Click `Load`
3. Click `Run Selected Experiment`
4. Open `Live Run` to see live render and metrics
5. Open `Wandering Agents` to click an agent and inspect stats

`Live Run` controls for this simulation include:
- `Hide dead agents` checkbox for render filtering
- metric-series checkboxes for showing/hiding plotted data

Note: the `Playback` tab is intentionally disabled in this build.

---

## Everyday use after setup

Each time you reopen your computer and want to use this project:

1. Open terminal in the project folder.
2. Activate the virtual environment.
3. Run commands.

### Activate again

- macOS/Linux:
  ```bash
  source .venv/bin/activate
  ```
- Windows PowerShell:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

### Deactivate when done

```bash
deactivate
```

---

## Common problems and exact fixes

### Problem A: `python` command not found

Try:

```bash
python3 --version
```

If still not found, install Python 3.11+ from python.org, then reopen terminal.

---

### Problem B: `pip` command not found

Use pip through Python:

```bash
python -m pip install -r requirements.txt
```

---

### Problem C: `ModuleNotFoundError: yaml`

Run:

```bash
pip install pyyaml
```

---

### Problem D: `ModuleNotFoundError` for local packages (`core`, `cli`, etc.) when testing

Use:

```bash
PYTHONPATH=. pytest -q
```

Windows PowerShell:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

---

### Problem E: `evo: command not found`

Run:

```bash
pip install -e .
```

Or use this form (always works):

```bash
python -m cli.main <command>
```

---

### Problem F: Chart file not created

Install matplotlib:

```bash
pip install matplotlib
```

Then re-run the plot command.

---

## Copy/paste quick start (macOS/Linux)

```bash
cd ~/Downloads/Evolution-Simulation-main
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m cli.main run --config configs/example_experiment.json --db simulation_metrics.db
```

## Copy/paste quick start (Windows PowerShell)

```powershell
cd "$HOME\Downloads\Evolution-Simulation-main"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m cli.main run --config configs/example_experiment.json --db simulation_metrics.db
```

---

## You are done ✅

If Step 9 runs successfully and Step 10 creates `artifacts/metrics.png`, the project is installed correctly and ready to use.
