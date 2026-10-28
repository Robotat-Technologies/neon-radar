"""Shared helpers for the detect tests: the circular-flow fixture with its known right answer,
case F (built here, never committed: fixtures stay synthetic), and the Phase 3 test modes
(PHASE-3.md 7.1.5, M3.2 deliverable 7).

The integration tests use the shared Neo4j fixtures (`neo4j`, one per test session, and
`graph_db`, migrated and wiped) of graph/tests/support/nr_test_neo4j.py, which the root
conftest.py registers once for every suite; tests import `Neo4jTarget` from that module.

Detector tests turn records into a `Source` with `kit.source_of`. `NR_DETECT_SOURCE=neo4j`
switches every one of them to the shared Neo4j: `neo4j_mode.factory` wipes it, loads the records
with the project's loader in strict mode and returns a `Neo4jSource` (no second container,
reconciliation T1)."""

import copy
import json
import os
import sys
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from neonradar_detect.catalog import TypologyFile, load_typology
from neonradar_detect.source import Source

# helpers (kit.py, neo4j_mode.py) sit next to the tests; pytest runs with --import-mode=importlib
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kit

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


def paid_ts(record: dict[str, Any]) -> datetime:
    """`PAID.ts` as the loader writes it: the C1 Payment date in UTC."""
    return datetime.fromisoformat(record["properties"]["date"][0]).replace(tzinfo=UTC)


@pytest.fixture(scope="session")
def neo4j_source_factory(neo4j: Any) -> Iterator[Callable[[list[dict[str, Any]]], Source]]:
    """Records to a Neo4jSource on the shared test database (PHASE-3.md 7.1.5)."""
    import neo4j_mode

    yield neo4j_mode.factory(neo4j)


if os.environ.get("NR_DETECT_SOURCE") == "neo4j":

    @pytest.fixture(scope="session", autouse=True)
    def _detector_tests_on_neo4j(
        neo4j_source_factory: Callable[[list[dict[str, Any]]], Source],
    ) -> Iterator[None]:
        """NR_DETECT_SOURCE=neo4j: every detector test runs on Neo4j (7.1.5)."""
        before = kit.SOURCE_FACTORY
        kit.SOURCE_FACTORY = neo4j_source_factory
        yield
        kit.SOURCE_FACTORY = before
