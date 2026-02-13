# Agent Behavior Guide (Generation Stack)

This guide is for adding new agent behavior used by `main.py` + `cli/main.py`.

## Target path

Use this guide when your simulation is started with:

```bash
python -m cli.main run --config <config> --db simulation_metrics.db
```

## 1) Create a new agent class

Create `agents/my_behavior_agent.py`.

Example skeleton:

```python
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Sequence

from agents.base import Agent
from agents.genome import Genome


@dataclass
class MyBehaviorAgent(Agent):
    genome: Genome
    rng: random.Random
    agent_id: str = ""
    exploration_rate: float = 0.1

    def act(self, observation: Any) -> int:
        if not isinstance(observation, dict) or "action_space" not in observation:
            raise ValueError("Observation must include 'action_space'.")

        action_space: Sequence[int] = observation["action_space"]
        if not action_space:
            raise ValueError("Action space must be non-empty.")

        if self.rng.random() < self.exploration_rate:
            return int(self.rng.choice(list(action_space)))

        # Replace this with your behavior logic.
        return int(action_space[0])

    def get_genome(self) -> Genome:
        return self.genome

    def set_genome(self, genome: Genome) -> None:
        self.genome = genome
```

## 2) Wire it into population creation

Register it in `engine/component_registry.py`.

Pattern:

```python
from engine.component_registry import register_agent_factory


def _my_behavior_agent_factory(agent_id, genome, rng, config):
    return MyBehaviorAgent(
        genome=genome,
        rng=rng,
        agent_id=agent_id,
        exploration_rate=float(config.get("exploration_rate", 0.1)),
    )


register_agent_factory("my_behavior", _my_behavior_agent_factory)
```

No changes are needed in `main.py` once the factory is registered.

## 3) Configure and run

Create a config such as `configs/my_behavior.yaml`:

```yaml
population_size: 100
generations: 30
mutation_rate: 0.05
environment: wander
seed: 42

evolution_strategy: ga
agent_type: my_behavior
exploration_rate: 0.05
width: 20
height: 20
max_steps: 30
```

Run:

```bash
python -m cli.main run --config configs/my_behavior.yaml --db simulation_metrics.db
```

## 4) Behavior design checklist

- Determinism: behavior should be reproducible for a fixed seed.
- Action validity: always pick from `observation["action_space"]`.
- Failure mode: raise clear errors on malformed observation payloads.
- Compatibility: avoid depending on environment internals not in observations.

## 5) Recommended tests

Add tests under `tests/`:

- action is always inside action space
- deterministic behavior for same seed and same observation
- end-to-end run through `build_components` + `simulator.run_generation()`

