"""Per-typology figures over several generator seeds (PHASE-3.md 7.6.3).

Following `evaluation-alerting.md` 2.3: scenarios of one seed share background activity, so the
figures carry two 95 percent intervals, the pooled Wilson interval over all scenarios (or alerts)
and a t interval over the per-seed rates, and the headline is the wider of the two. A rate with
nothing to count (no planted scenarios, or no alerts) is None and is published as "n = 0".
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from neonradar_detect.evaluation.match import Outcome
from neonradar_detect.evaluation.stats import wilson_interval

# two-sided 95 percent quantiles of Student's t, by degrees of freedom
T_975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}

Interval = tuple[float, float]


def t_interval(values: Sequence[float]) -> Interval | None:
    """Mean of per-seed rates plus or minus t * s / sqrt(n), clipped to [0, 1]; None below two
    seeds."""
    n = len(values)
    if n < 2:
        return None
    mean = statistics.fmean(values)
    half = T_975.get(n - 1, 1.960) * statistics.stdev(values) / math.sqrt(n)
    return max(0.0, mean - half), min(1.0, mean + half)


def wider(a: Interval | None, b: Interval | None) -> Interval | None:
    if a is None or b is None:
        return a or b
    return a if (a[1] - a[0]) >= (b[1] - b[0]) else b


@dataclass(frozen=True, slots=True)
class Rate:
    k: int
    n: int
    value: float | None
    wilson: Interval | None
    across_seeds: Interval | None
    headline: Interval | None
    seeds_counted: int


def rate(pairs: Sequence[tuple[int, int]]) -> Rate:
    """`pairs` holds (k, n) per seed; seeds with n = 0 do not enter the across-seed interval."""
    k = sum(x for x, _ in pairs)
    n = sum(y for _, y in pairs)
    per_seed = [x / y for x, y in pairs if y > 0]
    w = wilson_interval(k, n) if n > 0 else None
    t = t_interval(per_seed)
    return Rate(k, n, k / n if n else None, w, t, wider(w, t), len(per_seed))


@dataclass(frozen=True, slots=True)
class Figures:
    typology: str
    seeds: int
    recall: Rate
    precision: Rate
    alerts: int
    true: int
    duplicate: int
    lookalike: int
    partial: int
    other: int
    background: int
    lookalikes: int
    lookalikes_alerted: int
    payment_coverage: float | None
    seed_recall: tuple[float, float, float] | None  # minimum, median, maximum


def figures(per_seed: Mapping[int, Mapping[str, Outcome]], typology: str) -> Figures:
    rows = [per_seed[s][typology] for s in sorted(per_seed) if typology in per_seed[s]]
    recall = rate([(o.detected, o.planted) for o in rows])
    precision = rate([(o.true, o.alerts) for o in rows])
    labelled = sum(o.labelled_payments for o in rows)
    covered = sum(o.covered_payments for o in rows)
    seed_rates = sorted(o.detected / o.planted for o in rows if o.planted)
    spread = (seed_rates[0], statistics.median(seed_rates), seed_rates[-1]) if seed_rates else None
    return Figures(
        typology,
        len(rows),
        recall,
        precision,
        sum(o.alerts for o in rows),
        sum(o.true for o in rows),
        sum(o.duplicate for o in rows),
        sum(o.lookalike for o in rows),
        sum(o.partial for o in rows),
        sum(o.other for o in rows),
        sum(o.background for o in rows),
        sum(o.lookalikes for o in rows),
        sum(o.lookalikes_alerted for o in rows),
        covered / labelled if labelled else None,
        spread,
    )


def macro(all_figures: Sequence[Figures]) -> dict[str, float | int | None]:
    """Unweighted means over typologies; F1 is the mean of per-typology F1
    (`evaluation-alerting.md` 1.5)."""
    recalls = [f.recall.value for f in all_figures if f.recall.value is not None]
    precisions = [f.precision.value for f in all_figures if f.precision.value is not None]
    f1s = []
    for f in all_figures:
        r, p = f.recall.value, f.precision.value
        if r is not None and p is not None:
            f1s.append(0.0 if r + p == 0 else 2 * r * p / (r + p))
    return {
        "typologies": len(all_figures),
        "macro_recall": statistics.fmean(recalls) if recalls else None,
        "macro_precision": statistics.fmean(precisions) if precisions else None,
        "macro_precision_typologies": len(precisions),
        "macro_f1": statistics.fmean(f1s) if f1s else None,
    }
