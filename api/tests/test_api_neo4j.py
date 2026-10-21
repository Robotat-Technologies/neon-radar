"""Integration: every Phase 1 route against Neo4j with demo-mini and one detection run (M1.9c).

Expected values come from the fixture files through the C2 mapping and from the run report,
never from hard-coded demo-mini names or counts (the fixture is regenerated). Every response
is validated against its C3 model. Three synthetic records built here (never committed as a
fixture) join the load: a Sanction on the first demo-mini Company (a `:Sanction` node reached
through SUBJECT_OF) and two Addresses whose names Python lowercases differently from Lucene.
"""

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from neo4j import Driver
from neo4j.exceptions import ClientError
from nr_test_neo4j import Neo4jTarget

from neonradar_api.files import RepoFiles
from neonradar_api.graph import GraphConnection
from neonradar_api.main import create_app
from neonradar_contracts.api import (
    AlertDetail,
    AlertPage,
    EntityDetail,
    HealthResponse,
    MetaResponse,
    Problem,
    SearchResponse,
    Subgraph,
    TypologySummary,
)
from neonradar_detect import runner
from neonradar_graph.loader import collect_files, load_records, read_records, wipe
from neonradar_graph.mapping import NodeRow, RelationshipRow, to_node_rows, to_relationship_rows
from neonradar_graph.migrate import migrate

from .conftest import REPO_ROOT, TEST_HOSTS

pytestmark = pytest.mark.integration

P = "/api/v1"
DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
SANCTION = "syn-sanction-t0001"
TURKISH, GREEK = "İstanbul", "ΘΕΣΣΑΛΟΝΙΚΗΣ"  # dotted capital I; a final capital sigma


def synthetic(rid: str, schema: str, **props: list[str]) -> dict[str, Any]:
    return {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic"],
        "referents": [],
        "properties": props,
        "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"},
    }


