"""Detector tests on Neo4j (PHASE-3.md 7.1.5): records loaded into a test database, a Neo4jSource.

The adapter of the code book's reference `neo4j_mode.py` (M3.2 deliverable 7, reconciliation
T1). The behaviour kept: one database per test session, started like the project's integration
tests (the shared `neo4j` fixture of graph/tests/support/nr_test_neo4j.py: `neo4j:5.26.32-
community` with APOC and the pinned GDS jar, OD-13); for each call, wipe the database, load the
records with the project's own loader in strict mode, and return a `Neo4jSource` on that
database with a 60-second timeout. What changed: no second container and no plugin download
(the shared fixture), and the loader is called directly (`neonradar_graph.loader.load_records`,
the code `neonradar graph load --strict` runs) instead of through a temporary file and the
command line. Records that are not all synthetic cannot be loaded into the default instance (C2
L17), so a test that builds a non-synthetic look-alike is skipped in this mode: R-REAL is decided
after the Source, and the in-memory run of the same test covers it. Added for M3.5c: when the
session ends, `assert_no_projections` checks that `gds.graph.list()` is empty on the test database
(the M3.5c acceptance check: the ring step drops its projection in `finally`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from neo4j import RoutingControl
from nr_test_neo4j import Neo4jTarget

from neonradar_detect.neo4jsource import Neo4jSource
from neonradar_detect.source import Source
from neonradar_graph.loader import load_records, wipe
from neonradar_graph.migrate import migrate

Record = dict[str, Any]
TIMEOUT_S = 60.0
GDS_GRAPHS = "CALL gds.graph.list() YIELD graphName RETURN graphName ORDER BY graphName"


def assert_no_projections(target: Neo4jTarget) -> None:
    """No GDS projection is left behind on the test database (M3.5c acceptance)."""
    records, _, _ = target.driver.execute_query(
        GDS_GRAPHS, database_=target.database, routing_=RoutingControl.READ
    )
    names = [record["graphName"] for record in records]
    assert names == [], f"GDS projections left behind: {names}"


def load(target: Neo4jTarget, records: list[Record]) -> None:
    """Wipe the test database and load `records` strictly; any skipped record fails the test."""
    wipe(target.driver, target.database)
    migrate(target.driver, target.database)  # a no-op unless another test dropped the schema
    report = load_records(target.driver, records, database=target.database, strict=True)
    problems = (report.dangling, report.rejected, report.skipped)
    assert problems == ([], [], []), f"the loader did not take every record: {problems}"


def factory(target: Neo4jTarget) -> Callable[[list[Record]], Source]:
    def make(records: list[Record]) -> Source:
        if not all(r["datasets"] == ["nr_synthetic"] for r in records):
            pytest.skip("non-synthetic look-alike records: covered by the in-memory run (L17)")
        load(target, records)
        return Neo4jSource(target.driver, target.database, timeout_s=TIMEOUT_S)

    return make
