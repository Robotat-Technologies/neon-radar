"""Shared helpers for the API tests: graph connections without a database, and the Neo4j of
the integration tests.

The integration tests use the Neo4j fixtures of graph/tests/conftest.py (`neo4j`, one per test
session, and `graph_db`, migrated and wiped), loaded the way detect/tests/conftest.py loads
them, so every suite starts Neo4j the same way (Testcontainers with the pinned GDS jar, or
NR_TEST_NEO4J_URI)."""

import importlib.util
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from neonradar_api.graph import GraphConnection, GraphUnavailable

REPO_ROOT = Path(__file__).resolve().parents[2]


class OfflineGraph(GraphConnection):
    """Neo4j is down."""

    def read(self, query: str, parameters: Mapping[str, Any] | None = None) -> list[Any]:
        raise GraphUnavailable("no database in unit tests")


class ScriptedGraph(GraphConnection):
    """Answers each query with `answer(query, parameters)` and records the calls."""

    def __init__(self, answer: Callable[[str, dict[str, Any]], list[Any]]) -> None:
        super().__init__()
        self.answer = answer
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def read(self, query: str, parameters: Mapping[str, Any] | None = None) -> list[Any]:
        params = dict(parameters or {})
        self.calls.append((query, params))
        return self.answer(query, params)


def _graph_conftest() -> ModuleType:
    """graph/tests/conftest.py, under the module name pytest gives it, loaded once."""
    name = "graph.tests.conftest"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, REPO_ROOT / "graph" / "tests" / "conftest.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


_GRAPH = _graph_conftest()
Neo4jTarget = _GRAPH.Neo4jTarget
neo4j = _GRAPH.neo4j  # pytest fixture, re-exported for the API integration tests
