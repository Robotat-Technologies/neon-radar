"""The C1 record loader: `neonradar graph load` (PHASE-1.md M1.9a, contracts/C2-graph-schema.md).

1. Read every record of the load (`collect_files`, `read_records`).
2. Validate it against C1 (`plan_load`). A strict load refuses on any issue and writes nothing;
   a non-strict load skips each record that failed C1 and never maps it.
3. Map the rest with `neonradar_graph.mapping`; a strict load also refuses on any MappingIssue.
4. Write nodes, then relationships, in batches of 5,000 rows with `UNWIND $rows AS row`, one
   `driver.execute_query` transaction per batch. Labels and types come only from
   `neonradar_contracts.graph`, written into the query text per schema or type; record values
   travel only as parameters.

Relationships find both ends by id on the key label (`:Entity`, or `:Sanction`) with an index
seek hint, and check the C2 From and To label; a row whose end is missing is reported as
dangling. Loading the same files twice leaves the graph unchanged.

A reload of changed files is an upsert of what the files hold:
- properties are set again, and every mapped property the record no longer has is removed
  (sent as null); flag labels follow the record both ways;
- a relationship whose end or type changed (an Ownership between OWNS, CONSOLIDATES and
  HOLDS_ACCOUNT) is moved: the old one with the same id is deleted;
- a relationship whose new end is missing is deleted and its row reported as dangling, so the
  graph never keeps an edge the files no longer describe.
What stays until `wipe`: records no longer in the files, relationships from reference values a
record dropped (`addressEntity` to HAS_ADDRESS, `Sanction.entity` to SUBJECT_OF), and the
schema labels of a record whose schema changed. So invariants I1 to I5 are guaranteed after
`neonradar graph wipe --yes` followed by a load; wipe before loading a regenerated synthetic
dataset. Each batch is one transaction: a database error part-way leaves the earlier batches
committed, and running the same load again completes it (idempotent).
"""

import logging
import re
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from itertools import batched
from pathlib import Path
from typing import Any

from neo4j import Driver, RoutingControl, SummaryCounters

from neonradar_contracts.graph import (
    FLAG_LABELS,
    NODE_LABELS,
    NODE_MAPPINGS,
    REFERENCE_MAPPINGS,
    RELATIONSHIP_ENDPOINTS,
    RELATIONSHIP_MAPPINGS,
    RELATIONSHIP_TYPES,
)
from neonradar_contracts.records import (
    RecordFileError,
    RecordIssue,
    iter_records,
    validate_batch,
    validate_record,
)
from neonradar_graph.mapping import (
    MappingIssue,
    NodeRow,
    RelationshipRow,
    to_node_rows,
    to_relationship_rows,
)
from neonradar_graph.migrate import MIGRATIONS_DIR, discover

logger = logging.getLogger(__name__)

