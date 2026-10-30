"""Integration (PHASE-2.md M2.11 deliverable 7, G2-14): after a resolved load, an additive load
of a test-built file holding a synthetic BankAccount and an Ownership whose owner is a record id
that was merged (as Phase 3's overlay references record ids) puts the HOLDS_ACCOUNT on the
canonical node, found through the record's :SourceRecord (L13). C1 R8 still wants a holder in
the same load, so the account has a second, synthetic holder in the file, and an account whose
only holder is outside the load is dropped even when the graph holds it (OD-17,
phase-2-reconciliation 2.9 J5)."""

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from neonradar_graph.loader import load_files
from neonradar_graph.verify import verify

from .conftest import DEMO_DIRS, Neo4jTarget, record

pytestmark = pytest.mark.integration


def write(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_an_overlay_holding_of_a_merged_record_lands_on_its_canonical_node(
    graph_db: Neo4jTarget, demo_resolution: Path, tmp_path: Path
) -> None:
    resolved = load_files(
        graph_db.driver, DEMO_DIRS, database=graph_db.database, resolution=demo_resolution
    )
    assert resolved.dangling == []
    with (demo_resolution / "canonical.csv").open(encoding="utf-8", newline="") as handle:
        member = next(
            row
            for row in csv.DictReader(handle)
            if row["method"] == "deterministic" and row["class"] in ("person", "org")
        )
    assert member["canonical_id"] != member["record_id"]
    rows = [
        record("syn-p-0901", "Person", name="Syn Person 0901"),
        record("syn-acct-0901", "BankAccount", accountNumber="NRSYN0000000901", currency="EUR"),
        record("syn-ownership-0901", "Ownership", owner=member["record_id"], asset="syn-acct-0901"),
        record("syn-ownership-0902", "Ownership", owner="syn-p-0901", asset="syn-acct-0901"),
    ]
    # Non-strict: in strict mode C1 R4 refuses a reference to a record outside the load.
    report = load_files(
        graph_db.driver,
        [write(tmp_path / "overlay.ftm.jsonl", rows)],
        database=graph_db.database,
        replace=False,
        strict=False,
    )
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    assert report.resolved_through_source_record == 1
    assert report.relationships_by_type["HOLDS_ACCOUNT"] == 2
    holders, _, _ = graph_db.driver.execute_query(
        "MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(:Entity {id: 'syn-acct-0901'}) RETURN h.id AS id",
        database_=graph_db.database,
    )
    assert sorted(found["id"] for found in holders) == sorted(
        [member["canonical_id"], "syn-p-0901"]
    )
    assert verify(graph_db.driver, graph_db.database) == {f"I{n}": 0 for n in range(1, 18)}
    # An account whose only holder is outside the load fails C1 R8 and is dropped, although the
    # graph holds that holder; invariant I4 holds.
    alone = [
        record("syn-acct-0902", "BankAccount", accountNumber="NRSYN0000000902", currency="EUR"),
        record("syn-ownership-0903", "Ownership", owner=member["record_id"], asset="syn-acct-0902"),
    ]
    report = load_files(
        graph_db.driver,
        [write(tmp_path / "alone.ftm.jsonl", alone)],
        database=graph_db.database,
        replace=False,
        strict=False,
    )
    assert [(i.rule, i.record_id) for i in report.rejected] == [("R8", "syn-acct-0902")]
    found, _, _ = graph_db.driver.execute_query(
        "MATCH (a:Entity {id: 'syn-acct-0902'}) RETURN count(a) AS n", database_=graph_db.database
    )
    assert found[0]["n"] == 0
    assert verify(graph_db.driver, graph_db.database)["I4"] == 0
