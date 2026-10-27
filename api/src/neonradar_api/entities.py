"""`GET /search`, `GET /entities/{entity_id}` and its `/network` (contracts/C3-api.md).

An entity is an `:Entity` or `:Sanction` node, looked up by `id` through each label's
uniqueness index. Search uses the `entity_names` full-text index (LegalEntity and Address) with
the user's text escaped for Lucene, plus exact account numbers. The network has one fixed query
per depth, built in code from the same text, never from input.
"""

import re
from typing import Final, LiteralString, get_args

from neonradar_api import alerts, resolution
from neonradar_api.graph import GraphConnection
from neonradar_api.problems import NOT_FOUND, ProblemError
from neonradar_contracts.api import (
    MAX_ENTITY_ALERTS,
    EntityDetail,
    RelationshipType,
    SearchHit,
    SearchLabel,
    SearchResponse,
    Subgraph,
)
from neonradar_graph import cypher, shapes
from neonradar_graph.ownership import pick_entity

# Every type C3 shows (C3 1.1.0: the 16 built from records and POSSIBLY_SAME_AS).
SHOWN_TYPES: Final[list[str]] = list(get_args(RelationshipType))
# Full-text hits read before the label filter; `total_estimate` counts within this window.
SEARCH_WINDOW: Final = 200
LUCENE_SPECIAL: Final = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')
# The classic query parser's operators, as whole words.
OPERATOR: Final = re.compile(r"(?<!\S)(AND|OR|NOT)(?!\S)")
WORD: Final = re.compile(r"\w+")

FULLTEXT: Final = """
CALL db.index.fulltext.queryNodes('entity_names', $query, {limit: $window}) YIELD node, score
WHERE size($labels) = 0 OR any(label IN labels(node) WHERE label IN $labels)
WITH collect({props: properties(node), labels: labels(node), score: score}) AS hits
RETURN size(hits) AS total, hits[..$limit] AS hits
"""
ACCOUNT: Final = """
MATCH (n:Account {account_number: $number})
RETURN {props: properties(n), labels: labels(n)} AS node
LIMIT $limit
"""
ROOT: Final = """
OPTIONAL MATCH (e:Entity {id: $id})
OPTIONAL MATCH (s:Sanction {id: $id})
WITH coalesce(e, s) AS root
WHERE root IS NOT NULL
"""
# Entity detail also takes the id of a record merged into an entity (C3 1.1.0: any id in
# `referents`), through its :SourceRecord and RESOLVED_TO; one row per entity found.
DETAIL: Final = cypher.query("entity_detail.cypher")
# Breadth first: each hop expands only the nodes the previous hop found, keeps at most
# $max_nodes new ones, and the result keeps the nearest $max_nodes nodes.
_START: Final = ROOT + "WITH [root] AS seen, [root] AS frontier\n"
_HOP: Final = """
CALL (seen, frontier) {
  UNWIND frontier AS h
  MATCH (h)-[r]-(x)
  WHERE type(r) IN $types AND (x:Entity OR x:Sanction) AND NOT x IN seen
  WITH DISTINCT x LIMIT $max_nodes
  RETURN collect(x) AS found
}
WITH seen + found AS seen, found AS frontier
"""
_END: Final = """
WITH seen[..$max_nodes] AS nodes, size(seen) > $max_nodes AS cut
CALL (nodes) {
  UNWIND nodes AS a
  MATCH (a)-[r]->(b)
  WHERE type(r) IN $types AND b IN nodes
  WITH r LIMIT $edge_probe
  RETURN collect(r) AS rels
}
RETURN [n IN nodes | {props: properties(n), labels: labels(n)}] AS nodes,
       [r IN rels | {props: properties(r), type: type(r), source: startNode(r).id,
                     target: endNode(r).id}] AS edges,
       cut
"""
NETWORK: Final[dict[int, LiteralString]] = {
    1: _START + _HOP + _END,
    2: _START + _HOP + _HOP + _END,
    3: _START + _HOP + _HOP + _HOP + _END,
}


