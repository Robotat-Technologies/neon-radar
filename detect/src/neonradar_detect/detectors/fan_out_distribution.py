"""fan_out_distribution 0.2.0: one account paying many new counterparties in a short window, who
then move the money on (PHASE-1.md 7.2 entry 6; `typology-detection-definitions.md` section 6;
PHASE-3.md 7.3.6).

Per account and currency, a window of `window_hours` starting at an outflow qualifies when it pays
at least `min_recipients` accounts at least `min_total` in all, at most `max_prior_share` of the
recipients had a payment with the account (either way) in the `prior_days` before the window, and
at least `min_onward_share` of the recipients paid out at least `onward_fraction` of what they
received within `onward_hours` of receiving it (cash withdrawals or transfers). Similar amounts and
round amounts add to the strength but are not required. Windows that start less than `prior_days`
after the first payment in the data are skipped. Findings never share an outflow (largest total
first).

pattern_strength = 0.3 * min(1, recipients / (2 * min_recipients)) + 0.3 * (1 - prior share)
+ 0.2 * onward share + 0.2 * max(amount similarity, round share), where amount similarity is
1 - min(1, coefficient of variation / max_amount_cv).
"""

from __future__ import annotations

import math
import statistics
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta

from neonradar_detect.detectors.fan_in_collection import related_before
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "fan_out_distribution"
VERSION = "0.2.0"
QUERIES = (
    "flows_by_outbound.cypher",
    "paid_time_range.cypher",
    "paid_times.cypher",
    "payments_from.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    window_hours: int = 72
    min_recipients: int = 10
    min_total: float = 5000.0
    prior_days: int = 90
    max_prior_share: float = 0.2
    max_amount_cv: float = 0.2
    round_unit: float = 100.0
    onward_hours: int = 72
    onward_fraction: float = 0.8
    min_onward_share: float = 0.5
    max_candidates: int = 100_000


def _cv(amounts: list[float]) -> float:
    mean = statistics.fmean(amounts)
    return statistics.pstdev(amounts) / mean if mean > 0 else 0.0


def _round(amount: float, unit: float) -> bool:
    return round(amount * 100) % round(unit * 100) == 0


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.prior_days))
    candidates = source.flows_by_outbound(
        math.ceil(p.min_recipients / 2), window.start, window.end, p.window_hours, p.max_candidates
    )
    pairs: set[tuple[str, str]] = set()
    recipients: set[str] = set()
    for c in candidates:
        for x in c.outflows:
            pairs.add((c.account, x.counterparty))
            pairs.add((x.counterparty, c.account))
            recipients.add(x.counterparty)
    times = source.paid_times(pairs)
    onward = source.payments_from(
        recipients, window.start, window.end + timedelta(hours=p.onward_hours)
    )
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_evaluate(flows, times, onward, judged_from, p))
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates)})


def _moved_on(
    received: list[Pay], paid_out: list[Pay], times: list[datetime], p: Params
) -> list[Pay] | None:
    """The recipient's payments (`paid_out`, in time order, with their `times`) that moved on
    `onward_fraction` of what it received within `onward_hours` of receiving it, or None."""
    got = sum(x.amount for x in received)
    start = min(x.ts for x in received)
    until = max(x.ts for x in received) + timedelta(hours=p.onward_hours)
    moved = paid_out[bisect_left(times, start) : bisect_right(times, until)]
    return moved if sum(x.amount for x in moved) >= p.onward_fraction * got else None


def _evaluate(
    flows: AccountFlows,
    times: dict[tuple[str, str], tuple[datetime, ...]],
    onward: dict[str, list[Pay]],
    judged_from: datetime,
    p: Params,
) -> list[Finding]:
    out = []
    span = timedelta(hours=p.window_hours)
    for currency in sorted({x.currency for x in flows.outflows}):
        outs = [x for x in flows.outflows if x.currency == currency]
        paid_out = {
            r: sorted(
                (x for x in onward.get(r, []) if x.currency == currency),
                key=lambda x: (x.ts, x.edge_id),
            )
            for r in {x.counterparty for x in outs}
        }
        paid_times = {r: [x.ts for x in pays] for r, pays in paid_out.items()}
        windows = []
        j = 0
        for i, first in enumerate(outs):
            if first.ts < judged_from:
                continue
            j = max(j, i)
            while j < len(outs) and outs[j].ts < first.ts + span:
                j += 1
            members = outs[i:j]
            recips = sorted({x.counterparty for x in members})
            total = sum(x.amount for x in members)
            if len(recips) < p.min_recipients or total < p.min_total:
                continue
            allowed_prior = math.floor(p.max_prior_share * len(recips) + 1e-9)
            prior = 0
            for r in recips:
                if related_before(flows.account, r, first.ts, p.prior_days, times):
                    prior += 1
                    if prior > allowed_prior:
                        break
            if prior > allowed_prior:
                continue
            moved_by: dict[str, list[Pay]] = {}
            for r in recips:
                received = [x for x in members if x.counterparty == r]
                moved = _moved_on(received, paid_out[r], paid_times[r], p)
                if moved is not None:
                    moved_by[r] = moved
            if (
                prior / len(recips) <= p.max_prior_share
                and len(moved_by) / len(recips) >= p.min_onward_share
            ):
                windows.append((round(total * 100), i, j, prior, moved_by))
        chosen: list[tuple[int, int]] = []
        for _, i, j, prior, moved_by in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
                out.append(_finding(flows, outs[i:j], prior, moved_by, currency, p))
    return out


def _finding(
    flows: AccountFlows,
    members: list[Pay],
    prior: int,
    moved_by: dict[str, list[Pay]],
    currency: str,
    p: Params,
) -> Finding:
    recips = sorted({x.counterparty for x in members})
    n = len(recips)
    total = sum(x.amount for x in members)
    amounts = [x.amount for x in members]
    cv = _cv(amounts)
    round_share = sum(1 for a in amounts if _round(a, p.round_unit)) / len(amounts)
    similarity = 1 - min(1.0, cv / p.max_amount_cv) if p.max_amount_cv > 0 else 0.0
    onward_share = len(moved_by) / n
    strength = clip01(
        0.3 * min(1.0, n / (2 * p.min_recipients))
        + 0.3 * (1 - prior / n)
        + 0.2 * onward_share
        + 0.2 * max(similarity, round_share)
    )
    moved = sorted((x for pays in moved_by.values() for x in pays), key=lambda x: (x.ts, x.edge_id))
    second = sorted({x.counterparty for x in moved})
    metrics = {
        "recipients": n,
        "total_amount": round(total, 2),
        "currency": currency,
        "window_hours": p.window_hours,
        "amount_cv": round(cv, 4),
        "round_share": round(round_share, 4),
        "prior_share": round(prior / n, 4),
        "onward_share": round(onward_share, 4),
    }
    subjects = [Subject(flows.account, "distributor")] + [
        Subject(h, "distributor_holder") for h in flows.holders
    ]
    out_edges = tuple(sorted(x.edge_id for x in members))
    onward_edges = tuple(sorted(x.edge_id for x in moved))
    end = max([members[-1].ts] + [x.ts for x in moved])
    return Finding(
        typology=SLUG,
        variant="",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *recips, *second})),
        edge_ids=tuple(sorted(set(out_edges) | set(onward_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(out_edges, onward_edges) if onward_edges else (out_edges,),
        window=(members[0].ts, end),
        activity=True,
    )
