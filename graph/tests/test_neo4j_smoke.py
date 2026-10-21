"""Integration smoke test: a Neo4j 5.26 container answers, with APOC and GDS loaded.

It gives CI's integration job a real test from the start (`pytest -m integration` exits with
code 5 when nothing matches). M1.7b moves it onto the shared Neo4j fixture.
"""

import os

import pytest
from testcontainers.community.neo4j import Neo4jContainer
from testcontainers.core.config import testcontainers_config

IMAGE = os.environ.get("NR_NEO4J_IMAGE", "neo4j:5.26.32-community")
# NEO4J_PLUGINS downloads the GDS jar from graphdatascience.ninja when the container starts,
# which can take minutes; the default wait is 120 s. M1.7b switches to the pinned jar (M1.4).
STARTUP_TIMEOUT_S = 300

# Small enough to run next to the local stack (M1.4) and on a 7 GB CI runner.
MEMORY = {
    "NEO4J_server_memory_heap_initial__size": "512m",
    "NEO4J_server_memory_heap_max__size": "512m",
    "NEO4J_server_memory_pagecache_size": "256m",
}


@pytest.mark.integration
def test_neo4j_answers_with_apoc_and_gds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(testcontainers_config, "max_tries", STARTUP_TIMEOUT_S)
    monkeypatch.setattr(testcontainers_config, "sleep_time", 1.0)
    container = (
        Neo4jContainer(IMAGE, mem_limit="1536m")
        .with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')
        .with_envs(**MEMORY)
    )
    with container, container.get_driver() as driver:
        one, _, _ = driver.execute_query("RETURN 1 AS one", database_="neo4j")
        apoc, _, _ = driver.execute_query("RETURN apoc.version() AS version", database_="neo4j")
        gds, _, _ = driver.execute_query("RETURN gds.version() AS version", database_="neo4j")

    assert one[0]["one"] == 1
    assert apoc[0]["version"].startswith("5.26")
    assert gds[0]["version"].startswith("2.13")