Record = dict[str, Any]
BATCH_SIZE = 5_000
RECORD_GLOB = "*.ftm.jsonl"
# Labels and types are written into query text, so they must be plain identifiers.
LABEL_RE = re.compile(r"^[A-Z][A-Za-z]*\Z")
TYPE_RE = re.compile(r"^[A-Z][A-Z_]*[A-Z]\Z")
# Relationship types with a DATETIME `ts` (PAID): the row carries `<date>Z` in `row.ts`.
TS_TYPES = frozenset(
    mapping.type
    for mappings in RELATIONSHIP_MAPPINGS.values()
    for mapping in mappings
    if "ts" in mapping.properties.values()
)
# Every optional property each node schema and relationship type can carry. A load sends the
# absent ones as null, so `SET x += row.props` removes a property a reloaded record dropped.
# Never `address_key`, which Phase 2 computes (RESERVED_PROPERTIES).
NODE_OPTIONAL = {
    schema: tuple(
        dict.fromkeys(["source_url", "first_seen", "last_seen", *mapping.properties.values()])
    )
    for schema, mapping in NODE_MAPPINGS.items()
}
_ALWAYS_SET = {"id", "datasets", "synthetic", "ts"}  # ts is set with datetime() on PAID
RELATIONSHIP_OPTIONAL = {
    mapping.type: tuple(
        name
        for name in dict.fromkeys(["source_url", *mapping.properties.values()])
        if name not in _ALWAYS_SET
    )
    for mappings in RELATIONSHIP_MAPPINGS.values()
    for mapping in mappings
} | {ref.type: ("source_url", *ref.properties.values()) for ref in REFERENCE_MAPPINGS}
# Types built from the same FtM schema (Ownership): a reload that changes the type deletes the
# relationship with the same id under the other types.
SIBLING_TYPES = {
    mapping.type: tuple(other.type for other in mappings if other.type != mapping.type)
    for mappings in RELATIONSHIP_MAPPINGS.values()
    for mapping in mappings
}
WRITE_COUNTERS = (
    "nodes_created",
    "relationships_created",
    "relationships_deleted",
    "labels_added",
    "labels_removed",
)
APPLIED = "MATCH (m:SchemaMigration) RETURN m.id AS id"
WIPE = (
    "MATCH (n) WHERE NOT n:SchemaMigration"
    " CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS"
)
STATS = (
    "CALL apoc.meta.stats() YIELD nodeCount, relCount, labels, relTypesCount"
    " RETURN nodeCount, relCount, labels, relTypesCount"
)


class LoadError(Exception):
    """The load cannot start: no record files, an unreadable line, or a schema not migrated."""


class LoadRefused(Exception):
    """A strict load found C1 issues or MappingIssues; nothing was written."""

    def __init__(self, issues: Sequence[RecordIssue], skipped: Sequence[MappingIssue]) -> None:
        self.issues = list(issues)
        self.skipped = list(skipped)
        super().__init__(f"{len(self.issues) + len(self.skipped)} issue(s); nothing was written")


@dataclass(frozen=True, slots=True)
class DanglingReference:
    """A relationship row whose source or target has no node with the required label."""

    type: str
    id: str
    source: str
    target: str
    source_missing: bool
    target_missing: bool

    def __str__(self) -> str:
        source_label, target_label = RELATIONSHIP_ENDPOINTS[self.type]
        missing = [
            f"no :{label} node {node_id}"
            for label, node_id, gone in (
                (source_label, self.source, self.source_missing),
                (target_label, self.target, self.target_missing),
            )
            if gone
        ]
        return f"DANGLING {self.type} {self.id}: {' and '.join(missing)}"


@dataclass(slots=True)
class LoadPlan:
    """The rows to write and what was left out (`plan_load`)."""

    records: int
    nodes: list[NodeRow]
    relationships: list[RelationshipRow]
    rejected: list[RecordIssue] = field(default_factory=list)
    skipped: list[MappingIssue] = field(default_factory=list)


@dataclass(slots=True)
class LoadReport:
    """What a load did. Counts are rows written (nodes by each label they carry, relationships
    by type, dangling rows excluded); `written` holds the database's counters, which are all 0
    when the same files are loaded again."""

    strict: bool
    files: list[Path] = field(default_factory=list)
    records: int = 0
    nodes_by_label: Counter[str] = field(default_factory=Counter)
    relationships_by_type: Counter[str] = field(default_factory=Counter)
    dangling: list[DanglingReference] = field(default_factory=list)
    rejected: list[RecordIssue] = field(default_factory=list)
    skipped: list[MappingIssue] = field(default_factory=list)
    written: Counter[str] = field(default_factory=Counter)
    empty_files: list[Path] = field(default_factory=list)
    duration_s: float = 0.0

    @property
    def failed(self) -> bool:
        """A strict load fails on any dangling reference (C1 R4). Dangling rows are found while
        writing, so the rest of the load has been written by then."""
        return self.strict and bool(self.dangling)


@dataclass(frozen=True, slots=True)
class GraphStats:
    """Node and relationship totals from `apoc.meta.stats()`."""

    nodes: int
    relationships: int
    labels: dict[str, int]
    relationship_types: dict[str, int]


