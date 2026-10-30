"""cash_commingling 0.1.0: a business banking far more cash than similar businesses in its area,
with money moving on to its own people (PHASE-1.md 7.2 extended entry; `typology-detection-
definitions.md` section 14; PHASE-3.md 7.3.14).

"The volume of currency in a restaurant used to launder money will most likely be higher in
comparison with similar restaurants in the area" (FFIEC). For each company with cash deposits in
`currency` in the window, the peer group is the other companies of the same sector and the same
area (the postcode district of the registered address, or its city when there is no postcode). A
company with at least `min_peers` peers and at least `min_window_amount` banked qualifies when its
cash in the window is at least `min_ratio` times the median of its peers'. The strength adds the
change over time (the daily mean of the last `change_days` of the window against the
`prior_days` before them, when at least `change_days` of earlier data exist), the share of its
outflows in the window paid to accounts of its owners, directors or their relatives, and cash
banked on Sundays (London time; C2 has no opening hours, so this is a weak proxy).

The generator's calibration is the only benchmark in synthetic data, so the peer comparison is
circular there (section 14, "misleading alerts"); the evaluation report says so.

pattern_strength = 0.4 * min(1, ratio / (2 * min_ratio)) + 0.2 * min(1, max(0, change - 1) / 2)
+ 0.25 * min(1, related-party share / related_party_share) + 0.15 * min(1, 4 * Sunday share).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import CashProfile, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "cash_commingling"
VERSION = "0.1.0"
QUERIES = (
    "cash_profiles.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "paid_time_range.cypher",
    "payments_from.cypher",
    "payments_into.cypher",
)
LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True, slots=True)
class Params:
    currency: str = "GBP"
    min_peers: int = 5
    min_ratio: float = 3.0
    min_window_amount: float = 10000.0
    change_days: int = 90
    prior_days: int = 365
    related_party_share: float = 0.5
    max_candidates: int = 200_000


def area(profile: CashProfile) -> str:
    """The postcode district (outward code), else the city, else ""."""
    code = profile.postal_code.strip().upper()
    if code:
        return code.split()[0] if " " in code else code[:-3]
    return profile.city.strip().casefold()


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"profiles": 0})
    profiles = source.cash_profiles(
        window.start, window.start, window.end, p.currency, p.max_candidates
    )
    groups: dict[tuple[str, str], list[CashProfile]] = defaultdict(list)
    for x in profiles:
        if x.sector and area(x):
            groups[(x.sector, area(x))].append(x)
    flagged: list[tuple[CashProfile, float, int]] = []
    for members in groups.values():
        if len(members) < p.min_peers + 1:
            continue
        for x in members:
            peers = [y.window_pence for y in members if y.holder != x.holder]
            median = statistics.median(peers)
            if median <= 0 or x.window_pence < p.min_window_amount * 100:
                continue
            ratio = x.window_pence / median
            if ratio >= p.min_ratio:
                flagged.append((x, ratio, len(peers)))
    changes: dict[str, float] = {}
    if flagged:
        recent_start = window.end - timedelta(days=p.change_days)
        prior_start = max(recent_start - timedelta(days=p.prior_days), span[0])
        covered = (recent_start - prior_start).total_seconds() / 86400
        if covered >= p.change_days:
            for row in source.cash_profiles(
                prior_start, recent_start, window.end, p.currency, p.max_candidates
            ):
                if row.prior_pence > 0:
                    changes[row.holder] = (row.window_pence / p.change_days) / (
                        row.prior_pence / covered
                    )
    findings = [
        _finding(x, ratio, peers, changes.get(x.holder), source, p, window)
        for x, ratio, peers in sorted(flagged, key=lambda f: f[0].holder)
    ]
    return DetectorOutput(findings, {"profiles": len(profiles), "peer_groups": len(groups)})


def _finding(
    x: CashProfile,
    ratio: float,
    peers: int,
    change: float | None,
    source: Source,
    p: Params,
    window: Window,
) -> Finding:
    deposits = sorted(
        (
            d
            for pays in source.payments_into(x.accounts, window.start, window.end).values()
            for d in pays
            if d.channel == "cash_deposit" and d.currency == p.currency
        ),
        key=lambda d: (d.ts, d.edge_id),
    )
    owners = [
        y for rows in source.links_into([x.holder], ("OWNS", "DIRECTOR_OF")).values() for y in rows
    ]
    people = sorted({y.source for y in owners})
    family = source.links_from(people, ("FAMILY_OF",))
    family_in = source.links_into(people, ("FAMILY_OF",))
    relatives = {y.target for rows in family.values() for y in rows} | {
        y.source for rows in family_in.values() for y in rows
    }
    related = sorted(set(people) | relatives)
    holdings = source.links_from(related, ("HOLDS_ACCOUNT",))
    related_accounts = {y.target for rows in holdings.values() for y in rows}
    outflows: list[Pay] = sorted(
        (
            y
            for pays in source.payments_from(x.accounts, window.start, window.end).values()
            for y in pays
        ),
        key=lambda y: (y.ts, y.edge_id),
    )
    to_related = [y for y in outflows if y.counterparty in related_accounts]
    out_total = sum(y.amount for y in outflows)
    related_share = sum(y.amount for y in to_related) / out_total if out_total > 0 else 0.0
    sunday = (
        sum(1 for d in deposits if d.ts.astimezone(LONDON).weekday() == 6) / len(deposits)
        if deposits
        else 0.0
    )
    strength = clip01(
        0.4 * min(1.0, ratio / (2 * p.min_ratio))
        + 0.2 * (min(1.0, max(0.0, change - 1) / 2) if change is not None else 0.0)
        + 0.25 * min(1.0, related_share / p.related_party_share)
        + 0.15 * min(1.0, 4 * sunday)
    )
    metrics = {
        "cash_amount": round(x.window_pence / 100, 2),
        "cash_deposits": x.window_deposits,
        "currency": p.currency,
        "peers": peers,
        "peer_ratio": round(ratio, 2),
        "sector": x.sector,
        "area": area(x),
        "change_ratio": round(change, 2) if change is not None else -1,
        "related_party_share": round(related_share, 4),
        "sunday_share": round(sunday, 4),
    }
    subjects = [Subject(x.holder, "business")] + [
        Subject(a, "receiving_account") for a in x.accounts
    ]
    deposit_edges = tuple(d.edge_id for d in deposits)
    related_edges = tuple(y.edge_id for y in to_related)
    branches = {d.counterparty for d in deposits}
    holding_links = sorted(
        (
            y
            for rows in holdings.values()
            for y in rows
            if y.target in {z.counterparty for z in to_related}
        ),
        key=lambda y: y.rel_id,
    )
    nodes = {
        x.holder,
        *x.accounts,
        *branches,
        *(y.counterparty for y in to_related),
        *(y.source for y in holding_links),
    }
    edges = set(deposit_edges) | set(related_edges)
    steps: list[tuple[str, ...]] = [deposit_edges]
    if related_edges:
        steps.append(related_edges)
    ends = [d.ts for d in deposits] + [y.ts for y in to_related]
    return Finding(
        typology=SLUG,
        variant="",
        anchor=x.accounts[0],
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=(min(ends), max(ends)),
        activity=True,
    )
