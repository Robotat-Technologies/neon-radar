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
from .test_verify_overlay import OVERLAY, OVERLAY_INVARIANTS

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
    from neonradar_detect.runs import detect_on_graph  # detection writes the alerts I6 is about

    report = detect_on_graph(demo_mini.driver, demo_mini.database, runs_dir=tmp_path)
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
# One violation of each kind, written straight into the graph.
BREAK = {
    "I7": "CREATE (:SourceRecord {id: 'syn-p-0990', synthetic: true})",
    "I8": "CREATE (:Entity {id: 'syn-p-0991', referents: ['syn-p-0992'], synthetic: true})",
    "I11": "CREATE (:Entity:PEP {id: 'syn-p-0993', topics: [], referents: ['syn-p-0993']})",
    "I13": "MATCH (s:SourceRecord) WITH s LIMIT 1"
    " CREATE (:Entity {id: s.id, referents: [s.id], synthetic: true})",
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


# C2 1.2.0 (PHASE-3.md 5.2, 5.4): invariants I15 to I17, the three statements of
# verify_overlay.cypher (parsed in test_verify_overlay.py), run directly (`graph verify` runs
# them from M3.4). Each statement returns one row with a `violations` count.


def overlay_violations(db: Neo4jTarget) -> dict[str, int]:
    out = {}
    for name in OVERLAY_INVARIANTS:
        (row,) = query(db, OVERLAY[name])
        out[name] = row["violations"]
    return out


def test_overlay_invariants_hold_on_demo_mini(demo_mini: Neo4jTarget, tmp_path: Path) -> None:
    # I17 is about the alerts a detection run writes
    from neonradar_detect.runs import detect_on_graph

    report = detect_on_graph(demo_mini.driver, demo_mini.database, runs_dir=tmp_path)
    assert report.alerts, "the run found no alerts, so I17 would pass vacuously"
    assert overlay_violations(demo_mini) == {"I15": 0, "I16": 0, "I17": 0}


# Non-synthetic look-alikes, built here at run time and never committed (PHASE-3.md 2.9),
# with the labels the loader gives them; the violating nodes and relationships are written
# with test-only Cypher, never through the loader (M3.1 deliverable 4).
REAL_ORG = (
    "(org:Entity:LegalEntity:Organization:Company {id: 'gbch-co-T0000002', schema: 'Company',"
    " caption: 'Test Holding Ltd', datasets: ['gb_companies_house'], synthetic: false})"
)
REAL_ORG_2 = (
    "(org2:Entity:LegalEntity:Organization:Company {id: 'gbch-co-T0000005', schema: 'Company',"
    " caption: 'Test Trading Ltd', datasets: ['gb_companies_house'], synthetic: false})"
)
REAL_PERSON = (
    "(person:Entity:LegalEntity:Person {id: 'gbch-p-T0000003', schema: 'Person',"
    " caption: 'Test Person', datasets: ['gb_companies_house'], synthetic: false})"
)
# A list entry whose source does not say what kind of entity it is: a person for I17.
REAL_LEGAL_ENTITY = (
    "(listed:Entity:LegalEntity {id: 'ofac-T0000001', schema: 'LegalEntity',"
    " caption: 'Test Listed Entity', datasets: ['us_ofac_sdn'], synthetic: false})"
)
SYN_COMPANY = (
    "(syn:Entity:LegalEntity:Organization:Company:Synthetic {id: 'syn-ov-co-0000000000000001',"
    " schema: 'Company', caption: 'Synthetic Example Ltd', datasets: ['nr_synthetic'],"
    " synthetic: true})"
)


def account(var: str, n: int) -> str:
    return (
        f"({var}:Entity:Account:Synthetic {{id: 'syn-ov-acct-{n:016x}', schema: 'BankAccount',"
        f" caption: 'NRSYN{n:010d}', datasets: ['nr_synthetic'], synthetic: true}})"
    )


KINDS = {"HOLDS_ACCOUNT": "own", "LINKED_TO": "link"}


def rel(type_: str, n: int) -> str:
    rid = f"syn-ov-{KINDS[type_]}-{n:016x}"
    return f"[:{type_} {{id: '{rid}', datasets: ['nr_synthetic'], synthetic: true}}]"


def holds(holder: str, var: str, n: int) -> str:
    return f"CREATE ({holder})-{rel('HOLDS_ACCOUNT', n)}->{account(var, n)}"


def paid(source: str, target: str, n: int = 1) -> str:
    return (
        f"CREATE ({source})-[:PAID {{id: 'syn-ov-pay-{n:016x}', amount: 950.0, currency: 'GBP',"
        f" ts: datetime('2026-03-02T10:00:00Z'), channel: 'wire', datasets: ['nr_synthetic'],"
        f" synthetic: true}}]->({target})"
    )


def alert(real: bool, nodes: list[str], edges: list[str], flags: str | None = None) -> str:
    created = (
        "CREATE (alert:Alert {alert_id: 'alr-00000000000000000001', typology: 'test_shape',"
        f" wording_class: '{'structural_pattern' if real else 'synthetic_scenario'}',"
        f" involves_real_entities: {str(real).lower()}, evidence_node_ids: {nodes!r},"
        f" evidence_edge_ids: {edges!r}}})"
    )
    return created + (f" CREATE (alert)-[:FLAGS {{role: 'subject'}}]->({flags})" if flags else "")


PAY_EDGE = "syn-ov-pay-0000000000000001"
# Each case: the clauses of one test-only Cypher query (CREATE only, so variables carry from
# one clause to the next), and the violation count of each invariant after it.
OVERLAY_CASES = {
    # The bridge rule allows exactly this: a real organisation holds a synthetic account, which
    # pays and is paid by synthetic accounts.
    "bridge_holding_and_payment_allowed": (
        [f"CREATE {REAL_ORG}, {SYN_COMPANY}", holds("org", "a1", 1), holds("syn", "a2", 2),
         paid("a1", "a2")],
        {"I15": 0, "I16": 0, "I17": 0},
    ),
    "I15_linked_to_from_synthetic_to_real": (
        [f"CREATE {SYN_COMPANY}-{rel('LINKED_TO', 9)}->{REAL_ORG}"],
        {"I15": 1, "I16": 0, "I17": 0},
    ),
    "I15_real_person_holds_a_synthetic_account": (
        [f"CREATE {REAL_PERSON}", holds("person", "a1", 1)],
        {"I15": 1, "I16": 0, "I17": 0},
    ),
    "I16_payment_between_two_real_holders": (
        [f"CREATE {REAL_ORG}, {REAL_ORG_2}", holds("org", "a1", 1), holds("org2", "a2", 2),
         paid("a1", "a2")],
        {"I15": 0, "I16": 1, "I17": 0},
    ),
    "I17_alert_flags_a_real_person": (
        [f"CREATE {REAL_PERSON} " + alert(True, [], [], flags="person")],
        {"I15": 0, "I16": 0, "I17": 1},
    ),
    # An alert written under 1.1.0 has no evidence lists: I17 still reads its subjects.
    "I17_alert_without_evidence_lists_flags_a_real_person": (
        [f"CREATE {REAL_PERSON} CREATE (old:Alert {{alert_id: 'alr-00000000000000000003',"
         " involves_real_entities: true})-[:FLAGS {role: 'subject'}]->(person)"],
        {"I15": 0, "I16": 0, "I17": 1},
    ),
    "I17_alert_without_evidence_lists_on_a_real_organisation_allowed": (
        [f"CREATE {REAL_ORG} CREATE (old:Alert {{alert_id: 'alr-00000000000000000004',"
         " involves_real_entities: true})-[:FLAGS {role: 'subject'}]->(org)"],
        {"I15": 0, "I16": 0, "I17": 0},
    ),
    "I17_evidence_names_a_legal_entity_of_unstated_kind": (
        [f"CREATE {REAL_ORG}, {REAL_LEGAL_ENTITY} "
         + alert(True, ["gbch-co-T0000002", "ofac-T0000001"], [], flags="org")],
        {"I15": 0, "I16": 0, "I17": 1},
    ),
    "I17_real_alert_with_a_payment_in_its_evidence": (
        [f"CREATE {REAL_ORG}, {SYN_COMPANY}", holds("org", "a1", 1), holds("syn", "a2", 2),
         paid("a1", "a2"),
         alert(True, ["gbch-co-T0000002"], [PAY_EDGE], flags="org")],
        {"I15": 0, "I16": 0, "I17": 1},
    ),
    # What R-REAL leaves: a registry pattern about a real organisation whose evidence names
    # only organisations, and a payment pattern among synthetic entities only.
    "I17_registry_alert_on_a_real_organisation_allowed": (
        [f"CREATE {REAL_ORG}, {REAL_ORG_2}, {SYN_COMPANY}", holds("syn", "a2", 2),
         holds("syn", "a3", 3), paid("a2", "a3"),
         alert(True, ["gbch-co-T0000002", "gbch-co-T0000005"], [], flags="org"),
         "CREATE (b:Alert {alert_id: 'alr-00000000000000000002', involves_real_entities: false,"
         f" evidence_node_ids: ['syn-ov-co-0000000000000001'], evidence_edge_ids: ['{PAY_EDGE}']}})"
         "-[:FLAGS {role: 'subject'}]->(syn)"],
        {"I15": 0, "I16": 0, "I17": 0},
    ),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(OVERLAY_CASES))
def test_overlay_invariants_on_test_built_graphs(graph_db: Neo4jTarget, case: str) -> None:
    """Each case in a freshly wiped database: I15 to I17 fail on their violations and hold on
    what the bridge rule and R-REAL allow."""
    clauses, expected = OVERLAY_CASES[case]
    graph_db.driver.execute_query("\n".join(clauses), database_=graph_db.database)
    (built,) = query(graph_db, "MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS n")
    assert built["n"] == 0, "every node the case names was created with its labels"
    assert overlay_violations(graph_db) == expected
