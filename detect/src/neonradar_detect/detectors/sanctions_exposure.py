"""sanctions_exposure 0.2.0: an organisation without a sanctions flag of its own that listed
parties own or control, judged with each regime's own test (PHASE-1.md 7.2 entry 10, corrected
by `typology-detection-definitions.md` section 10; PHASE-3.md 7.3.10).

Registry evidence only, and only relationships that still hold at the end of the window (no end
date, or a later one): a sold holding or a resigned director is history. Each regime is seeded
with its own list only:

- `us`, the OFAC 50 Percent Rule: entities designated on `us_ofac_sdn`. Owners count in full and
  are added up across all listed owners; "50 percent or greater" passes the status on, entity by
  entity (OFAC FAQ 399 and 401). Ownership only (FAQ 398).
- `eu`, Council Best Practices 2024 para 63: entities designated on `eu_fsf`. The same arithmetic
  with "50% or more"; the entity-by-entity chain is NeonRadar's reading. Control criteria are
  reported apart: an appointment right is criterion (a), a CONSOLIDATES link from a listed parent
  criterion (g) (a NeonRadar reading of "while publishing consolidated accounts").
- `uk`, Russia Regulations 2019 reg 7 and Schedule 1 (NeonRadar applies the same test to every UK
  regime): entities with a `gb_fcdo_sanctions` designation whose provisions include an asset
  freeze. Per listed person: OFSI "would not simply aggregate" different listed persons'
  holdings unless, for example, they are held under a joint arrangement or one party controls
  the rights of another, which C2 cannot show. More than 50 percent of the shares or of the
  voting rights, or a right to appoint or remove a majority of the board, held directly or
  through entities the person has a majority stake in (a voting band of more than 50 percent or
  a board right; when a link has no voting band, shares stand in for votes and the finding says
  so with `votes_follow_shares`); the person's direct and indirect holdings are added (a reading
  of "directly or indirectly" and para 4). A holding recorded as a nominee holding is not
  counted for the nominee (Schedule 1 para 10: it is treated as held by the person it is held
  for, whom the records do not name; `uk_nominee_holdings` counts them). A designation whose
  provisions are empty may or may not include an asset freeze: it gives `left open by the
  bands` at most, with `uk_measures_unknown`.

A synthetic listed entity (dataset `nr_synthetic`) seeds all three tests. A designation with an
end date on or before the end of the window seeds nothing. The candidate step collects the OWNS
and CONTROLS relationships within `max_hops` of a seed (one `links_from` call per hop) and the
CONSOLIDATES and DIRECTOR_OF relationships that start at a seed.

Each test runs on the lower and on the upper bounds of the published bands (a missing upper bound
counts as 100 and is reported as `unbounded`), giving `met on the records`, `left open by the
bands`, `not met on the records`, or `no listed owner from this list`. Nothing is multiplied for
the tests. `listed_share_min` and `listed_share_max` are the recorded holdings in the
organisation of listed parties and of entities that pass the US and EU test on the same bounds,
added up (capped at 100); the effective share (products along each OWNS path, summed per listed
owner, the largest owner reported) is a teaching figure only (PHASE-2.md 7.2 rule 6). Natural
persons are never owned; only organisations become subjects, while other non-person legal
entities pass a status on.

A finding is made for an organisation with a test met or left open, a direct CONTROLS,
CONSOLIDATES or DIRECTOR_OF link from a seed, or listed holdings that can reach
`min_reported_share` percent (a modelling choice: 25 is the PSC register's floor, below which
holdings are not recorded at all; OFAC advises caution with "a significant ownership interest that
is less than 50 percent"). The `assessment` metric puts every regime's result into words for the
summary (`wording.detail`), with the control results and the limits of the records; the headline
names only the shape and the lists.

pattern_strength = 0.6 * ownership score + 0.2 * proximity + 0.2 * control score: the ownership
score is 1 when a test is met, 0.7 when one is left open, else `listed_share_min` / 100; proximity
is 1 - (shortest path - 1) / max_hops; the control score is 1 for a direct CONTROLS or
CONSOLIDATES link from a seed, 0.5 for a directorship alone. Priority: high whenever a test is
met on the records (the typology's own rule, C4).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow, ListedRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "sanctions_exposure"
VERSION = "0.2.0"
QUERIES = ("entities.cypher", "links_from.cypher", "listed_entities.cypher")
REGIMES = ("us", "eu", "uk")
LISTS = {"us": "us_ofac_sdn", "eu": "eu_fsf", "uk": "gb_fcdo_sanctions"}
SYNTHETIC = "nr_synthetic"
ASSET_FREEZE = "asset freeze"
MET = "met on the records"
OPEN = "left open by the bands"
NOT_MET = "not met on the records"
NONE = "no listed owner from this list"
LIST_NAMES = {
    "us": "the OFAC SDN List",
    "eu": "the EU consolidated list",
    "uk": "the UK Sanctions List",
}
SYNTHETIC_LIST = "a synthetic sanctions list"
# The summary's sentences (typology-detection-definitions.md 10.4); {list} names the list.
RESULT = {
    ("us", MET): "US test: recorded holdings of parties on {list} reach at least 50 percent, "
    "counting in full any entity that itself reaches that level (the method of OFAC FAQ 401).",
    ("us", OPEN): "US test: the published share bands leave open whether recorded holdings of "
    "parties on {list} reach 50 percent; the share register would settle it.",
    ("us", NOT_MET): "US test: recorded holdings of parties on {list} stay below 50 percent on "
    "these records.",
    ("eu", MET): "EU test: recorded holdings of parties on {list} reach 50 percent or more, added "
    "together as the Council's Best Practices describe.",
    ("eu", OPEN): "EU test: the published share bands leave open whether recorded holdings of "
    "parties on {list} reach 50 percent.",
    ("eu", NOT_MET): "EU test: recorded holdings of parties on {list} stay below 50 percent on "
    "these records.",
    ("uk", MET): "UK test: one party on {list} is recorded with more than 50 percent of the shares "
    "or voting rights, or the right to appoint or remove a majority of the board, directly or "
    "through entities it has a majority stake in.",
    ("uk", OPEN): "UK test: the published share bands leave open whether one party on {list} "
    "holds more than 50 percent.",
    ("uk", NOT_MET): "UK test: on the records this test counts, no single party on {list} holds "
    "more than 50 percent of the shares or voting rights, or the right to appoint or remove a "
    "majority of the board.",
}
US_CAUTION = (
    "A party on {list} is recorded with control other than majority ownership; the OFAC test "
    "counts ownership only (FAQ 398), and OFAC advises caution where listed parties may control "
    "an entity by other means."
)
UK_CONTROL = (
    "A party on {list} is recorded with other control (significant influence or a "
    "directorship); whether the UK control condition is met cannot be decided from these records."
)
UK_SEVERAL = (
    "OFSI does not simply add different listed parties' holdings together unless, for example, "
    "they are held under a joint arrangement or one party controls the rights of another, which "
    "these records cannot show."
)
UK_VOTES = "Voting rights were taken to follow shares where the register records no voting band."
UK_NOMINEE = (
    "Holdings recorded as nominee holdings were not counted for their holders: UK law treats a "
    "nominee's share as held by the person it is held for, whom these records do not name."
)
UK_UNKNOWN = (
    "A UK list entry here does not record whether it includes an asset freeze, so the UK result "
    "is left open."
)
EU_CRITERIA = {
    "(a)": "the right to appoint or remove a majority of the board",
    "(g)": "management on a unified basis with consolidated accounts",
}
EU_CONTROL = (
    "EU control criterion {criteria} is recorded for a party on {list}; the criteria can be "
    "rebutted case by case, and control is for the national authorities to assess."
)
CLOSING = (
    "These are NeonRadar calculations from the recorded share bands and links, not findings by "
    "OFAC, OFSI, the EU or a national authority."
)


@dataclass(frozen=True, slots=True)
class Params:
    max_hops: int = 6
    max_links: int = 200_000
    max_paths: int = 1_000
    max_steps: int = 12
    min_reported_share: float = 25.0


Bound = tuple[float, bool]  # (value, exclusive)


def bound(link: LinkRow, upper: bool) -> Bound:
    if upper:
        return (
            (link.share_max, link.share_max_exclusive)
            if link.share_max is not None
            else (100.0, False)
        )
    return (
        (link.share_min, link.share_min_exclusive) if link.share_min is not None else (0.0, False)
    )


def passes(terms: list[Bound], strict: bool, upper: bool) -> bool:
    """Whether a sum of band bounds meets "at least 50" (or "more than 50" when `strict`).

    Lower bounds: the true sum is at least their total, and more if any is open. Upper bounds:
    at most their total (capped at 100), and less if any is open (section 10.2)."""
    if not terms:
        return False
    total = min(100.0, round(sum(v for v, _ in terms), 9))
    is_open = any(x for _, x in terms)
    if total != 50:
        return total > 50
    if upper:
        return not strict and not is_open
    return is_open or not strict


def seeds(listed: list[ListedRow], as_of: str) -> tuple[dict[str, set[str]], set[str]]:
    """The seed set of each regime, and the UK entries whose provisions are not recorded."""
    out: dict[str, set[str]] = {r: set() for r in REGIMES}
    unknown: set[str] = set()
    for row in listed:
        current = [s for s in row.sanctions if not (s.end_date and s.end_date <= as_of)]
        if SYNTHETIC in row.datasets:
            if current or not row.sanctions:
                for r in REGIMES:
                    out[r].add(row.entity)
            continue
        for s in current:
            if LISTS["us"] in s.datasets:
                out["us"].add(row.entity)
            if LISTS["eu"] in s.datasets:
                out["eu"].add(row.entity)
            if LISTS["uk"] in s.datasets:
                if any(x.casefold() == ASSET_FREEZE for x in s.provisions):
                    out["uk"].add(row.entity)
                elif not s.provisions:
                    unknown.add(row.entity)
    return out, unknown - out["uk"]


def _appoints(link: LinkRow) -> bool:
    return link.rel_type == "CONTROLS" and link.control_type == "appointment"


def _voting(link: LinkRow) -> bool:
    return (
        link.rel_type == "CONTROLS" and link.control_type == "voting" and link.share_min is not None
    )


def aggregate_test(
    start: set[str], owns_into: dict[str, list[LinkRow]], ownable: set[str], upper: bool
) -> set[str]:
    """US and EU: the entities that listed owners, and entities passing the test, own at least
    50 percent of together, entity by entity (section 10.2). The seeds are included."""
    held = set(start)
    changed = True
    while changed:
        changed = False
        for target in sorted(owns_into):
            if target in held or target not in ownable:
                continue
            terms = [bound(x, upper) for x in owns_into[target] if x.source in held]
            if passes(terms, False, upper):
                held.add(target)
                changed = True
    return held


def _stake(
    seed: str,
    owns_from: dict[str, list[LinkRow]],
    controls_from: dict[str, list[LinkRow]],
    ownable: set[str],
    upper: bool,
    proxy: bool,
) -> set[str]:
    """The seed and the entities it has a majority stake in, directly or down a chain: a voting
    band of more than 50 percent or a board appointment right; with `proxy`, shares of more than
    50 percent where a link has no voting band. Nominee holdings do not count (Sch 1 para 10)."""
    stake = {seed}
    changed = True
    while changed:
        changed = False
        for m in sorted(stake):
            for b in sorted({x.target for x in owns_from[m] + controls_from[m]} - stake):
                if b not in ownable:
                    continue
                links = [x for x in controls_from[m] if x.target == b]
                votes = [bound(x, upper) for x in links if _voting(x)]
                shares = [
                    bound(x, upper) for x in owns_from[m] if x.target == b and not x.is_nominee
                ]
                if (
                    any(_appoints(x) for x in links)
                    or passes(votes, True, upper)
                    or (proxy and not votes and passes(shares, True, upper))
                ):
                    stake.add(b)
                    changed = True
    return stake


def uk_test(
    seed: str,
    owns_from: dict[str, list[LinkRow]],
    controls_from: dict[str, list[LinkRow]],
    ownable: set[str],
    upper: bool,
) -> tuple[set[str], set[str]]:
    """UK, one listed person: the entities it owns or controls (shares or votes of more than 50
    percent held through its majority-stake entities, each in full, or a board right), and those
    of them whose result relies on shares standing in for votes (section 10.2)."""
    full = _stake(seed, owns_from, controls_from, ownable, upper, True)
    strict = _stake(seed, owns_from, controls_from, ownable, upper, False)

    def met(c: str, members: set[str]) -> bool:
        shares = [
            bound(x, upper)
            for m in members
            for x in owns_from[m]
            if x.target == c and not x.is_nominee
        ]
        votes = [
            bound(x, upper)
            for m in members
            for x in controls_from[m]
            if x.target == c and _voting(x)
        ]
        board = any(_appoints(x) for m in members for x in controls_from[m] if x.target == c)
        return passes(shares, True, upper) or passes(votes, True, upper) or board

    caught: set[str] = set()
    relied: set[str] = set()
    reach = {x.target for m in full for x in owns_from[m] + controls_from[m]}
    for c in sorted((reach & ownable) - {seed}):
        if met(c, full - {c}):
            caught.add(c)
            if not met(c, strict - {c}):
                relied.add(c)
    return caught, relied


def _reach(start: set[str], links: list[LinkRow]) -> dict[str, int]:
    """Shortest distance from `start` to every node `links` reach (start nodes excluded)."""
    out: dict[str, list[str]] = defaultdict(list)
    for x in links:
        out[x.source].append(x.target)
    dist = {s: 0 for s in start}
    todo = deque(sorted(start))
    while todo:
        n = todo.popleft()
        for t in sorted(out[n]):
            if t not in dist:
                dist[t] = dist[n] + 1
                todo.append(t)
    return {k: v for k, v in dist.items() if k not in start}


def _collect(
    source: Source, start: set[str], p: Params, as_of: str
) -> tuple[dict[str, LinkRow], bool]:
    links: dict[str, LinkRow] = {}
    seen = set(start)
    frontier = sorted(start)
    for _ in range(p.max_hops):
        if not frontier:
            break
        nxt: set[str] = set()
        for rows in source.links_from(frontier, ("OWNS", "CONTROLS")).values():
            for x in rows:
                if not x.current(as_of):
                    continue
                links[x.rel_id] = x
                if x.target not in seen:
                    seen.add(x.target)
                    nxt.add(x.target)
        if len(links) > p.max_links:
            return links, True
        frontier = sorted(nxt)
    return links, False


def _paths(
    start: set[str], target: str, links: list[LinkRow], max_hops: int, limit: int
) -> tuple[list[list[LinkRow]], bool]:
    """Simple paths over `links` from a start node to `target`, at most `max_hops` long, shortest
    first, at most `limit` of them (and whether that limit cut the list)."""
    out_links: dict[str, list[LinkRow]] = defaultdict(list)
    into: dict[str, list[str]] = defaultdict(list)
    for x in sorted(links, key=lambda x: x.rel_id):
        out_links[x.source].append(x)
        into[x.target].append(x.source)
    back = {target: 0}  # distance to the target
    todo = deque([target])
    while todo:
        n = todo.popleft()
        for s in into[n]:
            if s not in back:
                back[s] = back[n] + 1
                todo.append(s)
    found: list[list[LinkRow]] = []
    queue: deque[tuple[str, list[LinkRow], frozenset[str]]] = deque(
        (s, [], frozenset({s})) for s in sorted(start) if s in back and s != target
    )
    while queue:
        node, path, visited = queue.popleft()
        if node == target:
            found.append(path)
            if len(found) >= limit:
                return found, bool(queue)
            continue
        for x in out_links[node]:
            if (
                x.target in visited
                or x.target not in back
                or len(path) + 1 + back[x.target] > max_hops
            ):
                continue
            if x.target in start and x.target != target:
                continue  # a path through another listed party is that party's own path
            queue.append((x.target, [*path, x], visited | {x.target}))
    return found, False


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date().isoformat()
    listed = source.listed_entities()
    regime_seeds, uk_unknown = seeds(listed, as_of)
    every = set().union(*regime_seeds.values(), uk_unknown)
    collected, truncated = _collect(source, every, p, as_of)
    direct = [
        x
        for rows in source.links_from(sorted(every), ("CONSOLIDATES", "DIRECTOR_OF")).values()
        for x in rows
        if x.current(as_of)
    ]
    links = sorted(collected.values(), key=lambda x: x.rel_id)
    ids = every | {x.source for x in links} | {x.target for x in links} | {x.target for x in direct}
    entities = source.entities(sorted(ids))
    ownable = {
        i for i, e in entities.items() if "LegalEntity" in e.labels and "Person" not in e.labels
    }
    owns = [x for x in links if x.rel_type == "OWNS"]
    owns_into: dict[str, list[LinkRow]] = defaultdict(list)
    owns_from: dict[str, list[LinkRow]] = defaultdict(list)
    controls_from: dict[str, list[LinkRow]] = defaultdict(list)
    for x in owns:
        owns_into[x.target].append(x)
        owns_from[x.source].append(x)
    for x in links:
        if x.rel_type == "CONTROLS":
            controls_from[x.source].append(x)
    results: dict[str, tuple[set[str], set[str], dict[str, int]]] = {}
    for r in ("us", "eu"):
        s = regime_seeds[r]
        results[r] = (
            aggregate_test(s, owns_into, ownable, False),
            aggregate_test(s, owns_into, ownable, True),
            _reach(s, owns),
        )
    uk_low: set[str] = set()
    uk_high: set[str] = set()
    unknown_reach: set[str] = set()
    proxied: set[str] = set()
    for seed in sorted(regime_seeds["uk"] | uk_unknown):
        low, low_proxy = uk_test(seed, owns_from, controls_from, ownable, False)
        high, high_proxy = uk_test(seed, owns_from, controls_from, ownable, True)
        if seed in uk_unknown:
            unknown_reach |= low | high  # may or may not be an asset-freeze designation
            continue
        uk_low |= low
        uk_high |= high
        proxied |= low_proxy | high_proxy
    measures_unknown = unknown_reach - uk_low - uk_high
    results["uk"] = (
        uk_low,
        uk_high | unknown_reach,
        _reach(regime_seeds["uk"] | uk_unknown, links),
    )
    certain = aggregate_test(every, owns_into, ownable, False)
    possible = aggregate_test(every, owns_into, ownable, True)
    owned = _reach(every, owns)
    direct_into: dict[str, list[LinkRow]] = defaultdict(list)
    for x in direct + [x for x in links if x.rel_type == "CONTROLS" and x.source in every]:
        direct_into[x.target].append(x)
    candidates = set(owned) | set(direct_into) | ((uk_high | unknown_reach) - every)
    ctx = Context(regime_seeds, uk_unknown, every, certain, possible, entities)
    findings = []
    for target in sorted(candidates):
        e = entities[target]
        if "Organization" not in e.labels or "Sanctioned" in e.labels:
            continue
        f = _finding(
            target,
            links,
            owns,
            direct_into.get(target, []),
            results,
            ctx,
            target in proxied,
            target in measures_unknown,
            p,
        )
        if f is not None:
            findings.append(f)
    stats = {
        "listed": len(listed),
        "seeds": len(every),
        "links": len(links),
        "truncated": int(truncated),
    }
    return DetectorOutput(findings, stats)


def priority(finding: Finding) -> str | None:
    """The typology's own rule (C4): high whenever a test is met on the records."""
    return "high" if any(finding.metrics.get(f"{r}_test") == MET for r in REGIMES) else None


