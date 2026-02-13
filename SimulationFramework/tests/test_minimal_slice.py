"""Tests for the minimal vertical slice."""

from engine.minimal_slice import run_minimal_vertical_slice


def test_minimal_vertical_slice_runs_and_preserves_population_size() -> None:
    result = run_minimal_vertical_slice(seed=7)
    assert len(result.fitness) == 2
    assert result.next_population_size == 2


def test_minimal_vertical_slice_is_deterministic_for_seed() -> None:
    first = run_minimal_vertical_slice(seed=99)
    second = run_minimal_vertical_slice(seed=99)
    assert first == second
