"""Integration: the detection store, C2 1.2.0 L19 (PHASE-3.md 5.4, M3.2 deliverable 8).

Two runs leave one :DetectionRun and the second run's alerts; the five new :DetectionRun
properties and the two :Alert properties are set, and `summary` parses as JSON; I17 holds after
the load; `--keep-previous` keeps earlier runs; a failed run records a failed :DetectionRun and
keeps the earlier results (OD-10); verify-alert finds every evidence node and relationship, and
reports a missing one.
"""

import json
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from kit import WINDOW, Kit
from neo4j import RoutingControl
from nr_test_neo4j import Neo4jTarget

from neonradar_detect import catalog, runner, runs
from neonradar_detect.detectors import circular_flow
from neonradar_detect.neo4jsource import Neo4jSource
from neonradar_graph.loader import load_records

pytestmark = pytest.mark.integration

VERIFY_OVERLAY = (
    Path(__file__).resolve().parents[2]
    / "graph"
    / "src"
    / "neonradar_graph"
    / "queries"
    / "verify_overlay.cypher"
)


def statements() -> dict[str, str]:
    """I15 to I17 from the C2 1.2.0 file: the `// I<n>:` comment that opens a block names the
    statement after it, which ends at the line ending with `;` (as graph/tests reads it)."""
    out: dict[str, str] = {}
    name, lines = "", list[str]()
    for line in VERIFY_OVERLAY.read_text(encoding="utf-8").splitlines():
        if line.startswith("//"):
            if not lines and line[3:].split(":")[0] in ("I15", "I16", "I17"):
                name = line[3:].split(":")[0]
            continue
        lines.append(line)
        if line.rstrip().endswith(";"):
            out[name] = "\n".join(lines).rstrip().removesuffix(";")
            name, lines = "", []
    return out


def read(db: Neo4jTarget, cypher: str, **params: Any) -> list[dict[str, Any]]:
    records, _, _ = db.driver.execute_query(
        cypher, params, database_=db.database, routing_=RoutingControl.READ
    )
    return [record.data() for record in records]


@pytest.fixture
def db(graph_db: Neo4jTarget) -> Neo4jTarget:
    k = Kit()
    for tag in ("a", "b"):
        accts = [k.account(f"{tag}{i}", k.company(f"{tag}{i}")) for i in range(4)]
        for i, (src, dst) in enumerate(zip(accts, accts[1:] + accts[:1], strict=True)):
            k.pay(src, dst, 50000 - 500 * i, f"2026-03-0{2 + i}T1{int(tag == 'b')}:00")
    report = load_records(graph_db.driver, k.records, database=graph_db.database)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    return graph_db


def detect(db: Neo4jTarget, tmp_path: Path, run_id: str, **kwargs: Any) -> runs.RunRecord:
    keep = kwargs.pop("keep_previous", False)
    return runs.run(
        Neo4jSource(db.driver, db.database, timeout_s=60.0),
        {"circular_flow": circular_flow.Params()},
        WINDOW,
        kwargs.pop("cat", None) or catalog.load(),
        run_id=run_id,
        engine="neo4j",
        runs_dir=tmp_path,
        profile="synth-eval",
        load=partial(runs.store, db.driver, db.database, keep_previous=keep),
        **kwargs,
    )


