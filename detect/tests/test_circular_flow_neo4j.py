"""Integration: the circular-flow detector and the detection runner on Neo4j (PHASE-1.md M1.9b).

The handcrafted fixture is loaded with the C2 loader and must give exactly the cycles in
expected.json; alerts validate against C4, keep their ids across runs and reproduce from their
evidence query; case F (a real holder, built in conftest.py) gives a structural_pattern alert;
and on demo-mini the labelled round_trip scenario's payments appear together in one alert.
"""

import csv
import io
from pathlib import Path
from typing import Any

import pytest
from neo4j import RoutingControl

from neonradar_contracts.alert import Alert
from neonradar_detect import runner
from neonradar_detect.detectors import circular_flow
from neonradar_graph.loader import load_files, load_records

from .conftest import (
    CASE_A_ORIGIN,
    CIRCULAR_FLOW,
    EXPECTED,
    REAL_HOLDER,
    REPO_ROOT,
    Neo4jTarget,
    case_f_records,
    fixture_records,
)

pytestmark = pytest.mark.integration

DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
CASE_A = EXPECTED["cases"]["A"]["edge_ids"]


def load(db: Neo4jTarget, records: list[dict[str, Any]]) -> Neo4jTarget:
    report = load_records(db.driver, records, database=db.database)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    return db


def read(db: Neo4jTarget, cypher: str, **params: Any) -> list[dict[str, Any]]:
    records, _, _ = db.driver.execute_query(
        cypher, params, database_=db.database, routing_=RoutingControl.READ
    )
    return [record.data() for record in records]


def detect_run(db: Neo4jTarget, runs_dir: Path, **kwargs: Any) -> runner.RunReport:
    return runner.run(db.driver, db.database, typology="circular_flow", runs_dir=runs_dir, **kwargs)


@pytest.fixture
def cases(graph_db: Neo4jTarget) -> Neo4jTarget:
    return load(graph_db, fixture_records())


def test_the_detector_finds_exactly_the_expected_cycles(cases: Neo4jTarget) -> None:
    findings = circular_flow.detect(cases.driver, cases.database, CIRCULAR_FLOW)
    found = sorted([edge.id for edge in finding.edges] for finding in findings)
    assert found == sorted(EXPECTED["found"])


def test_run_alerts_validate_keep_their_ids_and_load_idempotently(
    cases: Neo4jTarget, tmp_path: Path
) -> None:
    first = detect_run(cases, tmp_path)
    second = detect_run(cases, tmp_path)
    assert first.run_id != second.run_id
    assert [a.alert_id for a in first.alerts] == [a.alert_id for a in second.alerts]
    assert {a.wording_class for a in second.alerts} == {"synthetic_scenario"}  # cases A and B
    lines = (second.directory / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert [Alert.model_validate_json(line) for line in lines] == second.alerts
    stored = read(
        cases,
        "MATCH (a:Alert) OPTIONAL MATCH (a)-[f:FLAGS]->(e:Entity)"
        " RETURN a.alert_id AS id, a.run_id AS run_id, a.payload AS payload,"
        " collect([e.id, f.role]) AS flags ORDER BY id",
    )
    by_id = {alert.alert_id: alert for alert in second.alerts}
    assert sorted(by_id) == [row["id"] for row in stored]
    for row in stored:
        alert = by_id[row["id"]]
        assert row["run_id"] == second.run_id
        assert Alert.model_validate_json(row["payload"]) == alert
        assert sorted(row["flags"]) == sorted([s.entity_id, s.role] for s in alert.subjects)
    runs = read(
        cases,
        "MATCH (r:DetectionRun) RETURN r.run_id AS run_id, r.status AS status,"
        " r.alert_count AS alerts, COUNT { (r)-[:PRODUCED]->(:Alert) } AS produced ORDER BY run_id",
    )
    assert [(r["status"], r["alerts"], r["produced"]) for r in runs] == [("ok", 2, 2)] * 2


def test_an_alert_reproduces_from_its_evidence_query(cases: Neo4jTarget, tmp_path: Path) -> None:
    report = detect_run(cases, tmp_path)
    for alert in report.alerts:
        query = alert.evidence.query
        rows = read(cases, query.cypher, **query.parameters)
        assert alert.evidence.edge_ids in [[hop["id"] for hop in row["hops"]] for row in rows]


def test_a_rerun_removes_flags_to_former_subjects(cases: Neo4jTarget, tmp_path: Path) -> None:
    alert = detect_run(cases, tmp_path).alerts[0]
    cases.driver.execute_query(
        "MATCH (a:Alert {alert_id: $id}), (e:Entity {id: 'syn-co-cf03'})"
        " MERGE (a)-[:FLAGS {role: 'origin_holder'}]->(e)",
        {"id": alert.alert_id},
        database_=cases.database,
    )
    detect_run(cases, tmp_path)
    flagged = read(
        cases, "MATCH (:Alert {alert_id: $id})-[:FLAGS]->(e) RETURN e.id AS id", id=alert.alert_id
    )
    assert sorted(row["id"] for row in flagged) == sorted(s.entity_id for s in alert.subjects)


def test_case_f_real_holder_gives_a_structural_pattern(
    graph_db: Neo4jTarget, tmp_path: Path
) -> None:
    db = load(graph_db, case_f_records())
    report = detect_run(db, tmp_path)
    [alert] = [a for a in report.alerts if a.evidence.edge_ids == CASE_A]
    assert alert.wording_class == "structural_pattern"
    assert alert.data_flags.involves_real_entities is True
    assert alert.data_flags.synthetic_activity is True
    assert alert.headline == CIRCULAR_FLOW.wording.headline_structural.format(  # type: ignore[union-attr]
        cycle_length=4, duration_days=6
    )
    assert (REAL_HOLDER["id"], "origin_holder") in [(s.entity_id, s.role) for s in alert.subjects]
    assert alert.subjects[0].entity_id == CASE_A_ORIGIN
    i6 = read(
        db,
        "MATCH (a:Alert {wording_class: 'synthetic_scenario'})-[:FLAGS]->(n)"
        " WHERE NOT coalesce(n.synthetic = true, false) RETURN n.id AS id",
    )
    assert i6 == []


def labelled(name: str) -> list[dict[str, str]]:
    text = (DEMO_MINI / "labels" / name).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def test_the_round_trip_scenario_of_demo_mini_is_one_alert(
    graph_db: Neo4jTarget, tmp_path: Path
) -> None:
    report = load_files(graph_db.driver, [DEMO_MINI], database=graph_db.database)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    scenarios = {
        row["scenario_id"]
        for row in labelled("scenarios.csv")
        if row["typology"] == "circular_flow" and row["variant"] == "round_trip"
    }
    assert scenarios, "demo-mini labels no round_trip scenario"
    alerts = detect_run(graph_db, tmp_path).alerts
    for scenario in sorted(scenarios):
        payments = {
            row["tx_id"] for row in labelled("transactions.csv") if row["scenario_id"] == scenario
        }
        assert payments
        matching = [a for a in alerts if payments <= set(a.evidence.edge_ids)]
        assert matching, f"{scenario}: no alert holds all of {sorted(payments)}"
        assert {a.wording_class for a in matching} == {"synthetic_scenario"}
