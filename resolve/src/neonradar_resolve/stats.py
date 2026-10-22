"""Precision and agreement statistics for the published figure (PHASE-2.md 3.4 and 7.3)."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple

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


def cohens_kappa(first: Sequence[str], second: Sequence[str]) -> float:
    """Cohen's kappa for two labellers over the same items (Cohen 1960)."""
    if len(first) != len(second) or not first:
        raise ValueError("need two label lists of the same, non-zero length")
    n = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    left, right = Counter(first), Counter(second)
    expected = sum(left[c] * right[c] for c in set(left) | set(right)) / (n * n)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


class SpecificAgreement(NamedTuple):
    positive: float | None  # 2a / (2a + b + c); None when no item could count
    negative: float | None  # 2d / (2d + b + c)
    excluded: int  # items where either label is neither positive nor negative (unsure)


def specific_agreement(
    first: Sequence[str],
    second: Sequence[str],
    positive: str = "same",
    negative: str = "different",
) -> SpecificAgreement:
    """Positive and negative agreement (Cicchetti and Feinstein 1990).

    Reported next to kappa, which can be low or negative when almost every label is the
    same even though the labellers rarely disagree. Only items that both labellers marked
    `positive` or `negative` count; the others are returned as `excluded`.
    """
    if len(first) != len(second) or not first:
        raise ValueError("need two label lists of the same, non-zero length")
    allowed = {positive, negative}
    pairs = [(a, b) for a, b in zip(first, second, strict=True) if a in allowed and b in allowed]
    both_positive = sum(a == b == positive for a, b in pairs)
    both_negative = sum(a == b == negative for a, b in pairs)
    split = len(pairs) - both_positive - both_negative
    pos_denominator = 2 * both_positive + split
    neg_denominator = 2 * both_negative + split
    return SpecificAgreement(
        2 * both_positive / pos_denominator if pos_denominator else None,
        2 * both_negative / neg_denominator if neg_denominator else None,
        len(first) - len(pairs),
    )
