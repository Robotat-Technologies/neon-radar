"""fan_in_collection 0.2.0: many unrelated accounts paying one account in a short window, which
passes the money on; and the ring variant, a connected group of recently opened accounts
(PHASE-1.md 7.2 entry 5, corrected by `typology-detection-definitions.md` section 5; PHASE-3.md
7.3.5).

Variant `collector`: per account and currency (cash deposits excluded), a window of `window_days`
starting at an inflow qualifies when at least `min_senders` accounts paid in at least `min_total`,
at least `min_person_share` of them are held by people, at most `max_prior_share` of them had a
payment with the account (either way) in the `prior_days` before the window, and the account paid
on at least `min_onward_ratio` of the inflow by `onward_hours` after the window's last inflow.
Windows that start less than `prior_days` after the first payment in the data are skipped, because
earlier relationships cannot be judged there. Recency counts on the collector's side, not the
senders' (senders are often victims): a collector account opened within `new_account_days` before
the window adds to the strength. Findings never share an inflow (largest total first).

Variant `ring`: the PAID relationships of the period between two accounts that were each opened
at most `new_account_days` before the payment form weakly connected components (GDS WCC on Neo4j,
union-find in the reference). A component of `min_ring_accounts` to `max_ring_accounts` accounts,
at least `min_person_share` of them held by people, moving at least `min_total`, with one to three
hubs (accounts paid by at least three other accounts of the component) that at least half of the
component's accounts pay, is a finding. Its evidence adds what fed the ring (payments into its
accounts from outside it in the `window_days` before the ring's first payment and during it) and
what left it (the hubs' payments out up to `onward_hours` after its last payment). WCC is used
rather than Louvain because its result does not depend on the run (7.1.6).

pattern_strength (collector) = 0.3 * min(1, senders / (2 * min_senders)) + 0.25 * (1 - prior
share) + 0.25 * min(1, onward ratio) + 0.2 if the collector account is new.
pattern_strength (ring) = 0.4 * share of accounts paying a hub + 0.3 * min(1, accounts /
(2 * min_ring_accounts)) + 0.3 * person share.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Component, CounterpartyInfo, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "fan_in_collection"
VERSION = "0.2.0"
QUERIES = (
    "counterparty_info.cypher",
    "flows_by_inbound.cypher",
    "paid_time_range.cypher",
    "paid_times.cypher",
    "payments_from.cypher",
    "payments_into.cypher",
    "recent_account_components_drop.cypher",
    "recent_account_components_project.cypher",
    "recent_account_components_wcc.cypher",
    "recent_account_edges.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    window_days: int = 7
    min_senders: int = 10
    min_total: float = 5000.0
    min_person_share: float = 0.8
    prior_days: int = 90
    max_prior_share: float = 0.2
    onward_hours: int = 72
    min_onward_ratio: float = 0.8
    new_account_days: int = 90
    ring: bool = True
    min_ring_accounts: int = 5
    max_ring_accounts: int = 200
    max_candidates: int = 100_000


def _opened(info: CounterpartyInfo) -> date | None:
    return date.fromisoformat(info.opening_date) if len(info.opening_date) == 10 else None


def related_before(
    a: str, b: str, before: datetime, days: int, times: dict[tuple[str, str], tuple[datetime, ...]]
) -> bool:
    """Whether a payment joined a and b, either way, in the `days` before `before` (the times of
    each pair are sorted, so this is two binary searches)."""
    since = before - timedelta(days=days)
    for pair in ((a, b), (b, a)):
        ts = times.get(pair, ())
        i = bisect_left(ts, since)
        if i < len(ts) and ts[i] < before:
            return True
    return False


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0, "components": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.prior_days))
    candidates = source.flows_by_inbound(
        math.ceil(p.min_senders / 2),
        window.start,
        window.end,
        None,
        p.window_days * 24,
        p.max_candidates,
    )
    senders = {x.counterparty for c in candidates for x in c.inflows if x.channel != "cash_deposit"}
    info = source.counterparty_info(senders | {c.account for c in candidates})
    pairs: set[tuple[str, str]] = set()
    for c in candidates:
        for x in c.inflows:
            if x.channel != "cash_deposit":
                pairs.add((x.counterparty, c.account))
                pairs.add((c.account, x.counterparty))
    times = source.paid_times(pairs)
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_collector(flows, info, times, judged_from, p))
    rings = 0
    if p.ring:
        components = source.recent_account_components(
            p.new_account_days, window.start, window.end, p.min_ring_accounts
        )
        rings = len(components)
        ring_info = source.counterparty_info({a for comp in components for a in comp.accounts})
        for comp in components:
            f = _ring(comp, ring_info, source, p)
            if f is not None:
                findings.append(f)
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates), "components": rings})


def _collector(
    flows: AccountFlows,
    info: dict[str, CounterpartyInfo],
    times: dict[tuple[str, str], tuple[datetime, ...]],
    judged_from: datetime,
    p: Params,
) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    onward = timedelta(hours=p.onward_hours)
    for currency in sorted({x.currency for x in flows.inflows}):
        ins = [x for x in flows.inflows if x.currency == currency and x.channel != "cash_deposit"]
        outs = [x for x in flows.outflows if x.currency == currency]
        windows = []
        j = 0
        for i, start in enumerate(ins):
            if start.ts < judged_from:
                continue
            j = max(j, i)
            while j < len(ins) and ins[j].ts < start.ts + span:
                j += 1
            members = ins[i:j]
            senders = sorted({x.counterparty for x in members})
            total = sum(x.amount for x in members)
            if len(senders) < p.min_senders or total < p.min_total:
                continue
            people = sum(1 for s in senders if "Person" in info[s].holder_labels)
            prior = sum(
                1
                for s in senders
                if related_before(s, flows.account, start.ts, p.prior_days, times)
            )
            onward_pays = [x for x in outs if start.ts <= x.ts <= members[-1].ts + onward]
            onward_total = sum(x.amount for x in onward_pays)
            if (
                people / len(senders) >= p.min_person_share
                and prior / len(senders) <= p.max_prior_share
                and onward_total >= p.min_onward_ratio * total
            ):
                windows.append((round(total * 100), i, j, onward_pays, people, prior))
        chosen: list[tuple[int, int]] = []
        for _, i, j, onward_pays, people, prior in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
                out.append(
                    _collector_finding(
                        flows, ins[i:j], onward_pays, info, people, prior, currency, p
                    )
                )
    return out


def _collector_finding(
    flows: AccountFlows,
    members: list[Pay],
    onward_pays: list[Pay],
    info: dict[str, CounterpartyInfo],
    people: int,
    prior: int,
    currency: str,
    p: Params,
) -> Finding:
    senders = sorted({x.counterparty for x in members})
    total = sum(x.amount for x in members)
    opened = _opened(info[flows.account])
    new_collector = (
        opened is not None and (members[0].ts.date() - opened).days <= p.new_account_days
    )
    onward_total = sum(x.amount for x in onward_pays)
    n = len(senders)
    strength = clip01(
        0.3 * min(1.0, n / (2 * p.min_senders))
        + 0.25 * (1 - prior / n)
        + 0.25 * min(1.0, onward_total / total)
        + (0.2 if new_collector else 0.0)
    )
    beneficiaries = sorted({x.counterparty for x in onward_pays})
    metrics = {
        "senders": n,
        "total_amount": round(total, 2),
        "currency": currency,
        "window_days": p.window_days,
        "person_share": round(people / n, 4),
        "prior_share": round(prior / n, 4),
        "onward_ratio": round(onward_total / total, 4),
        "onward_beneficiaries": len(beneficiaries),
        "collector_account_days": (members[0].ts.date() - opened).days if opened else -1,
    }
    subjects = [Subject(flows.account, "collector")] + [
        Subject(h, "collector_holder") for h in flows.holders
    ]
    in_edges = sorted(x.edge_id for x in members)
    out_edges = sorted(x.edge_id for x in onward_pays)
    end = max([members[-1].ts] + [x.ts for x in onward_pays])
    return Finding(
        typology=SLUG,
        variant="collector",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *senders, *beneficiaries})),
        edge_ids=tuple(sorted(set(in_edges) | set(out_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(tuple(in_edges), tuple(out_edges)) if out_edges else (tuple(in_edges),),
        window=(members[0].ts, end),
        activity=True,
    )


def _ring(
    comp: Component, info: dict[str, CounterpartyInfo], source: Source, p: Params
) -> Finding | None:
    n = len(comp.accounts)
    if not p.min_ring_accounts <= n <= p.max_ring_accounts:
        return None
    currencies = Counter(e.currency for e in comp.edges)
    currency = sorted(currencies, key=lambda c: (-currencies[c], c))[0]
    edges = [e for e in comp.edges if e.currency == currency]
    total = sum(e.amount for e in edges)
    people = sum(1 for a in comp.accounts if "Person" in info[a].holder_labels)
    if total < p.min_total or people / n < p.min_person_share:
        return None
    payers: dict[str, set[str]] = {a: set() for a in comp.accounts}
    for e in edges:
        payers[e.target].add(e.source)
    hubs = sorted(a for a in comp.accounts if len(payers[a]) >= 3)
    feeding = set().union(*(payers[h] for h in hubs)) if hubs else set()
    feed_share = len(feeding) / n
    if not 1 <= len(hubs) <= 3 or feed_share < 0.5:
        return None
    strength = clip01(
        0.4 * feed_share + 0.3 * min(1.0, n / (2 * p.min_ring_accounts)) + 0.3 * (people / n)
    )
    first = min(e.ts for e in edges)
    last = max(e.ts for e in edges)
    members = set(comp.accounts)
    fed = sorted(
        (
            x
            for pays in source.payments_into(
                comp.accounts, first - timedelta(days=p.window_days), last
            ).values()
            for x in pays
            if x.counterparty not in members and x.currency == currency
        ),
        key=lambda x: (x.ts, x.edge_id),
    )
    left = sorted(
        (
            x
            for pays in source.payments_from(
                hubs, last, last + timedelta(hours=p.onward_hours)
            ).values()
            for x in pays
            if x.counterparty not in members and x.currency == currency
        ),
        key=lambda x: (x.ts, x.edge_id),
    )
    metrics = {
        "ring_accounts": n,
        "hubs": len(hubs),
        "total_amount": round(total, 2),
        "currency": currency,
        "span_days": max(1, math.ceil((last - first).total_seconds() / 86400)),
        "person_share": round(people / n, 4),
        "feeding_share": round(feed_share, 4),
    }
    metrics["fed_payments"] = len(fed)
    metrics["out_payments"] = len(left)
    subjects = [Subject(a, "collector") for a in hubs]
    subjects += [Subject(h, "collector_holder") for a in hubs for h in info[a].holders]
    into_hubs = tuple(e.edge_id for e in edges if e.target in hubs)
    rest = tuple(e.edge_id for e in edges if e.target not in hubs)
    steps = tuple(
        s
        for s in (tuple(x.edge_id for x in fed), rest, into_hubs, tuple(x.edge_id for x in left))
        if s
    )
    nodes = members | {x.counterparty for x in fed} | {x.counterparty for x in left}
    return Finding(
        typology=SLUG,
        variant="ring",
        anchor=hubs[0],
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(
            sorted(
                {e.edge_id for e in edges} | {x.edge_id for x in fed} | {x.edge_id for x in left}
            )
        ),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=steps,
        window=(min([first, *(x.ts for x in fed)]), max([last, *(x.ts for x in left)])),
        activity=True,
    )
