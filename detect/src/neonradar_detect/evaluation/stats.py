"""Wilson score interval for the published detection figures (PHASE-3.md 3.4).

The same formula and worked example as `neonradar_resolve.stats` (PHASE-2.md 3.4). It is repeated
here so that `neonradar_detect` does not depend on `neonradar_resolve`, which brings Splink, DuckDB
and PyArrow.
"""

from __future__ import annotations

import math

Z_95 = 1.959963984540054  # two-sided 95 percent normal quantile


def wilson_interval(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (Wilson 1927)."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n and n > 0")
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = (z / denominator) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high
