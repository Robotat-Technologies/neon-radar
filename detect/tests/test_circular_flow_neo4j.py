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


def shapes() -> tuple[list[dict[str, Any]], list[list[str]]]:
    """Records built here (synthetic, never committed) for the rules the fixture cases do not
    isolate, and the cycles the detector must report among them:

    - figure-eight through the origin, x1 -> y1 -> x1 -> z1 -> x1: two 2-hop cycles; the 4-hop
      walk visits x1 twice (simple-cycle rule);
    - inner loop, x2 -> y2 -> z2 -> y2 -> x2: x2 -> y2 -> x2 and y2 -> z2 -> y2; the 4-hop walk
      visits y2 twice;
    - EUR out, GBP back, c1 -> c2 -> c1: same-currency rule, not found;
    - two payments with the same timestamp, t1 -> t2 -> t1: strict time order, found zero times.
    The holders are the fixture's companies (names checked on Companies House, OD-12)."""
    holders = [r for r in fixture_records() if r["schema"] == "Company"]
    nr = {"v": "1.0", "synthetic": True, "synthetic_kind": "activity"}
    keys = ["x1", "y1", "z1", "x2", "y2", "z2", "c1", "c2", "t1", "t2"]
    owner = {key: holders[i % len(holders)]["id"] for i, key in enumerate(keys)}
    records: list[dict[str, Any]] = [*holders]
    for n, key in enumerate(keys, start=1):
        account = f"syn-acct-sh{key}"
        records.append(
            {
                "id": account,
                "schema": "BankAccount",
                "datasets": ["nr_synthetic"],
                "properties": {"accountNumber": [f"NRSYN92000000{n:02d}"]},
                "nr": {**nr, "account_kind": "customer"},
            }
        )
        records.append(
            {
                "id": f"syn-ownership-sh{key}",
                "schema": "Ownership",
                "datasets": ["nr_synthetic"],
                "properties": {"owner": [owner[key]], "asset": [account]},
                "nr": nr,
            }
        )
    payments = [  # id, from, to, amount, currency, date
        ("f1", "x1", "y1", "100000.00", "EUR", "2026-09-01T09:00:00"),
        ("f2", "y1", "x1", "98000.00", "EUR", "2026-09-02T09:00:00"),
        ("f3", "x1", "z1", "97000.00", "EUR", "2026-09-03T09:00:00"),
        ("f4", "z1", "x1", "95000.00", "EUR", "2026-09-04T09:00:00"),
        ("i1", "x2", "y2", "100000.00", "EUR", "2026-09-01T09:00:00"),
        ("i2", "y2", "z2", "99000.00", "EUR", "2026-09-02T09:00:00"),
        ("i3", "z2", "y2", "98000.00", "EUR", "2026-09-03T09:00:00"),
        ("i4", "y2", "x2", "97000.00", "EUR", "2026-09-04T09:00:00"),
        ("c1", "c1", "c2", "50000.00", "EUR", "2026-09-01T09:00:00"),
        ("c2", "c2", "c1", "49000.00", "GBP", "2026-09-02T09:00:00"),
        ("t1", "t1", "t2", "40000.00", "EUR", "2026-09-01T09:00:00"),
        ("t2", "t2", "t1", "39500.00", "EUR", "2026-09-01T09:00:00"),
    ]
    for key, src, dst, amount, currency, date in payments:
        records.append(
            {
                "id": f"syn-payment-sh{key}",
                "schema": "Payment",
                "datasets": ["nr_synthetic"],
                "properties": {
                    "payer": [owner[src]],
                    "beneficiary": [owner[dst]],
                    "payerAccount": [f"syn-acct-sh{src}"],
                    "beneficiaryAccount": [f"syn-acct-sh{dst}"],
                    "amount": [amount],
                    "currency": [currency],
                    "date": [date],
                },
                "nr": {**nr, "channel": "wire"},
            }
        )
    expected = [["f1", "f2"], ["f3", "f4"], ["i1", "i4"], ["i2", "i3"]]
    return records, [[f"syn-payment-sh{key}" for key in cycle] for cycle in expected]


def test_only_simple_cycles_in_one_currency_with_strictly_later_payments(
    graph_db: Neo4jTarget,
) -> None:
    records, expected = shapes()
    db = load(graph_db, records)
    findings = circular_flow.detect(db.driver, db.database, CIRCULAR_FLOW)
    assert sorted([edge.id for edge in finding.edges] for finding in findings) == sorted(expected)
    # Without the simple-cycle rule these 4-hop walks would pass every other rule.
    walks = read(
        db,
        "MATCH p = (a:Account)-[t:PAID]->{4}(a)"
        " WHERE all(i IN range(0, 2) WHERE t[i].ts < t[i + 1].ts)"
        " RETURN [r IN t | r.id] AS ids ORDER BY ids",
    )
    assert [row["ids"] for row in walks] == [
        [f"syn-payment-sh{key}" for key in keys]
        for keys in (["f1", "f2", "f3", "f4"], ["i1", "i2", "i3", "i4"])
    ]


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


def test_a_rerun_keeps_one_flags_per_current_subject(cases: Neo4jTarget, tmp_path: Path) -> None:
    """A re-run removes FLAGS to former subjects and duplicate FLAGS to current ones."""
    alert = detect_run(cases, tmp_path).alerts[0]
    cases.driver.execute_query(
        "MATCH (a:Alert {alert_id: $id}), (e:Entity {id: 'syn-co-cf03'}),"
        " (s:Entity {id: $subject})"
        " CREATE (a)-[:FLAGS {role: 'origin_holder'}]->(e),"
        " (a)-[:FLAGS {role: 'origin'}]->(s)",
        {"id": alert.alert_id, "subject": alert.subjects[0].entity_id},
        database_=cases.database,
    )
    detect_run(cases, tmp_path)
    flagged = read(
        cases, "MATCH (:Alert {alert_id: $id})-[:FLAGS]->(e) RETURN e.id AS id", id=alert.alert_id
    )
    assert sorted(row["id"] for row in flagged) == sorted(s.entity_id for s in alert.subjects)


def test_a_run_id_used_again_keeps_only_what_it_finds(cases: Neo4jTarget, tmp_path: Path) -> None:
    run_id = "run-20261021T101500-0abc"
    first = detect_run(cases, tmp_path, run_id=run_id)
    assert len(first.alerts) == 2
    cases.driver.execute_query(
        "MATCH ()-[p:PAID {id: $id}]->() DELETE p",
        {"id": EXPECTED["cases"]["B"]["edge_ids"][0]},
        database_=cases.database,
    )
    again = detect_run(cases, tmp_path, run_id=run_id)
    assert [a.evidence.edge_ids for a in again.alerts] == [CASE_A]
    stored = read(
        cases,
        "MATCH (a:Alert) RETURN a.alert_id AS id,"
        " COUNT { (:DetectionRun {run_id: $run_id})-[:PRODUCED]->(a) } AS produced",
        run_id=run_id,
    )
    assert stored == [{"id": again.alerts[0].alert_id, "produced": 1}]


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
