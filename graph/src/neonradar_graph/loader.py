"""The C1 record loader: `neonradar graph load` (PHASE-1.md M1.9a; resolution-aware since M2.11,
C2 loader rules L8 to L17, contracts/C2-graph-schema.md).

1. Read every record of the load and the manifests beside its files (`collect_files`,
   `read_records`).
2. L17, before connecting: refuse (exit 2) unless every record and manifest belongs to the
   instance the load names (`neonradar_graph.instances`).
3. Validate every record against C1 (`plan_load`). A strict load refuses on any issue and writes
   nothing; a non-strict load skips each record that failed C1 and never maps it.
4. Map the rest with `neonradar_graph.mapping`, through a resolution run when one is given (L8):
   merged entities, `:SourceRecord` rows, RESOLVED_TO, re-pointed relationships and possible
   matches. A strict load also refuses on any MappingIssue.
5. L9, with a resolution run (unless `replace=False`): remove what the run replaces
   (`queries/purge_real.cypher` on the real-data instance, `queries/purge_superseded.cypher` on
   the default one) through `session.run()`, because both use `CALL { } IN TRANSACTIONS`.
6. Write entity nodes, `:SourceRecord` nodes, RESOLVED_TO, relationships (the direct query,
   then the resolving query of L13), POSSIBLY_SAME_AS, in batches of 5,000 rows with
   `UNWIND $rows AS row`, one `driver.execute_query` transaction per batch, naming the
   instance's database. Labels and types come only from `neonradar_contracts.graph`; record
   values travel only as parameters. Every query but the node upserts is a file in `queries/`.

A relationship whose ends are both nodes of this load takes the direct query; one with an end
elsewhere takes the resolving query, which finds it by id or through a `:SourceRecord` (L13)
and checks its C2 label. Both delete a relationship with the row's id between other nodes
first (its end moved) and return the rows they could not write, which the report lists as
dangling (reconciliation E4).

A reload of changed files is an upsert of what the files hold:
- properties are set again, and every mapped property the record no longer has is removed
  (sent as null); flag labels follow the record both ways;
- a relationship whose end or type changed (an Ownership between OWNS, CONSOLIDATES and
  HOLDS_ACCOUNT) is moved: the old one with the same id is deleted;
- a relationship whose new end is missing is deleted and its row reported as dangling, so the
  graph never keeps an edge the files no longer describe.
Without a resolution run, what stays until `wipe` is: records no longer in the files,
relationships from reference values a record dropped (`addressEntity` to HAS_ADDRESS,
`Sanction.entity` to SUBJECT_OF), and the schema labels of a record whose schema changed. So
invariants I1 to I5 are guaranteed after `neonradar graph wipe --yes` followed by a load. Each
batch is one transaction: a database error part-way leaves the earlier batches committed, and
running the same load again completes it (idempotent; L16 with a resolution run).
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
from pydantic import ValidationError

from neonradar_contracts.graph import (
    FLAG_LABELS,
    NODE_LABELS,
    NODE_MAPPINGS,
    REFERENCE_MAPPINGS,
    RELATIONSHIP_ENDPOINTS,
    RELATIONSHIP_MAPPINGS,
    RELATIONSHIP_TYPES,
    RESERVED_PROPERTIES,
)
from neonradar_contracts.records import (
    Manifest,
    RecordFileError,
    RecordIssue,
    iter_records,
    manifest_path,
    validate_batch,
    validate_record,
)
from neonradar_graph import cypher
from neonradar_graph.client import get_driver, wait_until_ready
from neonradar_graph.instances import Instance, InstanceRefused, check_records, for_database
from neonradar_graph.mapping import (
    MappingIssue,
    NodeRow,
    RelationshipRow,
    SupportRow,
    to_node_rows,
    to_possibly_same_as_rows,
    to_relationship_rows,
    to_resolved_to_rows,
    to_source_record_rows,
)
from neonradar_graph.migrate import MIGRATIONS_DIR, discover
from neonradar_graph.resolution import ResolutionMap, resolvable_ids

logger = logging.getLogger(__name__)

Record = dict[str, Any]
BATCH_SIZE = 5_000
RECORD_GLOB = "*.ftm.jsonl"
# Labels are written into the node query text, so they must be plain identifiers.
LABEL_RE = re.compile(r"^[A-Z][A-Za-z]*\Z")
# Every optional property each node schema and relationship type can carry. A load sends the
# absent ones as null, so `SET x += row.props` removes a property a reloaded record dropped.
NODE_OPTIONAL = {
    schema: tuple(
        dict.fromkeys(
            [
                "source_url",
                "first_seen",
                "last_seen",
                *mapping.properties.values(),
                *RESERVED_PROPERTIES.get(schema, ()),  # address_key, computed since M2.11
            ]
        )
    )
    for schema, mapping in NODE_MAPPINGS.items()
}
_ALWAYS_SET = {"id", "datasets", "synthetic", "ts"}  # PAID always has its ts
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
    """The load cannot start or must stop: no record files, an unreadable line or manifest, a
    schema not migrated, or possible matches without their nodes."""

    exit_code = 1


class SchemaNotMigrated(LoadError):
    """A migration is pending: exit 1 on the default instance (Phase 1), 2 on the real one."""

    counts_only = True

    def __init__(self, message: str, *, real: bool) -> None:
        super().__init__(message)
        self.exit_code = 2 if real else 1


class PossibleMatchesNotWritten(LoadError):
    """The possible-match query wrote fewer relationships than it was sent (L14, exit 1)."""

    counts_only = True


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
    resolution: ResolutionMap | None = None
    record_ids: list[str] = field(default_factory=list)  # entity and sanction records (L9)
    source_records: list[SupportRow] = field(default_factory=list)
    resolved_to: list[SupportRow] = field(default_factory=list)
    possible_matches: list[SupportRow] = field(default_factory=list)
    counts: Counter[str] = field(default_factory=Counter)


@dataclass(slots=True)
class LoadReport:
    """What a load did. Counts are rows written (nodes by each label they carry, relationships
    by type, dangling rows excluded); `written` holds the database's counters, which are all 0
    when the same files are loaded again without a resolution run (a resolved load first
    removes the nodes it replaces, L9)."""

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
    instance: Instance = Instance.DEFAULT
    resolution_run: str | None = None
    canonical_entities: int = 0
    merged_entities: int = 0
    source_records: int = 0
    possible_matches: int = 0
    possible_matches_outside_load: int = 0  # a canonical node of the line is not in this load
    self_loops_dropped: int = 0
    duplicate_relationships_merged: int = 0
    superseded_removed: int = 0  # every node the L9 purge removed before the load
    detection_results_removed: int = 0
    resolved_through_source_record: int = 0
    overlay_records: int = 0  # L18: the overlay's records, and the overlay nodes it replaced
    overlay_removed: int = 0

    @property
    def failed(self) -> bool:
        """A strict load fails on any dangling reference (C1 R4). Dangling rows are found while
        writing, so the rest of the load has been written by then."""
        return self.strict and bool(self.dangling)

    def counts(self) -> dict[str, Any]:
        """Counts only (no id or value): what a load on the real-data instance prints."""
        return {
            "records": self.records,
            "files": len(self.files),
            "empty_files": len(self.empty_files),
            "nodes_by_label": {k.lower(): v for k, v in sorted(self.nodes_by_label.items())},
            "relationships_by_type": {
                k.lower(): v for k, v in sorted(self.relationships_by_type.items())
            },
            "canonical_entities": self.canonical_entities,
            "merged_entities": self.merged_entities,
            "source_records": self.source_records,
            "possible_matches": self.possible_matches,
            "possible_matches_outside_load": self.possible_matches_outside_load,
            "self_loops_dropped": self.self_loops_dropped,
            "duplicate_relationships_merged": self.duplicate_relationships_merged,
            "nodes_removed_before_load": self.superseded_removed,
            "detection_results_removed": self.detection_results_removed,
            "resolved_through_source_record": self.resolved_through_source_record,
            "overlay_records": self.overlay_records,
            "overlay_nodes_removed": self.overlay_removed,
            "dangling_references": len(self.dangling),
            "records_rejected": len(self.rejected),
            "mapping_issues": len(self.skipped),
            "written": dict(sorted(self.written.items())),
            "duration_s": round(self.duration_s, 3),
        }


@dataclass(frozen=True, slots=True)
class GraphStats:
    """Node and relationship totals from `apoc.meta.stats()`."""

    nodes: int
    relationships: int
    labels: dict[str, int]
    relationship_types: dict[str, int]


@dataclass(slots=True)
class LoadInput:
    """The records of one load, read from files, with what their manifests say."""

    records: list[Record] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    empty_files: list[Path] = field(default_factory=list)
    manifests: list[bool] = field(default_factory=list)  # each manifest's `synthetic`
    retrieved_at: dict[str, str] = field(default_factory=dict)  # record id -> manifest value


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


def read_manifest(path: Path) -> Manifest | None:
    """The manifest beside a record file, if there is one (C1); one that does not validate
    stops the load (its `synthetic` flag feeds L17)."""
    try:
        found = manifest_path(path)
    except ValueError:
        return None
    if not found.is_file():
        return None
    try:
        return Manifest.model_validate_json(found.read_text(encoding="utf-8"))
    except ValidationError:
        raise LoadError(f"{found.name}: the manifest does not validate (C1)") from None


def read_input(paths: Iterable[Path]) -> LoadInput:
    """The records of `paths` (files, or directories of `*.ftm.jsonl`) and their manifests."""
    loaded = LoadInput(files=collect_files(paths))
    for path in loaded.files:
        found = read_records([path])
        if not found:
            logger.warning("%s holds no records", path)
            loaded.empty_files.append(path)
        manifest = read_manifest(path)
        if manifest is not None:
            loaded.manifests.append(manifest.synthetic)
            if manifest.source.retrieved_at is not None:
                for record in found:
                    loaded.retrieved_at[str(record.get("id"))] = manifest.source.retrieved_at
        loaded.records.extend(found)
    return loaded


def _usable(
    records: Sequence[Record], record_issues: Sequence[list[RecordIssue]]
) -> tuple[list[Record], list[RecordIssue]]:
    """Non-strict: the records that pass C1, and the issues of those left out.

    A later record with an id already seen is left out even when the first one failed C1 (a
    duplicate never replaces the first record); a BankAccount without a holder among the
    records that pass fails R8 and is left out too, even when the graph holds an owner its
    Ownership names (C1 R8: the holder is in the same load; OD-17, 2.9 J5).
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


