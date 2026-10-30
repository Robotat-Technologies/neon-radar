"""structuring 0.2.0: several cash deposits just below a threshold, within a few days, into the
accounts of one holder (PHASE-1.md 7.2 entry 1, corrected by `typology-detection-definitions.md`
section 1; PHASE-3.md 7.3.1).

The threshold is `threshold` in the deposit's currency. Whether a deposit of exactly the threshold
counts as below it depends on the rule the threshold stands for: the US report covers cash "of
more than $10,000" (31 CFR 1010.311), so 10,000 exactly is below it. GBP is modelled on the UK
high value dealer rule ("£10,000 or more", MLR 2017 reg 27(3)) and EUR on the AMLR's due diligence
threshold ("at least EUR 10 000", from 10 July 2027), so there it is not; both mappings are
modelling choices (7.3.1). `below_inclusive_currencies` lists the currencies that use the US form.
A deposit is in band when `threshold * (1 - band) <= amount` and it is below the threshold.

For each holder and currency, a window of `window_days` starting at a deposit qualifies when it
holds at least `min_deposits` in-band deposits and in-band deposits are at least `min_band_share` of
the holder's cash deposits in it. A daily total above the threshold is not required (the US
definition covers amounts that "need not exceed" it "on any single day"): it adds to the strength.
Overlapping qualifying windows merge into one finding.

pattern_strength = 0.3 * min(1, deposits / (2 * min_deposits)) + 0.3 * mean closeness to the
threshold (0 at the lower edge of the band, 1 at the threshold) + 0.2 * min(1, (branches - 1) / 2)
+ 0.2 if some day's in-band total exceeds the threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Deposit, HolderDeposits
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "structuring"
VERSION = "0.2.0"
QUERIES = ("holder_cash_deposits.cypher",)


@dataclass(frozen=True, slots=True)
class Params:
    threshold: float = 10000.0
    band: float = 0.1
    below_inclusive_currencies: tuple[str, ...] = ("USD",)
    window_days: int = 7
    min_deposits: int = 3
    min_band_share: float = 0.5
    max_candidates: int = 100_000


def in_band(amount: float, currency: str, p: Params) -> bool:
    low = p.threshold * (1 - p.band)
    if currency in p.below_inclusive_currencies:
        return low <= amount <= p.threshold
    return low <= amount < p.threshold


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    band_low = p.threshold * (1 - p.band)
    candidates = source.holder_cash_deposits(
        band_low, p.threshold, p.min_deposits, window.start, window.end, p.max_candidates
    )
    findings: dict[tuple[str, ...], Finding] = {}
    for cand in candidates:
        for f in _evaluate(cand, p):
            findings.setdefault(f.edge_ids, f)  # a joint account appears under each holder
    ordered = sorted(
        findings.values(), key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids)
    )
    return DetectorOutput(ordered, {"candidates": len(candidates)})


def _evaluate(cand: HolderDeposits, p: Params) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    for currency in sorted({d.currency for d in cand.deposits}):
        deps = [d for d in cand.deposits if d.currency == currency]
        spans: list[tuple[int, int]] = []
        j = 0
        for i, d in enumerate(deps):
            j = max(j, i)
            while j + 1 < len(deps) and deps[j + 1].ts < d.ts + span:
                j += 1
            banded = [x for x in deps[i : j + 1] if in_band(x.amount, currency, p)]
            if len(banded) >= p.min_deposits and len(banded) / (j - i + 1) >= p.min_band_share:
                spans.append((i, j))
        for i, j in _merge(spans):
            out.append(_finding(cand.holder, deps[i : j + 1], currency, p))
    return out


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for i, j in sorted(spans):
        if merged and i <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], j))
        else:
            merged.append((i, j))
    return merged


def _finding(holder: str, window_deps: list[Deposit], currency: str, p: Params) -> Finding:
    band_low = p.threshold * (1 - p.band)
    banded = [d for d in window_deps if in_band(d.amount, currency, p)]
    total = sum(d.amount for d in banded)
    branches = sorted({d.branch for d in banded})
    accounts = sorted({d.account for d in banded})
    by_day: dict[str, list[Deposit]] = {}
    for d in banded:
        by_day.setdefault(d.ts.date().isoformat(), []).append(d)
    day_totals = {day: sum(d.amount for d in ds) for day, ds in by_day.items()}
    closeness = sum((d.amount - band_low) / (p.threshold - band_low) for d in banded) / len(banded)
    above = any(t > p.threshold for t in day_totals.values())
    strength = clip01(
        0.3 * min(1.0, len(banded) / (2 * p.min_deposits))
        + 0.3 * min(1.0, closeness)
        + 0.2 * min(1.0, (len(branches) - 1) / 2)
        + (0.2 if above else 0.0)
    )
    first, last = banded[0].ts, banded[-1].ts
    metrics = {
        "deposits": len(banded),
        "total_amount": round(total, 2),
        "threshold": p.threshold,
        "band_low": round(band_low, 2),
        "currency": currency,
        "branches": len(branches),
        "accounts": len(accounts),
        "days": len(by_day),
        "span_days": max(1, math.ceil((last - first).total_seconds() / 86400)),
        "max_day_total": round(max(day_totals.values()), 2),
        "band_share": round(len(banded) / len(window_deps), 4),
    }
    subjects = [Subject(holder, "holder")] + [Subject(a, "receiving_account") for a in accounts]
    return Finding(
        typology=SLUG,
        variant="multi_account" if len(accounts) > 1 else "single_account",
        anchor=accounts[0],
        node_ids=tuple(sorted(set(accounts) | set(branches))),
        edge_ids=tuple(sorted(d.edge_id for d in banded)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(tuple(d.edge_id for d in ds) for _, ds in sorted(by_day.items())),
        window=(first, last),
        activity=True,
    )