def _outcome(target: str, low: set[str], high: set[str], reached: dict[str, int]) -> str:
    if target not in reached:
        return NONE
    return MET if target in low else (OPEN if target in high else NOT_MET)


def _effective(paths: list[list[LinkRow]]) -> tuple[float, float]:
    """The largest listed owner's effective share: products along its OWNS paths, summed."""
    per_owner: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for path in paths:
        lo = hi = 1.0
        for x in path:
            lo *= bound(x, False)[0] / 100
            hi *= bound(x, True)[0] / 100
        acc = per_owner[path[0].source]
        acc[0] += lo
        acc[1] += hi
    if not per_owner:
        return 0.0, 0.0
    lo, hi = max(per_owner.values(), key=lambda v: (v[0], v[1]))
    return round(min(1.0, lo) * 100, 4), round(min(1.0, hi) * 100, 4)


@dataclass(frozen=True, slots=True)
class Context:
    regime_seeds: dict[str, set[str]]
    uk_unknown: set[str]
    every: set[str]
    certain: set[str]  # listed parties and entities passing the US and EU test on lower bounds
    possible: set[str]  # the same on upper bounds
    entities: dict[str, EntityRow]


def _listed_share(target: str, into: list[LinkRow], members: set[str], upper: bool) -> float:
    """Recorded holdings in `target` of `members`, added up and capped at 100."""
    total = sum(bound(x, upper)[0] for x in into if x.source in members and x.source != target)
    return round(min(100.0, total), 4)


