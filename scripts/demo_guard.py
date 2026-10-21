#!/usr/bin/env python3
"""Refuse to replace a graph that holds real data with the synthetic demo (PHASE-1.md M1.9e).

`make demo-mini` and `make demo-dev` wipe the graph (every node except `:SchemaMigration`)
before they load demo-mini. They run this check first, unless CONFIRM=yes is given on the
command line: it exits 3 when the wipe would delete anything that is not known to be synthetic
demo data, so a graph with registry data, onboarding data or anything else is never wiped by
accident. It reads the Neo4j settings like every `neonradar graph` command (NEO4J_URI,
NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, `.env`):

    uv run python scripts/demo_guard.py

Exit codes: 0 only synthetic data (or nothing), 3 something else, 1 no connection.
"""

import sys
from typing import Final, LiteralString

from neo4j import READ_ACCESS, Driver, NotificationMinimumSeverity
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready

# Everything the wipe deletes, less what is known to be synthetic: `:Entity` and `:Sanction`
# nodes with `synthetic = true` (C2), alerts that involve no real entity, and detection runs.
# A missing or non-boolean value counts as real, and so does any other kind of node.
QUERY: Final[LiteralString] = """
MATCH (n)
WHERE NOT n:SchemaMigration
  AND NOT n:DetectionRun
  AND NOT ((n:Entity OR n:Sanction) AND coalesce(n.synthetic = true, false))
  AND NOT (n:Alert AND coalesce(n.involves_real_entities = false, false))
RETURN count(n) AS real
"""
REFUSED: Final = 3


def count_not_synthetic(driver: Driver, database: str) -> int:
    """How many nodes the wipe would delete that are not known to be synthetic demo data.

    Notifications are off: on a new graph the server warns that labels and property keys such
    as `synthetic` do not exist yet, which is expected here.
    """
    with driver.session(
        database=database,
        default_access_mode=READ_ACCESS,
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    ) as session:
        record = session.run(QUERY).single(strict=True)
    return int(record["real"])


def check(driver: Driver, database: str) -> int:
    """0 when the graph may be wiped for the demo, REFUSED otherwise; one line either way."""
    real = count_not_synthetic(driver, database)
    if real:
        what = "node that is" if real == 1 else "nodes that are"
        print(
            f"REFUSED  the graph holds {real} {what} not synthetic demo data (entities or"
            " sanctions not marked synthetic, alerts that involve real entities, or other kinds"
            " of node), and the demo wipes the graph before loading. Load the demo elsewhere,"
            " or run it again with CONFIRM=yes to delete everything in the graph (for example:"
            " make demo-mini CONFIRM=yes).",
            file=sys.stderr,
        )
        return REFUSED
    print("OK  the graph holds nothing but synthetic demo data")
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
