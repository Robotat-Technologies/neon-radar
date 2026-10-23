"""Integration (PHASE-2.md M2.11 deliverable 7, G2-14): after a resolved load, an additive load
of a test-built file holding a synthetic BankAccount and an Ownership whose owner is a record id
that was merged (as Phase 3's overlay references record ids) puts the HOLDS_ACCOUNT on the
canonical node, found through the record's :SourceRecord (L13)."""

import csv
import json
from pathlib import Path

import pytest

from neonradar_graph.loader import load_files
from neonradar_graph.verify import verify

from .conftest import DEMO_DIRS, Neo4jTarget, record

pytestmark = pytest.mark.integration


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
    overlay = tmp_path / "overlay.ftm.jsonl"
    rows = [
        record("syn-acct-0901", "BankAccount", accountNumber="NRSYN0000000901", currency="EUR"),
        record("syn-ownership-0901", "Ownership", owner=member["record_id"], asset="syn-acct-0901"),
    ]
    overlay.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    # Non-strict: in strict mode C1 R4 refuses a reference to a record outside the load.
    report = load_files(
        graph_db.driver, [overlay], database=graph_db.database, replace=False, strict=False
    )
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    assert report.resolved_through_source_record == 1
    assert report.relationships_by_type["HOLDS_ACCOUNT"] == 1
    holders, _, _ = graph_db.driver.execute_query(
        "MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(:Entity {id: 'syn-acct-0901'}) RETURN h.id AS id",
        database_=graph_db.database,
    )
    assert [found["id"] for found in holders] == [member["canonical_id"]]
    assert member["canonical_id"] != member["record_id"]
    assert verify(graph_db.driver, graph_db.database) == {f"I{n}": 0 for n in range(1, 15)}
    # An account whose holder is neither in the load nor in the graph is still dropped (I4).
    rows[1]["properties"]["owner"] = ["syn-p-0999"]
    rows[0]["id"] = rows[1]["properties"]["asset"][0] = "syn-acct-0902"
    rows[1]["id"] = "syn-ownership-0902"
    overlay.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    report = load_files(graph_db.driver, [overlay], database=graph_db.database, strict=False)
    assert [(i.rule, i.record_id) for i in report.rejected] == [("R8", "syn-acct-0902")]
    assert verify(graph_db.driver, graph_db.database)["I4"] == 0
