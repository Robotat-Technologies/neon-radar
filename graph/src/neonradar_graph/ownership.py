"""Ownership chains and shortest paths as C3 1.1.0 promises them (PHASE-2.md 5.3, M2.12).

`ownership()` and `paths()` resolve each id with `queries/resolve_id.cypher` (a canonical id or
the id of a record merged into it; `UnknownId` otherwise), pick the query variant for
`max_hops` (one rendered text per value, from the file's `lint-values` header, never from
input), run it read-only with a 5-second transaction timeout (`QueryTimeout` when it runs out)
and build the C3 subgraph with Phase 1's builder (`neonradar_graph.shapes`).

Effective shares: the ownership queries round them in Cypher before they filter and order, and
Python passes them through. `paths()` computes them only for a path made entirely of `OWNS`
relationships that all point the same way, multiplying in the direction of the relationships
as the ownership queries do and rounding half up to 4 decimals, so both endpoints give the same
figures for the same chain. An effective share is NeonRadar's calculation from the published
bands, never a figure a register records or the result of a sanctions ownership test (ADR-0019).
"""

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from typing import Any, Final, get_args

from neo4j import Driver, Query, Record, RoutingControl
from neo4j.exceptions import Neo4jError

from neonradar_contracts.api import (
    MAX_OWNERSHIP_PATHS,
    MAX_PATH_SUBGRAPH_NODES,
    PATHS_DEFAULT_TYPES,
    QUERY_TIMEOUT_SECONDS,
    GraphEdge,
    GraphNode,
    OwnershipDirection,
    OwnershipResponse,
    PathRef,
    PathsResponse,
    RelationshipType,
    Subgraph,
)
from neonradar_graph import cypher, shapes

SCAN_LIMIT: Final = 5000
OWNERSHIP_FILES: Final[Mapping[OwnershipDirection, str]] = {
    "up": "ownership_up.cypher",
    "down": "ownership_down.cypher",
}
PATHS_FILE: Final = "paths.cypher"
PATH_TYPES: Final = frozenset(get_args(RelationshipType))
FOUR_PLACES: Final = Decimal("0.0001")
TIMED_OUT: Final = "TransactionTimedOut"  # in the codes of Neo4j's transaction timeout errors
TIMEOUT_DETAIL: Final = (
    f"The query did not finish within {QUERY_TIMEOUT_SECONDS:g} seconds. Try again with a"
    " smaller max_hops or fewer relationship types."
)


class UnknownId(LookupError):
    """Neither an entity nor a source record has the id (HTTP 404)."""


class QueryTimeout(Exception):
    """The transaction ran out of time (HTTP 503 with `TIMEOUT_DETAIL`)."""


@cache
def _variants(name: str) -> dict[int, str]:
    """The text of `queries/<name>` for each `max_hops` value its header lists."""
    return {
        int(hops): cypher.query(name, max_hops=hops)
        for hops in cypher.declared(name).get("max_hops", ())
    }


def _variant(name: str, max_hops: int) -> str:
    text = _variants(name).get(max_hops)
    if text is None:
        raise ValueError(f"max_hops must be one of {sorted(_variants(name))} for {name}")
    return text


def read(driver: Driver, database: str, text: str, parameters: Mapping[str, Any]) -> list[Record]:
    """One parameterised query in a READ transaction with the 5-second timeout."""
    try:
        records, _, _ = driver.execute_query(
            Query(text, timeout=QUERY_TIMEOUT_SECONDS),
            dict(parameters),
            database_=database,
            routing_=RoutingControl.READ,
        )
    except Neo4jError as error:
        if TIMED_OUT in (error.code or ""):
            raise QueryTimeout(TIMEOUT_DETAIL) from error
        raise
    return list(records)


def pick_entity(entity_id: str, found: Sequence[str]) -> str:
    """The entity `resolve_id.cypher` found for `entity_id`: the entity itself, else the one
    entity its record was merged into; `UnknownId` when there is none."""
    ids = sorted(set(found))
    if entity_id in ids:
        return entity_id
    if len(ids) == 1:
        return ids[0]
    if not ids:
        raise UnknownId("no entity has this id")
    raise RuntimeError("a record id resolves to more than one entity: run `graph verify`")


