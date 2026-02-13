"""Deterministic RNG container with serializable state snapshots."""

from __future__ import annotations

import base64
import hashlib
import pickle
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class DeterministicRNG:
    """Owns deterministic RNG streams without touching global random state."""

    seed: int

    def __post_init__(self) -> None:
        self.python_rng = random.Random(self.seed)
        try:
            import numpy as np  # type: ignore

            self.numpy_rng = np.random.default_rng(self.seed)
        except ModuleNotFoundError:
            self.numpy_rng = None

        self._streams: dict[str, random.Random] = {}

    def stream(self, name: str) -> random.Random:
        """Return independent deterministic stream by name."""
        if name not in self._streams:
            # Use stable cross-process seed derivation instead of built-in hash().
            digest = hashlib.sha256(f"{self.seed}:{name}".encode("utf-8")).digest()
            derived_seed = int.from_bytes(digest[:8], byteorder="big", signed=False) & 0xFFFFFFFF
            self._streams[name] = random.Random(derived_seed)
        return self._streams[name]

    def snapshot(self) -> dict[str, Any]:
        """Export RNG state to JSON-compatible dictionary."""
        state: dict[str, Any] = {
            "seed": self.seed,
            "python_rng_state": base64.b64encode(pickle.dumps(self.python_rng.getstate())).decode("ascii"),
            "streams": {
                name: base64.b64encode(pickle.dumps(rng.getstate())).decode("ascii")
                for name, rng in self._streams.items()
            },
        }
        if self.numpy_rng is not None:
            bitgen_state = self.numpy_rng.bit_generator.state
            state["numpy_rng_state"] = bitgen_state
        else:
            state["numpy_rng_state"] = None
        return state

    def restore(self, state: dict[str, Any]) -> None:
        """Restore RNG state exported by ``snapshot``."""
        self.seed = int(state["seed"])
        self.python_rng = random.Random(self.seed)
        py_state = pickle.loads(base64.b64decode(state["python_rng_state"].encode("ascii")))
        self.python_rng.setstate(py_state)

        self._streams = {}
        for name, encoded in dict(state.get("streams", {})).items():
            stream_rng = random.Random(self.seed)
            stream_rng.setstate(pickle.loads(base64.b64decode(encoded.encode("ascii"))))
            self._streams[name] = stream_rng

        numpy_state = state.get("numpy_rng_state")
        if numpy_state is None:
            self.numpy_rng = None
            return
        try:
            import numpy as np  # type: ignore

            self.numpy_rng = np.random.default_rng(self.seed)
            self.numpy_rng.bit_generator.state = numpy_state
        except ModuleNotFoundError:
            self.numpy_rng = None