def test_two_runs_leave_the_second_run_and_its_alerts(db: Neo4jTarget, tmp_path: Path) -> None:
    detect(db, tmp_path, "run-20261102T090000-0001")
    second = detect(db, tmp_path, "run-20261102T090100-0002")
    [run] = read(db, "MATCH (r:DetectionRun) RETURN properties(r) AS r")
    props = run["r"]
    assert props["run_id"] == second.run_id and props["status"] == "ok"
    assert props["profile"] == "synth-eval"
    assert props["params_sha256"] == runner.params_sha256({"circular_flow": circular_flow.Params()})
    assert (props["window_start"], props["window_end"]) == (
        "2026-01-01T00:00:00Z",
        "2026-07-01T00:00:00Z",
    )
    summary = json.loads(props["summary"])
    assert summary["alerts"] == 2 and summary["run_id"] == second.run_id
    assert json.loads(props["detectors"]) == [{"name": circular_flow.__name__, "version": "0.2.0"}]
    stored = read(
        db,
        "MATCH (r:DetectionRun)-[:PRODUCED]->(a:Alert) RETURN a.alert_id AS id, a.run_id AS run,"
        " a.evidence_node_ids AS nodes, a.evidence_edge_ids AS edges ORDER BY id",
    )
    by_id = {a.alert_id: a for a in second.alerts}
    assert [row["id"] for row in stored] == sorted(by_id)
    for row in stored:
        alert = by_id[row["id"]]
        assert row["run"] == second.run_id
        assert (row["nodes"], row["edges"]) == (alert.evidence.node_ids, alert.evidence.edge_ids)
    assert read(db, "MATCH (a:Alert) RETURN count(a) AS n") == [{"n": 2}]
    for name in ("I15", "I16", "I17"):
        assert read(db, statements()[name]) == [{"violations": 0}], name


def test_keep_previous_keeps_earlier_runs(db: Neo4jTarget, tmp_path: Path) -> None:
    detect(db, tmp_path, "run-20261102T090000-0001")
    detect(db, tmp_path, "run-20261102T090100-0002", keep_previous=True)
    found = read(
        db,
        "MATCH (r:DetectionRun) RETURN r.run_id AS id,"
        " COUNT { (r)-[:PRODUCED]->(:Alert) } AS produced ORDER BY id",
    )
    assert [row["produced"] for row in found] == [2, 2]
    assert read(db, "MATCH (a:Alert) RETURN count(a) AS n") == [{"n": 2}]


def test_a_failed_run_keeps_the_last_results(db: Neo4jTarget, tmp_path: Path) -> None:
    """A failed run has no results to replace the earlier ones with: it records its failed
    :DetectionRun and deletes nothing (orchestrator decision under OD-10 on L19)."""
    import dataclasses

    first = detect(db, tmp_path, "run-20261102T090000-0001")
    cat = catalog.load()
    bad = dict(cat["circular_flow"].wording, headline_synthetic="Synthetic scenario: layering")
    broken = {**cat, "circular_flow": dataclasses.replace(cat["circular_flow"], wording=bad)}
    with pytest.raises(runs.RunError, match="the headline matches"):
        detect(db, tmp_path, "run-20261102T090100-0002", cat=broken)
    found = read(db, "MATCH (r:DetectionRun) RETURN properties(r) AS r ORDER BY r.run_id")
    assert [(r["r"]["status"], r["r"]["alert_count"]) for r in found] == [("ok", 2), ("failed", 0)]
    failed = found[1]["r"]
    assert "params_sha256" not in failed and json.loads(failed["summary"])["alerts"] == 0
    stored = read(
        db,
        "MATCH (r:DetectionRun)-[:PRODUCED]->(a:Alert) RETURN r.run_id AS run, a.alert_id AS id"
        " ORDER BY id",
    )
    assert stored == [
        {"run": first.run_id, "id": a} for a in sorted(x.alert_id for x in first.alerts)
    ]
    for name in ("I15", "I16", "I17"):
        assert read(db, statements()[name]) == [{"violations": 0}], name


def test_verify_finds_the_evidence_and_reports_what_is_missing(
    db: Neo4jTarget, tmp_path: Path
) -> None:
    record = detect(db, tmp_path, "run-20261102T090000-0001")
    ids = runs.run_alert_ids(db.driver, db.database, record.run_id)
    assert ids == sorted(a.alert_id for a in record.alerts)
    assert all(check.ok for check in runs.verify(db.driver, db.database, ids))
    gone = record.alerts[0].evidence.edge_ids[0]
    db.driver.execute_query(
        "MATCH ()-[p:PAID {id: $id}]->() DELETE p", {"id": gone}, database_=db.database
    )
    checks = {c.alert_id: c for c in runs.verify(db.driver, db.database, ids)}
    broken = checks[record.alerts[0].alert_id]
    assert (broken.ok, broken.missing_edges, broken.missing_nodes) == (False, 1, 0)
    with pytest.raises(runs.RunError, match="not in the graph"):
        list(runs.verify(db.driver, db.database, ["alr-0123456789abcdef0123"]))
