"""Integration: the C2 graph invariants I1 to I5 hold after loading demo-mini (PHASE-1.md 5.2,
M1.9a), and I6 after a detection run on it (M1.9b). Each query returns at most 10 violating
ids. Since M2.11, I1 to I14 (`neonradar graph verify`) hold on the resolved load of the demo
profile's records (`demo_resolution`), so no `make load` is needed, and each catches its
violation."""

from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import iter_records
from neonradar_graph.client import REPO_ROOT
from neonradar_graph.loader import collect_files, load_files
from neonradar_graph.mapping import to_node_rows, to_relationship_rows
from neonradar_graph.verify import verify

from .conftest import DEMO_DIRS, Neo4jTarget

pytestmark = pytest.mark.integration

DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
INVARIANTS = {
    "I1": """
        MATCH (n:Entity)
        WHERE n.id IS NULL OR n.schema IS NULL OR n.caption IS NULL OR n.datasets IS NULL
           OR n.synthetic IS NULL
        RETURN elementId(n) AS bad LIMIT 10""",
    # The nodes the C2 flag table puts :Synthetic on, and every node that carries it; a
    # :SourceRecord (C2 1.1.0) has `synthetic` but no flag label.
    "I2": """
        MATCH (n) WHERE (n:Entity OR n:Sanction OR n:Synthetic)
          AND n:Synthetic <> coalesce(n.synthetic = true, false)
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
# I6 (guardrail G1): no synthetic_scenario alert flags a node that is not synthetic. A node
# without the property counts as real here, which is stricter than `synthetic = false`.
I6 = """
    MATCH (a:Alert {wording_class: 'synthetic_scenario'})-[:FLAGS]->(n)
    WHERE NOT coalesce(n.synthetic = true, false)
    RETURN elementId(n) AS bad LIMIT 10"""
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


def test_invariant_i6_holds_after_a_detection_run(demo_mini: Neo4jTarget, tmp_path: Path) -> None:
    from neonradar_detect.runner import run  # detection writes the alerts I6 is about

    report = run(demo_mini.driver, demo_mini.database, runs_dir=tmp_path)
    assert report.alerts, "the run found no alerts, so I6 would pass vacuously"
    assert query(demo_mini, I6) == []
    # The check catches a violation: a synthetic_scenario alert flagging a real node.
    demo_mini.driver.execute_query(
        "CREATE (:Alert {alert_id: 'alr-00000000000000000000', wording_class:"
        " 'synthetic_scenario'})-[:FLAGS {role: 'origin'}]->"
        "(:Entity {id: 'gbch-co-T0000002', synthetic: false})",
        database_=demo_mini.database,
    )
    assert len(query(demo_mini, I6)) == 1


# Each Phase 2 invariant must have something to check on the resolved demo load.
RESOLVED_SUBJECTS = """
RETURN COUNT { (:SourceRecord) } AS I7, COUNT { (e:Entity) WHERE e.cluster_size >= 2 } AS I8,
       COUNT { (:SourceRecord)-[:RESOLVED_TO]->() } AS I9,
       COUNT { ()-[:POSSIBLY_SAME_AS]->() } AS I10,
       COUNT { (e:Entity) WHERE e.cluster_size >= 2 AND size(e.topics) > 0 } AS I11,
       COUNT { ()-[:OWNS]->() } AS I12
"""
# One violation of each Phase 2 invariant (I7 to I14), written straight into the graph.
BREAK = {
    "I7": "CREATE (:SourceRecord {id: 'syn-p-0990', synthetic: true})",
    "I8": "CREATE (:Entity {id: 'syn-p-0991', referents: ['syn-p-0992'], synthetic: true})",
    "I9": "MATCH (e:Entity) WHERE e.cluster_size >= 2 WITH e ORDER BY e.id LIMIT 1"
    " CREATE (:SourceRecord {id: 'syn-p-0994', synthetic: false})-[:RESOLVED_TO]->(e)",
    "I10": "MATCH (e:LegalEntity) WITH e ORDER BY e.id LIMIT 1 CREATE (e)-[:POSSIBLY_SAME_AS]->(e)",
    "I11": "CREATE (:Entity:PEP {id: 'syn-p-0993', topics: [], referents: ['syn-p-0993']})",
    "I12": "MATCH (e:LegalEntity) WITH e ORDER BY e.id LIMIT 1 CREATE (e)-[:OWNS]->(e)",
    "I13": "MATCH (s:SourceRecord) WITH s ORDER BY s.id LIMIT 1"
    " CREATE (:Entity {id: s.id, referents: [s.id], synthetic: true})",
    "I14": "MATCH (c:Company) WITH c ORDER BY c.id LIMIT 2 WITH collect(c) AS cs"
    " WITH cs[0] AS a, cs[1] AS b"
    " CREATE (a)-[:CONTROLS {share_pct_min: 75.0, share_pct_max: 50.0}]->(b)",
}


def test_every_invariant_holds_on_the_resolved_demo_load_and_catches_its_violation(
    graph_db: Neo4jTarget, demo_resolution: Path
) -> None:
    report = load_files(
        graph_db.driver, DEMO_DIRS, database=graph_db.database, resolution=demo_resolution
    )
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    found = verify(graph_db.driver, graph_db.database)
    assert found == {f"I{n}": 0 for n in range(1, 15)}
    for name, phase_1 in INVARIANTS.items():  # Phase 1's queries agree
        assert query(graph_db, phase_1) == [], name
    (subjects,) = query(graph_db, RESOLVED_SUBJECTS)
    assert all(count > 0 for count in subjects.values()), subjects
    for name, statement in BREAK.items():
        graph_db.driver.execute_query(statement, database_=graph_db.database)
        assert verify(graph_db.driver, graph_db.database)[name] >= 1, name
