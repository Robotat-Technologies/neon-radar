"""Integration: `GET /entities/{entity_id}/ownership` on the ownership fixture (PHASE-2.md M2.12).

The expected paths are the table of M2.12 (`graph/tests/fixtures/ownership/expected.json`): the
oracle. A test that disagrees with the table is a failing test, not a reason to change it. The
table writes upward paths owner first; C3 lists every path root first (reconciliation E13).
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from neonradar_contracts.api import OwnershipResponse, Problem

from .ownership_fixture import EXPECTED, PREFIX, P, interval, serve, table_row

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(neo4j: Any) -> Iterator[TestClient]:
    yield from serve(neo4j)


def _ownership(client: TestClient, root: str, **params: Any) -> OwnershipResponse:
    response = client.get(f"{P}/entities/{PREFIX}{root}/ownership", params=params)
    assert response.status_code == 200, response.text
    return OwnershipResponse.model_validate_json(response.text)


def _case_id(case: dict[str, Any]) -> str:
    return f"{case['root']}-{case['direction']}-hops{case['max_hops']}-min{case['min_share']}"


@pytest.mark.parametrize("case", EXPECTED["ownership"], ids=_case_id)
def test_ownership_paths_match_the_table(client: TestClient, case: dict[str, Any]) -> None:
    body = _ownership(
        client,
        case["root"],
        direction=case["direction"],
        max_hops=case["max_hops"],
        min_share=case["min_share"],
    )
    expected = [
        (nodes[::-1] if case["direction"] == "up" else nodes, interval(band))
        for nodes, band in case["paths"]
    ]
    assert [table_row(path) for path in body.paths] == expected
    assert (body.root_id, body.direction) == (f"{PREFIX}{case['root']}", case["direction"])
    shown = {node.id for node in body.subgraph.nodes}
    assert shown == {node_id for path in body.paths for node_id in path.node_ids}
    assert {edge.type for edge in body.subgraph.edges} <= {"OWNS"}
    assert not body.subgraph.truncated


def test_the_acceptance_request_returns_five_paths(client: TestClient) -> None:
    body = _ownership(client, "co-3", direction="up", min_share=0)  # max_hops defaults to 6
    assert len(body.paths) == 5
    assert (body.subgraph.limits.max_nodes, body.subgraph.limits.max_edges) == (500, 1000)


def test_paths_are_cut_to_the_limit_and_marked_truncated(neo4j: Any, client: TestClient) -> None:
    from neonradar_graph.ownership import ownership

    body = ownership(neo4j.driver, f"{PREFIX}co-3", "up", 6, 0, limit=2, database=neo4j.database)
    assert [table_row(path)[0] for path in body.paths] == [
        ["co-3", "co-2"],
        ["co-3", "co-2", "co-1"],
    ]
    assert body.subgraph.truncated
    scanned = ownership(
        neo4j.driver, f"{PREFIX}co-3", "up", 6, 0, scan_limit=5, database=neo4j.database
    )
    assert len(scanned.paths) == 5 and scanned.subgraph.truncated  # the scan limit was reached
    small = ownership(
        neo4j.driver, f"{PREFIX}co-3", "up", 6, 0, max_nodes=3, max_edges=6, database=neo4j.database
    )
    assert [table_row(path)[0] for path in small.paths] == [
        ["co-3", "co-2"],
        ["co-3", "co-2", "co-1"],
    ]
    assert small.subgraph.truncated and len(small.subgraph.nodes) == 3


def test_an_unknown_root_is_a_404_problem(client: TestClient) -> None:
    response = client.get(f"{P}/entities/{PREFIX}co-99/ownership", params={"direction": "up"})
    assert response.status_code == 404, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert Problem.model_validate_json(response.text).detail == "No entity has this id."
