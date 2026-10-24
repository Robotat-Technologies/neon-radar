"""Shared helpers for the API tests: graph connections without a database.

The integration tests use the shared Neo4j fixture `neo4j` (one per test session) of
graph/tests/support/nr_test_neo4j.py, which the root conftest.py registers once for every
suite; tests import `Neo4jTarget` from that module, never the fixtures.

The app answers only this machine's host names (`neonradar_api.hardening.ALLOWED_HOSTS`), so
every test client uses a base URL on `http://127.0.0.1`, not TestClient's `http://testserver`
(PHASE-4.md M4.1).

The helpers of the Phase 4 tests (`apiclient.py`, `phase4app.py`, `benchapp.py`) sit next to
the tests, and the fake neo4j driver next to the graph tests; pytest runs with
--import-mode=importlib, so both folders go on the path.
"""

import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from neo4j import Driver

from neonradar_api.graph import GraphConnection, GraphUnavailable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "graph" / "tests"))
sys.path.insert(0, str(HERE))

REPO_ROOT = Path(__file__).resolve().parents[2]


class OfflineGraph(GraphConnection):
    """Neo4j is down."""

    def read(self, query: str, parameters: Mapping[str, Any] | None = None, **_: Any) -> list[Any]:
        raise GraphUnavailable("no database in unit tests")

    def call[T](self, work: Callable[[Driver, str], T]) -> T:
        raise GraphUnavailable("no database in unit tests")


class ScriptedGraph(GraphConnection):
    """Answers each query with `answer(query, parameters)` and records the calls."""

    def __init__(self, answer: Callable[[str, dict[str, Any]], list[Any]]) -> None:
        super().__init__()
        self.answer = answer
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def read(self, query: str, parameters: Mapping[str, Any] | None = None, **_: Any) -> list[Any]:
        params = dict(parameters or {})
        self.calls.append((query, params))
        return self.answer(query, params)


class SessionGraph(GraphConnection):
    """The API's connection on the test session's driver (integration tests), which it must not
    close: `SessionGraph(neo4j)` with the shared `neo4j` fixture's `Neo4jTarget`."""

    def __init__(self, target: Any) -> None:
        super().__init__()
        self._driver: Driver | None = target.driver
        self._database = target.database

    def close(self) -> None:
        return None
