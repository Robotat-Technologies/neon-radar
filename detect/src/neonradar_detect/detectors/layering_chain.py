"""layering_chain 0.2.0: funds passed on through a chain of accounts of different holders
(PHASE-1.md 7.2 entry 3; `typology-detection-definitions.md` section 3; PHASE-3.md 7.3.3).

Starts are payments of at least `min_amount`. Each next hop leaves the account the previous hop
reached, within `max_dwell_hours` after it, in the same currency, for between `min_hop_ratio` and
`1 + max_hop_gain` times the previous amount, to an account none of whose holders held an account
earlier in the chain (so a return to the origin's side is left to `circular_flow`). A chain of
`min_hops` to `max_hops` payments whose last amount is at least `min_retained_ratio` of its first
(fees of "5-20 %" of the sum, Europol EFECTA 2023) is a finding unless it lies inside a longer
chain that is one. Splits and merges are not followed: a chain that splits is found only up to the
split (a documented limitation; the generator plants such chains, 7.2.5).

What makes a chain more than commerce is the registry around it (PHASE-1.md 7.2): the detector
counts pairs of holders in the chain that share a registered address, a director or an agent, and
intermediate accounts with little other activity. On a real profile the policy withholds every
chain that touches a real entity (R-REAL), so these counts only ever combine synthetic data.

pattern_strength = 0.25 * min(1, (hops - 2) / 4) + 0.25 * retained ratio + 0.2 * (1 - longest
dwell / max_dwell_hours) + 0.15 * share of quiet intermediaries + 0.15 * min(1, linked holder
pairs / 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations, pairwise

from neonradar_detect.expand import FrontierItem, Path, expand
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Hop
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "layering_chain"
VERSION = "0.2.0"
QUERIES = (
    "activity_counts.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "paid_hop.cypher",
    "paid_starts.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    min_hops: int = 3
    max_hops: int = 6
    max_dwell_hours: int = 72
    min_hop_ratio: float = 0.85
    max_hop_gain: float = 0.02
    min_retained_ratio: float = 0.8
    min_amount: float = 10000.0
    quiet_days: int = 30
    max_quiet_payments: int = 5
    max_starts: int = 1_000_000
    max_branching: int = 10
    max_frontier: int = 50_000


def _holders_so_far(path: Path) -> set[str]:
    held = set(path.first.source_holders)
    for h in path.hops:
        held.update(h.target_holders)
    return held


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    if not 3 <= p.min_hops <= p.max_hops <= 8:
        raise ValueError("need 3 <= min_hops <= max_hops <= 8")
    dwell = timedelta(hours=p.max_dwell_hours)
    starts = [
        h
        for h in source.paid_starts(p.min_amount, window.start, window.end, p.max_starts)
        if not set(h.source_holders) & set(h.target_holders)
    ]

    def extend(path: Path, key: int) -> FrontierItem | None:
        if len(path.hops) >= p.max_hops:
            return None
        last = path.last
        return FrontierItem(
            key=key,
            account=last.target,
            after=last.ts,
            until=last.ts + dwell,
            min_amount=p.min_hop_ratio * last.amount,
            max_amount=(1 + p.max_hop_gain) * last.amount,
            currency=last.currency,
            visited=tuple(sorted(set(path.accounts))),
        )

    def keep(path: Path, hop: Hop) -> bool:
        return bool(hop.target_holders) and not set(hop.target_holders) & _holders_so_far(path)

    def accept(path: Path) -> bool:
        return (
            len(path.hops) >= p.min_hops
            and path.last.amount >= p.min_retained_ratio * path.first.amount
        )

    chains, stats = expand(
        starts,
        source.paid_hop,
        extend=extend,
        keep=keep,
        accept=accept,
        max_hops=p.max_hops,
        max_branching=p.max_branching,
        max_frontier=p.max_frontier,
    )
    maximal = _maximal(chains)
    findings = [_finding(c, p, source) for c in maximal]
    return DetectorOutput(
        findings,
        {
            "starts": len(starts),
            "partial_paths": stats.partial_paths,
            "truncated": stats.truncated,
            "chains": len(chains),
        },
    )


def _maximal(chains: list[Path]) -> list[Path]:
    """Chains whose payments are not all part of a longer chain, in a stable order."""
    ordered = sorted(
        chains, key=lambda c: (-len(c.hops), c.first.ts, tuple(h.edge_id for h in c.hops))
    )
    kept: list[Path] = []
    kept_sets: list[frozenset[str]] = []
    for chain in ordered:
        edges = frozenset(h.edge_id for h in chain.hops)
        if any(edges <= other for other in kept_sets):
            continue
        kept.append(chain)
        kept_sets.append(edges)
    return sorted(kept, key=lambda c: (c.first.ts, tuple(h.edge_id for h in c.hops)))


def _finding(chain: Path, p: Params, source: Source) -> Finding:
    first, last = chain.first, chain.last
    hops = len(chain.hops)
    hours = (last.ts - first.ts).total_seconds() / 3600
    dwells = [(b.ts - a.ts).total_seconds() / 3600 for a, b in pairwise(chain.hops)]
    longest = max(dwells)
    retained = last.amount / first.amount
    # holders of each account in order; the chain rule keeps them disjoint
    holders = [tuple(sorted(first.source_holders))] + [
        tuple(sorted(h.target_holders)) for h in chain.hops
    ]
    all_holders = sorted({x for hs in holders for x in hs})
    linked, link_nodes, link_edges, link_steps = _linked_pairs(all_holders, source)
    quiet_from = first.ts - timedelta(days=p.quiet_days)
    quiet_to = last.ts + timedelta(days=p.quiet_days)
    intermediates = list(chain.accounts[1:-1])
    counts = source.activity_counts(intermediates, quiet_from, quiet_to)
    chain_edges = {h.edge_id for h in chain.hops}
    quiet = 0
    for account in intermediates:
        own = sum(1 for h in chain.hops if account in (h.source, h.target))
        if counts.get(account, 0) - own <= p.max_quiet_payments:
            quiet += 1
    quiet_share = quiet / len(intermediates)
    strength = clip01(
        0.25 * min(1.0, (hops - 2) / 4)
        + 0.25 * min(1.0, retained)
        + 0.2 * (1 - longest / p.max_dwell_hours)
        + 0.15 * quiet_share
        + 0.15 * min(1.0, linked / 2)
    )
    subjects = [Subject(first.source, "origin")]
    subjects += [Subject(h, "origin_holder") for h in holders[0]]
    subjects.append(Subject(last.target, "destination"))
    subjects += [Subject(h, "destination_holder") for h in holders[-1]]
    metrics = {
        "chain_length": hops,
        "first_amount": round(first.amount, 2),
        "last_amount": round(last.amount, 2),
        "currency": first.currency,
        "duration_hours": round(hours, 1),
        "duration_days": max(1, math.ceil(hours / 24)),
        "retained_ratio": round(retained, 4),
        "longest_dwell_hours": round(longest, 1),
        "holders": len(all_holders),
        "linked_holder_pairs": linked,
        "quiet_intermediaries": quiet,
    }
    node_ids = set(chain.accounts) | link_nodes
    if link_nodes:
        node_ids |= set(all_holders)
    return Finding(
        typology=SLUG,
        variant="",
        anchor=first.source,
        node_ids=tuple(sorted(node_ids)),
        edge_ids=tuple(sorted(chain_edges | link_edges)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple((h.edge_id,) for h in chain.hops) + tuple(link_steps),
        window=(first.ts, last.ts),
        activity=True,
    )


def _linked_pairs(
    holders: list[str], source: Source
) -> tuple[int, set[str], set[str], list[tuple[str, ...]]]:
    """Pairs of holders that share a registered address, a director or an agent."""
    addresses = source.links_from(holders, ("HAS_ADDRESS",))
    into = source.links_into(holders, ("DIRECTOR_OF", "REPRESENTS"))
    shared: dict[str, dict[str, str]] = {}  # holder -> {shared key: relationship id}
    for h in holders:
        keys: dict[str, str] = {}
        for link in addresses.get(h, []):
            if link.role == "registered":
                keys[f"address:{link.target}"] = link.rel_id
        for link in into.get(h, []):
            kind = "director" if link.rel_type == "DIRECTOR_OF" else "agent"
            keys[f"{kind}:{link.source}"] = link.rel_id
        shared[h] = keys
    linked = 0
    nodes: set[str] = set()
    edges: set[str] = set()
    steps: list[tuple[str, ...]] = []
    for a, b in combinations(holders, 2):
        common = sorted(set(shared[a]) & set(shared[b]))
        if not common:
            continue
        linked += 1
        key = common[0]
        node = key.split(":", 1)[1]
        pair_edges = tuple(sorted((shared[a][key], shared[b][key])))
        nodes.add(node)
        edges.update(pair_edges)
        steps.append(pair_edges)
    return linked, nodes, edges, steps
