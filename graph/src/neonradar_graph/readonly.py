"""The one way the API and the copilot run a read query (PHASE-4.md 7.5.1).

`run_read` opens a session in READ access mode and an explicit transaction with a server-side
timeout and a metadata entry that names the query (never its parameters or a question), runs one
committed query text with parameters, fetches at most `max_rows + 1` rows so the caller learns
whether the result was cut, and closes the transaction without committing: a read never commits,
so a write that slipped past every other check is rolled back. It then checks the server's
summary: a query whose type is not "r", or that reports any update, raises `ReadRefused`, which
the API reports as a defect of the query file (a 500 problem), never as data.

On Neo4j 5.26 Community the READ access mode is a check of each statement by the query router,
not a security boundary, and every user is an administrator (research note
`api-readonly-cypher.md` 2.1 and 2.5); this helper is one layer of several (PHASE-4.md 7.5.2), and
query text only ever comes from committed files.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import neo4j
from neo4j import Driver

TX_TIMEOUT_S = 5.0
APP = "neonradar"


class ReadRefused(RuntimeError):
    """The server's summary shows something other than a pure read."""


@dataclass(frozen=True, slots=True)
class ReadResult:
    rows: list[dict[str, Any]]
    truncated: bool


def run_read(
    driver: Driver,
    name: str,
    text: str,
    parameters: Mapping[str, Any],
    *,
    max_rows: int,
    timeout_s: float = TX_TIMEOUT_S,
    database: str | None = None,
) -> ReadResult:
    """Run one committed read query; at most `max_rows` rows, and whether more existed."""
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1")
    with driver.session(database=database, default_access_mode=neo4j.READ_ACCESS) as session:
        tx = session.begin_transaction(metadata={"app": APP, "query": name}, timeout=timeout_s)
        try:
            result = tx.run(text, dict(parameters))
            records = result.fetch(max_rows + 1)
            summary = result.consume()
        finally:
            tx.close()  # rolls back: a read never commits
    counters = summary.counters
    if summary.query_type != "r" or counters.contains_updates or counters.contains_system_updates:
        raise ReadRefused(f"{name}: query_type={summary.query_type!r}, updates reported")
    return ReadResult([record.data() for record in records[:max_rows]], len(records) > max_rows)