ORPHAN = "a member of a merged entity whose node was not mapped"


def plan_load(
    records: Sequence[Record],
    *,
    strict: bool,
    resolution: ResolutionMap | None = None,
    replace: bool = True,
    retrieved_at: dict[str, str] | None = None,
) -> LoadPlan:
    """Validate (C1) and map (C2) one load without touching the database.

    Raises LoadRefused in strict mode on any C1 issue (dangling references included) or
    MappingIssue, and ResolutionError when the run does not fit the records (a load that
    replaces, `replace=True`, must hold exactly the run's resolvable records). Records that
    failed C1 are never mapped.
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
    schemas = resolvable_ids(usable)
    if resolution is not None:
        resolution.check_load(schemas, complete=replace)
    nodes = to_node_rows(usable, resolution)
    relationships = to_relationship_rows(usable, resolution, {row.id for row in nodes.rows})
    plan = LoadPlan(len(records), nodes.rows, relationships.rows, rejected, resolution=resolution)
    plan.counts.update(relationships.counts)
    plan.record_ids = [rid for rid, schema in schemas.items() if schema in NODE_MAPPINGS]
    found = [*nodes.skipped, *relationships.skipped]
    if resolution is not None:
        loaded = {row.id: row for row in nodes.rows}
        sources = to_source_record_rows(usable, resolution, retrieved_at)
        # a member of a merged entity whose node was skipped would have no RESOLVED_TO (I7)
        orphans = {r.keys["id"] for r in sources.rows if r.props["canonical_id"] not in loaded}
        found.extend(MappingIssue(rid, ORPHAN) for rid in sorted(orphans))
        plan.source_records = [r for r in sources.rows if r.keys["id"] not in orphans]
        possible = to_possibly_same_as_rows(resolution, loaded)
        plan.possible_matches = possible.rows
        plan.counts["possible_matches_outside_load"] = possible.counts["outside_this_load"]
        record_ids = {row.keys["id"] for row in plan.source_records}
        plan.resolved_to = to_resolved_to_rows(resolution, record_ids)
        found.extend([*sources.skipped, *possible.skipped])
    plan.skipped = list(dict.fromkeys(found))
    if strict and plan.skipped:
        raise LoadRefused([], plan.skipped)
    if not strict:  # an account whose holding Ownership was skipped would break invariant I4
        held = {row.target for row in plan.relationships if row.type == "HOLDS_ACCOUNT"}
        unheld = {row.id for row in plan.nodes if "Account" in row.labels and row.id not in held}
        message = "BankAccount has no HOLDS_ACCOUNT after mapping (its Ownership was skipped)"
        rejected.extend(RecordIssue("R8", rid, message) for rid in sorted(unheld))
        plan.nodes = [row for row in plan.nodes if row.id not in unheld]
    return plan


def _label(name: str) -> str:
    if not LABEL_RE.fullmatch(name) or name not in (*NODE_LABELS, *FLAG_LABELS):
        raise ValueError(f"{name!r} is not a label name of C2")
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


def require_migrated(driver: Driver, database: str, directory: Path = MIGRATIONS_DIR) -> None:
    """Raise SchemaNotMigrated while a schema migration is pending: the loader relies on its
    uniqueness constraints (MERGE on `id`). Exit 2 on the real-data instance."""
    with driver.session(database=database, notifications_min_severity="OFF") as session:
        applied = {str(record["id"]) for record in session.run(APPLIED)}
    pending = [migration.id for migration in discover(directory) if migration.id not in applied]
    if pending:
        real = for_database(database) is Instance.REAL
        command = "neonradar graph migrate" + (" --real" if real else "")
        raise SchemaNotMigrated(
            f"the graph schema is not migrated ({', '.join(pending)} pending):"
            f" run `{command}` first",
            real=real,
        )


def _count(written: Counter[str], counters: SummaryCounters) -> None:
    for name in WRITE_COUNTERS:
        written[name] += getattr(counters, name)


def _run(driver: Driver, query: str, database: str, report: LoadReport, **params: Any) -> list[Any]:
    records, summary, _ = driver.execute_query(query, params, database_=database)
    _count(report.written, summary.counters)
    return list(records)


def _purge(driver: Driver, plan: LoadPlan, database: str, report: LoadReport) -> None:
    """L9: remove what a resolved load replaces, then every detection result."""
    real = for_database(database) is Instance.REAL
    entities, detections = cypher.statements(
        "purge_real.cypher" if real else "purge_superseded.cypher"
    )
    params = {} if real else {"record_ids": plan.record_ids}
    with driver.session(database=database) as session:
        report.superseded_removed = session.run(entities, params).consume().counters.nodes_deleted
        removed = session.run(detections).consume().counters.nodes_deleted
        report.detection_results_removed = removed


def _write_nodes(
    driver: Driver, plan: LoadPlan, report: LoadReport, database: str, batch_size: int
) -> None:
    for schema in NODE_MAPPINGS:
        rows = [row for row in plan.nodes if row.schema == schema]
        query = node_query(schema)
        absent = dict.fromkeys(NODE_OPTIONAL[schema])
        for chunk in batched(rows, batch_size, strict=False):
            params = [{**row.as_param(), "props": {**absent, **row.props}} for row in chunk]
            _run(driver, query, database, report, rows=params)
            for row in chunk:
                report.nodes_by_label.update([*row.labels, *row.flags])
        if rows:
            logger.info("loaded %d %s nodes", len(rows), schema)
    entities = [row for row in plan.nodes if row.labels[0] == "Entity"]
    report.canonical_entities = len(entities)
    report.merged_entities = sum(row.props.get("cluster_size", 1) >= 2 for row in entities)


def _write_support(
    driver: Driver,
    name: str,
    rows: Sequence[SupportRow],
    report: LoadReport,
    database: str,
    batch_size: int,
) -> None:
    query = cypher.query(name)
    for chunk in batched(rows, batch_size, strict=False):
        _run(driver, query, database, report, rows=[row.as_param() for row in chunk])


def _dangling(row: RelationshipRow, found: Any) -> DanglingReference:
    return DanglingReference(
        row.type,
        row.id,
        row.source,
        row.target,
        bool(found["source_missing"]),
        bool(found["target_missing"]),
    )


def _write_type(
    driver: Driver,
    rel_type: str,
    rows: Sequence[RelationshipRow],
    report: LoadReport,
    database: str,
    batch_size: int,
) -> None:
    """The rows of one relationship type: moves from sibling types, then the direct and the
    resolving query (reconciliation E4)."""
    by_id = {row.id: row for row in rows}
    for other in SIBLING_TYPES.get(rel_type, ()):
        delete = cypher.query("delete_relationships.cypher", rel_type=other)
        for ids in batched(by_id, batch_size, strict=False):
            _run(driver, delete, database, report, ids=list(ids))
    absent = dict.fromkeys(RELATIONSHIP_OPTIONAL[rel_type])
    direct = cypher.query(
        "upsert_relationships.cypher", rel_type=rel_type, target_label=rows[0].endpoint_keys[1]
    )
    resolving = cypher.query("upsert_relationships_resolving.cypher", rel_type=rel_type)
    source_label, target_label = RELATIONSHIP_ENDPOINTS[rel_type]
    labels = {"source": source_label, "target": target_label}
    for is_resolving in (False, True):
        chosen = [row for row in rows if row.resolving is is_resolving]
        for chunk in batched(chosen, batch_size, strict=False):
            params = [{**row.as_param(), "props": {**absent, **row.props}} for row in chunk]
            if not is_resolving:
                missing = _run(driver, direct, database, report, rows=params)
                report.dangling.extend(_dangling(by_id[found["id"]], found) for found in missing)
                report.relationships_by_type[rel_type] += len(chunk) - len(missing)
                continue
            for found in _run(driver, resolving, database, report, rows=params, labels=labels):
                if found["source_missing"] or found["target_missing"]:
                    report.dangling.append(_dangling(by_id[found["id"]], found))
                elif found["self_loop"]:
                    report.self_loops_dropped += 1
                else:
                    report.relationships_by_type[rel_type] += 1
                    report.resolved_through_source_record += found["s_via"] + found["t_via"]
    logger.info("loaded %d %s relationship rows", len(rows), rel_type)


def _write_possible_matches(
    driver: Driver, plan: LoadPlan, report: LoadReport, database: str, batch_size: int
) -> None:
    query = cypher.query("upsert_possibly_same_as.cypher")
    for chunk in batched(plan.possible_matches, batch_size, strict=False):
        found = _run(driver, query, database, report, rows=[row.as_param() for row in chunk])
        written = int(found[0]["written"]) if found else 0
        report.possible_matches += written
        if written != len(chunk):
            raise PossibleMatchesNotWritten(
                f"{len(chunk) - written} of {len(chunk)} possible matches (not confirmed) found"
                " no two :LegalEntity nodes (L14); the rest of the load was written"
            )


def check_rows(plan: LoadPlan, database: str, *, overlay: bool = False) -> None:
    """L17 on the rows themselves: every row's `synthetic` flag belongs to the database's
    instance. The default instance always takes synthetic rows only; an overlay load (L18,
    `neonradar_graph.overlay`) is the one exception, synthetic rows on the real-data instance."""
    synthetic = True if overlay else for_database(database) is Instance.DEFAULT
    written: list[NodeRow | RelationshipRow | SupportRow] = [
        *plan.nodes, *plan.relationships, *plan.source_records, *plan.possible_matches
    ]  # fmt: skip
    wrong = sum(row.props.get("synthetic") is not synthetic for row in written)
    if wrong:
        raise InstanceRefused(
            f"{wrong} row(s) of this load do not belong to the {for_database(database)} instance"
            " (C2 L17); nothing was written"
        )


def execute_plan(
    driver: Driver,
    plan: LoadPlan,
    report: LoadReport,
    *,
    database: str,
    replace: bool = True,
    batch_size: int = BATCH_SIZE,
    overlay: bool = False,
) -> LoadReport:
    """Write a plan into a migrated graph: purge (L9), nodes, source records, RESOLVED_TO,
    relationships, possible matches. L17 is checked again on the rows themselves
    (`check_rows`), so no path writes a row whose `synthetic` flag does not belong to the
    database's instance; only `overlay=True` (L18) lets synthetic rows onto the real one."""
    check_rows(plan, database, overlay=overlay)
    require_migrated(driver, database)
    report.records, report.rejected, report.skipped = plan.records, plan.rejected, plan.skipped
    report.instance = for_database(database)
    report.self_loops_dropped = plan.counts["self_loops_dropped"]
    report.duplicate_relationships_merged = plan.counts["duplicate_relationships_merged"]
    report.possible_matches_outside_load = plan.counts["possible_matches_outside_load"]
    if plan.resolution is not None:
        report.resolution_run = plan.resolution.run_id
        if replace:
            _purge(driver, plan, database, report)
    _write_nodes(driver, plan, report, database, batch_size)
    _write_support(
        driver, "upsert_source_records.cypher", plan.source_records, report, database, batch_size
    )
    report.source_records = len(plan.source_records)
    _write_support(
        driver, "upsert_resolved_to.cypher", plan.resolved_to, report, database, batch_size
    )
    for rel_type in RELATIONSHIP_TYPES:
        rows = [row for row in plan.relationships if row.type == rel_type]
        if rows:
            _write_type(driver, rel_type, rows, report, database, batch_size)
    _write_possible_matches(driver, plan, report, database, batch_size)
    return report