def extra_records(demo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    company = next(record["id"] for record in demo if record["schema"] == "Company")
    return [
        synthetic(
            SANCTION,
            "Sanction",
            entity=[company],
            authority=["Synthetic Test Authority"],
            program=["Synthetic test programme"],
        ),
        synthetic("syn-addr-t-tr", "Address", full=[TURKISH], city=[TURKISH], country=["tr"]),
        synthetic("syn-addr-t-gr", "Address", full=[GREEK], city=[GREEK], country=["gr"]),
    ]


def breadth_first(rels: list[RelationshipRow], root: str, depth: int) -> set[str]:
    """The nodes within `depth` hops of `root`, either direction, over every record type."""
    seen, frontier = {root}, {root}
    for _ in range(depth):
        frontier = {
            end
            for r in rels
            for start, end in ((r.source, r.target), (r.target, r.source))
            if start in frontier and end not in seen
        }
        seen |= frontier
    return seen


class SessionGraph(GraphConnection):
    """The API's connection on the test session's driver, which it must not close."""

    def __init__(self, target: Neo4jTarget) -> None:
        super().__init__()
        self._driver: Driver | None = target.driver
        self._database = target.database

    def close(self) -> None:
        return None


@dataclass
class Stack:
    client: TestClient
    graph: SessionGraph
    run: runner.RunReport
    nodes: list[NodeRow]
    rels: list[RelationshipRow]


@pytest.fixture(scope="module")
def stack(neo4j: Neo4jTarget, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    wipe(neo4j.driver, neo4j.database)
    migrate(neo4j.driver, neo4j.database)
    demo = read_records(collect_files([DEMO_MINI]))
    records = [*demo, *extra_records(demo)]
    report = load_records(neo4j.driver, records, database=neo4j.database)
    assert not report.failed
    run = runner.run(
        neo4j.driver,
        neo4j.database,
        typology="circular_flow",
        runs_dir=tmp_path_factory.mktemp("runs"),
    )
    assert run.alerts, "demo-mini's round_trip scenario gives at least one alert"
    graph = SessionGraph(neo4j)
    app = create_app(graph, RepoFiles(REPO_ROOT), allowed_hosts=TEST_HOSTS)
    with TestClient(app) as client:
        yield Stack(
            client, graph, run, to_node_rows(records).rows, to_relationship_rows(records).rows
        )


def ok(response: Any) -> str:
    assert response.status_code == 200, response.text
    return str(response.text)


def problem(response: Any, status: int) -> Problem:
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    return Problem.model_validate_json(response.text)


def queue_order(alerts: list[Any]) -> list[str]:
    rank = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(alerts, key=lambda a: (rank[a.priority], -a.pattern_strength, a.alert_id))
    return [alert.alert_id for alert in ordered]


def test_reads_run_in_read_transactions(stack: Stack) -> None:
    with pytest.raises(ClientError, match=r"(?i)write"):
        stack.graph.read("CREATE (:ApiWriteProbe)")


def test_health_is_ok_with_apoc_and_gds(stack: Stack) -> None:
    health = HealthResponse.model_validate_json(ok(stack.client.get(f"{P}/health")))
    assert (health.status, health.neo4j.connected) == ("ok", True)


def test_meta_counts_the_loaded_records_per_dataset(stack: Stack) -> None:
    meta = MetaResponse.model_validate_json(ok(stack.client.get(f"{P}/meta")))
    counts = {d.slug: d.record_count for d in meta.datasets}
    assert counts.pop("nr_synthetic") == len(stack.nodes)
    assert set(counts.values()) == {0}
    assert meta.counts.nodes_by_label["Alert"] == len(stack.run.alerts)
    assert meta.counts.relationships_by_type["PAID"] == Counter(r.type for r in stack.rels)["PAID"]


def test_search_finds_a_company_by_the_first_word_of_its_name(stack: Stack) -> None:
    company = next(row for row in stack.nodes if row.schema == "Company")
    word = str(company.props["names"][0]).split()[0]
    found = SearchResponse.model_validate_json(
        ok(stack.client.get(f"{P}/search", params={"q": word, "labels": "Company", "limit": 50}))
    )
    assert company.id in [hit.entity.id for hit in found.items]
    assert {hit.entity.schema_ for hit in found.items} == {"Company"}
    assert all(word.lower() in hit.matched_name.lower() for hit in found.items)


def test_search_matches_account_numbers_exactly_and_survives_lucene_syntax(stack: Stack) -> None:
    account = next(row for row in stack.nodes if row.schema == "BankAccount")
    number = str(account.props["account_number"])
    found = SearchResponse.model_validate_json(
        ok(stack.client.get(f"{P}/search", params={"q": number, "labels": "Account"}))
    )
    assert [(hit.entity.id, hit.matched_name) for hit in found.items] == [(account.id, number)]
    for text in ['Ltd AND (" OR', "**", "a/b\\c:", "NOT ~1"]:
        SearchResponse.model_validate_json(ok(stack.client.get(f"{P}/search", params={"q": text})))


def test_entity_detail_counts_relationships_and_lists_alerts(stack: Stack) -> None:
    alert = stack.run.alerts[0]
    subject = alert.subjects[-1].entity_id
    detail = EntityDetail.model_validate_json(ok(stack.client.get(f"{P}/entities/{subject}")))
    expected = Counter(r.type for r in stack.rels if subject in (r.source, r.target))
    assert detail.relationship_counts == dict(expected)
    assert alert.alert_id in [summary.alert_id for summary in detail.alerts]
    assert [p.record_id for p in detail.provenance] == [subject]
    assert detail.entity.flags.synthetic is True


def test_unknown_ids_are_404_problems(stack: Stack) -> None:
    for url in (
        f"{P}/entities/syn-nothing-0000",
        f"{P}/entities/syn-nothing-0000/network",
        f"{P}/alerts/alr-00000000000000000000",
        f"{P}/typologies/no_such_typology",
    ):
        assert problem(stack.client.get(url), 404).instance == url


def test_the_network_follows_the_mapping_and_caps_its_size(stack: Stack) -> None:
    root = stack.run.alerts[0].subjects[0].entity_id
    url = f"{P}/entities/{root}/network"
    one = Subgraph.model_validate_json(ok(stack.client.get(url)))
    near = breadth_first(stack.rels, root, 1)
    assert {node.id for node in one.nodes} == near
    assert {edge.id for edge in one.edges} == {
        r.id for r in stack.rels if r.source in near and r.target in near
    }
    assert not one.truncated
    for depth in (2, 3):
        params = {"depth": depth, "max_nodes": 500}
        wider = Subgraph.model_validate_json(ok(stack.client.get(url, params=params)))
        assert {node.id for node in wider.nodes} == breadth_first(stack.rels, root, depth)
        assert not wider.truncated
    paid = Subgraph.model_validate_json(ok(stack.client.get(url, params={"rel_types": "PAID"})))
    assert {edge.type for edge in paid.edges} == {"PAID"}
    capped = Subgraph.model_validate_json(
        ok(stack.client.get(url, params={"depth": 3, "max_nodes": 2}))
    )
    assert (len(capped.nodes), capped.truncated, capped.limits.max_edges) == (2, True, 4)
    assert capped.nodes[0].id == root


def test_the_alert_queue_pages_in_order_and_filters(stack: Stack) -> None:
    every = AlertPage.model_validate_json(ok(stack.client.get(f"{P}/alerts")))
    assert [a.alert_id for a in every.items] == queue_order(stack.run.alerts)
    assert every.next_cursor is None
    paged, cursor = [], None
    while True:
        params: dict[str, Any] = {"limit": 1} | ({"cursor": cursor} if cursor else {})
        page = AlertPage.model_validate_json(ok(stack.client.get(f"{P}/alerts", params=params)))
        paged += [a.alert_id for a in page.items]
        if (cursor := page.next_cursor) is None:
            break
    assert paged == [a.alert_id for a in every.items]
    run_id = stack.run.run_id
    by_run = AlertPage.model_validate_json(ok(stack.client.get(f"{P}/alerts?run_id={run_id}")))
    assert len(by_run.items) == len(every.items)
    other = AlertPage.model_validate_json(
        ok(stack.client.get(f"{P}/alerts?run_id=run-20000101T000000-0000&typology=circular_flow"))
    )
    assert other.items == []
    subject = stack.run.alerts[0].subjects[0].entity_id
    flagged = AlertPage.model_validate_json(ok(stack.client.get(f"{P}/alerts?entity_id={subject}")))
    assert all(subject in a.subject_ids for a in flagged.items) and flagged.items


def test_an_alert_comes_with_its_complete_evidence(stack: Stack) -> None:
    stored = stack.run.alerts[0]
    detail = AlertDetail.model_validate_json(ok(stack.client.get(f"{P}/alerts/{stored.alert_id}")))
    assert detail.alert == stored
    assert not detail.evidence.truncated
    edges = {edge.id: edge for edge in detail.evidence.edges}
    assert set(stored.evidence.edge_ids) <= set(edges)
    assert {edges[e].type for e in stored.evidence.edge_ids} == {"PAID"}
    nodes = {node.id for node in detail.evidence.nodes}
    holds = {(r.source, r.target) for r in stack.rels if r.type == "HOLDS_ACCOUNT"}
    assert {(e.source, e.target) for e in edges.values() if e.type == "HOLDS_ACCOUNT"} == {
        pair for pair in holds if set(pair) <= nodes
    }


def test_typologies_are_served_from_the_catalog(stack: Stack) -> None:
    items = [TypologySummary.model_validate(t) for t in stack.client.get(f"{P}/typologies").json()]
    assert "circular_flow" in [t.slug for t in items if t.detector_available]


def test_a_sanction_node_is_an_entity_reached_through_subject_of(stack: Stack) -> None:
    listed = next(r.source for r in stack.rels if r.type == "SUBJECT_OF" and r.target == SANCTION)
    sanction = EntityDetail.model_validate_json(ok(stack.client.get(f"{P}/entities/{SANCTION}")))
    assert (sanction.entity.schema_, sanction.entity.labels) == ("Sanction", ["Sanction"])
    assert sanction.relationship_counts == {"SUBJECT_OF": 1}
    assert sanction.properties["authority"] == "Synthetic Test Authority"
    url = f"{P}/entities/{SANCTION}/network"
    network = Subgraph.model_validate_json(ok(stack.client.get(url)))
    assert {node.id for node in network.nodes} == {SANCTION, listed}
    assert [edge.type for edge in network.edges] == ["SUBJECT_OF"]
    company = EntityDetail.model_validate_json(ok(stack.client.get(f"{P}/entities/{listed}")))
    assert company.relationship_counts["SUBJECT_OF"] == 1
    assert company.entity.flags.sanctioned is False  # only source topics set the flag (C2)
    found = SearchResponse.model_validate_json(
        ok(stack.client.get(f"{P}/search", params={"q": "Synthetic Test Authority"}))
    )
    assert SANCTION not in [hit.entity.id for hit in found.items]  # search never lists them


def test_search_filters_on_supertype_labels(stack: Stack) -> None:
    person = next(row for row in stack.nodes if row.schema == "Person")
    word = str(person.props["names"][0]).split()[-1]
    for labels, schemas in (
        ("LegalEntity", {"Person", "Company", "Organization", "PublicBody", "LegalEntity"}),
        ("Organization", {"Company", "Organization", "PublicBody"}),
    ):
        params = {"q": word, "labels": labels, "limit": 50}
        found = SearchResponse.model_validate_json(
            ok(stack.client.get(f"{P}/search", params=params))
        )
        assert {hit.entity.schema_ for hit in found.items} <= schemas
    legal = SearchResponse.model_validate_json(
        ok(
            stack.client.get(
                f"{P}/search", params={"q": word, "labels": "LegalEntity", "limit": 50}
            )
        )
    )
    assert person.id in [hit.entity.id for hit in legal.items]


@pytest.mark.parametrize("name", [TURKISH, GREEK])
def test_search_leaves_lowercasing_to_the_index(stack: Stack, name: str) -> None:
    found = SearchResponse.model_validate_json(
        ok(stack.client.get(f"{P}/search", params={"q": name, "labels": "Address"}))
    )
    assert [hit.matched_name for hit in found.items] == [name]
