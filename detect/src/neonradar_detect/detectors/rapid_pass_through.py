"""rapid_pass_through 0.2.0: an account that passes on what it receives within hours or days,
from several sources (PHASE-1.md 7.2 entry 2; `typology-detection-definitions.md` section 2;
PHASE-3.md 7.3.2).

Per account and currency, inflows are matched to later outflows first in, first out, over the
window and the `history_days` before it, so money an account already held is spent before new
money (a business with a working balance does not pass on what it has just received); the part of
an inflow that leaves within `max_dwell_hours` of arriving counts as passed through (money is
fungible, so this allocation is a modelling choice, not a fact). Windows that start less than
`history_days` after the first payment in the data are skipped: there the earlier balance is
unknown (left-censoring). A window of `window_days` starting at an inflow qualifies when its
inflows total at least `min_inflow`, at least `min_pass_ratio` of that total was passed through,
and the inflows came from at least `min_sources` accounts. Few
beneficiaries make the pattern stronger but are not required ("a small number of foreign
beneficiaries" is a red flag, not the definition). Among qualifying windows the detector takes the
one with the largest passed amount, then the largest that overlaps no window already taken, and so
on, so findings never share an inflow.

pattern_strength = 0.35 * pass ratio + 0.3 * (1 - median dwell / max_dwell_hours)
+ 0.15 * min(1, sources / (2 * min_sources)) + 0.2 * concentration, where concentration is 1 with
at most `max_beneficiaries` beneficiaries and max_beneficiaries / beneficiaries above that.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "rapid_pass_through"
VERSION = "0.2.0"
QUERIES = ("flows_by_inbound.cypher", "paid_time_range.cypher")


@dataclass(frozen=True, slots=True)
class Params:
    window_days: int = 7
    max_dwell_hours: int = 72
    min_inflow: float = 10000.0
    min_pass_ratio: float = 0.9
    min_sources: int = 3
    max_beneficiaries: int = 3
    history_days: int = 90
    max_candidates: int = 100_000


def cents(amount: float) -> int:
    """Amounts carry two decimals (C1 R7), so whole cents keep every sum exact."""
    return round(amount * 100)


@dataclass(slots=True)
class _Lot:
    pay: Pay
    left: int  # cents
    passed: int = 0  # cents
    dwell_hours: list[float] = field(default_factory=list)
    out_edges: set[str] = field(default_factory=set)
    beneficiaries: set[str] = field(default_factory=set)


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.history_days))
    candidates = source.flows_by_inbound(
        math.ceil(p.min_sources / 2),
        window.start - timedelta(days=p.history_days),
        window.end,
        None,
        p.window_days * 24,
        p.max_candidates,
    )
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_evaluate(flows, judged_from, p))
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates)})


def _match(flows: AccountFlows, currency: str, p: Params) -> list[_Lot]:
    """FIFO matching of outflows to earlier inflows of one currency."""
    dwell = timedelta(hours=p.max_dwell_hours)
    events = [(x.ts, 0, x) for x in flows.inflows if x.currency == currency]
    events += [(x.ts, 1, x) for x in flows.outflows if x.currency == currency]
    events.sort(key=lambda e: (e[0], e[1], e[2].edge_id))
    lots: list[_Lot] = []
    queue: list[_Lot] = []
    for _, kind, pay in events:
        if kind == 0:
            lot = _Lot(pay, cents(pay.amount))
            lots.append(lot)
            queue.append(lot)
            continue
        need = cents(pay.amount)
        while need > 0 and queue:
            lot = queue[0]
            take = min(lot.left, need)
            lot.left -= take
            need -= take
            if pay.ts - lot.pay.ts <= dwell:
                lot.passed += take
                lot.dwell_hours.append((pay.ts - lot.pay.ts).total_seconds() / 3600)
                lot.out_edges.add(pay.edge_id)
                lot.beneficiaries.add(pay.counterparty)
            if lot.left == 0:
                queue.pop(0)
    return lots


def _evaluate(flows: AccountFlows, judged_from: datetime, p: Params) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    for currency in sorted({x.currency for x in flows.inflows}):
        lots = _match(flows, currency, p)
        windows = [w for w in _windows(lots, span, p) if lots[w[1]].pay.ts >= judged_from]
        chosen: list[tuple[int, int]] = []
        for _, i, j in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
        for i, j in sorted(chosen):
            out.append(_finding(flows, lots[i:j], currency, p))
    return out


def _windows(lots: list[_Lot], span: timedelta, p: Params) -> list[tuple[int, int, int]]:
    """Qualifying windows as (passed cents, first lot, end lot), two pointers over time order."""
    sources: Counter[str] = Counter()
    beneficiaries: Counter[str] = Counter()
    inflow = passed = 0
    found = []
    j = 0
    for i, lot in enumerate(lots):
        while j < len(lots) and lots[j].pay.ts < lot.pay.ts + span:
            inflow += cents(lots[j].pay.amount)
            passed += lots[j].passed
            sources[lots[j].pay.counterparty] += 1
            beneficiaries.update(lots[j].beneficiaries)
            j += 1
        if (
            inflow >= cents(p.min_inflow)
            and passed >= p.min_pass_ratio * inflow
            and len(sources) >= p.min_sources
            and len(beneficiaries) > 0
        ):
            found.append((passed, i, j))
        inflow -= cents(lot.pay.amount)
        passed -= lot.passed
        sources[lot.pay.counterparty] -= 1
        if sources[lot.pay.counterparty] == 0:
            del sources[lot.pay.counterparty]
        beneficiaries.subtract(lot.beneficiaries)
        beneficiaries = +beneficiaries
    return found


def _finding(flows: AccountFlows, lots: list[_Lot], currency: str, p: Params) -> Finding:
    inflow = sum(cents(lot.pay.amount) for lot in lots) / 100
    passed = sum(lot.passed for lot in lots) / 100
    sources = sorted({lot.pay.counterparty for lot in lots})
    beneficiaries = sorted(set().union(*(lot.beneficiaries for lot in lots)))
    dwells = sorted(h for lot in lots for h in lot.dwell_hours)
    median_dwell = statistics.median(dwells) if dwells else float(p.max_dwell_hours)
    out_edges = sorted(set().union(*(lot.out_edges for lot in lots)))
    in_edges = sorted(lot.pay.edge_id for lot in lots)
    ratio = passed / inflow
    concentration = (
        1.0
        if len(beneficiaries) <= p.max_beneficiaries
        else p.max_beneficiaries / len(beneficiaries)
    )
    strength = clip01(
        0.35 * min(1.0, ratio)
        + 0.3 * (1 - min(1.0, median_dwell / p.max_dwell_hours))
        + 0.15 * min(1.0, len(sources) / (2 * p.min_sources))
        + 0.2 * concentration
    )
    first = min(lot.pay.ts for lot in lots)
    last_out = max((x.ts for x in flows.outflows if x.edge_id in set(out_edges)), default=first)
    metrics = {
        "inflow_amount": round(inflow, 2),
        "passed_amount": round(passed, 2),
        "pass_ratio": round(ratio, 4),
        "currency": currency,
        "sources": len(sources),
        "beneficiaries": len(beneficiaries),
        "median_dwell_hours": round(median_dwell, 1),
        "window_days": p.window_days,
    }
    subjects = [Subject(flows.account, "pass_through_account")]
    subjects += [Subject(h, "holder") for h in flows.holders]
    in_steps = tuple((e,) for e in in_edges)
    return Finding(
        typology=SLUG,
        variant="",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *sources, *beneficiaries})),
        edge_ids=tuple(sorted(set(in_edges) | set(out_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(*in_steps, tuple(out_edges)),
        window=(first, last_out),
        activity=True,
    )
