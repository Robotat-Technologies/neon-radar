"""Integration smoke test on the shared Neo4j fixture: the server, APOC and the pinned GDS answer,
and Neo4j reads the C2 `PAID.ts` format as a UTC DATETIME.

It also gives CI's integration job a real test (`pytest -m integration` exits with code 5 when
nothing matches).
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from neonradar_contracts.records import iter_records
from neonradar_graph.mapping import to_relationship_rows
from neonradar_graph.smoke import run_smoke

from .conftest import Neo4jTarget, pinned_gds

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"


def test_neo4j_answers_with_apoc_and_gds(neo4j: Neo4jTarget) -> None:
    one, _, _ = neo4j.driver.execute_query("RETURN 1 AS one", database_=neo4j.database)
    report = run_smoke(neo4j.driver, neo4j.database)
    assert one[0]["one"] == 1
    assert report.ok, report.lines()
    assert report.neo4j is not None and report.neo4j.startswith("5.26.")
    assert report.neo4j.endswith(" community")
    assert report.apoc is not None and report.apoc.startswith("5.26.")
    assert report.gds == pinned_gds()[0]


def test_paid_ts_is_read_as_a_utc_datetime(neo4j: Neo4jTarget) -> None:
    (paid,) = [
        row for row in to_relationship_rows(iter_records(FIXTURE)).rows if row.type == "PAID"
    ]
    records, _, _ = neo4j.driver.execute_query(
        "WITH datetime($ts) AS ts RETURN ts.timezone AS zone, ts.epochSeconds AS seconds",
        ts=paid.ts,
        database_=neo4j.database,
    )
    assert records[0]["zone"] == "Z"
    assert records[0]["seconds"] == int(datetime(2026, 3, 14, 10, 22, 5, tzinfo=UTC).timestamp())
