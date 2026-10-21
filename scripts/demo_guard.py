#!/usr/bin/env python3
"""Refuse to replace a graph that holds real data with the synthetic demo (PHASE-1.md M1.9e).

`make demo-mini` and `make demo-dev` wipe the graph before they load demo-mini. They run this
check first, unless CONFIRM=yes: it exits 3 when any `:Entity` node is not marked synthetic, so
a graph with registry data is never wiped by accident. It reads the Neo4j settings like every
`neonradar graph` command (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, `.env`):

    uv run python scripts/demo_guard.py

Exit codes: 0 every entity is synthetic (or there are none), 3 some are not, 1 no connection.
"""

import sys
from typing import Final, LiteralString

from neo4j import Driver, RoutingControl
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready

# `synthetic` mirrors the dataset's flag on every :Entity (C2); a missing value counts as real.
QUERY: Final[LiteralString] = (
    "MATCH (n:Entity) WHERE n.synthetic IS NULL OR n.synthetic <> true RETURN count(n) AS real"
)
REFUSED: Final = 3


def count_not_synthetic(driver: Driver, database: str) -> int:
    """How many `:Entity` nodes are not marked `synthetic = true`."""
    records, _, _ = driver.execute_query(QUERY, database_=database, routing_=RoutingControl.READ)
    return int(records[0]["real"])


def check(driver: Driver, database: str) -> int:
    """0 when the graph may be wiped for the demo, REFUSED otherwise; one line either way."""
    real = count_not_synthetic(driver, database)
    if real:
        what = "entity that is" if real == 1 else "entities that are"
        print(
            f"REFUSED  the graph holds {real} {what} not synthetic, and the demo wipes the"
            " graph before loading. Load the demo elsewhere, or run it again with CONFIRM=yes"
            " to delete everything in the graph (for example: make demo-mini CONFIRM=yes).",
            file=sys.stderr,
        )
        return REFUSED
    print("OK  the graph holds no entities that are not synthetic")
    return 0


def main() -> int:
    try:
        settings = Neo4jSettings()
    except ValidationError:
        print("FAIL  NEO4J_PASSWORD is not set: create .env or export it", file=sys.stderr)
        return 1
    try:
        with get_driver(settings) as driver:
            wait_until_ready(driver, timeout_s=60)
            return check(driver, settings.database)
    except (DriverError, Neo4jError, TimeoutError) as error:
        print(f"FAIL  Neo4j at {settings.uri}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
