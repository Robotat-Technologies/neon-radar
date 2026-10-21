"""scripts/demo_guard.py on Neo4j: it allows the wipe only when everything the wipe deletes is
synthetic demo data (PHASE-1.md M1.9e). Uses the shared Neo4j of the integration suites."""

from typing import LiteralString

import demo_guard
import pytest
from nr_test_neo4j import Neo4jTarget

# (case, statements that create the nodes, how many of them are not synthetic demo data)
CASES: list[tuple[str, list[LiteralString], int]] = [
    ("nothing but the schema migrations", [], 0),
    (
        "synthetic entities, a synthetic sanction, a synthetic alert and its run",
        [
            "CREATE (:Entity:LegalEntity:Company:Synthetic {id: 'tst-co-1', synthetic: true})",
            "CREATE (:Entity:Account:Synthetic {id: 'tst-acct-1', synthetic: true})",
            "CREATE (:Sanction:Synthetic {id: 'tst-sanction-1', synthetic: true})",
            "CREATE (:Alert {alert_id: 'tst-alert-1', involves_real_entities: false})",
            "CREATE (:DetectionRun {run_id: 'tst-run-1'})",
        ],
        0,
    ),
    ("an entity marked not synthetic", ["CREATE (:Entity {id: 'tst-co-2', synthetic: false})"], 1),
    ("an entity without the flag", ["CREATE (:Entity {id: 'tst-co-3'})"], 1),
    ("a string flag", ["CREATE (:Entity {id: 'tst-co-4', synthetic: 'true'})"], 1),
    ("a sanction not synthetic", ["CREATE (:Sanction {id: 'tst-s-2', synthetic: false})"], 1),
    ("a sanction without the flag", ["CREATE (:Sanction {id: 'tst-s-3'})"], 1),
    (
        "an alert that involves real entities",
        ["CREATE (:Alert {alert_id: 'tst-alert-2', involves_real_entities: true})"],
        1,
    ),
    ("an alert without the flag", ["CREATE (:Alert {alert_id: 'tst-alert-3'})"], 1),
    ("a node of another kind", ["CREATE (:OnbCompany {id: 'tst-onb-1'})"], 1),
    (
        "synthetic data next to two nodes of other kinds",
        [
            "CREATE (:Entity:Synthetic {id: 'tst-co-5', synthetic: true})",
            "CREATE (:OnbCompany {id: 'tst-onb-2'})",
            "CREATE (:OnbPerson {id: 'tst-onb-3'})",
        ],
        2,
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("statements", "real"), [(s, r) for _, s, r in CASES], ids=[c for c, _, _ in CASES]
)
def test_the_guard_refuses_whatever_is_not_synthetic_demo_data(
    graph_db: Neo4jTarget, statements: list[LiteralString], real: int
) -> None:
    for statement in statements:
        graph_db.driver.execute_query(statement, database_=graph_db.database)
    assert demo_guard.count_not_synthetic(graph_db.driver, graph_db.database) == real
    expected = demo_guard.REFUSED if real else 0
    assert demo_guard.check(graph_db.driver, graph_db.database) == expected