def lists_text(sources: list[str], ctx: Context) -> str:
    """The lists the linked parties are on, in words."""
    if any(SYNTHETIC in ctx.entities[s].datasets for s in sources if s in ctx.entities):
        return SYNTHETIC_LIST
    names = [
        LIST_NAMES[r]
        for r in REGIMES
        if any(s in ctx.regime_seeds[r] or (r == "uk" and s in ctx.uk_unknown) for s in sources)
    ]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def assessment(m: dict[str, object], synthetic: bool, uk_holders: int) -> str:
    """Every regime's result in words, with the control results and the limits of the records."""

    def named(regime: str) -> str:
        return "the synthetic list" if synthetic else LIST_NAMES[regime]

    out: list[str] = []
    for r in REGIMES:
        test = str(m[f"{r}_test"])
        if test != NONE:
            out.append(RESULT[(r, test)].format(list=named(r)))
        if r == "us" and m["us_control_caution"]:
            out.append(US_CAUTION.format(list=named(r)))
        if r == "uk":
            if m["uk_control_to_assess"]:
                out.append(UK_CONTROL.format(list=named(r)))
            if test in (NOT_MET, OPEN) and uk_holders >= 2:
                out.append(UK_SEVERAL)
            if m["votes_follow_shares"]:
                out.append(UK_VOTES)
            if m["uk_nominee_holdings"] and test != NONE:
                out.append(UK_NOMINEE)
            if m["uk_measures_unknown"]:
                out.append(UK_UNKNOWN)
        if r == "eu" and m["eu_control_criteria"]:
            criteria = str(m["eu_control_criteria"]).split(", ")
            text = " and ".join(f"{c} ({EU_CRITERIA[c]})" for c in criteria)
            out.append(EU_CONTROL.format(criteria=text, list=named(r)))
    return " ".join([*out, CLOSING])


