"""Smoke check of the running Neo4j: server version and edition, APOC and GDS (PHASE-1.md M1.4)."""

from dataclasses import dataclass

from neo4j import Driver, RoutingControl
from neo4j.exceptions import Neo4jError

COMPONENTS = "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition"
APOC_VERSION = "RETURN apoc.version() AS version"
GDS_VERSION = "RETURN gds.version() AS version"


@dataclass(frozen=True)
class SmokeReport:
    """What the server reports; None means the component is missing or failed."""

    neo4j: str | None
    apoc: str | None
    gds: str | None

    @property
    def ok(self) -> bool:
        return None not in (self.neo4j, self.apoc, self.gds)

    def lines(self) -> list[str]:
        rows = (("Neo4j", self.neo4j), ("APOC", self.apoc), ("GDS", self.gds))
        return [
            f"{'OK' if found else 'FAIL':<5} {name:<6} {found or 'missing'}" for name, found in rows
        ]


def _single_value(driver: Driver, database: str, query: str) -> str | None:
    try:
        records, _, _ = driver.execute_query(
            query, database_=database, routing_=RoutingControl.READ
        )
    except Neo4jError:
        return None  # for example "Unknown function 'gds.version'" when the plugin is missing
    return str(records[0]["version"]) if records and records[0]["version"] else None


def _neo4j_version(driver: Driver, database: str) -> str | None:
    records, _, _ = driver.execute_query(
        COMPONENTS, database_=database, routing_=RoutingControl.READ
    )
    for record in records:
        if record["name"] == "Neo4j Kernel" and record["versions"]:
            return f"{record['versions'][0]} {record['edition']}"
    return None


def run_smoke(driver: Driver, database: str = "neo4j") -> SmokeReport:
    return SmokeReport(
        neo4j=_neo4j_version(driver, database),
        apoc=_single_value(driver, database, APOC_VERSION),
        gds=_single_value(driver, database, GDS_VERSION),
    )
