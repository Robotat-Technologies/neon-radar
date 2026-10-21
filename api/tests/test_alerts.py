"""The alert queue's cursor and the alert detail's problems, without a database (M1.9c)."""

import base64
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from neonradar_api import alerts
from neonradar_api.main import create_app
from neonradar_contracts.api import AlertPage, Problem

from .conftest import REPO_ROOT, ScriptedGraph

P = "/api/v1"
ALERT_ID = "alr-f82a84574538090f0624"


def row(alert_id: str, priority: str, strength: float, rank: int) -> dict[str, Any]:
    subjects = [{"entity_id": "syn-co-0003"}, {"entity_id": "syn-acct-0007"}]
    return {
        "alert": {
            "alert_id": alert_id,
            "typology": "circular_flow",
            "priority": priority,
            "pattern_strength": strength,
            "headline": "Synthetic scenario: funds returned",
            "created_at": "2026-10-21T10:15:02Z",
            "involves_real_entities": False,
            "synthetic_activity": True,
            "payload": json.dumps({"subjects": subjects}),
        },
        "rank": rank,
        "flagged": ["syn-acct-0007", "syn-co-0003"],
    }


NO_FILTERS = alerts._digest({"typology": None, "priority": None, "entity_id": None, "run_id": None})


def raw_cursor(start: str) -> str:
    """A cursor for the unfiltered queue whose JSON starts with `start` (rank and strength)."""
    text = f'{start},"{ALERT_ID}","{NO_FILTERS}"]'
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


ROWS = [
    row("alr-00000000000000000001", "high", 0.9, 0),
    row("alr-00000000000000000002", "medium", 0.6, 1),
    row("alr-00000000000000000003", "low", 0.2, 2),
]


def problem(response: Any, status: int) -> Problem:
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    return Problem.model_validate_json(response.text)


def test_a_page_ends_with_a_cursor_to_the_next_one() -> None:
    graph = ScriptedGraph(lambda query, params: ROWS[: params["limit"]])
    with TestClient(create_app(graph)) as client:
        page = AlertPage.model_validate_json(client.get(f"{P}/alerts?limit=2").text)
        assert [item.alert_id for item in page.items] == [r["alert"]["alert_id"] for r in ROWS[:2]]
        assert page.items[0].subject_ids == ["syn-co-0003", "syn-acct-0007"]  # C4 order
        assert page.next_cursor is not None
        client.get(f"{P}/alerts", params={"limit": 2, "cursor": page.next_cursor})
    assert graph.calls[0][1]["after"] is None and graph.calls[0][1]["limit"] == 3
    assert graph.calls[1][1]["after"] == {
        "rank": 1,
        "strength": 0.6,
        "alert_id": "alr-00000000000000000002",
    }
    filters = {"typology": None, "priority": None, "entity_id": None, "run_id": None}
    assert alerts.decode_cursor(page.next_cursor, alerts._digest(filters))["rank"] == 1


def test_the_last_page_has_no_cursor() -> None:
    graph = ScriptedGraph(lambda query, params: ROWS[: params["limit"]])
    with TestClient(create_app(graph)) as client:
        page = AlertPage.model_validate_json(client.get(f"{P}/alerts").text)
    assert (len(page.items), page.next_cursor) == (3, None)


@pytest.mark.parametrize(
    "cursor",
    [
        "x",
        "not base64!",
        alerts.encode_cursor(1, 0.6, ALERT_ID, "0" * 16),  # issued for other filters
        alerts.encode_cursor(7, 0.6, ALERT_ID, "digest"),
        "WzEsIm5vIl0",  # [1,"no"]
        raw_cursor(f"[1,{'9' * 320}"),  # a huge strength must not overflow into a 500
        raw_cursor("[1,1"),  # strengths are floats in [0, 1]
        raw_cursor("[1,1.5"),
        raw_cursor("[1,1e400"),  # infinity
        raw_cursor("[true,0.5"),  # a rank is an int, not a bool
    ],
)
def test_a_bad_cursor_is_a_422_problem(cursor: str) -> None:
    graph = ScriptedGraph(lambda query, params: [])
    with TestClient(create_app(graph)) as client:
        found = problem(client.get(f"{P}/alerts", params={"cursor": cursor}), 422)
    assert found.detail == alerts.BAD_CURSOR
    assert graph.calls == []


