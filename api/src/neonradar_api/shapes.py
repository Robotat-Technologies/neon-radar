"""C2 nodes and relationships as C3 models (contracts/C3-api.md, "Graph shapes").

Queries return each node as `{props: properties(n), labels: labels(n)}` and each relationship
as `{props: properties(r), type: type(r), source: startNode(r).id, target: endNode(r).id}`, so
Neo4j `elementId()` values never leave the database. Property maps keep only the C2 properties
of the node's schema or the relationship's type (an allow-list from `neonradar_contracts.graph`),
minus what C3 leaves out, and `PAID.ts` becomes `YYYY-MM-DDTHH:MM:SSZ`.
"""

from collections.abc import Iterable, Mapping
from datetime import UTC
from typing import Any, Final

from neo4j.time import DateTime
from pydantic import JsonValue

from neonradar_contracts.api import (
    DETAIL_PROPERTIES_LEFT_OUT,
    EDGE_PROPERTIES_LEFT_OUT,
    NODE_PROPERTIES_LEFT_OUT,
    EntitySummary,
    GraphEdge,
    GraphNode,
    NodeFlags,
    NodeSchema,
    RelationshipType,
    Subgraph,
    SubgraphLimits,
)
from neonradar_contracts.graph import (
    COMMON_NODE_PROPERTIES,
    COMMON_RELATIONSHIP_PROPERTIES,
    NODE_MAPPINGS,
    REFERENCE_MAPPINGS,
    RELATIONSHIP_MAPPINGS,
    RESERVED_PROPERTIES,
    SUPPORT_RELATIONSHIPS,
)

Row = Mapping[str, Any]

NODE_KEYS: Final = {
    schema: frozenset(COMMON_NODE_PROPERTIES)
    | set(mapping.properties.values())
    | set(RESERVED_PROPERTIES.get(schema, ()))
    for schema, mapping in NODE_MAPPINGS.items()
}


def _edge_keys() -> dict[str, frozenset[str]]:
    keys: dict[str, set[str]] = {}
    for mappings in RELATIONSHIP_MAPPINGS.values():
        for mapping in mappings:
            keys.setdefault(mapping.type, set()).update(mapping.properties.values())
    for reference in REFERENCE_MAPPINGS:
        own = keys.setdefault(reference.type, set())
        own.update(reference.properties.values(), reference.defaults)
    # C2 1.1.0: entity resolution writes POSSIBLY_SAME_AS (a support relationship), which C3
    # shows like a record-built one (PHASE-2.md 5.2).
    keys["POSSIBLY_SAME_AS"] = set(SUPPORT_RELATIONSHIPS["POSSIBLY_SAME_AS"])
    common = frozenset(COMMON_RELATIONSHIP_PROPERTIES)
    return {rel_type: common | own for rel_type, own in keys.items()}


EDGE_KEYS: Final = _edge_keys()
# The identifier properties EntityDetail lists (C3 v1 keys).
IDENTIFIER_KEYS: Final = ("registration_number", "lei", "account_number")


def json_value(value: Any) -> JsonValue:
    """A Neo4j property value as JSON; the only DATETIME in C2 (`PAID.ts`) becomes UTC text."""
    if isinstance(value, DateTime):
        return value.to_native().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    return value  # type: ignore[no-any-return]


def properties(props: Row, keys: frozenset[str], left_out: frozenset[str]) -> dict[str, Any]:
    allowed = keys - left_out
    return {key: json_value(value) for key, value in sorted(props.items()) if key in allowed}


def schema_of(row: Row) -> NodeSchema:
    schema: NodeSchema = row["props"]["schema"]
    return schema


def flags(labels: Iterable[str]) -> NodeFlags:
    """The C2 flag labels; source facts, never findings."""
    found = set(labels)
    return NodeFlags(
        synthetic="Synthetic" in found,
        sanctioned="Sanctioned" in found,
        pep="PEP" in found,
        rca="RCA" in found,
    )


def _node_fields(row: Row) -> dict[str, Any]:
    """The fields GraphNode and EntitySummary share (`schema` is an alias, so they validate)."""
    props, schema = row["props"], schema_of(row)
    return {
        "id": props["id"],
        "schema": schema,
        "caption": props["caption"],
        "labels": list(NODE_MAPPINGS[schema].labels),  # never the flag labels
        "flags": flags(row["labels"]),
    }


def graph_node(row: Row) -> GraphNode:
    keys = NODE_KEYS[schema_of(row)]
    props = properties(row["props"], keys, NODE_PROPERTIES_LEFT_OUT)
    return GraphNode.model_validate({**_node_fields(row), "properties": props})


def summary(row: Row) -> EntitySummary:
    props = row["props"]
    return EntitySummary.model_validate(
        {
            **_node_fields(row),
            "countries": list(props.get("countries") or []),
            "datasets": list(props.get("datasets") or []),
        }
    )


def detail_properties(row: Row) -> dict[str, Any]:
    """EntityDetail.properties: the schema properties, first_seen, last_seen and source_url."""
    return properties(row["props"], NODE_KEYS[schema_of(row)], DETAIL_PROPERTIES_LEFT_OUT)


def identifiers(props: Row) -> dict[str, list[str]]:
    return {key: [str(props[key])] for key in IDENTIFIER_KEYS if props.get(key)}


def graph_edge(row: Row) -> GraphEdge:
    rel_type: RelationshipType = row["type"]
    return GraphEdge(
        id=row["props"]["id"],
        type=rel_type,
        source=row["source"],
        target=row["target"],
        properties=properties(row["props"], EDGE_KEYS[rel_type], EDGE_PROPERTIES_LEFT_OUT),
    )


def subgraph(
    nodes: list[GraphNode], edges: list[GraphEdge], *, truncated: bool, max_nodes: int
) -> Subgraph:
    limits = SubgraphLimits(max_nodes=max_nodes, max_edges=2 * max_nodes)
    return Subgraph(nodes=nodes, edges=edges, truncated=truncated, limits=limits)
