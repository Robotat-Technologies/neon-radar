"""recycled_directors 0.1.0: one person serving as director of many unrelated companies, or
appointed to many in a short time (PHASE-1.md 7.2 extended entry; `typology-detection-
definitions.md` section 12; PHASE-3.md 7.3.12).

Registry evidence only. Candidates are the people with DIRECTOR_OF relationships to at least
min(`min_active_appointments`, `burst_appointments`) organisations. The companies are first put
into groups: two of them are in one group when one owns or consolidates the other or a common
parent owns or consolidates both, because appointments across one group are ordinary ("directors
across one group", the look-alike of section 12). A person qualifies when the active appointments
(no end date on or before the end of the window, company active) span at least
`min_active_appointments` groups, or when appointments starting within `burst_days` of each other
span at least `burst_appointments` groups. Short tenures (ended within `short_tenure_days`), a
nominee appointment, a directorship of a company owned by the person's own relative (`FAMILY_OF`
an owner, "family members with no role", Annex E) and payments among the companies (only when
all are synthetic, R-REAL) add to the strength.

The subject is a person, so on a real profile the policy withholds every finding about a real
person (R-REAL (b)); the counts appear in the run summary.

pattern_strength = 0.3 * min(1, active groups / (2 * min_active_appointments)) + 0.25 * min(1,
burst groups / (2 * burst_appointments)) + 0.15 * min(1, short tenures / 3) + 0.15 * (nominee or
family) + 0.15 * min(1, paying pairs / 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, Hub, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "recycled_directors"
VERSION = "0.1.0"
QUERIES = (
    "entities.cypher",
    "hubs.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
)
INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})


@dataclass(frozen=True, slots=True)
class Params:
    min_active_appointments: int = 10
    burst_appointments: int = 5
    burst_days: int = 30
    short_tenure_days: int = 90
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def _active(e: EntityRow) -> bool:
    return not e.dissolution_date and e.status.casefold() not in INACTIVE


def groups(companies: list[str], owns_into: dict[str, list[LinkRow]]) -> dict[str, str]:
    """Each company's group: the smallest company id reachable through ownership or consolidation
    between the companies or through a common parent."""
    parent = {c: c for c in companies}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_parent: dict[str, list[str]] = {}
    for c in companies:
        for link in owns_into.get(c, []):
            if link.source in parent:
                union(link.source, c)
            by_parent.setdefault(link.source, []).append(c)
    for children in by_parent.values():
        for other in children[1:]:
            union(children[0], other)
    return {c: find(c) for c in companies}


def _span(links: list[LinkRow], group_of: dict[str, str], days: int) -> list[LinkRow]:
    """The appointments starting within `days` of each other that span the most groups."""
    dated = sorted(
        (date.fromisoformat(x.start_date), x.rel_id, x) for x in links if len(x.start_date) == 10
    )
    best: list[LinkRow] = []
    best_groups = 0
    j = 0
    for i, (start, _, _) in enumerate(dated):
        while j < len(dated) and dated[j][0] <= start + timedelta(days=days):
            j += 1
        chosen = [x for _, _, x in dated[i:j]]
        n = len({group_of[x.target] for x in chosen})
        if n > best_groups:
            best, best_groups = chosen, n
    return best


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    hubs = source.hubs(
        "DIRECTOR_OF", min(p.min_active_appointments, p.burst_appointments), p.max_candidates
    )
    findings = []
    for hub in hubs:
        f = _evaluate(hub, source, p, window)
        if f is not None:
            findings.append(f)
    return DetectorOutput(findings, {"candidates": len(hubs)})


def _evaluate(hub: Hub, source: Source, p: Params, window: Window) -> Finding | None:
    companies = sorted({x.target for x in hub.links})
    entities = source.entities([hub.hub, *companies])
    if "Person" not in entities[hub.hub].labels:
        return None
    as_of = window.end.date().isoformat()
    owns_into = source.links_into(companies, ("OWNS", "CONSOLIDATES"))
    group_of = groups(companies, owns_into)
    active = [
        x
        for x in hub.links
        if not (x.end_date and x.end_date <= as_of) and _active(entities[x.target])
    ]
    active_groups = len({group_of[x.target] for x in active})
    burst = _span(list(hub.links), group_of, p.burst_days)
    burst_groups = len({group_of[x.target] for x in burst})
    if active_groups < p.min_active_appointments and burst_groups < p.burst_appointments:
        return None
    short = [
        x
        for x in hub.links
        if len(x.start_date) == 10
        and len(x.end_date) == 10
        and (date.fromisoformat(x.end_date) - date.fromisoformat(x.start_date)).days
        <= p.short_tenure_days
    ]
    nominee = [x for x in hub.links if x.is_nominee]
    relatives = {
        x.target for x in source.links_from([hub.hub], ("FAMILY_OF",)).get(hub.hub, [])
    } | {x.source for x in source.links_into([hub.hub], ("FAMILY_OF",)).get(hub.hub, [])}
    family = sorted(
        (
            o
            for c in companies
            for o in owns_into.get(c, [])
            if o.rel_type == "OWNS" and o.source in relatives
        ),
        key=lambda x: x.rel_id,
    )
    pairs: set[tuple[str, str]] = set()
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[c].synthetic for c in companies):
        for c, links in source.links_from(companies, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = c
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
        pairs = {
            (min(holder_of[a], holder_of[b]), max(holder_of[a], holder_of[b]))
            for _, a, b in paying
            if holder_of[a] != holder_of[b]
        }
    strength = clip01(
        0.3 * min(1.0, active_groups / (2 * p.min_active_appointments))
        + 0.25 * min(1.0, burst_groups / (2 * p.burst_appointments))
        + 0.15 * min(1.0, len(short) / 3)
        + (0.15 if nominee or family else 0.0)
        + 0.15 * min(1.0, len(pairs) / 3)
    )
    ordered = sorted(hub.links, key=lambda x: (x not in burst, x not in active, x.rel_id))
    shown = ordered[: p.max_evidence_companies]
    shown_targets = {x.target for x in shown}
    pay_edges = sorted(
        e
        for e, a, b in paying
        if holder_of[a] in shown_targets
        and holder_of[b] in shown_targets
        and holder_of[a] != holder_of[b]
    )
    pay_set = set(pay_edges)
    family_shown = [x for x in family if x.target in shown_targets]
    metrics = {
        "appointments": len(hub.links),
        "active_appointments": len(active),
        "active_groups": active_groups,
        "burst_appointments": len(burst),
        "burst_groups": burst_groups,
        "burst_days": p.burst_days,
        "short_tenures": len(short),
        "nominee_appointments": len(nominee),
        "relative_owned_companies": len({x.target for x in family}),
        "paying_pairs": len(pairs),
        "companies_shown": len(shown_targets),
    }
    steps: list[tuple[str, ...]] = []
    if burst:
        steps.append(tuple(sorted(x.rel_id for x in burst if x.target in shown_targets)))
    rest = sorted(x.rel_id for x in shown if x not in burst)
    if rest:
        steps.append(tuple(rest))
    if family_shown:
        steps.append(tuple(x.rel_id for x in family_shown))
    if pay_edges:
        steps.append(tuple(pay_edges))
    nodes = {hub.hub, *shown_targets, *(x.source for x in family_shown)}
    nodes |= {x for e, a, b in paying if e in pay_set for x in (a, b)}
    edges = {x.rel_id for x in shown} | {x.rel_id for x in family_shown} | pay_set
    return Finding(
        typology=SLUG,
        variant="burst" if burst_groups >= p.burst_appointments else "many_boards",
        anchor=hub.hub,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=(Subject(hub.hub, "director"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
