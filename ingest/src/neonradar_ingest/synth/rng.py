"""Seeded random streams: one root seed, one independent stream per component.

Each component draws from `numpy.random.SeedSequence(seed, spawn_key=(component id,))`, the
same mechanism `SeedSequence.spawn` uses, keyed by a fixed id so that adding a component never
shifts the others. Draw only with `integers`, `random`, `choice` and `permutation`: they are
bit-exact on every platform, while distributions that go through libm (normal, lognormal) may
differ in the last bit between machines.
"""

from collections.abc import Sequence

import numpy as np

COMPONENTS = {
    "names": 1,
    "companies": 2,
    "registry": 3,
    "accounts": 4,
    "background": 5,
    "scenario": 6,
    "join": 7,
}


def stream(seed: int, component: str) -> np.random.Generator:
    """The random stream of one component."""
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(COMPONENTS[component],)))


def slot_stream(seed: int, component: str, slot: int, attempt: int) -> np.random.Generator:
    """The stream of one draw (for example one person's name), keyed by slot and attempt, so
    that drawing one slot again changes no other slot."""
    key = (COMPONENTS[component], slot, attempt)
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=key))


def pick[T](rng: np.random.Generator, items: Sequence[T]) -> T:
    """One item, uniformly."""
    return items[int(rng.integers(len(items)))]


def chance(rng: np.random.Generator, probability: float) -> bool:
    return bool(rng.random() < probability)


def between(rng: np.random.Generator, low: int, high: int) -> int:
    """An integer in [low, high], both ends included."""
    return int(rng.integers(low, high + 1))
