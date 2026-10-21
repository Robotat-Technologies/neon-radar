"""Shared helpers for the detect tests: the circular-flow fixture with its known right answer,
case F (built here, never committed: fixtures stay synthetic), and the query row the detector
receives for a cycle, built from the C1 records the way the C2 loader maps them.

The integration tests use the shared Neo4j fixtures (`neo4j`, one per test session, and
`graph_db`, migrated and wiped) of graph/tests/support/nr_test_neo4j.py, which the root
conftest.py registers once for every suite; tests import `Neo4jTarget` from that module."""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neonradar_contracts.datasets import load_registry
from neonradar_detect.catalog import TypologyFile, load_typology

TESTS = Path(__file__).resolve().parent
REPO_ROOT = TESTS.parents[1]
FIXTURE_DIR = TESTS / "fixtures" / "circular_flow"
CASES_FILE = FIXTURE_DIR / "cases.ftm.jsonl"
EXPECTED: dict[str, Any] = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))
CIRCULAR_FLOW: TypologyFile = load_typology(
    REPO_ROOT / "detect" / "typologies" / "circular_flow.yaml"
)


# Case F (PHASE-1.md M1.9b): case A's cycle with a non-synthetic origin holder. The id and name
# are the spec's; "Test Holder Ltd" had no exact match on the Companies House name search
# (company-name-availability?q=Test+Holder+Ltd, 21 October 2026).
REAL_HOLDER = {
    "id": "gbch-co-T0000001",
    "schema": "Company",
    "datasets": ["gb_companies_house"],
    "properties": {"name": ["Test Holder Ltd"], "jurisdiction": ["gb"]},
}
CASE_A_ORIGIN = "syn-acct-cfa1"


def fixture_records() -> list[dict[str, Any]]:
    lines = CASES_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def case_f_records() -> list[dict[str, Any]]:
    """The fixture with case A's origin account held by the real-looking company instead."""
    records = copy.deepcopy(fixture_records())
    holder = next(
        r
        for r in records
        if r["schema"] == "Ownership" and r["properties"]["asset"] == [CASE_A_ORIGIN]
    )
    previous = holder["properties"]["owner"][0]
    holder["properties"]["owner"] = [REAL_HOLDER["id"]]
    for record in records:
        props = record["properties"]
        if record["schema"] != "Payment":
            continue
        if props["payerAccount"] == [CASE_A_ORIGIN] and props["payer"] == [previous]:
            props["payer"] = [REAL_HOLDER["id"]]
        if props["beneficiaryAccount"] == [CASE_A_ORIGIN] and props["beneficiary"] == [previous]:
            props["beneficiary"] = [REAL_HOLDER["id"]]
    return [*records, copy.deepcopy(REAL_HOLDER)]


def _synthetic(record: dict[str, Any]) -> bool:
    dataset = load_registry().get(record["datasets"][0])
    return dataset is not None and dataset.synthetic


def _caption(record: dict[str, Any]) -> str:
    props = record["properties"]
    return str((props.get("name") or props.get("accountNumber"))[0])


def _node(record: dict[str, Any]) -> dict[str, Any]:
    node = {
        "id": record["id"],
        "caption": _caption(record),
        "synthetic": _synthetic(record),
        "datasets": list(record["datasets"]),
    }
    if record["schema"] == "BankAccount":
        node["account_number"] = record["properties"]["accountNumber"][0]
    return node


def paid_ts(record: dict[str, Any]) -> datetime:
    """`PAID.ts` as the loader writes it: the C1 Payment date in UTC."""
    return datetime.fromisoformat(record["properties"]["date"][0]).replace(tzinfo=UTC)


def query_row(records: list[dict[str, Any]], edge_ids: list[str]) -> dict[str, Any]:
    """The row queries/circular_flow.cypher returns for the cycle `edge_ids` (in hop order)."""
    by_id = {record["id"]: record for record in records}
    hops = []
    for edge_id in edge_ids:
        payment = by_id[edge_id]
        props = payment["properties"]
        hops.append(
            {
                "id": edge_id,
                "amount": float(props["amount"][0]),
                "currency": props["currency"][0],
                "ts": paid_ts(payment),
                "synthetic": _synthetic(payment),
                "datasets": list(payment["datasets"]),
                "source": props["payerAccount"][0],
                "target": props["beneficiaryAccount"][0],
            }
        )
    accounts = [hop["source"] for hop in hops]
    holders = [
        {
            "account": record["properties"]["asset"][0],
            **_node(by_id[record["properties"]["owner"][0]]),
        }
        for record in records
        if record["schema"] == "Ownership" and record["properties"]["asset"][0] in accounts
    ]
    return {
        "origin": accounts[0],
        "accounts": [_node(by_id[account]) for account in accounts],
        "hops": hops,
        "holders": holders,
    }
