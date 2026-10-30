"""Constrained clustering for NeonRadar entity resolution (PHASE-2.md 7.1.6).

Pure Python and deterministic: the same members, links, hints and config give the same result.
Splink scores pairs; this module decides merges and possible matches, applying the cannot-link
rules X1 to X8 and the merge policy P1 to P6 (PHASE-2.md 7.1.3 and 7.1.4).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace

from neonradar_keys.names import name_similarity

NAME_CHECK_RULES = frozenset({"D1", "D2", "D3", "D4"})
PROBABILITY_DECIMALS = 9  # Splink's floats can differ in the last bits between runs
RULE_ORDER = {"D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6}
CONFLICT_ORDER = ("rule", "record_a", "record_b", "link_method", "link_rule")
COUNTS = (
    "decisions_applied",
    "decisions_awaiting_second_review",
    "decisions_not_applicable",
    "hints_not_applicable",
    "hints_used",
)


@dataclass(frozen=True)
class Member:
    """What the clustering needs to know about one resolvable record (7.1.1)."""

    record_id: str
    dataset: str
    kind: str  # registry | list | leak | synthetic (7.1.1: a synthetic record may be list or leak)
    priority: int  # anchor_priority (contracts/datasets.yaml)
    schema: str
    entity_class: str  # person | org | legal_entity | address
    synthetic: bool
    flag_topics: frozenset[str] = frozenset()  # the record's non-descriptive topics; listed if any
    list_source: str | None = None  # the list a listed record comes from (P6)
    list_party: str | None = None  # set when the record is a whole party of that list (X6)
    company_numbers: frozenset[str] = frozenset()  # the record's own UK company number(s)
    leis: frozenset[str] = frozenset()
    birth_dates: frozenset[str] = frozenset()  # ISO prefixes: 1979, 1979-08, 1979-08-23
    name_keys: frozenset[str] = frozenset()  # from name, alias and previousName, never weakAlias


@dataclass(frozen=True)
class Link:
    record_a: str
    record_b: str
    method: str  # deterministic | probabilistic | human
    rule: str | None = None  # D1 to D7
    probability: float = 1.0
    weight: float | None = None
    features: Mapping[str, str] = field(default_factory=dict)
    strong_evidence: bool = True  # P3: a non-name comparison agrees at a strong level
    birth_or_id_agrees: bool = True  # P6: birth years compatible, or an identifier shared
    model: str | None = None  # person | org: the Splink model that scored a probabilistic link
    reviewers: frozenset[str] = frozenset()  # D7: handles whose newest decision is "same"


@dataclass(frozen=True)
class Config:
    merge_threshold: Mapping[str, float]  # Splink model -> threshold
    candidate_threshold: float
    cluster_cap: int = 30
    name_check_jaro_winkler: float = 0.85
    senior_reviewers: frozenset[str] = frozenset()  # people.er_senior_reviewers


@dataclass
class Candidate:
    record_a: str
    record_b: str
    probability: float | None
    weight: float | None
    method: str  # probabilistic | deterministic | source_hint
    rule: str | None
    reasons: set[str]
    features: Mapping[str, str]


@dataclass
class Result:
    canonical: list[dict[str, object]]
    candidates: list[dict[str, object]]
    conflicts: list[dict[str, object]]
    counts: dict[str, int]


def dates_compatible(left: frozenset[str], right: frozenset[str]) -> bool:
    """X5: compatible when some pair is equal at the precision both have."""
    if not left or not right:
        return True
    return any(a.startswith(b) or b.startswith(a) for a in left for b in right)


def name_check(a: Member, b: Member, threshold: float, strict: bool) -> bool:
    """7.1.2: an exact shared name key; unless strict, also a Jaro-Winkler match."""
    if a.name_keys & b.name_keys:
        return True
    if strict:
        return False
    return any(name_similarity(x, y) >= threshold for x in a.name_keys for y in b.name_keys)


def flags(ms: list[Member]) -> frozenset[str]:
    return frozenset(t for m in ms for t in m.flag_topics)


def p1_reason(left: list[Member], right: list[Member]) -> str | None:
    """P1: merging would give records flag topics they do not have themselves."""
    fl, fr = flags(left), flags(right)
    if fl == fr:
        return None
    return "listed_unlisted" if not fl or not fr else "listed_differently"


def crosses_p2(left: list[Member], right: list[Member]) -> bool:
    """P2: merging would join a leaked record with a record from another kind of source."""
    kl, kr = {m.kind == "leak" for m in left}, {m.kind == "leak" for m in right}
    return (True in kl and False in kr) or (False in kl and True in kr)


def hard_conflict(
    left: list[Member],
    right: list[Member],
    different: set[frozenset[str]],
    common_schema: Callable[[Iterable[str]], str | None],
) -> str | None:
    """The first of X1 to X6 and X8 that merging the two clusters would break (X7 is separate)."""
    both = left + right
    if len({m.synthetic for m in both}) > 1:
        return "X1"
    if common_schema(sorted({m.schema for m in both})) is None:
        return "X2"
    if len({n for m in both for n in m.company_numbers}) > 1:
        return "X3"
    if len({n for m in both for n in m.leis}) > 1:
        return "X4"
    for a in left:
        for b in right:
            if a.entity_class == b.entity_class == "person" and not dates_compatible(
                a.birth_dates, b.birth_dates
            ):
                return "X5"
    parties = {m.list_party for m in left if m.list_party}
    if parties & {m.list_party for m in right if m.list_party}:
        return "X6"
    if any(frozenset((a.record_id, b.record_id)) in different for a in left for b in right):
        return "X8"
    return None


class _Clusters:
    def __init__(self, members: Iterable[Member]) -> None:
        self.members = {m.record_id: m for m in members}
        self.parent = {rid: rid for rid in self.members}
        self.items: dict[str, list[str]] = {rid: [rid] for rid in self.members}

    def find(self, rid: str) -> str:
        while self.parent[rid] != rid:
            self.parent[rid] = self.parent[self.parent[rid]]
            rid = self.parent[rid]
        return rid

    def records(self, root: str) -> list[Member]:
        return [self.members[r] for r in self.items[root]]

    def union(self, a: str, b: str) -> None:
        ra, rb = sorted((self.find(a), self.find(b)))
        self.parent[rb] = ra
        self.items[ra] = sorted(self.items[ra] + self.items.pop(rb))


def resolve(
    members: Iterable[Member],
    deterministic: Iterable[Link],
    probabilistic: Iterable[Link],
    human_same: Iterable[Link],
    human_different: Iterable[tuple[str, str]],
    hints: Iterable[tuple[str, str, str]],
    config: Config,
    common_schema: Callable[[Iterable[str]], str | None],
) -> Result:
    clusters = _Clusters(members)
    known = clusters.members
    counts = dict.fromkeys(COUNTS, 0)
    different: set[frozenset[str]] = set()
    for x, y in human_different:
        if x in known and y in known:
            different.add(frozenset((x, y)))
            counts["decisions_applied"] += 1
        else:
            counts["decisions_not_applicable"] += 1
    accepted: list[Link] = []
    candidates: list[Candidate] = []
    conflicts: list[dict[str, object]] = []

    def conflict(rule: str, a: str, b: str, method: str, link_rule: str | None) -> None:
        ra, rb = sorted((a, b))
        conflicts.append(
            {
                "rule": rule,
                "record_a": ra,
                "record_b": rb,
                "link_method": method,
                "link_rule": link_rule,
            }
        )

    def possible(link: Link, reason: str) -> None:
        a, b = sorted((link.record_a, link.record_b))
        probabilistic_link = link.method == "probabilistic"
        candidates.append(
            Candidate(
                a,
                b,
                link.probability if probabilistic_link else None,
                link.weight if probabilistic_link else None,
                link.method,
                link.rule if link.method == "deterministic" else None,
                {reason},
                dict(link.features),
            )
        )

    def sides(link: Link) -> tuple[list[Member], list[Member]] | None:
        for rid in (link.record_a, link.record_b):
            if rid not in known:
                raise ValueError(f"link to unknown record {rid}")
        ra, rb = clusters.find(link.record_a), clusters.find(link.record_b)
        return None if ra == rb else (clusters.records(ra), clusters.records(rb))

    def merge(link: Link) -> None:
        clusters.union(link.record_a, link.record_b)
        accepted.append(link)

    # D7: human "same" decisions first; they check X1 and X2 only (7.1.6).
    for link in sorted(human_same, key=lambda x: (x.record_a, x.record_b)):
        if link.record_a not in known or link.record_b not in known:
            counts["decisions_not_applicable"] += 1
            continue
        pair = sides(link)
        if pair is None:
            counts["decisions_applied"] += 1
            continue
        left, right = pair
        crossing = p1_reason(left, right) is not None or crosses_p2(left, right)
        if crossing and len(link.reviewers) < 2 and not link.reviewers & config.senior_reviewers:
            counts["decisions_awaiting_second_review"] += 1
            continue
        both = left + right
        rule = "X1" if len({m.synthetic for m in both}) > 1 else None
        if rule is None and common_schema(sorted({m.schema for m in both})) is None:
            rule = "X2"
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        merge(link)
        counts["decisions_applied"] += 1

    # D1 to D6, in rule order, then by record ids.
    for link in sorted(
        deterministic, key=lambda x: (RULE_ORDER[x.rule or ""], x.record_a, x.record_b)
    ):
        pair = sides(link)
        if pair is None:
            continue
        left, right = pair
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        too_big = len(left) + len(right) > config.cluster_cap
        a, b = known[link.record_a], known[link.record_b]
        if "address" in (a.entity_class, b.entity_class):  # D6: addresses carry no flags
            if too_big:
                conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            else:
                merge(link)
            continue
        crossing = p1_reason(left, right) is not None or crosses_p2(left, right)
        needs_check = link.rule in NAME_CHECK_RULES or crossing
        if needs_check and not name_check(a, b, config.name_check_jaro_winkler, strict=crossing):
            possible(link, "identifier_name_mismatch")
        elif too_big:
            conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            possible(link, "cluster_cap")
        else:
            merge(link)

    # Probabilistic pairs, by rounded probability descending, then by record ids.
    rounded = [
        replace(x, probability=round(x.probability, PROBABILITY_DECIMALS)) for x in probabilistic
    ]
    for link in sorted(rounded, key=lambda x: (-x.probability, x.record_a, x.record_b)):
        if link.probability < config.candidate_threshold:
            continue
        pair = sides(link)
        if pair is None:
            continue
        left, right = pair
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        if link.model is None:
            raise ValueError(f"probabilistic link {link.record_a} {link.record_b} has no model")
        a, b = known[link.record_a], known[link.record_b]
        reason = p1_reason(left, right)
        if link.probability < config.merge_threshold[link.model]:
            possible(link, "below_merge_threshold")
        elif reason is not None:
            possible(link, reason)
        elif crosses_p2(left, right):
            possible(link, "leaked_cross_source")
        elif not link.strong_evidence:
            possible(link, "name_only")
        elif (
            a.entity_class == b.entity_class == "person"
            and a.list_source is not None
            and b.list_source is not None
            and a.list_source != b.list_source
            and not link.birth_or_id_agrees
        ):
            possible(link, "listed_needs_birth_date")
        elif len(left) + len(right) > config.cluster_cap:
            conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            possible(link, "cluster_cap")
        else:
            merge(link)

    # Source hints (ICIJ "same as" relationships) become possible matches, never merges.
    for record_a, record_b, hint in sorted(set(hints)):
        if record_a not in known or record_b not in known:
            counts["hints_not_applicable"] += 1
            continue
        if "address" in (known[record_a].entity_class, known[record_b].entity_class):
            counts["hints_not_applicable"] += 1
            continue
        link = Link(record_a, record_b, "source_hint")
        pair = sides(link)
        if pair is None:
            counts["hints_not_applicable"] += 1
            continue
        rule = hard_conflict(pair[0], pair[1], different, common_schema)
        if rule is not None:
            conflict(rule, record_a, record_b, "source_hint", None)
            continue
        possible(link, f"source_hint:{hint}")
        counts["hints_used"] += 1

    return _output(clusters, accepted, candidates, conflicts, counts, different, common_schema)


def _output(
    clusters: _Clusters,
    accepted: list[Link],
    candidates: list[Candidate],
    conflicts: list[dict[str, object]],
    counts: dict[str, int],
    different: set[frozenset[str]],
    common_schema: Callable[[Iterable[str]], str | None],
) -> Result:
    edges: dict[str, list[tuple[str, Link]]] = {}
    for link in accepted:
        edges.setdefault(link.record_a, []).append((link.record_b, link))
        edges.setdefault(link.record_b, []).append((link.record_a, link))
    canonical_of: dict[str, str] = {}
    rows: list[dict[str, object]] = []
    for root in sorted(clusters.items):
        group = clusters.records(root)
        anchor = min(group, key=lambda m: (m.priority, m.record_id)).record_id
        cid = anchor if len(group) == 1 else "nr-" + anchor
        # Accepted links form a tree in each cluster: walk it from the anchor in id order.
        parent: dict[str, tuple[str, Link] | None] = {anchor: None}
        queue = [anchor]
        while queue:
            node = queue.pop(0)
            for other, edge in sorted(edges.get(node, []), key=lambda e: e[0]):
                if other not in parent:
                    parent[other] = (node, edge)
                    queue.append(other)
        for m in sorted(group, key=lambda x: x.record_id):
            canonical_of[m.record_id] = cid
            row: dict[str, object] = {
                "record_id": m.record_id,
                "canonical_id": cid,
                "class": m.entity_class,
                "cluster_size": len(group),
                "method": "identity" if len(group) == 1 else "anchor",
                "rule": None,
                "match_probability": None if len(group) == 1 else 1.0,
                "via": None,
                "path_methods": None,
                "features": None,
            }
            step = parent.get(m.record_id)
            if step is not None:
                via, edge = step
                methods = {edge.method}
                up = parent[via]
                while up is not None:
                    methods.add(up[1].method)
                    up = parent[up[0]]
                probabilistic_link = edge.method == "probabilistic"
                row.update(
                    method=edge.method,
                    rule=edge.rule,
                    match_probability=edge.probability if probabilistic_link else 1.0,
                    via=via,
                    path_methods="+".join(sorted(methods)),
                    features=json.dumps(dict(sorted(edge.features.items())), separators=(",", ":"))
                    if probabilistic_link
                    else None,
                )
            rows.append(row)

    def rank(c: Candidate) -> tuple[float, str, str]:
        return (-(c.probability if c.probability is not None else -1.0), c.record_a, c.record_b)

    best: dict[tuple[str, str], Candidate] = {}
    for c in candidates:
        a, b = sorted((canonical_of[c.record_a], canonical_of[c.record_b]))
        if a == b:
            continue
        current = best.get((a, b))
        if current is None:
            best[(a, b)] = replace(c, reasons=set(c.reasons))
        elif rank(c) < rank(current):
            best[(a, b)] = replace(c, reasons=current.reasons | c.reasons)
        else:
            current.reasons |= c.reasons
    out: list[dict[str, object]] = []
    for (a, b), c in sorted(best.items()):
        left = clusters.records(clusters.find(c.record_a))
        right = clusters.records(clusters.find(c.record_b))
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:  # a later merge made the two clusters incompatible
            conflicts.append(
                {
                    "rule": rule,
                    "record_a": c.record_a,
                    "record_b": c.record_b,
                    "link_method": c.method,
                    "link_rule": c.rule,
                }
            )
            continue
        record_a, record_b = (
            (c.record_a, c.record_b) if canonical_of[c.record_a] == a else (c.record_b, c.record_a)
        )
        out.append(
            {
                "a": a,
                "b": b,
                "record_a": record_a,
                "record_b": record_b,
                "match_probability": c.probability,
                "match_weight": c.weight,
                "method": c.method,
                "rule": c.rule,
                "reasons": sorted(c.reasons),
                "features": dict(sorted(c.features.items())),
            }
        )
    return Result(
        sorted(rows, key=lambda r: str(r["record_id"])),
        out,
        sorted(conflicts, key=lambda r: tuple(str(r[k]) for k in CONFLICT_ORDER)),
        counts,
    )
