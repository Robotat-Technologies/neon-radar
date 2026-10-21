"""Every C3 route, its parameter limits and its problem bodies (PHASE-1.md 5.3, M1.7d)."""

import importlib.util
from collections.abc import Iterator
from typing import Annotated, Any

import pytest
from fastapi import Depends
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from neonradar_api.graph import GraphConnection, GraphUnavailable, get_graph
from neonradar_api.main import create_app, router
from neonradar_contracts.api import Problem

P = "/api/v1"
ENTITY = f"{P}/entities/syn-co-0001"
ALERT_ID = "alr-f82a84574538090f0624"
# Each route that answers 501 in M1.7d, a valid request for it, and who implements it.
PENDING: list[tuple[str, str, dict[str, Any], str]] = [
    ("GET", f"{P}/meta", {}, "M1.9c"),
    ("GET", f"{P}/search?q=ab&labels=Person&labels=Account&limit=50", {}, "M1.9c"),
    ("GET", ENTITY, {}, "M1.9c"),
    ("GET", f"{ENTITY}/network?depth=3&rel_types=PAID&max_nodes=500", {}, "M1.9c"),
    ("GET", f"{ENTITY}/ownership?direction=up&max_hops=8&min_share=25", {}, "Phase 2"),
    ("GET", f"{P}/paths?from_id=syn-co-0001&to_id=syn-p-0001&max_hops=6", {}, "Phase 2"),
    ("GET", f"{P}/alerts?typology=circular_flow&priority=high&limit=200&cursor=x", {}, "M1.9c"),
    ("GET", f"{P}/alerts?entity_id=syn-co-0001&run_id=run-20261021T101500-7f3a", {}, "M1.9c"),
    ("GET", f"{P}/alerts/{ALERT_ID}", {}, "M1.9c"),
    ("GET", f"{P}/typologies", {}, "M1.9c"),
    ("GET", f"{P}/typologies/circular_flow", {}, "M1.9c"),
    ("POST", f"{P}/copilot/ask", {"json": {"question": "who owns syn-co-0001?"}}, "Phase 4"),
]
# Requests that break one limit of 5.3 each.
INVALID: list[tuple[str, str, dict[str, Any]]] = [
    ("GET", f"{P}/search?q=a", {}),
    ("GET", f"{P}/search?q={'x' * 201}", {}),
    ("GET", f"{P}/search", {}),
    ("GET", f"{P}/search?q=ab&limit=0", {}),
    ("GET", f"{P}/search?q=ab&limit=51", {}),
    ("GET", f"{P}/search?q=ab&labels=Sanction", {}),
    ("GET", f"{P}/entities/not_an_id", {}),
    ("GET", f"{ENTITY}/network?depth=0", {}),
    ("GET", f"{ENTITY}/network?depth=4", {}),
    ("GET", f"{ENTITY}/network?max_nodes=0", {}),
    ("GET", f"{ENTITY}/network?max_nodes=501", {}),
    ("GET", f"{ENTITY}/network?rel_types=FLAGS", {}),
    ("GET", f"{ENTITY}/ownership", {}),
    ("GET", f"{ENTITY}/ownership?direction=sideways", {}),
    ("GET", f"{ENTITY}/ownership?direction=up&max_hops=0", {}),
    ("GET", f"{ENTITY}/ownership?direction=up&max_hops=9", {}),
    ("GET", f"{ENTITY}/ownership?direction=up&min_share=-1", {}),
    ("GET", f"{ENTITY}/ownership?direction=up&min_share=101", {}),
    ("GET", f"{P}/paths?from_id=syn-co-0001", {}),
    ("GET", f"{P}/paths?from_id=syn-co-0001&to_id=syn-p-0001&max_hops=0", {}),
    ("GET", f"{P}/paths?from_id=syn-co-0001&to_id=syn-p-0001&max_hops=7", {}),
    ("GET", f"{P}/alerts?limit=0", {}),
    ("GET", f"{P}/alerts?limit=201", {}),
    ("GET", f"{P}/alerts?priority=urgent", {}),
    ("GET", f"{P}/alerts?typology=Circular-Flow", {}),
    ("GET", f"{P}/alerts?run_id=run-1", {}),
    ("GET", f"{P}/alerts?cursor={'c' * 513}", {}),
    ("GET", f"{P}/alerts/alr-123", {}),
    ("GET", f"{P}/typologies/Circular-Flow", {}),
    ("POST", f"{P}/copilot/ask", {"json": {"question": ""}}),
    ("POST", f"{P}/copilot/ask", {"json": {"question": "x" * 501}}),
    ("POST", f"{P}/copilot/ask", {"json": {"question": "q", "sql": "x"}}),
    ("POST", f"{P}/copilot/ask", {"json": {"question": 5}}),
    ("POST", f"{P}/copilot/ask", {}),
]


class OfflineGraph(GraphConnection):
    def read(self, query: str, parameters: Any = None) -> list[Any]:
        raise GraphUnavailable("no database in unit tests")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(OfflineGraph()), raise_server_exceptions=False) as test_client:
        yield test_client


def _problem(response: Any, status: int) -> Problem:
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    problem = Problem.model_validate(response.json())
    assert (problem.type, problem.status) == ("about:blank", status)
    return problem


