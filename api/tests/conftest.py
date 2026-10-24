"""Shared helpers for the API tests: graph connections without a database.

The integration tests use the shared Neo4j fixture `neo4j` (one per test session) of
graph/tests/support/nr_test_neo4j.py, which the root conftest.py registers once for every
suite; tests import `Neo4jTarget` from that module, never the fixtures."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from neo4j import Driver

from neonradar_api.graph import GraphConnection, GraphUnavailable
from neonradar_api.settings import DEFAULT_ALLOWED_HOSTS

REPO_ROOT = Path(__file__).resolve().parents[2]
# FastAPI's TestClient sends `Host: testserver`; the app answers only its allowed hosts.
TEST_HOSTS = [*DEFAULT_ALLOWED_HOSTS, "testserver"]


@pytest.fixture(autouse=True)
def allow_the_test_client_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every app a test builds also answers the TestClient's host."""
    monkeypatch.setenv("NR_ALLOWED_HOSTS", json.dumps(TEST_HOSTS))


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
