"""Assignment 1 end to end against a real Neo4j: the documented LOAD CSV, the reference loader,
the first queries (read-only, with a timeout) and the reset."""

import os
import re
from collections.abc import Iterator
from typing import Any

import pytest
from neo4j import Driver
from neo4j.exceptions import Neo4jError
from testcontainers.community.neo4j import Neo4jContainer

from neonradar_graph.client import REPO_ROOT
from neonradar_graph.onboarding import (
    CSV_PATH,
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

IMAGE = os.environ.get("NR_NEO4J_IMAGE", "neo4j:5.26.32-community")
ASSIGNMENT = REPO_ROOT / "docs" / "team" / "assignment-1.md"
MEMORY = {
    "NEO4J_server_memory_heap_initial__size": "512m",
    "NEO4J_server_memory_heap_max__size": "512m",
    "NEO4J_server_memory_pagecache_size": "256m",
}
EXPECTED = {
    "OnbCompany": 20,
    "OnbPerson": 15,
    "OnbAddress": 16,
    "DIRECTS": 20,
    "REGISTERED_AT": 20,
    "PARENT_OF": 2,
}
SNAPSHOT = """
MATCH (n:OnbCompany|OnbPerson|OnbAddress)
RETURN labels(n) AS labels, properties(n) AS props ORDER BY coalesce(n.id, n.full)
"""

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def neo4j() -> Iterator[Driver]:
    # The CSV's folder is mounted as /import, as compose.yaml mounts data/import/.
    container = (
        Neo4jContainer(IMAGE, mem_limit="1536m")
        .with_envs(**MEMORY)
        .with_volume_mapping(str(CSV_PATH.parent), "/import", "ro")
    )
    with container, container.get_driver() as driver:
        yield driver


@pytest.fixture
def driver(neo4j: Driver) -> Driver:
    neo4j.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
    return neo4j


def counts(driver: Driver) -> dict[str, int]:
    nodes, _, _ = driver.execute_query(
        "MATCH (n:OnbCompany|OnbPerson|OnbAddress) RETURN labels(n)[0] AS key, count(*) AS n"
    )
    rels, _, _ = driver.execute_query(
        "MATCH ()-[r:DIRECTS|REGISTERED_AT|PARENT_OF]->() RETURN type(r) AS key, count(*) AS n"
    )
    return {record["key"]: record["n"] for record in [*nodes, *rels]}


def snapshot(driver: Driver) -> list[dict[str, Any]]:
    records, _, _ = driver.execute_query(SNAPSHOT)
    return [record.data() for record in records]


def documented_load() -> list[str]:
    """The statements of the reference load printed in docs/team/assignment-1.md."""
    found = re.search(r"```cypher\n(// Reference load.*?)```", ASSIGNMENT.read_text(), re.S)
    assert found, "assignment-1.md has no cypher block starting '// Reference load'"
    return [statement.strip() for statement in found.group(1).split(";") if statement.strip()]


def test_the_documented_load_and_the_reference_loader_build_the_same_graph(
    driver: Driver,
) -> None:
    for statement in documented_load():
        driver.execute_query(statement, database_="neo4j")
    assert counts(driver) == EXPECTED
    documented = snapshot(driver)
    assert documented[0]["props"]["synthetic"] is True

    assert load(driver, read_rows()) == Counts(20, 15, 16)
    assert counts(driver) == EXPECTED
    assert snapshot(driver) == documented
    load(driver, read_rows())  # idempotent
    assert counts(driver) == EXPECTED


def test_the_example_query_finds_the_companies_at_the_shared_address(driver: Driver) -> None:
    load(driver, read_rows())
    entries = parse_first_queries(QUERIES_PATH.read_text(encoding="utf-8"))
    records, _, _ = driver.execute_query(entries[0].queries[0])
    assert [record["company_id"] for record in records] == [
        "onb-co-06",
        "onb-co-09",
        "onb-co-12",
        "onb-co-16",
    ]
    results = check_queries(driver, entries)
    assert results[0] == QueryResult("@example", rows=4)
    assert [result for result in results if result.error] == []  # every first query runs


def test_first_queries_cannot_write_and_time_out(driver: Driver) -> None:
    with pytest.raises(Neo4jError, match="read access mode"):
        run_read_only(driver, "CREATE (:OnbProbe) RETURN 1")
    slow = "UNWIND range(1, 300000000) AS x WITH x WHERE x % 7 = 3 RETURN count(*)"
    with pytest.raises(Neo4jError) as timed_out:
        run_read_only(driver, slow, timeout_s=0.5)
    assert "TransactionTimedOut" in str(timed_out.value.code)
    probes, _, _ = driver.execute_query("MATCH (n:OnbProbe) RETURN count(n) AS n")
    assert probes[0]["n"] == 0


def test_reset_removes_only_the_onboarding_nodes(driver: Driver) -> None:
    load(driver, read_rows())
    driver.execute_query("CREATE (:Entity {id: 'syn-co-9999', synthetic: true})")
    assert reset(driver) == 51
    remaining, _, _ = driver.execute_query("MATCH (n) RETURN labels(n) AS labels")
    assert [record["labels"] for record in remaining] == [["Entity"]]
