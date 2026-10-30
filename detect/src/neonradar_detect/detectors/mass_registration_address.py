"""mass_registration_address 0.2.0: many active organisations registered at one address, with the
signals that set a formation factory apart from an ordinary registered agent (PHASE-1.md 7.2
entry 9, corrected by `typology-detection-definitions.md` section 9; PHASE-3.md 7.3.9).

An address qualifies when at least `min_companies` active organisations (no dissolution date, and
a status that is not an inactive one) have it as their registered address and, when `top_share`
is set, its count is at least the nearest-rank (1 - `top_share`) quantile of the counts of all
loaded addresses ("in the top 0.1 percent"). Small synthetic worlds set `top_share` to 0 in their
profile: a quantile over a few thousand addresses would leave only the largest one. The three
Companies House default addresses (by postcode, `exclude_postcodes`) are never findings: companies
are moved there when their own address was not appropriate (Registrar's Rules, Volume 6).

The strength adds four signals: incorporations in bursts (the most organisations incorporated
within `burst_days` of each other, as a share of all), directors shared between organisations at
the address (current directorships only: no end date, or one after the end of the window),
payments among their accounts ("Transacting businesses share the same address", FinCEN; only
when every organisation at the address is synthetic, R-REAL), and a PO box address (Annex E's
"Only a post-box address"; for UK companies, Companies House has also refused PO boxes as
registered offices since 4 March 2024). The evidence
holds at most `max_evidence_companies` organisations (those in the largest burst first, then by
id); the metrics count all of them.

pattern_strength = 0.3 * min(1, companies / (5 * min_companies)) + 0.2 * burst share + 0.2 * share
of organisations with a shared director + 0.2 * min(1, paying pairs / 3) + 0.1 if a PO box.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AddressCluster, EntityRow, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "mass_registration_address"
VERSION = "0.2.0"
QUERIES = (
    "entities.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
    "registered_clusters.cypher",
    "registered_count_quantile.cypher",
)
DEFAULT_ADDRESS_POSTCODES = ("CF14 8LH", "EH7 9HR", "BT1 9DY")
PO_BOX = re.compile(r"\bP\.?\s?O\.?\s+BOX\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Params:
    min_companies: int = 25
    top_share: float = 0.001
    active_only: bool = True
    exclude_postcodes: tuple[str, ...] = DEFAULT_ADDRESS_POSTCODES
    burst_days: int = 30
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def normalise_postcode(value: str) -> str:
    compact = re.sub(r"\s+", "", value).upper()
    return f"{compact[:-3]} {compact[-3:]}" if len(compact) > 3 else compact


def is_po_box(cluster: AddressCluster) -> bool:
    return bool(PO_BOX.search(cluster.full))


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    threshold = p.min_companies
    if p.top_share > 0:
        threshold = max(threshold, source.registered_count_quantile(1 - p.top_share, p.active_only))
    clusters = source.registered_clusters(threshold, p.active_only, p.max_candidates)
    excluded = {normalise_postcode(x) for x in p.exclude_postcodes}
    findings = []
    skipped = 0
    for cluster in clusters:
        if normalise_postcode(cluster.postal_code) in excluded:
            skipped += 1
            continue
        findings.append(_evaluate(cluster, source, p, window))
    return DetectorOutput(
        findings,
        {"candidates": len(clusters), "threshold": threshold, "default_addresses": skipped},
    )


def _burst(members: list[str], entities: dict[str, EntityRow], days: int) -> list[str]:
    dated = sorted(
        (date.fromisoformat(entities[m].incorporation_date), m)
        for m in members
        if len(entities[m].incorporation_date) == 10
    )
    best: list[str] = []
    j = 0
    for i, (start, _) in enumerate(dated):
        while j < len(dated) and dated[j][0] <= start + timedelta(days=days):
            j += 1
        if j - i > len(best):
            best = [m for _, m in dated[i:j]]
    return best


def _evaluate(cluster: AddressCluster, source: Source, p: Params, window: Window) -> Finding:
    members = [m for m, _ in cluster.members]
    rel_of = dict(cluster.members)
    entities = source.entities(members)
    burst = _burst(members, entities, p.burst_days)
    directors = source.links_into(members, ("DIRECTOR_OF",))
    as_of = window.end.date().isoformat()
    by_director: dict[str, list[LinkRow]] = defaultdict(list)
    for m in members:
        for d in directors.get(m, []):
            if d.current(as_of):
                by_director[d.source].append(d)
    shared = {d: links for d, links in by_director.items() if len({x.target for x in links}) >= 2}
    with_shared = {x.target for links in shared.values() for x in links}
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[m].synthetic for m in members):
        for m, links in source.links_from(members, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = m
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
    pairs = {
        tuple(sorted((holder_of[a], holder_of[b])))
        for _, a, b in paying
        if holder_of[a] != holder_of[b]
    }
    n = len(members)
    po_box = is_po_box(cluster)
    strength = clip01(
        0.3 * min(1.0, n / (5 * p.min_companies))
        + 0.2 * (len(burst) / n)
        + 0.2 * (len(with_shared) / n)
        + 0.2 * min(1.0, len(pairs) / 3)
        + (0.1 if po_box else 0.0)
    )
    shown = [*burst, *sorted(set(members) - set(burst))][: p.max_evidence_companies]
    shown_set = set(shown)
    dir_links = sorted(
        (x for links in shared.values() for x in links if x.target in shown_set),
        key=lambda x: x.rel_id,
    )
    metrics = {
        "companies": n,
        "companies_shown": len(shown),
        "incorporated_in_burst": len(burst),
        "burst_days": p.burst_days,
        "shared_directors": len(shared),
        "companies_with_shared_director": len(with_shared),
        "paying_pairs": len(pairs),
        "po_box": po_box,
    }
    steps: list[tuple[str, ...]] = [tuple(sorted(rel_of[m] for m in shown))]
    if dir_links:
        steps.append(tuple(x.rel_id for x in dir_links))
    pay_edges = sorted(
        e for e, a, b in paying if holder_of.get(a) in shown_set and holder_of.get(b) in shown_set
    )
    if pay_edges:
        steps.append(tuple(pay_edges))
    shown_pay = set(pay_edges)
    pay_nodes = {x for e, a, b in paying if e in shown_pay for x in (a, b)}
    return Finding(
        typology=SLUG,
        variant="",
        anchor=cluster.address,
        node_ids=tuple(
            sorted({cluster.address, *shown, *(x.source for x in dir_links), *pay_nodes})
        ),
        edge_ids=tuple(
            sorted({rel_of[m] for m in shown} | {x.rel_id for x in dir_links} | shown_pay)
        ),
        subjects=(Subject(cluster.address, "registered_address"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
