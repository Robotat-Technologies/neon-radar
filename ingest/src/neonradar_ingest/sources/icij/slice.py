"""Which ICIJ nodes a profile loads, and its profile block (PHASE-2.md M2.5 deliverable 2).

`select` streams the archive's CSV members (several passes, keeping only node ids) and returns
the nodes by level. `district-linked`: level 0 the addresses with a UK postcode in the
profile's Companies House postcode districts, level 1 the entities and officers registered at
them, level 2 the officers and intermediaries of those entities. `gb-linked`: level 0 the nodes
with `GBR` among their country codes, level 1 their direct neighbours. `full`: every node. Only
nodes with a usable name (addresses: address text) count. Over `max_nodes`, whole levels are
kept in order and, inside the level that overflows, the nodes with the smallest
`sha256("<sample_seed>|<node_id>")`.
"""

import hashlib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveInt,
    StrictBool,
    StrictInt,
    ValidationInfo,
    model_validator,
)

from neonradar_keys.postcodes import find_uk_postcode, postcode_parts

Mode = Literal["district-linked", "gb-linked", "full"]
Row = Mapping[str, str | None]
Rows = Callable[[str], Iterable[Row]]  # member name -> its rows, read again on every call
Usable = Callable[[str, Row], bool]  # (kind, row) -> the row has a name (addresses: text)
NODE_FILES = {
    "nodes-entities.csv": "entity",
    "nodes-officers.csv": "officer",
    "nodes-intermediaries.csv": "intermediary",
    "nodes-others.csv": "other",
    "nodes-addresses.csv": "address",
}
RELATIONSHIPS = "relationships.csv"
HINT_PREFIXES = ("same_", "similar", "probably_same_")
SKIP_NO_NAME = "nodes without a usable name"
SKIP_KIND_CLASH = "node ids in an address file and another node file (first kept)"


def postcode_districts(sources: Mapping[str, Any]) -> frozenset[str]:
    """`gb_companies_house.companies.postcode_districts` of a profile's `sources`, upper case."""
    config = sources.get("gb_companies_house")
    options = getattr(config, "options", config)  # a SourceConfig, a dict or None
    companies = options.get("companies") if isinstance(options, Mapping) else None
    found = companies.get("postcode_districts") if isinstance(companies, Mapping) else None
    if not isinstance(found, list):
        return frozenset()
    return frozenset(str(item).strip().upper() for item in found if str(item).strip())


class IcijSource(BaseModel):
    """The `icij_offshore_leaks` block of a profile (unknown keys fail)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    mode: Mode = "district-linked"
    max_nodes: PositiveInt = 50_000  # ignored in `full` mode
    sample_seed: StrictInt = 0

    @model_validator(mode="after")
    def _needs_districts(self, info: ValidationInfo) -> Self:
        """`district-linked` needs the same profile's Companies House postcode districts."""
        sources = (info.context or {}).get("sources", {})
        if self.enabled and self.mode == "district-linked" and not postcode_districts(sources):
            raise ValueError(
                "mode district-linked needs gb_companies_house.companies.postcode_districts"
                " in the same profile"
            )
        return self


def is_hint(rel_type: str) -> bool:
    """ICIJ's own duplicate hints (`same_*`, `similar*`, `probably_same_*`)."""
    return rel_type.startswith(HINT_PREFIXES)


def ends(row: Row) -> tuple[str, str, str]:
    """(start node id, end node id, rel_type in lower case), stripped."""
    start, end = (row.get("node_id_start") or "").strip(), (row.get("node_id_end") or "").strip()
    return start, end, (row.get("rel_type") or "").strip().lower()


def in_districts(address: str | None, districts: frozenset[str]) -> bool:
    postcode, _ = find_uk_postcode(address or "")
    return postcode is not None and postcode_parts(postcode).district in districts


def is_gb(row: Row) -> bool:
    return "GBR" in {code.strip().upper() for code in (row.get("country_codes") or "").split(";")}


@dataclass
class Selection:
    """Selected node ids by level, the kept ones after the cap, and each kept id's kinds."""

    levels: list[set[str]]
    kept: set[str]
    kinds: dict[str, tuple[str, ...]]  # file kinds of each kept id, in file order
    skipped: Counter[str] = field(default_factory=Counter)

    @property
    def selected(self) -> set[str]:
        return self.kept if len(self.levels) == 1 else set().union(*self.levels)

    def counts(self) -> dict[str, Any]:
        sizes = [len(level) for level in self.levels]
        return {
            "nodes_by_level": {f"level_{n}": size for n, size in enumerate(sizes)},
            "nodes_selected": sum(sizes),
            "nodes_kept": len(self.kept),
            "nodes_dropped_by_cap": sum(sizes) - len(self.kept),
        }