def collect_files(paths: Iterable[Path]) -> list[Path]:
    """The record files of one load, each once: a directory gives every `*.ftm.jsonl` directly
    inside it (label CSVs and subfolders are ignored); a file gives itself."""
    files: dict[Path, None] = {}
    for path in paths:
        if path.is_dir():
            found = sorted(item for item in path.glob(RECORD_GLOB) if item.is_file())
            if not found:
                raise LoadError(f"{path}: no {RECORD_GLOB} files directly inside it")
            files.update(dict.fromkeys(item.resolve() for item in found))
        elif path.is_file():
            files[path.resolve()] = None
        else:
            raise LoadError(f"{path}: no such file or directory")
    return list(files)


def read_records(files: Sequence[Path]) -> list[Record]:
    """Every record of the files, in order; a line that is not one JSON object stops the load."""
    try:
        return [record for path in files for record in iter_records(path)]
    except RecordFileError as error:
        raise LoadError(f"FORMAT {error}") from error


def _usable(
    records: Sequence[Record], record_issues: Sequence[list[RecordIssue]]
) -> tuple[list[Record], list[RecordIssue]]:
    """Non-strict: the records that pass C1, and the issues of those left out.

    A later record with an id already seen is left out even when the first one failed C1 (a
    duplicate never replaces the first record); a BankAccount without a holder among the
    records that pass fails R8 and is left out too.
    """
    rejected: list[RecordIssue] = []
    valid: list[Record] = []
    seen: set[str] = set()
    for record, issues in zip(records, record_issues, strict=True):
        rid = record.get("id")
        if isinstance(rid, str):
            if rid in seen:
                message = "duplicate id: another record in this load has it; the first is kept"
                rejected.append(RecordIssue("R4", rid, message))
                continue
            seen.add(rid)
        if issues:
            rejected.extend(issues)
        else:
            valid.append(record)
    unheld = [issue for issue in validate_batch(valid, strict=False) if issue.rule == "R8"]
    rejected.extend(unheld)
    left_out = {issue.record_id for issue in unheld}
    return [record for record in valid if record.get("id") not in left_out], rejected


def plan_load(records: Sequence[Record], *, strict: bool) -> LoadPlan:
    """Validate (C1) and map (C2) one load without touching the database.

    Raises LoadRefused in strict mode on any C1 issue (dangling references included) or
    MappingIssue. Records that failed C1 are never mapped.
    """
    record_issues = [validate_record(record) for record in records]
    rejected: list[RecordIssue] = []
    if strict:
        issues = [issue for found in record_issues for issue in found]
        issues.extend(validate_batch(records, strict=True))
        if issues:
            raise LoadRefused(issues, [])
        usable = list(records)
    else:
        usable, rejected = _usable(records, record_issues)
    nodes, relationships = to_node_rows(usable), to_relationship_rows(usable)
    skipped = list(dict.fromkeys([*nodes.skipped, *relationships.skipped]))
    if strict and skipped:
        raise LoadRefused([], skipped)
    node_rows = nodes.rows
    if not strict:  # an account whose holding Ownership was skipped would break invariant I4
        held = {row.target for row in relationships.rows if row.type == "HOLDS_ACCOUNT"}
        unheld = {row.id for row in node_rows if "Account" in row.labels and row.id not in held}
        message = "BankAccount has no HOLDS_ACCOUNT after mapping (its Ownership was skipped)"
        rejected.extend(RecordIssue("R8", rid, message) for rid in sorted(unheld))
        node_rows = [row for row in node_rows if row.id not in unheld]
    return LoadPlan(len(records), node_rows, relationships.rows, rejected, skipped)


def _label(name: str) -> str:
    if not LABEL_RE.fullmatch(name) or name not in (*NODE_LABELS, *FLAG_LABELS):
        raise ValueError(f"{name!r} is not a label name of C2")
    return name


def _type(name: str) -> str:
    if not TYPE_RE.fullmatch(name) or name not in RELATIONSHIP_TYPES:
        raise ValueError(f"{name!r} is not a relationship type name of C2")
    return name


