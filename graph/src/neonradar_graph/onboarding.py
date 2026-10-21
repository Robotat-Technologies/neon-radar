"""Onboarding sandbox for Assignment 1 (PHASE-1.md M1.11a, docs/team/assignment-1.md).

Loads the synthetic onboarding CSV into the `OnbCompany`, `OnbPerson` and `OnbAddress` labels,
which are deliberately separate from the C2 graph schema; runs every query in
docs/team/first-queries.md read-only with a timeout; and removes the `Onb*` nodes again.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from neo4j import READ_ACCESS, Driver
from neo4j.exceptions import Neo4jError

from neonradar_graph.client import REPO_ROOT

CSV_PATH = REPO_ROOT / "data" / "fixtures" / "onboarding" / "companies-20.csv"
QUERIES_PATH = REPO_ROOT / "docs" / "team" / "first-queries.md"
HEADER = [
    "synthetic",
    "company_id",
    "company_name",
    "jurisdiction",
    "incorporated_on",
    "director_id",
    "director_name",
    "registered_address",
    "parent_company_id",
]
QUERY_TIMEOUT_S = 10.0

# The same statements as the reference load in docs/team/assignment-1.md, with UNWIND over
# parameters instead of LOAD CSV (an integration test proves both build the same graph).
LOAD_NODES = """
UNWIND $rows AS row
MERGE (c:OnbCompany {id: row.company_id})
SET c.name = row.company_name, c.jurisdiction = row.jurisdiction,
    c.incorporated_on = date(row.incorporated_on), c.synthetic = toBoolean(row.synthetic)
MERGE (p:OnbPerson {id: row.director_id})
SET p.name = row.director_name, p.synthetic = toBoolean(row.synthetic)
MERGE (a:OnbAddress {full: row.registered_address})
SET a.synthetic = toBoolean(row.synthetic)
MERGE (p)-[:DIRECTS]->(c)
MERGE (c)-[:REGISTERED_AT]->(a)
"""
LOAD_PARENTS = """
UNWIND $rows AS row
WITH row WHERE row.parent_company_id IS NOT NULL
MATCH (child:OnbCompany {id: row.company_id})
MATCH (parent:OnbCompany {id: row.parent_company_id})
MERGE (parent)-[:PARENT_OF]->(child)
"""
COUNT_NODES = """
RETURN COUNT { (:OnbCompany) } AS companies, COUNT { (:OnbPerson) } AS people,
       COUNT { (:OnbAddress) } AS addresses
"""
RESET = "MATCH (n:OnbCompany|OnbPerson|OnbAddress) DETACH DELETE n RETURN count(n) AS removed"

HANDLE_RE = re.compile(r"@[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}")  # a GitHub handle
FENCE_RE = re.compile(r"```\s*(\S*)\s*")


class OnboardingError(Exception):
    """The onboarding CSV is not what the loader expects."""


class Counts(NamedTuple):
    companies: int
    people: int
    addresses: int


def read_rows(path: Path = CSV_PATH) -> list[dict[str, str | None]]:
    """Read the CSV; empty fields become None, as LOAD CSV makes them null."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise OnboardingError(f"{path}: header is {reader.fieldnames}, expected {HEADER}")
        rows: list[dict[str, str | None]] = []
        for row in reader:
            if row["synthetic"] != "true":
                raise OnboardingError(f"{path}:{reader.line_num}: synthetic is not 'true'")
            rows.append({key: value or None for key, value in row.items()})
    return rows


def expected_counts(rows: list[dict[str, str | None]]) -> Counts:
    return Counts(
        companies=len({row["company_id"] for row in rows}),
        people=len({row["director_id"] for row in rows}),
        addresses=len({row["registered_address"] for row in rows}),
    )


def load(driver: Driver, rows: list[dict[str, str | None]], database: str = "neo4j") -> Counts:
    """MERGE the rows into the Onb* labels (idempotent); return the Onb* node counts."""
    driver.execute_query(LOAD_NODES, rows=rows, database_=database)
    driver.execute_query(LOAD_PARENTS, rows=rows, database_=database)
    records, _, _ = driver.execute_query(COUNT_NODES, database_=database)
    return Counts(records[0]["companies"], records[0]["people"], records[0]["addresses"])


def reset(driver: Driver, database: str = "neo4j") -> int:
    """Delete every Onb* node and its relationships; return how many nodes went."""
    records, _, _ = driver.execute_query(RESET, database_=database)
    return int(records[0]["removed"])


@dataclass
class Entry:
    """One `## @handle` section of first-queries.md."""

    handle: str
    line: int
    queries: list[str] = field(default_factory=list)
    problem: str | None = None


def parse_first_queries(text: str) -> list[Entry]:
    """Every `## @handle` section with its ```cypher blocks and any format problem.

    Text before the first `## @handle` heading and under any other `## ` heading is ignored.
    """
    entries: list[Entry] = []
    current: Entry | None = None
    fence: str | None = None  # the language of the open code block
    block: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        marker = FENCE_RE.fullmatch(line.strip())
        if fence is not None:
            if marker and not marker.group(1):
                if fence == "cypher" and current is not None:
                    current.queries.append("\n".join(block).strip())
                fence = None
            else:
                block.append(line)
        elif marker:
            fence, block = marker.group(1).lower(), []
        elif line.startswith("## "):
            title = line[3:].strip()
            current = Entry(title, number) if title.startswith("@") else None
            if current is not None:
                entries.append(current)
    if fence is not None and current is not None:
        current.problem = "a code block is not closed"
    seen: set[str] = set()
    for entry in entries:
        if entry.problem:
            continue
        if not HANDLE_RE.fullmatch(entry.handle):
            entry.problem = f"'{entry.handle}' is not a GitHub handle"
        elif entry.handle.lower() in seen:
            entry.problem = f"a second section for {entry.handle}"
        elif len(entry.queries) != 1:
            entry.problem = f"expected exactly one ```cypher block, found {len(entry.queries)}"
        elif not entry.queries[0]:
            entry.problem = "the ```cypher block is empty"
        seen.add(entry.handle.lower())
    return entries


@dataclass(frozen=True)
class QueryResult:
    handle: str
    rows: int | None = None
    error: str | None = None

    def line(self) -> str:
        if self.error is not None:
            return f"FAIL  {self.handle}  {self.error}"
        return f"OK    {self.handle}  ran, {self.rows} rows returned"


def run_read_only(
    driver: Driver, query: str, database: str = "neo4j", timeout_s: float = QUERY_TIMEOUT_S
) -> int:
    """Run one query in a read transaction with a server-side timeout; return the row count.

    The server refuses writes in a read transaction, and the transaction is rolled back.
    """
    with (
        driver.session(database=database, default_access_mode=READ_ACCESS) as session,
        session.begin_transaction(timeout=timeout_s) as tx,
    ):
        return sum(1 for _ in tx.run(query))


def check_queries(
    driver: Driver,
    entries: list[Entry],
    database: str = "neo4j",
    timeout_s: float = QUERY_TIMEOUT_S,
) -> list[QueryResult]:
    results: list[QueryResult] = []
    for entry in entries:
        if entry.problem:
            results.append(QueryResult(entry.handle, error=f"format: {entry.problem}"))
            continue
        try:
            rows = run_read_only(driver, entry.queries[0], database, timeout_s)
        except Neo4jError as error:
            message = (error.message or "").splitlines()[0] if error.message else ""
            results.append(QueryResult(entry.handle, error=f"{error.code}: {message}"))
        else:
            results.append(QueryResult(entry.handle, rows=rows))
    return results