def test_every_route_of_5_3_is_declared() -> None:
    routes = {
        (method, route.path)
        for route in router.routes  # FastAPI 0.143 mounts included routers lazily
        if isinstance(route, APIRoute)
        for method in route.methods or ()
    }
    assert routes == {
        ("GET", f"{P}/health"),
        ("GET", f"{P}/meta"),
        ("GET", f"{P}/search"),
        ("GET", f"{P}/entities/{{entity_id}}"),
        ("GET", f"{P}/entities/{{entity_id}}/network"),
        ("GET", f"{P}/entities/{{entity_id}}/ownership"),
        ("GET", f"{P}/paths"),
        ("GET", f"{P}/alerts"),
        ("GET", f"{P}/alerts/{{alert_id}}"),
        ("GET", f"{P}/typologies"),
        ("GET", f"{P}/typologies/{{slug}}"),
        ("POST", f"{P}/copilot/ask"),
    }


@pytest.mark.parametrize(("method", "url", "options", "arrives_in"), PENDING)
def test_pending_routes_answer_501_naming_their_milestone(
    client: TestClient, method: str, url: str, options: dict[str, Any], arrives_in: str
) -> None:
    problem = _problem(client.request(method, url, **options), 501)
    assert problem.title == "Not Implemented"
    assert problem.detail.endswith(f"it arrives in {arrives_in}.")
    assert problem.instance == url.split("?")[0]


@pytest.mark.parametrize(("method", "url", "options"), INVALID)
def test_parameter_limits_answer_422_problems(
    client: TestClient, method: str, url: str, options: dict[str, Any]
) -> None:
    problem = _problem(client.request(method, url, **options), 422)
    assert problem.title == "Unprocessable Content"
    assert ": " in problem.detail  # "<location>: <message>"
    assert "x" * 201 not in problem.detail  # the input is not echoed


def test_unknown_routes_and_methods_answer_problems(client: TestClient) -> None:
    missing = _problem(client.get(f"{P}/nothing"), 404)
    assert missing.detail == f"No route matches GET {P}/nothing."
    wrong = client.delete(f"{P}/health")
    problem = _problem(wrong, 405)
    assert wrong.headers["allow"] == "GET"
    assert problem.detail == (
        f"DELETE is not allowed on {P}/health; the Allow header lists the methods it accepts."
    )


def test_an_unexpected_error_answers_a_generic_500_problem() -> None:
    app = create_app(OfflineGraph())

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail that must not leak")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        problem = _problem(test_client.get("/boom"), 500)
    assert "secret" not in problem.detail


def test_the_openapi_document_is_served_and_the_cdn_docs_pages_are_not(client: TestClient) -> None:
    assert client.get(f"{P}/openapi.json").json()["info"]["title"] == "NeonRadar API"
    for page in ("/docs", "/redoc", "/docs/oauth2-redirect", "/openapi.json"):
        _problem(client.get(page), 404)


def test_cors_allows_only_the_vite_dev_server(client: TestClient) -> None:
    preflight = {"access-control-request-method": "GET"}
    allowed = client.options(
        f"{P}/health", headers={"origin": "http://localhost:5173", **preflight}
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.options(f"{P}/health", headers={"origin": "http://evil.example", **preflight})
    assert "access-control-allow-origin" not in other.headers


def test_fastapi_telemetry_stays_off_even_when_the_environment_asks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FASTAPI_OTEL_AUTO_CONFIGURE", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
    app = create_app(OfflineGraph())
    settings = app._telemetry  # FastAPI 0.143 has no public accessor
    assert not any(settings[key] for key in ("tracing", "metrics", "logs", "operation_spans"))
    assert settings["auto_configure"] is False
    assert app._native_telemetry.enabled() is False
    with TestClient(app) as test_client:  # the lifespan runs without configuring exporters
        assert test_client.get(f"{P}/health").status_code == 200


def test_no_opentelemetry_sdk_or_exporter_is_installed() -> None:
    """opentelemetry-api alone is a no-op; an SDK or exporter would make export possible (G3)."""
    for module in ("opentelemetry.sdk", "opentelemetry.exporter"):
        try:
            found = importlib.util.find_spec(module)
        except ModuleNotFoundError:
            found = None
        assert found is None, module


def test_an_unknown_body_key_is_reported_without_echoing_it(client: TestClient) -> None:
    body = {"question": "q", "sentinel_key_7f3a": 1, "another_key_9c1d": 2}
    problem = _problem(client.post(f"{P}/copilot/ask", json=body), 422)
    assert problem.detail == "body: unknown keys are not permitted"
    assert "sentinel" not in problem.detail and "another" not in problem.detail


def test_an_unavailable_graph_answers_a_503_problem_without_internals() -> None:
    app = create_app(OfflineGraph())

    @app.get("/needs-graph")
    def needs_graph(graph: Annotated[GraphConnection, Depends(get_graph)]) -> None:
        graph.read("RETURN 1 AS n")

    with TestClient(app) as test_client:
        problem = _problem(test_client.get("/needs-graph"), 503)
    assert problem.title == "Service Unavailable"
    assert problem.detail == "The graph database is not available."
