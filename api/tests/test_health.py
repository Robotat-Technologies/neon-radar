"""`GET /api/v1/health` without a database: a fake connection answers the three queries."""

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient
from neo4j import RoutingControl
from neo4j.exceptions import ClientError, ServiceUnavailable
from pydantic import SecretStr, ValidationError

from neonradar_api.graph import GraphConnection, GraphUnavailable
from neonradar_api.health import check_health
from neonradar_api.main import create_app
from neonradar_graph.client import Neo4jSettings
from neonradar_graph.smoke import APOC_VERSION, COMPONENTS, GDS_VERSION

KERNEL = [{"name": "Neo4j Kernel", "versions": ["5.26.32"], "edition": "community"}]


class FakeGraph(GraphConnection):
    def __init__(self, answers: Mapping[str, list[dict[str, Any]] | Exception]) -> None:
        super().__init__()
        self.answers = answers
        self.queries: list[str] = []

    def read(self, query: str, parameters: Mapping[str, Any] | None = None) -> list[Any]:
        self.queries.append(query)
        answer = self.answers[query]
        if isinstance(answer, Exception):
            raise answer
        return answer


ALL: dict[str, list[dict[str, Any]] | Exception] = {
    COMPONENTS: KERNEL,
    APOC_VERSION: [{"version": "5.26.32"}],
    GDS_VERSION: [{"version": "2.13.4"}],
}


def test_ok_when_neo4j_apoc_and_gds_answer() -> None:
    health = check_health(FakeGraph(ALL))
    assert health.model_dump() == {
        "status": "ok",
        "neo4j": {"connected": True, "version": "5.26.32", "edition": "community"},
        "apoc_version": "5.26.32",
        "gds_version": "2.13.4",
    }


def test_degraded_without_gds() -> None:
    missing = ClientError("Unknown function 'gds.version'")
    health = check_health(FakeGraph({**ALL, GDS_VERSION: missing}))
    assert (health.status, health.neo4j.connected, health.gds_version) == ("degraded", True, None)
    assert health.apoc_version == "5.26.32"


def test_degraded_and_offline_when_neo4j_is_unavailable() -> None:
    graph = FakeGraph({COMPONENTS: GraphUnavailable("connection refused")})
    health = check_health(graph)
    assert health.status == "degraded"
    assert health.neo4j.model_dump() == {"connected": False, "version": None, "edition": None}
    assert graph.queries == [COMPONENTS]  # stops at the first failure


def test_the_route_answers_200_even_when_degraded() -> None:
    with TestClient(create_app(FakeGraph({COMPONENTS: GraphUnavailable("down")}))) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


def _unconfigured() -> Neo4jSettings:
    # What Neo4jSettings() raises without NEO4J_PASSWORD; built here so no env or .env is read.
    missing = {"type": "missing", "loc": ("password",), "input": {}}
    raise ValidationError.from_exception_data("Neo4jSettings", [missing])  # type: ignore[list-item]


def test_missing_settings_mean_unavailable_without_reading_any_env_file() -> None:
    graph = GraphConnection(settings=_unconfigured)
    with pytest.raises(GraphUnavailable, match="not configured"):
        graph.read("RETURN 1 AS n")
    assert check_health(graph).neo4j.connected is False


class FakeDriver:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def execute_query(self, query: str, parameters: Mapping[str, Any], **options: Any) -> Any:
        self.calls.append({"query": query, "parameters": parameters, **options})
        if self.error:
            raise self.error
        return ([{"n": 1}], None, None)

    def close(self) -> None:
        self.closed = True


def _connection(monkeypatch: pytest.MonkeyPatch, driver: FakeDriver) -> GraphConnection:
    monkeypatch.setattr("neonradar_api.graph.get_driver", lambda settings: driver)
    settings = Neo4jSettings(password=SecretStr("unused"), database="neo4j")
    return GraphConnection(settings=lambda: settings)


def test_every_query_is_a_read_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = FakeDriver()
    graph = _connection(monkeypatch, driver)
    assert graph.read("RETURN $n AS n", {"n": 1}) == [{"n": 1}]
    assert driver.calls == [
        {
            "query": "RETURN $n AS n",
            "parameters": {"n": 1},
            "database_": "neo4j",
            "routing_": RoutingControl.READ,
        }
    ]
    graph.close()
    assert driver.closed


def test_driver_errors_mean_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = _connection(monkeypatch, FakeDriver(ServiceUnavailable("refused")))
    with pytest.raises(GraphUnavailable):
        graph.read("RETURN 1 AS n")
