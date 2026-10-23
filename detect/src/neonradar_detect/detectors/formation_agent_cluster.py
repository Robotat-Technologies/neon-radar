"""formation_agent_cluster 0.1.0: one agent behind a burst of company formations whose officers
recur across the companies (PHASE-1.md 7.2 extended entry; `typology-detection-definitions.md`
section 11; PHASE-3.md 7.3.11).

Registry evidence only. Candidates are the agents with REPRESENTS relationships to at least
`min_companies` organisations. An agent qualifies when at least `min_companies` of its clients
were incorporated within `window_days` of each other (the largest such set is the burst) and at
least `min_shared_officers` people or organisations are current directors (no end date, or one
after the end of the window) of two or more burst companies.
The strength adds the share of burst companies with a shared officer, the share registered at one
of the agent's own addresses, nominee officers among the shared ones, and payments among the burst
companies' accounts (only when every burst company is synthetic, R-REAL). Company formation is a
lawful trade: the alert describes a shape, and an ACSP name or an AML supervisor in the register
(not in C2 1.2.0) would be context, never a trigger.

pattern_strength = 0.3 * min(1, burst / (3 * min_companies)) + 0.25 * share with a shared officer
+ 0.15 * share at the agent's address + 0.15 * (a shared officer is a nominee)
+ 0.15 * min(1, paying pairs / 3).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, Hub, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "formation_agent_cluster"
VERSION = "0.1.0"
QUERIES = (
    "entities.cypher",
    "hubs.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    min_companies: int = 10
    window_days: int = 30
    min_shared_officers: int = 2
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def incorporation_burst(members: list[str], entities: dict[str, EntityRow], days: int) -> list[str]:
    """The largest set of `members` incorporated within `days` of the first of them (earliest set
    on a tie), in date order."""
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


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    hubs = source.hubs("REPRESENTS", p.min_companies, p.max_candidates)
    findings = []
    for hub in hubs:
        f = _evaluate(hub, source, p, window)
        if f is not None:
            findings.append(f)
    return DetectorOutput(findings, {"candidates": len(hubs)})


def _evaluate(hub: Hub, source: Source, p: Params, window: Window) -> Finding | None:
    rep_of = {x.target: x for x in hub.links}
    clients = sorted(rep_of)
    entities = source.entities([*clients, hub.hub])
    burst = incorporation_burst(clients, entities, p.window_days)
    if len(burst) < p.min_companies:
        return None
    directors = source.links_into(burst, ("DIRECTOR_OF",))
    as_of = window.end.date().isoformat()
    by_officer: dict[str, list[LinkRow]] = defaultdict(list)
    for c in burst:
        for d in directors.get(c, []):
            if d.current(as_of):
                by_officer[d.source].append(d)
    shared = {o: links for o, links in by_officer.items() if len({x.target for x in links}) >= 2}
    if len(shared) < p.min_shared_officers:
        return None
    with_shared = {x.target for links in shared.values() for x in links}
    nominee = any(x.is_nominee for links in shared.values() for x in links)
    agent_addresses = {
        x.target for x in source.links_from([hub.hub], ("HAS_ADDRESS",)).get(hub.hub, [])
    }
    registered = source.links_from(burst, ("HAS_ADDRESS",))
    at_agent = {
        c: x
        for c in burst
        for x in registered.get(c, [])
        if x.role == "registered" and x.target in agent_addresses
    }
    pairs: set[tuple[str, str]] = set()
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[c].synthetic for c in burst):
        for c, links in source.links_from(burst, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = c
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
        pairs = {
            (min(holder_of[a], holder_of[b]), max(holder_of[a], holder_of[b]))
            for _, a, b in paying
            if holder_of[a] != holder_of[b]
        }
    n = len(burst)
    strength = clip01(
        0.3 * min(1.0, n / (3 * p.min_companies))
        + 0.25 * len(with_shared) / n
        + 0.15 * len(at_agent) / n
        + (0.15 if nominee else 0.0)
        + 0.15 * min(1.0, len(pairs) / 3)
    )
    shown = [*sorted(with_shared, key=burst.index), *(c for c in burst if c not in with_shared)]
    shown = shown[: p.max_evidence_companies]
    shown_set = set(shown)
    officer_links = sorted(
        (x for links in shared.values() for x in links if x.target in shown_set),
        key=lambda x: x.rel_id,
    )
    address_links = sorted(
        (x for c, x in at_agent.items() if c in shown_set), key=lambda x: x.rel_id
    )
    pay_edges = sorted(
        e
        for e, a, b in paying
        if holder_of[a] in shown_set and holder_of[b] in shown_set and holder_of[a] != holder_of[b]
    )
    pay_set = set(pay_edges)
    pay_nodes = {x for e, a, b in paying if e in pay_set for x in (a, b)}
    first, last = entities[burst[0]].incorporation_date, entities[burst[-1]].incorporation_date
    metrics = {
        "clients": len(clients),
        "incorporated_in_burst": n,
        "burst_first": first,
        "burst_last": last,
        "window_days": p.window_days,
        "shared_officers": len(shared),
        "companies_with_shared_officer": len(with_shared),
        "at_agent_address": len(at_agent),
        "nominee_officers": sum(1 for links in shared.values() if any(x.is_nominee for x in links)),
        "paying_pairs": len(pairs),
        "companies_shown": len(shown),
    }
    steps: list[tuple[str, ...]] = [tuple(sorted(rep_of[c].rel_id for c in shown))]
    if officer_links:
        steps.append(tuple(x.rel_id for x in officer_links))
    if address_links:
        steps.append(tuple(x.rel_id for x in address_links))
    if pay_edges:
        steps.append(tuple(pay_edges))
    nodes = {
        hub.hub,
        *shown,
        *(x.source for x in officer_links),
        *(x.target for x in address_links),
        *pay_nodes,
    }
    edges = (
        {rep_of[c].rel_id for c in shown}
        | {x.rel_id for x in officer_links}
        | {x.rel_id for x in address_links}
    )
    return Finding(
        typology=SLUG,
        variant="",
        anchor=hub.hub,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges | pay_set)),
        subjects=(Subject(hub.hub, "agent"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
