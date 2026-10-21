"""Integration: the record loader on a real Neo4j 5.26 Community (PHASE-1.md M1.9a, C2 loader
rules). Expected rows come from `neonradar_graph.mapping`, so a regenerated fixture still
passes; records that may not be committed (non-synthetic or invalid ones) are built here."""

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from neo4j.time import DateTime

from neonradar_contracts.graph import RELATIONSHIP_ENDPOINTS
from neonradar_contracts.records import iter_records
from neonradar_graph.client import REPO_ROOT
from neonradar_graph.loader import (
    LoadError,
    LoadRefused,
    load_files,
    load_records,
    stats,
    wipe,
)
from neonradar_graph.mapping import to_node_rows, to_relationship_rows

from .conftest import Neo4jTarget, record

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"
DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
NODES = (
    "MATCH (n) WHERE NOT n:SchemaMigration"
    " RETURN n.id AS id, labels(n) AS labels, properties(n) AS props ORDER BY id"
)
RELATIONSHIPS = (
    "MATCH (a)-[r]->(b) RETURN type(r) AS type, r.id AS id, a.id AS source, b.id AS target,"
    " labels(a) AS source_labels, labels(b) AS target_labels, properties(r) AS props"
    " ORDER BY type, id"
)


def query(db: Neo4jTarget, cypher: str, **params: Any) -> list[dict[str, Any]]:
    records, _, _ = db.driver.execute_query(cypher, params, database_=db.database)
    return [record.data() for record in records]


def snapshot(db: Neo4jTarget) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = [{**row, "labels": sorted(row["labels"])} for row in query(db, NODES)]
    return nodes, query(db, RELATIONSHIPS)


def node_count(db: Neo4jTarget) -> int:
    return len(query(db, NODES))


def fixture() -> dict[str, dict[str, Any]]:
    """The all-schemata records by id, copied so that a test can change them."""
    return {data["id"]: copy.deepcopy(data) for data in iter_records(FIXTURE)}


def test_every_schema_loads_as_the_mapping_says(graph_db: Neo4jTarget) -> None:
    records = list(fixture().values())
    nodes, relationships = to_node_rows(records).rows, to_relationship_rows(records).rows
    report = load_records(graph_db.driver, records, database=graph_db.database)
    assert (report.dangling, report.rejected, report.skipped, report.failed) == ([], [], [], False)
    assert report.nodes_by_label == Counter(
        label for row in nodes for label in (*row.labels, *row.flags)
    )
    assert report.relationships_by_type == Counter(row.type for row in relationships)
    assert report.written["nodes_created"] == len(nodes)
    assert report.written["relationships_created"] == len(relationships)
    stored_nodes, stored_relationships = snapshot(graph_db)
    assert stored_nodes == [
        {"id": row.id, "labels": sorted([*row.labels, *row.flags]), "props": row.props}
        for row in sorted(nodes, key=lambda row: row.id)
    ]
    expected = {(row.type, row.id): row for row in relationships}
    assert {(row["type"], row["id"]) for row in stored_relationships} == set(expected)
    for stored in stored_relationships:
        row = expected[stored["type"], stored["id"]]
        source_label, target_label = RELATIONSHIP_ENDPOINTS[row.type]
        assert (stored["source"], stored["target"]) == (row.source, row.target)
        assert source_label in stored["source_labels"]
        assert target_label in stored["target_labels"]  # SUBJECT_OF ends at a :Sanction
        props = dict(stored["props"])
        if row.type == "PAID":
            ts = props.pop("ts")
            assert isinstance(ts, DateTime) and ts.utcoffset().total_seconds() == 0
            assert ts.iso_format().startswith(row.ts.removesuffix("Z"))  # type: ignore[union-attr]
        assert props == row.props


def test_loading_demo_mini_twice_changes_nothing(graph_db: Neo4jTarget) -> None:
    first = load_files(graph_db.driver, [DEMO_MINI], database=graph_db.database)
    before = snapshot(graph_db)
    second = load_files(graph_db.driver, [DEMO_MINI], database=graph_db.database)
    assert first.dangling == [] and first.duration_s < 30
    assert first.records == second.records > 0
    assert first.written["nodes_created"] == len(before[0]) > 0
    assert first.written["relationships_created"] == len(before[1]) > 0
    assert second.nodes_by_label == first.nodes_by_label
    assert second.relationships_by_type == first.relationships_by_type
    assert all(count == 0 for count in second.written.values()), second.written
    assert snapshot(graph_db) == before


def test_a_reload_follows_the_changed_record(graph_db: Neo4jTarget) -> None:
    records = fixture()
    person = record("gbch-p-1", "Person", name="Zoe Example", topics=["role.pep.natl"])
    load_records(graph_db.driver, [*records.values(), person], database=graph_db.database)
    labels = "MATCH (n:Entity {id: $id}) RETURN labels(n) AS labels, n.topics AS topics"
    assert "PEP" in query(graph_db, labels, id="gbch-p-1")[0]["labels"]
    # The source drops the topic, and an Ownership changes its asset.
    person["properties"]["topics"] = []
    owns = records["syn-ownership-0001"]
    old_asset = owns["properties"]["asset"]
    owns["properties"]["asset"] = ["syn-co-0002"]
    report = load_records(graph_db.driver, [*records.values(), person], database=graph_db.database)
    (stored,) = query(graph_db, labels, id="gbch-p-1")
    assert "PEP" not in stored["labels"] and stored["topics"] == []
    assert report.written["labels_removed"] == 1
    assert report.written["relationships_deleted"] == report.written["relationships_created"] == 1
    moved = query(
        graph_db,
        "MATCH (a)-[r:OWNS {id: $id}]->(b) RETURN a.id AS source, b.id AS target",
        id="syn-ownership-0001",
    )
    assert moved == [{"source": owns["properties"]["owner"][0], "target": "syn-co-0002"}]
    assert old_asset != ["syn-co-0002"]