def _finding(
    target: str,
    links: list[LinkRow],
    owns: list[LinkRow],
    direct: list[LinkRow],
    results: dict[str, tuple[set[str], set[str], dict[str, int]]],
    ctx: Context,
    proxied: bool,
    measures_unknown: bool,
    p: Params,
) -> Finding | None:
    regime_seeds, every = ctx.regime_seeds, ctx.every
    tests = {r: _outcome(target, *results[r]) for r in REGIMES}
    own_paths, own_capped = _paths(every, target, owns, p.max_hops, p.max_paths)
    all_paths, all_capped = _paths(every, target, links, p.max_hops, p.max_paths)
    low, high = _effective(own_paths)
    into = [x for x in owns if x.target == target]
    share_min = _listed_share(target, into, ctx.certain, False)
    share_max = _listed_share(target, into, ctx.possible, True)
    if not direct and share_max < p.min_reported_share and not ({MET, OPEN} & set(tests.values())):
        return None
    extra = [x for x in direct if x.rel_type in ("CONSOLIDATES", "DIRECTOR_OF")]
    shortest = min([len(x) for x in all_paths] + [1 for _ in extra])
    if MET in tests.values():
        own_score = 1.0
    elif OPEN in tests.values():
        own_score = 0.7
    else:
        own_score = share_min / 100
    strong = any(x.rel_type in ("CONTROLS", "CONSOLIDATES") for x in direct)
    control_score = 1.0 if strong else (0.5 if direct else 0.0)
    strength = clip01(
        0.6 * own_score + 0.2 * (1 - (shortest - 1) / p.max_hops) + 0.2 * control_score
    )
    evidence = {x.rel_id: x for path in all_paths for x in path} | {x.rel_id: x for x in extra}
    sources = sorted({path[0].source for path in all_paths} | {x.source for x in extra})
    uk_seeds = regime_seeds["uk"] | ctx.uk_unknown
    eu_criteria = []
    if any(_appoints(x) and x.source in regime_seeds["eu"] for x in direct):
        eu_criteria.append("(a)")
    if any(x.rel_type == "CONSOLIDATES" and x.source in regime_seeds["eu"] for x in direct):
        eu_criteria.append("(g)")
    metrics: dict[str, object] = {
        "listed_parties": len(sources),
        "shortest_path": shortest,
        "ownership_paths": len(own_paths),
        "paths_capped": own_capped or all_capped,
        "listed_share_min": share_min,
        "listed_share_max": share_max,
        "effective_share_min": low,
        "effective_share_max": high,
        "us_test": tests["us"],
        "eu_test": tests["eu"],
        "uk_test": tests["uk"],
        "votes_follow_shares": proxied,
        "unbounded": any(x.share_max is None for x in evidence.values() if x.rel_type == "OWNS"),
        "bands_inconsistent": sum(bound(x, False)[0] for x in into) > 100,
        "control_links": sum(1 for x in direct if x.rel_type == "CONTROLS"),
        "consolidation_links": sum(1 for x in direct if x.rel_type == "CONSOLIDATES"),
        "director_links": sum(1 for x in direct if x.rel_type == "DIRECTOR_OF"),
        "us_control_caution": tests["us"] != MET
        and any(x.rel_type == "CONTROLS" and x.source in regime_seeds["us"] for x in direct),
        "uk_control_to_assess": tests["uk"] != MET
        and any(
            x.rel_type == "DIRECTOR_OF"
            or (x.rel_type == "CONTROLS" and not _appoints(x) and not _voting(x))
            for x in direct
            if x.source in uk_seeds
        ),
        "uk_nominee_holdings": sum(
            1 for x in evidence.values() if x.rel_type == "OWNS" and x.is_nominee
        ),
        "uk_measures_unknown": measures_unknown,
        "eu_control_criteria": ", ".join(eu_criteria),
        "lists": ", ".join(
            r
            for r in REGIMES
            if any(s in regime_seeds[r] or (r == "uk" and s in ctx.uk_unknown) for s in sources)
        ),
        "lists_text": lists_text(sources, ctx),
    }
    synthetic = metrics["lists_text"] == SYNTHETIC_LIST
    uk_holders = {path[0].source for path in own_paths if path[0].source in uk_seeds}
    metrics["assessment"] = assessment(metrics, synthetic, len(uk_holders))
    steps = [tuple(x.rel_id for x in path) for path in all_paths[: p.max_steps]]
    room = max(0, p.max_steps - len(steps))
    steps += [(x.rel_id,) for x in sorted(extra, key=lambda x: x.rel_id)][:room]
    if own_paths:
        variant = "ownership"
    elif strong or all_paths:
        variant = "control"
    else:
        variant = "director"
    nodes = {target, *sources} | {n for x in evidence.values() for n in (x.source, x.target)}
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=target,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(evidence)),
        subjects=(Subject(target, "exposed_entity"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=False,
    )