def node_kinds(
    rows: Rows,
    usable: Usable,
    skipped: Counter[str],
    *,
    wanted: set[str] | None = None,
    files: Iterable[str] = NODE_FILES,
    match: Callable[[str, Row], bool] | None = None,
) -> dict[str, tuple[str, ...]]:
    """The kinds of every usable node row (of `wanted` ids, else all) that `match` accepts.

    Rows without a usable name are counted in `skipped`. An id in the addresses file and in
    another node file keeps its first kind only.
    """
    kinds: dict[str, tuple[str, ...]] = {}
    for name in files:
        kind = NODE_FILES[name]
        for row in rows(name):
            node = (row.get("node_id") or "").strip()
            if not node or (wanted is not None and node not in wanted):
                continue
            if match is not None and not match(kind, row):
                continue
            if not usable(kind, row):
                skipped[SKIP_NO_NAME] += 1
                continue
            known = kinds.get(node, ())
            if kind in known:
                continue
            if known and ("address" in known) != (kind == "address"):
                skipped[SKIP_KIND_CLASH] += 1
                continue
            kinds[node] = (*known, kind)
    return kinds


def _district_linked(
    rows: Rows, usable: Usable, districts: frozenset[str], skipped: Counter[str]
) -> tuple[list[set[str]], dict[str, tuple[str, ...]]]:
    def located(kind: str, row: Row) -> bool:
        return in_districts(row.get("address"), districts)

    level0 = set(node_kinds(rows, usable, Counter(), files=["nodes-addresses.csv"], match=located))
    registered: set[str] = set()
    for row in rows(RELATIONSHIPS):
        start, end, rel = ends(row)
        if rel == "registered_address" and end in level0:
            registered.add(start)
    pairs: list[tuple[str, str]] = []
    for row in rows(RELATIONSHIPS):
        start, end, rel = ends(row)
        if rel in ("officer_of", "intermediary_of") and end in registered:
            pairs.append((start, end))
    wanted = level0 | registered | {start for start, _ in pairs}
    kinds = node_kinds(rows, usable, skipped, wanted=wanted)
    level1 = {n for n in registered if {"entity", "officer"} & set(kinds.get(n, ()))} - level0
    entities = {n for n in level1 if "entity" in kinds[n]}
    level2 = (
        {
            start
            for start, end in pairs
            if end in entities and {"officer", "intermediary"} & set(kinds.get(start, ()))
        }
        - level0
        - level1
    )
    return [level0, level1, level2], kinds


def _gb_linked(
    rows: Rows, usable: Usable, skipped: Counter[str]
) -> tuple[list[set[str]], dict[str, tuple[str, ...]]]:
    level0 = set(node_kinds(rows, usable, Counter(), match=lambda kind, row: is_gb(row)))
    neighbours: set[str] = set()
    for row in rows(RELATIONSHIPS):
        start, end, rel = ends(row)
        if is_hint(rel):
            continue  # a hint is not a link
        if start in level0:
            neighbours.add(end)
        if end in level0:
            neighbours.add(start)
    kinds = node_kinds(rows, usable, skipped, wanted=level0 | neighbours)
    return [level0, {n for n in neighbours if n in kinds} - level0], kinds


def _cap(levels: list[set[str]], max_nodes: int, seed: int) -> set[str]:
    kept: set[str] = set()
    for level in levels:
        room = max_nodes - len(kept)
        if len(level) <= room:
            kept |= level
            continue

        def order(node: str) -> str:
            return hashlib.sha256(f"{seed}|{node}".encode()).hexdigest()

        kept.update(sorted(level, key=order)[: max(room, 0)])
        break
    return kept


def select(rows: Rows, usable: Usable, options: IcijSource, districts: frozenset[str]) -> Selection:
    """The nodes `options.mode` selects, capped at `options.max_nodes` (not in `full` mode)."""
    skipped: Counter[str] = Counter()
    if options.mode == "full":
        kinds = node_kinds(rows, usable, skipped)
        everything = set(kinds)
        return Selection([everything], everything, kinds, skipped)
    if options.mode == "district-linked":
        levels, kinds = _district_linked(rows, usable, districts, skipped)
    else:
        levels, kinds = _gb_linked(rows, usable, skipped)
    kept = _cap(levels, options.max_nodes, options.sample_seed)
    return Selection(levels, kept, {n: kinds[n] for n in kept}, skipped)