def test_non_strict_counts_dangling_references(graph_db: Neo4jTarget) -> None:
    records = fixture()
    # An earlier load holds the person; this load refers to it.
    load_records(graph_db.driver, [records["syn-p-0001"]], database=graph_db.database)
    load = [
        records[rid]
        for rid in (
            "syn-co-0001",
            "syn-addr-0001",
            "syn-co-0002",
            "syn-acct-0001",
            "syn-ownership-0002",
        )
    ]
    payment = records["syn-payment-000001"]
    payment["properties"]["beneficiaryAccount"] = ["syn-acct-0099"]  # in neither load
    owns = records["syn-ownership-0001"]  # syn-p-0001 owns syn-co-0001: resolves
    wrong = record(  # the "organization" is a Person in the graph: wrong label
        "syn-directorship-0009", "Directorship", director="syn-co-0001", organization="syn-p-0001"
    )
    # In strict mode the same load is refused before anything is written.
    before = node_count(graph_db)
    with pytest.raises(LoadRefused) as refused:
        load_records(graph_db.driver, [*load, payment, owns, wrong], database=graph_db.database)
    assert {issue.rule for issue in refused.value.issues} == {"R4"}
    assert node_count(graph_db) == before
    report = load_records(
        graph_db.driver, [*load, payment, owns, wrong], strict=False, database=graph_db.database
    )
    dangling = {(d.type, d.id, d.source_missing, d.target_missing) for d in report.dangling}
    assert dangling == {
        ("PAID", "syn-payment-000001", False, True),
        ("DIRECTOR_OF", "syn-directorship-0009", False, True),
    }
    assert not report.failed
    assert (
        report.relationships_by_type["OWNS"] == report.relationships_by_type["HOLDS_ACCOUNT"] == 1
    )
    assert report.relationships_by_type["PAID"] == report.relationships_by_type["DIRECTOR_OF"] == 0
    assert query(graph_db, "MATCH ()-[r:PAID|DIRECTOR_OF]->() RETURN count(r) AS n") == [{"n": 0}]


def bad_payment(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records["syn-payment-000001"]["properties"]["amount"] = ["-5"]  # R7
    return list(records.values())


def dangling_payment(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records["syn-payment-000001"]["properties"]["beneficiaryAccount"] = ["syn-acct-0099"]  # R4
    return list(records.values())


def two_owners(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records["syn-ownership-0001"]["properties"]["owner"].append("syn-p-0002")  # MappingIssue
    return list(records.values())


@pytest.mark.parametrize("change", [bad_payment, dangling_payment, two_owners])
def test_strict_refuses_bad_input_and_writes_nothing(graph_db: Neo4jTarget, change: Any) -> None:
    with pytest.raises(LoadRefused) as refused:
        load_records(graph_db.driver, change(fixture()), database=graph_db.database)
    assert refused.value.issues or refused.value.skipped
    assert node_count(graph_db) == 0


def test_non_strict_skips_records_that_fail_c1(graph_db: Neo4jTarget) -> None:
    records = fixture()
    duplicate = copy.deepcopy(records["syn-co-0002"])
    duplicate["properties"]["name"] = ["Another Name"]
    bad_id = record("gbch-co-x", "Company", name="Zoe Example")  # R1: needs gb_companies_house ids
    bad_id["datasets"] = ["nr_synthetic"]
    unheld = record("syn-acct-0009", "BankAccount", accountNumber="NRSYN0000000009")  # R8
    report = load_records(
        graph_db.driver,
        [*records.values(), duplicate, bad_id, unheld],
        strict=False,
        database=graph_db.database,
    )
    rules = Counter(issue.rule for issue in report.rejected)
    assert rules["R4"] == 1 and rules["R8"] == 1 and rules["R1"] >= 1
    loaded = {row["id"] for row in query(graph_db, NODES)}
    assert loaded == {row.id for row in to_node_rows(list(records.values())).rows}
    name = "MATCH (n:Entity {id: 'syn-co-0002'}) RETURN n.names AS names"
    assert query(graph_db, name)[0]["names"] == records["syn-co-0002"]["properties"]["name"]


def test_stats_and_wipe(graph_db: Neo4jTarget) -> None:
    load_records(graph_db.driver, list(fixture().values()), database=graph_db.database)
    nodes, relationships = snapshot(graph_db)
    counted = stats(graph_db.driver, graph_db.database)
    assert counted.nodes == len(nodes) + 1  # and the :SchemaMigration node
    assert counted.relationships == len(relationships)
    assert counted.relationship_types == dict(Counter(row["type"] for row in relationships))
    assert counted.labels["Entity"] == sum("Entity" in row["labels"] for row in nodes)
    assert wipe(graph_db.driver, graph_db.database) == len(nodes)
    assert node_count(graph_db) == 0
    assert query(graph_db, "MATCH (m:SchemaMigration) RETURN m.id AS id") == [{"id": "0001_init"}]
    assert len(query(graph_db, "SHOW CONSTRAINTS YIELD name")) == 22


def test_a_load_needs_the_migrated_schema(empty_neo4j: Neo4jTarget) -> None:
    with pytest.raises(LoadError, match="neonradar graph migrate"):
        load_records(empty_neo4j.driver, list(fixture().values()), database=empty_neo4j.database)
    assert node_count(empty_neo4j) == 0
