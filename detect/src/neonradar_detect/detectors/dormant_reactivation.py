"""dormant_reactivation 0.2.0: an account with little activity for a long time that suddenly moves
large sums in and out, often soon after a change of director or owner; and the company variants
(PHASE-1.md 7.2 entry 7, corrected by `typology-detection-definitions.md` section 7; PHASE-3.md
7.3.7).

Variant `account`. A quiet period is at least `min_gap_days` with at most `max_quiet_payments`
payments totalling at most `max_quiet_amount` ("an account with little activity", FFIEC), between
a payment of the account, or its opening date, and the payment that ends it. An opening date
counts only when it is on or after the first payment in the data: before that, the data cannot say
whether the account was quiet (left-censoring). The quiet period must end inside the detection
window. A burst follows: the payments from the one that ends the quiet period to `burst_days`
after it, at least `min_burst_payments` of them, in both directions, totalling at least
max(`min_burst_amount`, `burst_ratio` times the account's mean monthly volume before the quiet
period). The ratio keeps seasonal businesses and genuine restarts, which come back at their usual
level, below the threshold. A director appointed to, or an owner acquiring, a holder within
`change_days` before the burst is the change event.

Variant `dormant_company`: an account whose holder's last accounts were filed as dormant
(`accounts_category` DORMANT) with a burst in the window, quiet period or not; an account finding
on such an account takes this variant. Variant `new_company`: a burst that starts at most
`new_company_days` after the holder's incorporation in which "large sums of capital funding" are
"spent or transferred elsewhere in a short period of time" (FATF and Egmont 2018 Annex E): the
burst's inflow alone is at least `min_burst_amount`, its three largest inflows bring at least
`min_inflow_concentration` of it and at least `min_moved_on` of it leaves in the burst. A new
business's ordinary trading, receipts and supplier payments of similar size, does not qualify.
Both variants use `min_burst_amount`.

pattern_strength = 0.3 * min(1, gap days / (2 * min_gap_days)) (0.3 for the company variants)
+ 0.3 * min(1, burst amount / (5 * threshold)) + 0.2 * min(1, burst payments /
(3 * min_burst_payments)) + 0.2 if there is a change event.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountHistory, EntityRow, LinkRow, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "dormant_reactivation"
VERSION = "0.2.0"
QUERIES = (
    "company_account_histories.cypher",
    "entities.cypher",
    "links_into.cypher",
    "paid_time_range.cypher",
    "quiet_account_histories.cypher",
)
DAYS_PER_MONTH = 30.4375


@dataclass(frozen=True, slots=True)
class Params:
    min_gap_days: int = 180
    max_quiet_payments: int = 2
    max_quiet_amount: float = 1000.0
    burst_days: int = 14
    min_burst_payments: int = 4
    min_burst_amount: float = 50000.0
    burst_ratio: float = 10.0
    change_days: int = 30
    company_variants: bool = True
    new_company_days: int = 90
    min_inflow_concentration: float = 0.8
    min_moved_on: float = 0.8
    max_candidates: int = 100_000


@dataclass(frozen=True, slots=True)
class Quiet:
    end: int  # index of the payment that ends the quiet period
    before: (
        int | None
    )  # index of the last payment before it; None when it starts at the opening date
    began: datetime
    payments: int  # payments inside the quiet period


def quiet_periods(
    pays: list[tuple[Pay, str]], opened: datetime | None, window: Window, p: Params
) -> list[Quiet]:
    """The longest quiet period ending at each payment inside the window, in order (the
    explanation says how many payments it holds)."""
    gap = timedelta(days=p.min_gap_days)
    ts = [x.ts for x, _ in pays]
    amt = [x.amount for x, _ in pays]
    out = []
    for j in range(len(pays)):
        if not window.start <= ts[j] < window.end:
            continue
        best: Quiet | None = None
        for m in range(p.max_quiet_payments + 1):
            k = j - m - 1
            if k < 0:
                break
            if ts[j] - ts[k] >= gap and sum(amt[k + 1 : j]) <= p.max_quiet_amount:
                best = Quiet(j, k, ts[k], m)
        if (
            opened is not None
            and j <= p.max_quiet_payments
            and sum(amt[:j]) <= p.max_quiet_amount
            and ts[j] - opened >= gap
        ):
            best = Quiet(j, None, opened, j)
        if best is not None:
            out.append(best)
    return out


def _burst(
    pays: list[tuple[Pay, str]], start: int, threshold: float, p: Params
) -> list[tuple[Pay, str]] | None:
    first = pays[start][0].ts
    burst = [x for x in pays[start:] if x[0].ts <= first + timedelta(days=p.burst_days)]
    directions = {d for _, d in burst}
    if (
        len(burst) >= p.min_burst_payments
        and directions == {"in", "out"}
        and sum(x[0].amount for x in burst) >= threshold
    ):
        return burst
    return None


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"histories": 0, "company_accounts": 0})
    history_start = span[0].date().isoformat()
    histories = source.quiet_account_histories(
        p.min_gap_days,
        p.max_quiet_payments,
        p.max_quiet_amount,
        history_start,
        window.start,
        window.end,
        p.max_candidates,
    )
    company_rows: list[AccountHistory] = []
    if p.company_variants:
        since = (window.start - timedelta(days=p.new_company_days)).date().isoformat()
        company_rows = source.company_account_histories(
            since, window.start, window.end, p.min_burst_payments, p.max_candidates
        )
    holders = sorted({h for x in [*histories, *company_rows] for h in x.holders})
    entities = source.entities(holders)
    changes = source.links_into(holders, ("DIRECTOR_OF", "OWNS"))
    findings: dict[tuple[str, ...], Finding] = {}
    for hist in histories:
        for f in _account_variant(hist, history_start, span[0], entities, changes, p, window):
            findings.setdefault(f.edge_ids, f)
    for hist in company_rows:
        company = _company_variant(hist, entities, changes, p, window)
        if company is not None:
            findings.setdefault(company.edge_ids, company)
    ordered = sorted(
        findings.values(), key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids)
    )
    return DetectorOutput(
        ordered, {"histories": len(histories), "company_accounts": len(company_rows)}
    )


def _account_variant(
    hist: AccountHistory,
    history_start: str,
    data_start: datetime,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
    window: Window,
) -> list[Finding]:
    pays = list(hist.payments)
    opened = None
    if len(hist.opening_date) == 10 and hist.opening_date >= history_start:
        opened = datetime.fromisoformat(hist.opening_date).replace(tzinfo=pays[0][0].ts.tzinfo)
    dormant = any(entities[h].accounts_category.upper() == "DORMANT" for h in hist.holders)
    out = []
    covered = -1
    for q in quiet_periods(pays, opened, window, p):
        if q.end <= covered:
            continue
        if q.before is None:
            mean = 0.0
        else:
            begin = max(data_start, opened) if opened is not None else data_start
            months = max(
                1.0, (pays[q.before][0].ts - begin).total_seconds() / 86400 / DAYS_PER_MONTH
            )
            mean = sum(x.amount for x, _ in pays[: q.before + 1]) / months
        threshold = max(p.min_burst_amount, p.burst_ratio * mean)
        burst = _burst(pays, q.end, threshold, p)
        if burst is None:
            continue
        covered = q.end + len(burst) - 1
        variant = "dormant_company" if dormant and p.company_variants else "account"
        gap_days = (pays[q.end][0].ts - q.began).total_seconds() / 86400
        out.append(
            _finding(
                hist, burst, variant, gap_days, q.payments, mean, threshold, entities, changes, p
            )
        )
    return out


def _company_variant(
    hist: AccountHistory,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
    window: Window,
) -> Finding | None:
    pays = [x for x in hist.payments if window.start <= x[0].ts < window.end]
    for i in range(len(pays)):
        burst = _burst(pays, i, p.min_burst_amount, p)
        if burst is None:
            continue
        begin = burst[0][0].ts.date()
        for h in hist.holders:
            e = entities[h]
            if e.accounts_category.upper() == "DORMANT":
                return _finding(
                    hist,
                    burst,
                    "dormant_company",
                    None,
                    0,
                    0.0,
                    p.min_burst_amount,
                    entities,
                    changes,
                    p,
                )
            if len(e.incorporation_date) == 10:
                age = (begin - date.fromisoformat(e.incorporation_date)).days
                if 0 <= age <= p.new_company_days and _flipped(burst, p):
                    return _finding(
                        hist,
                        burst,
                        "new_company",
                        None,
                        0,
                        0.0,
                        p.min_burst_amount,
                        entities,
                        changes,
                        p,
                    )
    return None


def _flipped(burst: list[tuple[Pay, str]], p: Params) -> bool:
    """Large sums in from few payments, most of it out again within the burst."""
    ins = sorted((x.amount for x, d in burst if d == "in"), reverse=True)
    total_in = sum(ins)
    total_out = sum(x.amount for x, d in burst if d == "out")
    return (
        total_in >= p.min_burst_amount
        and sum(ins[:3]) >= p.min_inflow_concentration * total_in
        and total_out >= p.min_moved_on * total_in
    )


def _change_event(
    holders: tuple[str, ...], begin: datetime, changes: dict[str, list[LinkRow]], p: Params
) -> tuple[str, list[LinkRow]]:
    found: list[LinkRow] = []
    for h in holders:
        for link in changes.get(h, []):
            if len(link.start_date) == 10:
                started = date.fromisoformat(link.start_date)
                if 0 <= (begin.date() - started).days <= p.change_days:
                    found.append(link)
    found.sort(key=lambda x: (x.start_date, x.rel_id))
    if not found:
        return "none", []
    kinds = {x.rel_type for x in found}
    if kinds == {"DIRECTOR_OF"}:
        return "director appointed", found
    if kinds == {"OWNS"}:
        return "new owner", found
    return "director appointed and new owner", found


def _finding(
    hist: AccountHistory,
    burst: list[tuple[Pay, str]],
    variant: str,
    gap_days: float | None,
    quiet_payments: int,
    mean: float,
    threshold: float,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
) -> Finding:
    begin = burst[0][0].ts
    end = burst[-1][0].ts
    amount_in = sum(x.amount for x, d in burst if d == "in")
    amount_out = sum(x.amount for x, d in burst if d == "out")
    currencies = Counter(x.currency for x, _ in burst)
    currency = sorted(currencies, key=lambda c: (-currencies[c], c))[0]
    event, links = _change_event(hist.holders, begin, changes, p)
    gap_score = 0.3 * min(1.0, gap_days / (2 * p.min_gap_days)) if gap_days is not None else 0.3
    strength = clip01(
        gap_score
        + 0.3 * min(1.0, (amount_in + amount_out) / (5 * threshold))
        + 0.2 * min(1.0, len(burst) / (3 * p.min_burst_payments))
        + (0.2 if links else 0.0)
    )
    metrics = {
        "gap_days": math.floor(gap_days) if gap_days is not None else 0,
        "quiet_payments": quiet_payments,
        "pre_gap_monthly_mean": round(mean, 2),
        "burst_threshold": round(threshold, 2),
        "burst_payments": len(burst),
        "burst_in_amount": round(amount_in, 2),
        "burst_out_amount": round(amount_out, 2),
        "burst_amount": round(amount_in + amount_out, 2),
        "currency": currency,
        "burst_days": max(1, math.ceil((end - begin).total_seconds() / 86400)),
        "change_event": event,
    }
    counterparties = {x.counterparty for x, _ in burst}
    subjects = [Subject(hist.account, "reactivated_account")] + [
        Subject(h, "holder") for h in hist.holders
    ]
    pay_edges = tuple(x.edge_id for x, _ in burst)
    link_edges = tuple(x.rel_id for x in links)
    node_ids = {hist.account, *counterparties}
    if links:
        node_ids |= {x.source for x in links} | set(hist.holders)
    steps = (pay_edges,) + ((link_edges,) if link_edges else ())
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=hist.account,
        node_ids=tuple(sorted(node_ids)),
        edge_ids=tuple(sorted(set(pay_edges) | set(link_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=steps,
        window=(begin, end),
        activity=True,
    )
