"""Time-respecting path expansion over PAID, one hop at a time (PHASE-3.md 7.1.3).

Path typologies (`circular_flow`, `layering_chain`) never ask Neo4j for every path of length 2 to
6 at once: on a payment graph each account pays many others, and a quantified path pattern whose
conditions sit in a later WHERE clause enumerates every path before it filters (3.2). Instead the
detector keeps a frontier of partial paths and asks the source for the next hop of all of them in
one call (`Source.paid_hop`, query `paid_hop.cypher`), with the time, amount and currency
conditions inside the hop query. The order of every result is fixed, so the paths found do not
depend on the source.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from neonradar_detect.rows import Hop


@dataclass(frozen=True, slots=True)
class FrontierItem:
    """One partial path waiting for its next hop; `paid_hop` receives these as maps."""

    key: int
    account: str
    after: datetime
    until: datetime
    min_amount: float
    max_amount: float
    currency: str
    visited: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Path:
    hops: tuple[Hop, ...]

    @property
    def accounts(self) -> tuple[str, ...]:
        return (self.hops[0].source, *(h.target for h in self.hops))

    @property
    def first(self) -> Hop:
        return self.hops[0]

    @property
    def last(self) -> Hop:
        return self.hops[-1]


@dataclass(frozen=True, slots=True)
class ExpansionStats:
    partial_paths: int
    truncated: int


HopFn = Callable[[Sequence[FrontierItem]], dict[int, list[Hop]]]


def expand(
    starts: Sequence[Hop],
    hop: HopFn,
    *,
    extend: Callable[[Path, int], FrontierItem | None],
    keep: Callable[[Path, Hop], bool],
    accept: Callable[[Path], bool],
    max_hops: int,
    max_branching: int,
    max_frontier: int,
    chunk: int = 10_000,
) -> tuple[list[Path], ExpansionStats]:
    """Every path that `extend`, `keep` and `accept` allow, breadth first from each start hop.

    `extend(path, key)` gives the frontier item for the next hop of `path`, or None to stop it;
    `keep(path, hop)` filters the hops the source returned (conditions a query cannot express,
    such as holder overlaps); `accept(path)` says whether a path is a result. Starts are expanded
    `chunk` at a time (in time order), so the frontier stays bounded however many starts there
    are. Per partial path at most `max_branching` next hops are kept (earliest first, then by edge
    id), and per level of a chunk at most `max_frontier` partial paths (in path order); whatever
    is cut is counted in `truncated`, which the run summary reports.
    """
    ordered = sorted(starts, key=lambda h: (h.ts, h.edge_id))
    results: list[Path] = []
    partial = truncated = 0
    for i in range(0, len(ordered), chunk):
        found, stats = _expand_chunk(
            ordered[i : i + chunk], hop, extend, keep, accept, max_hops, max_branching, max_frontier
        )
        results.extend(found)
        partial += stats.partial_paths
        truncated += stats.truncated
    return results, ExpansionStats(partial, truncated)


def _expand_chunk(
    starts: Sequence[Hop],
    hop: HopFn,
    extend: Callable[[Path, int], FrontierItem | None],
    keep: Callable[[Path, Hop], bool],
    accept: Callable[[Path], bool],
    max_hops: int,
    max_branching: int,
    max_frontier: int,
) -> tuple[list[Path], ExpansionStats]:
    level = [Path((s,)) for s in starts]
    results = [p for p in level if accept(p)]
    partial = len(level)
    truncated = 0
    for _ in range(1, max_hops):
        if not level:
            break
        if len(level) > max_frontier:
            truncated += len(level) - max_frontier
            level = level[:max_frontier]
        frontier: list[FrontierItem] = []
        by_key: dict[int, Path] = {}
        for key, path in enumerate(level):
            item = extend(path, key)
            if item is not None:
                frontier.append(item)
                by_key[key] = path
        nexts = hop(frontier) if frontier else {}
        level = []
        for key in sorted(nexts):
            path = by_key[key]
            hops = [h for h in nexts[key] if keep(path, h)]
            if len(hops) > max_branching:
                truncated += len(hops) - max_branching
                hops = hops[:max_branching]
            for h in hops:
                grown = Path((*path.hops, h))
                if accept(grown):
                    results.append(grown)
                level.append(grown)
        partial += len(level)
    return results, ExpansionStats(partial, truncated)
