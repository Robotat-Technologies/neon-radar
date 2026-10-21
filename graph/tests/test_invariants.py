"""Integration: the C2 graph invariants I1 to I5 hold after loading demo-mini (PHASE-1.md 5.2,
M1.9a). I6 needs alerts and joins in M1.9b. Each query returns at most 10 violating ids."""

from collections import Counter
from typing import Any

import pytest

from neonradar_contracts.records import iter_records
from neonradar_graph.client import REPO_ROOT
from neonradar_graph.loader import collect_files, load_files
from neonradar_graph.mapping import to_node_rows, to_relationship_rows

from .conftest import Neo4jTarget

pytestmark = pytest.mark.integration

DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
INVARIANTS = {
    "I1": """
        MATCH (n:Entity)
        WHERE n.id IS NULL OR n.schema IS NULL OR n.caption IS NULL OR n.datasets IS NULL
           OR n.synthetic IS NULL
        RETURN elementId(n) AS bad LIMIT 10""",
    "I2": """
        MATCH (n) WHERE n:Synthetic <> coalesce(n.synthetic = true, false)
        RETURN elementId(n) AS bad LIMIT 10""",
    "I3": """
        MATCH (a)-[r:PAID]->(b)
        WHERE NOT (a:Account AND b:Account) OR NOT coalesce(r.amount > 0, false)
           OR NOT coalesce(r.currency =~ '[A-Z]{3}', false)
           OR NOT (r.ts IS :: ZONED DATETIME NOT NULL)
        RETURN elementId(r) AS bad LIMIT 10""",
    "I4": """
        MATCH (a:Account) WHERE NOT EXISTS { (:LegalEntity)-[:HOLDS_ACCOUNT]->(a) }
        RETURN elementId(a) AS bad LIMIT 10""",
    # A one-sided band (only min or only max) is valid; C1 compares the two when both exist.
    "I5": """
        MATCH ()-[r:OWNS]->()
        WITH r, r.share_pct_min AS low, r.share_pct_max AS high
        WHERE (low IS NOT NULL AND NOT (0 <= low AND low <= 100))
           OR (high IS NOT NULL AND NOT (0 <= high AND high <= 100))
           OR (low IS NOT NULL AND high IS NOT NULL AND low > high)
        RETURN elementId(r) AS bad LIMIT 10""",
}
# Each invariant must have something to check on demo-mini, or it would pass vacuously.
SUBJECTS = """
RETURN COUNT { (n:Entity) } AS I1, COUNT { (n:Synthetic) } AS I2, COUNT { ()-[:PAID]->() } AS I3,
       COUNT { (:Account) } AS I4,
       COUNT { ()-[r:OWNS]->() WHERE r.share_pct_min IS NOT NULL } AS I5
"""
# The review query of M1.9a: ownership chains from a person to a company.
CHAINS = "MATCH p = (:Person)-[:OWNS]->{1,3}(:Company) RETURN count(p) AS n"


def query(db: Neo4jTarget, cypher: str) -> list[dict[str, Any]]:
    records, _, _ = db.driver.execute_query(cypher, database_=db.database)
    return [record.data() for record in records]


@pytest.fixture
def demo_mini(graph_db: Neo4jTarget) -> Neo4jTarget:
    report = load_files(graph_db.driver, [DEMO_MINI], database=graph_db.database)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    return graph_db


@pytest.mark.parametrize("name", sorted(INVARIANTS))
def test_invariant_holds_on_demo_mini(demo_mini: Neo4jTarget, name: str) -> None:
    assert query(demo_mini, INVARIANTS[name]) == []


def test_demo_mini_gives_every_invariant_something_to_check(demo_mini: Neo4jTarget) -> None:
    (subjects,) = query(demo_mini, SUBJECTS)
    assert all(count > 0 for count in subjects.values()), subjects
    assert query(demo_mini, CHAINS)[0]["n"] > 0


def test_demo_mini_flags_match_its_records(demo_mini: Neo4jTarget) -> None:
    records = [data for path in collect_files([DEMO_MINI]) for data in iter_records(path)]
    nodes, relationships = to_node_rows(records).rows, to_relationship_rows(records).rows
    flags = Counter(flag for row in nodes for flag in row.flags)
    assert flags["Sanctioned"] > 0 and flags["PEP"] > 0  # demo-mini exercises the flags
    stored = query(
        demo_mini,
        "MATCH (n:Synthetic|Sanctioned|PEP|RCA) UNWIND labels(n) AS label"
        " WITH label WHERE label IN ['Synthetic', 'Sanctioned', 'PEP', 'RCA']"
        " RETURN label, count(*) AS n",
    )
    assert {row["label"]: row["n"] for row in stored} == dict(flags)
    paid = query(demo_mini, "MATCH ()-[r:PAID]->() RETURN count(r) AS n")[0]["n"]
    assert paid == sum(row.type == "PAID" for row in relationships)
