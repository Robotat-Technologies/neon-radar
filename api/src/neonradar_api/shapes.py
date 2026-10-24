"""C3's "Graph shapes" pointer (contracts/C3-api.md, Code): the builders moved to
`neonradar_graph.shapes` in M2.12, so the API and the copilot build the same subgraphs. This
module only re-exports them until a C3 wording patch names the new home."""

from neonradar_graph.shapes import (
    EDGE_KEYS,
    IDENTIFIER_KEYS,
    NODE_KEYS,
    detail_properties,
    flags,
    graph_edge,
    graph_node,
    identifiers,
    json_value,
    properties,
    schema_of,
    subgraph,
    summary,
)

__all__ = [
    "EDGE_KEYS",
    "IDENTIFIER_KEYS",
    "NODE_KEYS",
    "detail_properties",
    "flags",
    "graph_edge",
    "graph_node",
    "identifiers",
    "json_value",
    "properties",
    "schema_of",
    "subgraph",
    "summary",
]
