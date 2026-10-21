"""The Neo4j the integration tests share (PHASE-1.md M1.7b).

- `NR_TEST_NEO4J_URI` set: use that running database (faster locally), with the user and
  password of `Neo4jSettings` (NEO4J_USER, NEO4J_PASSWORD or the root `.env`). The tests wipe
  it, so a database that holds `:Entity` nodes is refused unless `NR_TEST_ALLOW_WIPE=1`.
- Otherwise: a throwaway Testcontainers Neo4j (`NR_NEO4J_IMAGE`, default the compose image)
  with a random password, APOC Core from the image and the GDS jar that `make plugins` pinned
  (operator decision OD-13), copied into the container before it starts. Nothing is downloaded
  when it starts, and the telemetry settings of compose.yaml apply.
"""

import hashlib
import os
import re
import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from neo4j import Driver

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready

REPO_ROOT = Path(__file__).resolve().parents[2]
FETCH_GDS = REPO_ROOT / "scripts" / "fetch_gds.sh"
PLUGINS_DIR = REPO_ROOT / "data" / "cache" / "neo4j-plugins"
IMAGE = os.environ.get("NR_NEO4J_IMAGE", "neo4j:5.26.32-community")
CONTAINER_ENV = {
    "NEO4J_PLUGINS": '["apoc"]',  # APOC Core is in the image's labs/ folder
    "NEO4J_dbms_security_procedures_unrestricted": "apoc.*,gds.*",
    "NEO4J_client_allow__telemetry": "false",
    "NEO4J_dbms_usage__report_enabled": "false",
    # Small enough to run next to the local stack and on a 7 GB CI runner.
    "NEO4J_server_memory_heap_initial__size": "512m",
    "NEO4J_server_memory_heap_max__size": "512m",
    "NEO4J_server_memory_pagecache_size": "256m",
}


@dataclass(frozen=True)
class Neo4jTarget:
    driver: Driver
    database: str


def pinned_gds() -> tuple[str, Path]:
    """The GDS version and jar that scripts/fetch_gds.sh pins; fails if the jar is missing."""
    text = FETCH_GDS.read_text(encoding="utf-8")
    version = re.search(r'^GDS_VERSION="([^"]+)"$', text, re.MULTILINE)
    sha256 = re.search(r'^GDS_SHA256="([0-9a-f]{64})"$', text, re.MULTILINE)
    assert version and sha256, f"{FETCH_GDS} no longer pins GDS_VERSION and GDS_SHA256"
    jar = PLUGINS_DIR / f"neo4j-graph-data-science-{version[1]}.jar"
    if not jar.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest() != sha256[1]:
        pytest.fail(f"{jar.relative_to(REPO_ROOT)} is missing or wrong: run `make plugins` once")
    return version[1], jar


def _external(uri: str) -> Iterator[Neo4jTarget]:
    settings = Neo4jSettings(uri=uri)
    with get_driver(settings) as driver:
        wait_until_ready(driver, timeout_s=60)
        records, _, _ = driver.execute_query(
            "MATCH (n:Entity) RETURN count(n) AS n", database_=settings.database
        )
        if records[0]["n"] and os.environ.get("NR_TEST_ALLOW_WIPE") != "1":
            pytest.fail(
                f"NR_TEST_NEO4J_URI={uri} holds {records[0]['n']} :Entity nodes and the tests wipe"
                " the database: set NR_TEST_ALLOW_WIPE=1 to allow it, or unset NR_TEST_NEO4J_URI"
            )
        yield Neo4jTarget(driver, settings.database)


def _container() -> Iterator[Neo4jTarget]:
    from testcontainers.community.neo4j import Neo4jContainer  # only when a test needs it

    _, jar = pinned_gds()
    container = (
        Neo4jContainer(IMAGE, password=secrets.token_hex(16), mem_limit="1536m")
        .with_envs(**CONTAINER_ENV)
        .with_copy_into_container(jar, f"/var/lib/neo4j/plugins/{jar.name}")
    )
    with container, container.get_driver(telemetry_disabled=True) as driver:
        yield Neo4jTarget(driver, "neo4j")


@pytest.fixture(scope="session")
def neo4j() -> Iterator[Neo4jTarget]:
    """One Neo4j for the whole session."""
    uri = os.environ.get("NR_TEST_NEO4J_URI")
    yield from _external(uri) if uri else _container()


def _quoted(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


@pytest.fixture
def empty_neo4j(neo4j: Neo4jTarget) -> Neo4jTarget:
    """The shared Neo4j without nodes, constraints or indexes (the two lookup indexes stay)."""
    with neo4j.driver.session(database=neo4j.database) as session:
        session.run(
            "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS"
        ).consume()
        # Schema names come from the database itself, not from data; DDL takes no parameters.
        for record in session.run("SHOW CONSTRAINTS YIELD name").data():
            session.run(f"DROP CONSTRAINT {_quoted(record['name'])} IF EXISTS").consume()
        for record in session.run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'").data():
            session.run(f"DROP INDEX {_quoted(record['name'])} IF EXISTS").consume()
    return neo4j
