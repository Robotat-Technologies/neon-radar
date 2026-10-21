"""Assignment 1 against a real Neo4j (the shared integration database, tests/conftest.py): the
documented load, the reference loader, the first queries (read-only, with a timeout), reset."""

import os
import re
from typing import Any

import pytest
from neo4j.exceptions import Neo4jError

from neonradar_graph.client import REPO_ROOT
from neonradar_graph.onboarding import (
    QUERIES_PATH,
    Counts,
    QueryResult,
    check_queries,
    load,
    parse_first_queries,
    read_rows,
    reset,
    run_read_only,
)

from .conftest import Neo4jTarget

ASSIGNMENT = REPO_ROOT / "docs" / "team" / "assignment-1.md"
SOURCE = "LOAD CSV WITH HEADERS FROM 'file:///companies-20.csv' AS row"
EXPECTED = {
    "OnbCompany": 20,
    "OnbPerson": 15,
    "OnbAddress": 16,
    "DIRECTS": 20,
    "REGISTERED_AT": 20,
    "PARENT_OF": 2,
}
NODES = """
MATCH (n:OnbCompany|OnbPerson|OnbAddress)
RETURN labels(n) AS labels, properties(n) AS props ORDER BY coalesce(n.id, n.full)
"""
RELATIONSHIPS = """
MATCH (a)-[r:DIRECTS|REGISTERED_AT|PARENT_OF]->(b)
RETURN type(r) AS type, coalesce(a.id, a.full) AS start, coalesce(b.id, b.full) AS end
ORDER BY type, start, end
"""

pytestmark = pytest.mark.integration


def counts(db: Neo4jTarget) -> dict[str, int]:
    nodes, _, _ = db.driver.execute_query(
        "MATCH (n:OnbCompany|OnbPerson|OnbAddress) RETURN labels(n)[0] AS key, count(*) AS n",
        database_=db.database,
    )
    rels, _, _ = db.driver.execute_query(
        "MATCH ()-[r:DIRECTS|REGISTERED_AT|PARENT_OF]->() RETURN type(r) AS key, count(*) AS n",
        database_=db.database,
    )
    return {record["key"]: record["n"] for record in [*nodes, *rels]}


def graph(db: Neo4jTarget) -> list[list[dict[str, Any]]]:
    """Every Onb* node with its properties, and every relationship by type and endpoints."""
    return [
        [record.data() for record in db.driver.execute_query(q, database_=db.database)[0]]
        for q in (NODES, RELATIONSHIPS)
    ]


def documented_load() -> list[str]:
    """The reference load printed in docs/team/assignment-1.md.

    The Testcontainers database has the CSV in its /import folder (conftest.py), so the
    statements run as printed. A database from NR_TEST_NEO4J_URI may not have it, so there they
    read `$rows` instead: `read_rows` gives the same strings and turns empty fields into None,
    as LOAD CSV turns them into null.
    """
    found = re.search(r"```cypher\n(// Reference load.*?)```", ASSIGNMENT.read_text(), re.S)
    assert found, "assignment-1.md has no cypher block starting '// Reference load'"
    statements = [part.strip() for part in found.group(1).split(";") if part.strip()]
    assert len(statements) == 2 and all(SOURCE in statement for statement in statements)
    if os.environ.get("NR_TEST_NEO4J_URI"):
        return [statement.replace(SOURCE, "UNWIND $rows AS row") for statement in statements]
    return statements


def test_the_documented_load_and_the_reference_loader_build_the_same_graph(
    empty_neo4j: Neo4jTarget,
) -> None:
    db = empty_neo4j
    assert load(db.driver, read_rows(), db.database) == Counts(20, 15, 16)
    assert counts(db) == EXPECTED
    loaded = graph(db)
    db.driver.execute_query("MATCH (n) DETACH DELETE n", database_=db.database)

    for statement in documented_load():
        db.driver.execute_query(statement, rows=read_rows(), database_=db.database)
    assert counts(db) == EXPECTED
    assert graph(db) == loaded
    assert loaded[0][0]["props"]["synthetic"] is True

    load(db.driver, read_rows(), db.database)  # on top of the documented load: no change
    assert graph(db) == loaded


def test_the_example_query_finds_the_companies_at_the_shared_address(
    empty_neo4j: Neo4jTarget,
) -> None:
    db = empty_neo4j
    load(db.driver, read_rows(), db.database)
    entries = parse_first_queries(QUERIES_PATH.read_text(encoding="utf-8"))
    records, _, _ = db.driver.execute_query(entries[0].queries[0], database_=db.database)
    assert [record["company_id"] for record in records] == [
        "onb-co-06",
        "onb-co-09",
        "onb-co-12",
        "onb-co-16",
    ]
    results = check_queries(db.driver, entries, db.database)
    assert results[0] == QueryResult("@example", rows=4)
    assert [result for result in results if result.error] == []  # every first query runs


def test_first_queries_cannot_write_and_time_out(empty_neo4j: Neo4jTarget) -> None:
    db = empty_neo4j
    with pytest.raises(Neo4jError, match="read access mode"):
        run_read_only(db.driver, "CREATE (:OnbProbe) RETURN 1", db.database)
    slow = "UNWIND range(1, 300000000) AS x WITH x WHERE x % 7 = 3 RETURN count(*)"
    with pytest.raises(Neo4jError) as timed_out:
        run_read_only(db.driver, slow, db.database, timeout_s=0.5)
    assert "TransactionTimedOut" in str(timed_out.value.code)
    probes, _, _ = db.driver.execute_query(
        "MATCH (n:OnbProbe) RETURN count(n) AS n", database_=db.database
    )
    assert probes[0]["n"] == 0


def test_reset_removes_only_the_onboarding_nodes(empty_neo4j: Neo4jTarget) -> None:
    db = empty_neo4j
    load(db.driver, read_rows(), db.database)
    db.driver.execute_query(
        "CREATE (:Entity {id: 'syn-co-9999', synthetic: true})", database_=db.database
    )
    assert reset(db.driver, db.database) == 51
    remaining, _, _ = db.driver.execute_query(
        "MATCH (n) RETURN labels(n) AS labels", database_=db.database
    )
    assert [record["labels"] for record in remaining] == [["Entity"]]
