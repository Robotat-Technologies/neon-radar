"""Helpers for the graph tests. The shared Neo4j (fixtures `neo4j`, `empty_neo4j` and
`graph_db`, `Neo4jTarget`, `pinned_gds`) lives in graph/tests/support/nr_test_neo4j.py, a
pytest plugin that the root conftest.py registers once for every suite; this file re-exports
the two names the graph tests import, never the fixtures."""

from typing import Any

from nr_test_neo4j import Neo4jTarget, pinned_gds

__all__ = ["Neo4jTarget", "pinned_gds", "record"]


def record(rid: str, schema: str, nr: dict[str, Any] | None = None, **props: Any) -> dict[str, Any]:
    """A C1-shaped record of nr_synthetic (prefix syn) or gb_companies_house (prefix gbch)."""
    synthetic = rid.startswith("syn-")
    data: dict[str, Any] = {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic" if synthetic else "gb_companies_house"],
        "properties": {
            key: value if isinstance(value, list) else [value] for key, value in props.items()
        },
    }
    if synthetic or nr:
        data["nr"] = {"v": "1.0", **({"synthetic": True} if synthetic else {}), **(nr or {})}
    return data