def _resolution(resolution: Path | ResolutionMap | None) -> ResolutionMap | None:
    return ResolutionMap.load(resolution) if isinstance(resolution, Path) else resolution


def _prepare(
    loaded: LoadInput,
    instance: Instance,
    *,
    strict: bool,
    resolution: Path | ResolutionMap | None,
    replace: bool,
) -> LoadPlan:
    """Everything before the database: L17, the resolution run, C1 and the mapping."""
    check_records(loaded.records, instance, loaded.manifests)
    run = _resolution(resolution)
    return plan_load(
        loaded.records,
        strict=strict,
        resolution=run,
        replace=replace,
        retrieved_at=loaded.retrieved_at,
    )


def _report(strict: bool, loaded: LoadInput) -> LoadReport:
    return LoadReport(strict, files=loaded.files, empty_files=loaded.empty_files)


def load_records(
    driver: Driver,
    records: Sequence[Record],
    *,
    strict: bool = True,
    database: str = "neo4j",
    batch_size: int = BATCH_SIZE,
    resolution: Path | ResolutionMap | None = None,
    replace: bool = True,
) -> LoadReport:
    """Load C1 records (one load) into a migrated graph; L17 follows `database`.

    Raises InstanceRefused (L17), LoadRefused (strict, nothing written), ResolutionError or
    LoadError (for example a schema not migrated). A strict load with dangling references
    returns a report whose `failed` is true.
    """
    started = time.monotonic()
    loaded = LoadInput(records=list(records))
    plan = _prepare(
        loaded, for_database(database), strict=strict, resolution=resolution, replace=replace
    )
    report = execute_plan(
        driver, plan, _report(strict, loaded), database=database, replace=replace,
        batch_size=batch_size,
    )  # fmt: skip
    report.duration_s = time.monotonic() - started
    return report