def node_query(schema: str) -> str:
    """MERGE the nodes of one FtM schema on their key label, set the other labels, the
    properties and every flag label (set when true, removed when false)."""
    key, *others = NODE_MAPPINGS[schema].labels
    lines = ["UNWIND $rows AS row", f"MERGE (n:{_label(key)} {{id: row.id}})"]
    if others:
        lines.append("SET n:" + ":".join(_label(label) for label in others))
    lines.append("SET n += row.props")
    for flag in map(_label, FLAG_LABELS):
        lines.append(
            f"FOREACH (_ IN CASE WHEN row.flags.{flag} THEN [1] ELSE [] END | SET n:{flag})"
        )
        lines.append(
            f"FOREACH (_ IN CASE WHEN NOT row.flags.{flag} THEN [1] ELSE [] END | REMOVE n:{flag})"
        )
    return "\n".join(lines)


def relationship_query(sample: RelationshipRow) -> str:
    """MERGE the relationships of `sample.type` between existing nodes; return dangling rows.

    Each end is found on its key label with `{id: ...}` (an index seek) and checked for its C2
    label. A relationship with the row's id between other nodes (its end changed or is
    missing) or under another type built from the same schema (its type changed) is deleted
    first.
    """
    rel = _type(sample.type)
    (source_key, target_key), (source_label, target_label) = (
        sample.endpoint_keys,
        sample.endpoint_labels,
    )
    set_ts = ", r.ts = datetime(row.ts)" if rel in TS_TYPES else ""
    others = [_type(other) for other in SIBLING_TYPES.get(rel, ())]
    source_key, target_key = _label(source_key), _label(target_key)
    return "\n".join(
        [
            "UNWIND $rows AS row",
            f"OPTIONAL MATCH (s:{source_key} {{id: row.source}})"
            f" USING INDEX SEEK s:{source_key}(id) WHERE s:{_label(source_label)}",
            f"OPTIONAL MATCH (t:{target_key} {{id: row.target}})"
            f" USING INDEX SEEK t:{target_key}(id) WHERE t:{_label(target_label)}",
            f"OPTIONAL MATCH (a)-[old:{rel} {{id: row.id}}]->(b)",
            "  WHERE s IS NULL OR t IS NULL OR a <> s OR b <> t",
            *(
                f"OPTIONAL MATCH ()-[o{n}:{other} {{id: row.id}}]->()"
                for n, other in enumerate(others)
            ),
            "DELETE " + ", ".join(["old", *(f"o{n}" for n in range(len(others)))]),
            "FOREACH (_ IN CASE WHEN s IS NOT NULL AND t IS NOT NULL THEN [1] ELSE [] END |",
            f"  MERGE (s)-[r:{rel} {{id: row.id}}]->(t)",
            f"  SET r += row.props{set_ts})",
            "WITH row, s, t WHERE s IS NULL OR t IS NULL",
            "RETURN row.id AS id, row.source AS source, row.target AS target,",
            "       s IS NULL AS source_missing, t IS NULL AS target_missing",
        ]
    )


def require_migrated(driver: Driver, database: str, directory: Path = MIGRATIONS_DIR) -> None:
    """Raise LoadError while a schema migration is pending: the loader relies on its
    uniqueness constraints (MERGE on `id`)."""
    with driver.session(database=database, notifications_min_severity="OFF") as session:
        applied = {str(record["id"]) for record in session.run(APPLIED)}
    pending = [migration.id for migration in discover(directory) if migration.id not in applied]
    if pending:
        raise LoadError(
            f"the graph schema is not migrated ({', '.join(pending)} pending):"
            " run `neonradar graph migrate` first"
        )


def _count(written: Counter[str], counters: SummaryCounters) -> None:
    for name in WRITE_COUNTERS:
        written[name] += getattr(counters, name)


