"""The read helper and the server settings on Neo4j 5.26 Community (PHASE-4.md 7.5.2).

Integration tests on a container started with the `compose.yaml` settings (the procedure
allowlist and the transaction memory limit). They check what the research note could only read
in the source (`api-readonly-cypher.md` 6.4): a write in a READ session is rejected, the summary
tripwire refuses anything but "r", a client timeout ends a long query, and APOC's file and web
procedures are not loaded.
"""

from collections.abc import Iterator
from typing import Any

import neo4j
import pytest
from neo4j.exceptions import ClientError
from neonradar_graph.readonly import ReadRefused, run_read

pytestmark = pytest.mark.integration
IMAGE = "neo4j:5.26.32-community"


@pytest.fixture(scope="module")
def driver() -> Iterator[Any]:
    pytest.importorskip("testcontainers")
    from testcontainers.community.neo4j import Neo4jContainer

    with (
        Neo4jContainer(IMAGE)
        .with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')
        .with_env("NEO4J_dbms_security_procedures_unrestricted", "apoc.*,gds.*")
        .with_env(
            "NEO4J_dbms_security_procedures_allowlist",
            "apoc.version,apoc.meta.stats,apoc.coll.*,gds.*",
        )
        .with_env("NEO4J_db_memory_transaction_max", "1G") as neo
    ):
        driver = neo.get_driver()
        try:
            yield driver
        finally:
            driver.close()


def test_a_write_in_read_mode_is_rejected_and_leaves_nothing(driver: Any) -> None:
    with pytest.raises(ClientError) as error:
        run_read(driver, "probe", "CREATE (n:ReadProbe) RETURN n", {}, max_rows=1)
    assert error.value.code == "Neo.ClientError.Statement.AccessMode"
    records, _, _ = driver.execute_query("MATCH (n:ReadProbe) RETURN count(n) AS n")
    assert records[0]["n"] == 0


def test_the_tripwire_refuses_a_dbms_procedure(driver: Any) -> None:
    with pytest.raises(ReadRefused):
        run_read(driver, "probe", "CALL dbms.components()", {}, max_rows=5)


def test_a_client_timeout_ends_a_long_query(driver: Any) -> None:
    text = (
        "UNWIND range(1, 10000) AS a UNWIND range(1, 10000) AS b "
        "WITH a, b WHERE a * b < 0 RETURN count(*) AS n"
    )
    with pytest.raises(ClientError) as error:
        run_read(driver, "probe", text, {}, max_rows=1, timeout_s=1.0)
    assert "TransactionTimedOut" in (error.value.code or "")


def test_apoc_file_and_web_procedures_are_not_loaded(driver: Any) -> None:
    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        names = [r["name"] for r in session.run("SHOW PROCEDURES YIELD name")]
        assert not [
            n for n in names if n.startswith(("apoc.load.", "apoc.export.", "apoc.cypher."))
        ]
        assert session.run("RETURN apoc.version() AS v").single()["v"]
        assert session.run("RETURN gds.version() AS v").single()["v"]


def test_load_csv_cannot_read_server_files(driver: Any) -> None:
    """A file outside the import folder cannot be read: the path is resolved inside it. (A READ
    query can still read a file placed in the import folder, which is why query text only ever
    comes from committed files, PHASE-4.md 7.5.2 layer 4.)"""
    with pytest.raises(ClientError) as error:
        run_read(
            driver, "probe", "LOAD CSV FROM 'file:///etc/hostname' AS r RETURN r", {}, max_rows=1
        )
    assert "ExternalResourceFailed" in (error.value.code or "")