def lucene_query(text: str) -> str:
    """The user's text as plain Lucene terms: every special character escaped, and the operator
    words AND, OR and NOT in lower case so they are searched as words. The rest is left to the
    index analyzer: Python lowercases some letters differently from Lucene (Turkish dotted I,
    Greek final sigma), so lowercasing the whole text would lose hits."""
    escaped = LUCENE_SPECIAL.sub(r"\\\1", text)
    return OPERATOR.sub(lambda found: found[0].lower(), escaped)


def matched_name(names: list[str], caption: str, text: str) -> str:
    """The name that shares the most words with the query (the first one on a tie)."""
    terms = set(WORD.findall(text.lower()))
    best = max(names, key=lambda name: len(terms & set(WORD.findall(name.lower()))), default="")
    return best or caption


def search(
    graph: GraphConnection, text: str, labels: list[SearchLabel] | None, limit: int
) -> SearchResponse:
    wanted: list[str] = list(dict.fromkeys(labels or []))
    hits: list[SearchHit] = []
    total = 0
    if (not wanted or "Account" in wanted) and text.strip():
        records = graph.read(ACCOUNT, {"number": text.strip(), "limit": limit})
        for record in records:
            node = record["node"]
            number = str(node["props"].get("account_number", ""))
            hits.append(SearchHit(entity=shapes.summary(node), score=1.0, matched_name=number))
        total += len(records)
    fulltext_labels = [label for label in wanted if label != "Account"]
    if WORD.search(text) and (not wanted or fulltext_labels):
        query = {"query": lucene_query(text), "labels": fulltext_labels, "window": SEARCH_WINDOW}
        row = graph.read(FULLTEXT, {**query, "limit": limit})[0]
        total += int(row["total"])
        top = max((float(hit["score"]) for hit in row["hits"]), default=1.0)
        # Exact account numbers come first, with the top score of this response.
        hits = [hit.model_copy(update={"score": top}) for hit in hits]
        for hit in row["hits"]:
            props = hit["props"]
            names = [str(name) for name in props.get("names") or []]
            hits.append(
                SearchHit(
                    entity=shapes.summary(hit),
                    score=max(0.0, float(hit["score"])),
                    matched_name=matched_name(names, str(props["caption"]), text),
                )
            )
    return SearchResponse(query=text, items=hits[:limit], total_estimate=total)


def entity(graph: GraphConnection, entity_id: str) -> EntityDetail:
    records = graph.read(DETAIL, {"id": entity_id, "types": SHOWN_TYPES})
    if not records:
        raise ProblemError(404, NOT_FOUND)
    # A record id merged into two entities breaks I7: refuse, as the C3 1.1.0 routes do.
    by_id = {str(record["node"]["props"]["id"]): record for record in records}
    record = by_id[pick_entity(entity_id, list(by_id))]
    node = record["node"]
    counts: list[tuple[RelationshipType, int]] = record["counts"]
    props = node["props"]
    flagged = alerts.queue(graph, entity_id=str(props["id"]), limit=MAX_ENTITY_ALERTS)
    return EntityDetail(
        entity=shapes.summary(node),
        names=[str(name) for name in props.get("names") or []],
        properties=shapes.detail_properties(node),
        identifiers=shapes.identifiers(props),
        provenance=resolution.provenance(graph, props),
        relationship_counts={rel_type: int(count) for rel_type, count in sorted(counts)},
        alerts=list(flagged.items),
    )


def network(
    graph: GraphConnection,
    entity_id: str,
    *,
    depth: int,
    rel_types: list[RelationshipType] | None,
    max_nodes: int,
) -> Subgraph:
    parameters = {
        "id": entity_id,
        "types": list(dict.fromkeys(rel_types or SHOWN_TYPES)),
        "max_nodes": max_nodes,
        "edge_probe": 2 * max_nodes + 1,
    }
    records = graph.read(NETWORK[depth], parameters)
    if not records:
        raise ProblemError(404, NOT_FOUND)
    row = records[0]
    nodes = [shapes.graph_node(node) for node in row["nodes"]]
    edges = [shapes.graph_edge(edge) for edge in row["edges"]]
    truncated = bool(row["cut"]) or len(edges) > 2 * max_nodes
    return shapes.subgraph(nodes, edges[: 2 * max_nodes], truncated=truncated, max_nodes=max_nodes)