def _write(
    driver: Driver, plan: LoadPlan, report: LoadReport, database: str, batch_size: int
) -> None:
    for schema in NODE_MAPPINGS:
        rows = [row for row in plan.nodes if row.schema == schema]
        query = node_query(schema)
        absent = dict.fromkeys(NODE_OPTIONAL[schema])
        for chunk in batched(rows, batch_size, strict=False):
            params = [{**row.as_param(), "props": {**absent, **row.props}} for row in chunk]
            _, summary, _ = driver.execute_query(query, rows=params, database_=database)
            _count(report.written, summary.counters)
            for row in chunk:
                report.nodes_by_label.update([*row.labels, *row.flags])
        if rows:
            logger.info("loaded %d %s nodes", len(rows), schema)
    for rel_type in RELATIONSHIP_TYPES:
        rel_rows = [row for row in plan.relationships if row.type == rel_type]
        if not rel_rows:
            continue
        query = relationship_query(rel_rows[0])
        rel_absent = dict.fromkeys(RELATIONSHIP_OPTIONAL[rel_type])
        for rel_chunk in batched(rel_rows, batch_size, strict=False):
            params = [{**row.as_param(), "props": {**rel_absent, **row.props}} for row in rel_chunk]
            records, summary, _ = driver.execute_query(query, rows=params, database_=database)
            _count(report.written, summary.counters)
            dangling = [
                DanglingReference(
                    rel_type,
                    record["id"],
                    record["source"],
                    record["target"],
                    record["source_missing"],
                    record["target_missing"],
                )
                for record in records
            ]
            report.dangling.extend(dangling)
            report.relationships_by_type[rel_type] += len(rel_chunk) - len(dangling)
        logger.info("loaded %d %s relationship rows", len(rel_rows), rel_type)


def load_records(
    driver: Driver,
    records: Sequence[Record],
    *,
    strict: bool = True,
    database: str = "neo4j",
    batch_size: int = BATCH_SIZE,
) -> LoadReport:
    """Load C1 records (one load) into a migrated graph.

    Raises LoadRefused (strict, nothing written) or LoadError (schema not migrated). A strict
    load with dangling references returns a report whose `failed` is true.
    """
    started = time.monotonic()
    plan = plan_load(records, strict=strict)
    require_migrated(driver, database)
    report = LoadReport(strict, records=plan.records, rejected=plan.rejected, skipped=plan.skipped)
    _write(driver, plan, report, database, batch_size)
    report.duration_s = time.monotonic() - started
    return report


def load_files(
    driver: Driver,
    paths: Iterable[Path],
    *,
    strict: bool = True,
    database: str = "neo4j",
    batch_size: int = BATCH_SIZE,
) -> LoadReport:
    """Load the record files in `paths` (files, or directories of `*.ftm.jsonl`) as one load."""
    started = time.monotonic()
    files = collect_files(paths)
    records: list[Record] = []
    empty: list[Path] = []
    for path in files:
        found = read_records([path])
        if not found:
            logger.warning("%s holds no records", path)
            empty.append(path)
        records.extend(found)
    report = load_records(driver, records, strict=strict, database=database, batch_size=batch_size)
    report.files, report.empty_files = files, empty
    report.duration_s = time.monotonic() - started
    return report


def wipe(driver: Driver, database: str = "neo4j") -> int:
    """Delete every node except `:SchemaMigration` (constraints and indexes stay); returns the
    number of nodes deleted. `IN TRANSACTIONS` needs an auto-commit `session.run()`."""
    with driver.session(database=database) as session:
        summary = session.run(WIPE).consume()
    return summary.counters.nodes_deleted


def stats(driver: Driver, database: str = "neo4j") -> GraphStats:
    """Node and relationship counts by label and type (`apoc.meta.stats()`, from the count
    store)."""
    records, _, _ = driver.execute_query(STATS, database_=database, routing_=RoutingControl.READ)
    record = records[0]
    return GraphStats(
        nodes=int(record["nodeCount"]),
        relationships=int(record["relCount"]),
        labels={str(k): int(v) for k, v in sorted(record["labels"].items())},
        relationship_types={str(k): int(v) for k, v in sorted(record["relTypesCount"].items())},
    )