def resolve_id(driver: Driver, entity_id: str, *, database: str = "neo4j") -> str:
    """The entity id for an entity id or for the id of a record merged into it."""
    rows = read(driver, database, cypher.query("resolve_id.cypher"), {"id": entity_id})
    return pick_entity(entity_id, [str(row["id"]) for row in rows])


def _rounded(value: float) -> float:
    """Half up to 4 decimals, from the shortest decimal form of the float (as Cypher's round)."""
    return float(Decimal(repr(value)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP))


def _product(bounds: Sequence[float | None]) -> float | None:
    """The bounds (each / 100) multiplied in order, times 100, rounded: the ownership queries'
    `round(reduce(acc = 1.0, r IN rels | acc * r.bound / 100.0) * 100.0, 4)`."""
    if any(bound is None for bound in bounds):
        return None
    acc = 1.0
    for bound in bounds:
        acc = acc * float(bound) / 100.0  # type: ignore[arg-type]
    return _rounded(acc * 100.0)


def chain_shares(row: Mapping[str, Any]) -> dict[str, Any]:
    """The effective share fields of one `paths.cypher` row: set only when every relationship is
    `OWNS` and all point the same way along the path, else all four null (5.3, Paths 3)."""
    none: dict[str, Any] = dict.fromkeys(
        ("effective_share_min", "effective_share_max", "effective_share_min_exclusive",
         "effective_share_max_exclusive"),
    )  # fmt: skip
    nodes, starts = list(row["node_ids"]), list(row["starts"])
    if not starts or any(kind != "OWNS" for kind in row["types"]):
        return none
    order = list(range(len(starts)))
    if all(starts[i] == nodes[i] for i in order):
        pass
    elif all(starts[i] == nodes[i + 1] for i in order):
        order.reverse()  # every OWNS points back along the path: multiply from its owner end
    else:
        return none
    low = _product([row["mins"][i] for i in order])
    high = _product([row["maxes"][i] for i in order])
    return {
        "effective_share_min": low,
        "effective_share_max": high,
        "effective_share_min_exclusive": None if low is None else any(row["mins_open"]),
        "effective_share_max_exclusive": None if high is None else any(row["maxes_open"]),
    }


def _subgraph(
    driver: Driver,
    database: str,
    paths: list[PathRef],
    types: list[list[str]],
    *,
    max_nodes: int,
    max_edges: int,
    truncated: bool,
) -> tuple[list[PathRef], Subgraph]:
    """The paths that fit the limits, in order, and the subgraph of their nodes and edges;
    `truncated` when a limit left a path out."""
    if max_edges != 2 * max_nodes:
        raise ValueError("C3 subgraph limits: max_edges is twice max_nodes")
    kept: list[tuple[PathRef, list[str]]] = []
    node_ids: dict[str, None] = {}
    edge_ids: dict[str, None] = {}
    for path, kinds in zip(paths, types, strict=True):
        more_nodes = {n: None for n in path.node_ids if n not in node_ids}
        more_edges = {e: None for e in path.edge_ids if e not in edge_ids}
        if len(node_ids) + len(more_nodes) > max_nodes or (
            len(edge_ids) + len(more_edges) > max_edges
        ):
            truncated = True
            continue
        node_ids.update(more_nodes)
        edge_ids.update(more_edges)
        kept.append((path, kinds))
    nodes_text, edges_text = cypher.statements("path_elements.cypher")
    found = read(driver, database, nodes_text, {"ids": list(node_ids)})
    by_id = {str(row["node"]["props"]["id"]): row["node"] for row in found}
    nodes: list[GraphNode] = [
        shapes.graph_node(by_id[node_id]) for node_id in node_ids if node_id in by_id
    ]
    links: dict[str, dict[str, str]] = {}
    for path, kinds in kept:
        for i, (edge_id, kind) in enumerate(zip(path.edge_ids, kinds, strict=True)):
            a, b = path.node_ids[i], path.node_ids[i + 1]
            if "Entity" not in by_id.get(a, {}).get("labels", ()):
                a, b = b, a  # look the relationship up from its :Entity end
            links.setdefault(edge_id, {"a": a, "b": b, "id": edge_id, "type": kind})
    rows = read(driver, database, edges_text, {"links": list(links.values())})
    by_edge = {str(row["edge"]["props"]["id"]): row["edge"] for row in rows}
    edges: list[GraphEdge] = [shapes.graph_edge(by_edge[e]) for e in edge_ids if e in by_edge]
    if len(nodes) != len(node_ids) or len(edges) != len(edge_ids):
        raise RuntimeError("a path element left the graph while it was read: try again")
    subgraph = shapes.subgraph(nodes, edges, truncated=truncated, max_nodes=max_nodes)
    return [path for path, _ in kept], subgraph


