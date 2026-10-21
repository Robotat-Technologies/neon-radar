from typing import Any, cast

from neo4j import Driver
from neo4j.exceptions import ClientError

from neonradar_graph import smoke
from neonradar_graph.smoke import SmokeReport, run_smoke

KERNEL = {"name": "Neo4j Kernel", "versions": ["5.26.32"], "edition": "community"}


class FakeDriver:
    """Answers the three smoke queries; a query without an answer fails like a missing plugin."""

    def __init__(self, answers: dict[str, list[dict[str, Any]]]) -> None:
        self.answers = answers
        self.databases: set[str] = set()

    def execute_query(self, query: str, **kwargs: Any) -> tuple[list[dict[str, Any]], None, None]:
        self.databases.add(kwargs["database_"])
        if query not in self.answers:
            raise ClientError("Unknown function")
        return self.answers[query], None, None


def test_reports_all_three_components() -> None:
    driver = FakeDriver(
        {
            smoke.COMPONENTS: [KERNEL],
            smoke.APOC_VERSION: [{"version": "5.26.32"}],
            smoke.GDS_VERSION: [{"version": "2.13.4"}],
        }
    )
    report = run_smoke(cast(Driver, driver))
    assert report == SmokeReport("5.26.32 community", "5.26.32", "2.13.4")
    assert report.ok
    assert report.lines() == [
        "OK    Neo4j  5.26.32 community",
        "OK    APOC   5.26.32",
        "OK    GDS    2.13.4",
    ]
    assert driver.databases == {"neo4j"}


def test_a_missing_plugin_fails() -> None:
    driver = FakeDriver({smoke.COMPONENTS: [KERNEL], smoke.APOC_VERSION: [{"version": "5.26.32"}]})
    report = run_smoke(cast(Driver, driver), database="other")
    assert report.gds is None
    assert not report.ok
    assert report.lines()[2] == "FAIL  GDS    missing"
    assert driver.databases == {"other"}


def test_no_kernel_component_fails() -> None:
    driver = FakeDriver({smoke.COMPONENTS: [], smoke.APOC_VERSION: [], smoke.GDS_VERSION: []})
    report = run_smoke(cast(Driver, driver))
    assert report == SmokeReport(None, None, None)