def test_a_cursor_belongs_to_its_filters() -> None:
    graph = ScriptedGraph(lambda query, params: ROWS[: params["limit"]])
    with TestClient(create_app(graph)) as client:
        cursor = client.get(f"{P}/alerts?limit=1&priority=high").json()["next_cursor"]
        assert client.get(f"{P}/alerts?priority=high&cursor={cursor}").status_code == 200
        problem(client.get(f"{P}/alerts?priority=low&cursor={cursor}"), 422)


def test_unknown_and_stale_alerts_are_problems() -> None:
    stored = {ALERT_ID: [{"payload": '{"alert_id": "alr-00000000000000000000"}'}]}
    graph = ScriptedGraph(lambda query, params: stored.get(params["alert_id"], []))
    with TestClient(create_app(graph), raise_server_exceptions=False) as client:
        missing = problem(client.get(f"{P}/alerts/alr-00000000000000000009"), 404)
        stale = problem(client.get(f"{P}/alerts/{ALERT_ID}"), 500)
    assert missing.detail == alerts.NOT_FOUND
    assert stale.detail == alerts.STALE
    assert "re-run detection" in stale.detail


def test_an_alert_whose_evidence_left_the_graph_is_a_500_problem() -> None:
    """C3's AlertDetail cannot hold a partial evidence subgraph, so the API says to re-run."""
    example = REPO_ROOT / "contracts" / "examples" / "c4" / "circular_flow.json"

    def answer(query: str, params: dict[str, Any]) -> list[Any]:
        if query == alerts.PAYLOAD:
            return [{"payload": example.read_text(encoding="utf-8")}]
        return [{"nodes": [], "edges": []}]  # every evidence node was wiped

    with TestClient(create_app(ScriptedGraph(answer)), raise_server_exceptions=False) as client:
        found = problem(client.get(f"{P}/alerts/{ALERT_ID}"), 500)
    assert found.detail == alerts.MISSING_EVIDENCE


def test_a_valid_cursor_for_the_same_filters_is_accepted() -> None:
    graph = ScriptedGraph(lambda query, params: [])
    with TestClient(create_app(graph)) as client:
        assert client.get(f"{P}/alerts", params={"cursor": raw_cursor("[1,0.5")}).status_code == 200
    assert graph.calls[0][1]["after"] == {"rank": 1, "strength": 0.5, "alert_id": ALERT_ID}


def test_an_unreadable_alert_is_left_out_of_its_page() -> None:
    broken = row("alr-00000000000000000004", "high", 0.95, 0)
    broken["alert"]["payload"], broken["flagged"] = "not json", []
    graph = ScriptedGraph(lambda query, params: [broken, *ROWS][: params["limit"]])
    with TestClient(create_app(graph)) as client:
        page = AlertPage.model_validate_json(client.get(f"{P}/alerts").text)
    assert [item.alert_id for item in page.items] == [r["alert"]["alert_id"] for r in ROWS]


def test_a_payload_stored_under_another_alert_id_is_stale() -> None:
    example = REPO_ROOT / "contracts" / "examples" / "c4" / "circular_flow.json"
    graph = ScriptedGraph(lambda query, params: [{"payload": example.read_text(encoding="utf-8")}])
    with TestClient(create_app(graph), raise_server_exceptions=False) as client:
        found = problem(client.get(f"{P}/alerts/alr-00000000000000000009"), 500)
    assert found.detail == alerts.STALE
    assert "wipe and reload the data" in found.detail