def ownership(
    driver: Driver,
    root_id: str,
    direction: OwnershipDirection,
    max_hops: int,
    min_share: float | None,
    limit: int = MAX_OWNERSHIP_PATHS,
    scan_limit: int = SCAN_LIMIT,
    max_nodes: int = MAX_PATH_SUBGRAPH_NODES,
    max_edges: int = 2 * MAX_PATH_SUBGRAPH_NODES,
    *,
    database: str = "neo4j",
) -> OwnershipResponse:
    """Chains of OWNS that end at the entity (`up`) or start at it (`down`), root first."""
    text = _variant(OWNERSHIP_FILES[direction], max_hops)
    root = resolve_id(driver, root_id, database=database)
    parameters = {"root_id": root, "min_share": float(min_share or 0), "scan_limit": scan_limit}
    rows = read(driver, database, text, parameters)
    paths = []
    for row in rows:
        node_ids, edge_ids = list(row["node_ids"]), list(row["edge_ids"])
        if direction == "up":  # the query lists owner first; C3 lists the root first (E13)
            node_ids.reverse()
            edge_ids.reverse()
        paths.append(
            PathRef(
                node_ids=node_ids,
                edge_ids=edge_ids,
                effective_share_min=row["eff_min"],
                effective_share_max=row["eff_max"],
                effective_share_min_exclusive=row["eff_min_exclusive"],
                effective_share_max_exclusive=row["eff_max_exclusive"],
            )
        )
    paths.sort(
        key=lambda p: (
            p.effective_share_max is None,
            -(p.effective_share_max or 0.0),
            len(p.edge_ids),
            p.node_ids,
        )
    )
    truncated = len(rows) >= scan_limit or len(paths) > limit
    kept, subgraph = _subgraph(
        driver,
        database,
        paths[:limit],
        [["OWNS"] * len(path.edge_ids) for path in paths[:limit]],
        max_nodes=max_nodes,
        max_edges=max_edges,
        truncated=truncated,
    )
    return OwnershipResponse(root_id=root, direction=direction, paths=kept, subgraph=subgraph)


def paths(
    driver: Driver,
    from_id: str,
    to_id: str,
    max_hops: int,
    rel_types: Sequence[str] | None,
    max_nodes: int = MAX_PATH_SUBGRAPH_NODES,
    max_edges: int = 2 * MAX_PATH_SUBGRAPH_NODES,
    *,
    database: str = "neo4j",
) -> PathsResponse:
    """Up to 5 shortest paths between two nodes, ignoring direction (5.3, Paths)."""
    types = list(dict.fromkeys(rel_types or PATHS_DEFAULT_TYPES))
    refused = sorted(set(types) - PATH_TYPES)
    if refused:
        raise ValueError(f"relationship types not allowed in paths: {refused}")
    text = _variant(PATHS_FILE, max_hops)
    start = resolve_id(driver, from_id, database=database)
    end = resolve_id(driver, to_id, database=database)
    rows = read(driver, database, text, {"from_id": start, "to_id": end, "rel_types": types})
    found: list[PathRef] = []
    kinds: list[list[str]] = []
    for row in rows:
        node_ids = [str(node_id) for node_id in row["node_ids"]]
        if len(set(node_ids)) != len(node_ids):
            continue  # simple paths only (ADR-0019): a walk that repeats a node is left out
        found.append(
            PathRef(node_ids=node_ids, edge_ids=list(row["edge_ids"]), **chain_shares(row))
        )
        kinds.append([str(kind) for kind in row["types"]])
    kept, subgraph = _subgraph(
        driver, database, found, kinds, max_nodes=max_nodes, max_edges=max_edges, truncated=False
    )
    return PathsResponse(from_id=start, to_id=end, paths=kept, subgraph=subgraph)
