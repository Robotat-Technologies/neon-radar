"""A small generated world and overlay for detection tests (PHASE-3.md M3.2 deliverable 8).

M3.3's generator with the settings M3.6's `test_world_parity.py` uses: 80 companies, 120 people,
one scenario and one look-alike per typology, seed 5, the period 1 January 2025 to 1 July 2026.
Generated at run time and never committed (2.9); cached for the session (about 20 seconds).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from functools import cache
from typing import Any

from neonradar_detect.source import Window
from neonradar_ingest.synth import overlay, world
from neonradar_ingest.synth.namesource import default_names

SEED = 5
CONFIG = world.WorldConfig(companies=80, people=120, agent_every=40, professional_every=40)
START, END = date(2025, 1, 1), date(2026, 7, 1)
WINDOW = Window(
    datetime.combine(START, datetime.min.time(), UTC),
    datetime.combine(END, datetime.min.time(), UTC),
)


@cache
def _records(seed: int) -> tuple[dict[str, Any], ...]:
    names = default_names()
    base = world.generate(seed, CONFIG, names)
    cfg = overlay.OverlayConfig(seed, START, END, illicit=1, lookalikes=1)
    return tuple(base + overlay.generate(base, {"nr_synthetic": "synthetic"}, cfg, names).records)


def small_world(seed: int = SEED) -> list[dict[str, Any]]:
    """The world's and the overlay's records, synthetic only."""
    return list(_records(seed))
