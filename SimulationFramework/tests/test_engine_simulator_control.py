from __future__ import annotations

import random
import threading
import time

from agents.random_agent import RandomAgent
from agents.trivial_genome import TrivialGenome
from core.deterministic_rng import DeterministicRNG
from engine.simulator import Simulator
from environment.dummy import DummyEnvironment
from evolution.trivial import IdentityEvolutionStrategy


def _build_simulator(seed: int = 11) -> Simulator:
    env = DummyEnvironment(agent_ids=("agent_0",), max_steps=1)
    env.reset()
    return Simulator(
        environment=env,
        population=[RandomAgent(genome=TrivialGenome(value=0.1), rng=random.Random(seed), agent_id="agent_0")],
        evolution_strategy=IdentityEvolutionStrategy(),
        seed=seed,
    )


def test_controlled_step_acknowledges_once() -> None:
    sim = _build_simulator()

    thread = threading.Thread(target=lambda: sim.run_controlled(100_000), daemon=True)
    thread.start()

    time.sleep(0.01)
    sim.pause()

    deadline = time.time() + 2.0
    while sim.control_state() != "paused" and time.time() < deadline:
        time.sleep(0.01)

    before = sim.generation_index
    assert sim.request_step_once(timeout=2.0) is True

    # wait for transition back to paused
    deadline = time.time() + 2.0
    while sim.control_state() != "paused" and time.time() < deadline:
        time.sleep(0.01)

    after = sim.generation_index
    assert after >= before

    sim.stop()
    thread.join(timeout=2.0)


def test_named_rng_stream_seed_is_stable() -> None:
    rng_a = DeterministicRNG(42)
    rng_b = DeterministicRNG(42)

    vals_a = [rng_a.stream("policy").random() for _ in range(4)]
    vals_b = [rng_b.stream("policy").random() for _ in range(4)]
    assert vals_a == vals_b
