"""Integration: `GET /paths` on the ownership fixture (PHASE-2.md M2.12).

The expected paths are the table of M2.12 (`graph/tests/fixtures/ownership/expected.json`): the
oracle. Effective shares are set only for a path of `OWNS` relationships that all point the same
way along it, with the figures `/ownership` gives for the same chain.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from neonradar_contracts.api import OwnershipResponse, PathsResponse, Problem

from .ownership_fixture import EXPECTED, PREFIX, P, interval, serve, table_row

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(neo4j: Any) -> Iterator[TestClient]:
    yield from serve(neo4j)


def _paths(client: TestClient, start: str, end: str, **params: Any) -> PathsResponse:
    params = {"from_id": f"{PREFIX}{start}", "to_id": f"{PREFIX}{end}", **params}
    response = client.get(f"{P}/paths", params=params)
    assert response.status_code == 200, response.text
    return PathsResponse.model_validate_json(response.text)


@pytest.mark.parametrize("case", EXPECTED["paths"], ids=lambda case: f"{case['from']}-{case['to']}")
def test_paths_match_the_table(client: TestClient, case: dict[str, Any]) -> None:
    body = _paths(client, case["from"], case["to"], max_hops=case["max_hops"])
    expected = [(nodes, interval(band)) for nodes, band in case["paths"]]
    assert [table_row(path) for path in body.paths] == expected
    assert {node.id for node in body.subgraph.nodes} == {
        node_id for path in body.paths for node_id in path.node_ids
    }
    assert not body.subgraph.truncated


def test_both_endpoints_give_the_same_figures_for_the_same_chain(client: TestClient) -> None:
    down = client.get(f"{P}/entities/{PREFIX}p-1/ownership", params={"direction": "down"})
    chain = next(
        p for p in OwnershipResponse.model_validate_json(down.text).paths if len(p.edge_ids) == 3
    )
    forward = _paths(client, "p-1", "co-3").paths[0]
    backward = _paths(client, "co-3", "p-1").paths[0]  # every OWNS points back along the path
    assert table_row(forward)[1] == table_row(backward)[1] == table_row(chain)[1]
    assert backward.node_ids == forward.node_ids[::-1]


def test_other_relationship_types_leave_the_shares_null(client: TestClient) -> None:
    body = _paths(client, "p-1", "co-3", rel_types=["CONTROLS"])
    assert body.paths == [] and body.subgraph.nodes == []
    assert table_row(_paths(client, "p-1", "co-2", rel_types=["OWNS", "CONTROLS"]).paths[0])[1] == (
        interval("(12.5, 37.5)")
    )


def test_unknown_ids_and_refused_types(client: TestClient) -> None:
    missing = client.get(f"{P}/paths", params={"from_id": f"{PREFIX}p-1", "to_id": f"{PREFIX}p-9"})
    assert missing.status_code == 404, missing.text
    assert Problem.model_validate_json(missing.text).detail == "No entity has this id."
    refused = client.get(
        f"{P}/paths",
        params={"from_id": f"{PREFIX}p-1", "to_id": f"{PREFIX}co-3", "rel_types": "RESOLVED_TO"},
    )
    assert refused.status_code == 422, refused.text