def load_files(
    driver: Driver,
    paths: Iterable[Path],
    *,
    strict: bool = True,
    database: str = "neo4j",
    batch_size: int = BATCH_SIZE,
    resolution: Path | ResolutionMap | None = None,
    replace: bool = True,
) -> LoadReport:
    """Load the record files in `paths` (files, or directories of `*.ftm.jsonl`) as one load."""
    started = time.monotonic()
    loaded = read_input(paths)
    plan = _prepare(
        loaded, for_database(database), strict=strict, resolution=resolution, replace=replace
    )
    report = execute_plan(
        driver, plan, _report(strict, loaded), database=database, replace=replace,
        batch_size=batch_size,
    )  # fmt: skip
    report.duration_s = time.monotonic() - started
    return report


def load(
    paths: Iterable[Path],
    resolution: Path | ResolutionMap | None = None,
    replace: bool = True,
    instance: Instance = Instance.DEFAULT,
    *,
    strict: bool = True,
    driver: Driver | None = None,
    batch_size: int = BATCH_SIZE,
    timeout_s: float = 30.0,
) -> LoadReport:
    """Load record files into an instance (PHASE-2.md M2.11 deliverable 4).

    Before connecting: L17 (InstanceRefused, exit 2), the resolution run (ResolutionError) and
    the C1 and mapping checks (LoadRefused). Then it connects to the instance (or uses
    `driver`, which it does not close), naming the instance's database in every query.
    """
    started = time.monotonic()
    loaded = read_input(paths)
    plan = _prepare(loaded, instance, strict=strict, resolution=resolution, replace=replace)
    database = instance.database
    report = _report(strict, loaded)
    if driver is not None:
        execute_plan(driver, plan, report, database=database, replace=replace,
                     batch_size=batch_size)  # fmt: skip
    else:
        with get_driver(instance.settings()) as owned:
            wait_until_ready(owned, timeout_s=timeout_s)
            execute_plan(owned, plan, report, database=database, replace=replace,
                         batch_size=batch_size)  # fmt: skip
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
