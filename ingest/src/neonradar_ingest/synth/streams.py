"""Seeded random streams for the generator (PHASE-3.md 7.2.1).

Every stream is derived from the root seed and a tuple of string keys through
`numpy.random.SeedSequence(entropy=seed, spawn_key=...)`, so a stream depends only on what it is
for (for example `("background", "syn-w-co-000123")`), never on how many streams were drawn
before it. Adding a scenario therefore leaves the background of every other entity unchanged.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _key(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def stream(seed: int, *keys: str) -> np.random.Generator:
    """An independent generator for `keys` under the root `seed`."""
    if seed < 0:
        raise ValueError("seed must be a non-negative integer")
    sequence = np.random.SeedSequence(entropy=seed, spawn_key=tuple(_key(k) for k in keys))
    return np.random.Generator(np.random.PCG64(sequence))


def pick(rng: np.random.Generator, items: list[str]) -> str:
    """One item, uniformly; `items` must already be in a stable order."""
    if not items:
        raise ValueError("cannot pick from an empty list")
    return items[int(rng.integers(len(items)))]


def sample(rng: np.random.Generator, items: list[str], k: int) -> list[str]:
    """`k` distinct items in the order drawn; `items` must already be in a stable order."""
    if k > len(items):
        raise ValueError("sample larger than population")
    idx = rng.choice(len(items), size=k, replace=False)
    return [items[int(i)] for i in idx]
