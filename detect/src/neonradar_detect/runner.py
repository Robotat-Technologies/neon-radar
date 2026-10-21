"""Detection runs (PHASE-1.md M1.9b; contracts/C4-alert.md, Runs and storage).

`run` executes the detector of every selected typology, builds the C4 alerts, and fails the
whole run if any alert breaks the contract or the wording lint. A run writes its audit copy,
`data/runs/<run_id>/alerts.jsonl` and `run.json`, and loads `(:DetectionRun)-[:PRODUCED]->
(:Alert)-[:FLAGS {role}]->(:Entity)` into Neo4j in one transaction, merged on `run_id`,
`alert_id` and the alert-subject pair, so a re-run on the same graph finds the same alerts. A
run that fails writes `run.json` and a `:DetectionRun` with `status: failed` and no alerts.
"""

import json
import logging
import re
import secrets
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from neo4j import Driver, ManagedTransaction
from neo4j.exceptions import DriverError, Neo4jError

from neonradar_contracts.alert import RUN_ID_PATTERN, Alert
from neonradar_detect.alerts import Finding, build_alert, utc_text
from neonradar_detect.catalog import REPO_ROOT, TypologyFile, load_catalog
from neonradar_detect.detectors import circular_flow

logger = logging.getLogger(__name__)

RUNS_DIR = REPO_ROOT / "data" / "runs"


class DetectorModule(Protocol):
    """A detector module (neonradar_detect.detectors)."""

    NAME: str
    VERSION: str

    def detect(self, driver: Driver, database: str, typology: TypologyFile) -> list[Finding]: ...


# The detectors a typology file may name. A fixed table, so the catalog selects code but never
# makes the runner import a module path it reads from a file.
DETECTORS: Mapping[str, DetectorModule] = {circular_flow.NAME: circular_flow}

MERGE_RUN = "MERGE (r:DetectionRun {run_id: $run.run_id}) SET r += $run"
MERGE_ALERTS = """
MATCH (r:DetectionRun {run_id: $run_id})
UNWIND $rows AS row
MERGE (a:Alert {alert_id: row.props.alert_id})
SET a += row.props
MERGE (r)-[:PRODUCED]->(a)
WITH a, row
CALL (a, row) {
  MATCH (a)-[old:FLAGS]->(e:Entity)
  WHERE NOT e.id IN [s IN row.subjects | s.entity_id]
  DELETE old
}
CALL (a, row) {
  UNWIND row.subjects AS s
  MATCH (e:Entity {id: s.entity_id})
  MERGE (a)-[f:FLAGS]->(e)
  SET f.role = s.role
  RETURN count(f) AS flagged
}
RETURN count(a) AS alerts, sum(flagged) AS flagged
"""


class RunError(RuntimeError):
    """The run could not start, or it failed (the message says why)."""


@dataclass(slots=True)
class RunReport:
    """What a run did: its id, status, times, typologies, detectors and alerts."""

    run_id: str
    directory: Path
    started_at: str
    finished_at: str = ""
    status: Literal["ok", "failed"] = "failed"
    typologies: list[str] = field(default_factory=list)
    detectors: list[dict[str, str]] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        """`run.json`: the `:DetectionRun` properties plus the alert ids and any error."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "typologies": self.typologies,
            "detectors": self.detectors,
            "alert_count": len(self.alerts),
            "alert_ids": [alert.alert_id for alert in self.alerts],
            "error": self.error,
        }

    def node_properties(self) -> dict[str, Any]:
        """The `:DetectionRun` properties (C2)."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "typologies": self.typologies,
            "detectors": json.dumps(self.detectors, separators=(",", ":")),
            "alert_count": len(self.alerts),
            "status": self.status,
        }


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_run_id(moment: datetime) -> str:
    """`run-<UTC yyyymmddThhmmss>-<4 hex>` (C4)."""
    return f"run-{moment.astimezone(UTC):%Y%m%dT%H%M%S}-{secrets.token_hex(2)}"


def select(catalog: Mapping[str, TypologyFile], slug: str | None) -> list[TypologyFile]:
    """The typologies to run: `slug`, or every typology with a detector, by slug."""
    if slug is not None:
        if slug not in catalog:
            raise RunError(f"unknown typology {slug!r}; known: {', '.join(sorted(catalog))}")
        chosen = [catalog[slug]]
        if chosen[0].detector is None:
            raise RunError(f"typology {slug} has no detector yet (detector: null)")
    else:
        chosen = [typology for _, typology in sorted(catalog.items()) if typology.detector]
    for typology in chosen:
        if typology.detector not in DETECTORS:
            raise RunError(
                f"typology {typology.slug} names an unknown detector {typology.detector}"
            )
    return chosen


def alert_row(alert: Alert) -> dict[str, Any]:
    """The `:Alert` properties (C2) and the subjects for `FLAGS`."""
    flags = alert.data_flags
    return {
        "props": {
            "alert_id": alert.alert_id,
            "typology": alert.typology,
            "typology_version": alert.typology_version,
            "priority": alert.priority,
            "pattern_strength": alert.pattern_strength,
            "headline": alert.headline,
            "created_at": alert.created_at,
            "run_id": alert.run_id,
            "wording_class": alert.wording_class,
            "involves_real_entities": flags.involves_real_entities,
            "synthetic_activity": flags.synthetic_activity,
            "payload": alert.model_dump_json(),
        },
        "subjects": [
            {"entity_id": subject.entity_id, "role": subject.role} for subject in alert.subjects
        ],
    }


def _store(tx: ManagedTransaction, run: dict[str, Any], alerts: Sequence[Alert]) -> None:
    tx.run(MERGE_RUN, run=run).consume()
    rows = [alert_row(alert) for alert in alerts]
    record = tx.run(MERGE_ALERTS, run_id=run["run_id"], rows=rows).single(strict=True)
    expected = sum(len(row["subjects"]) for row in rows)
    if record["alerts"] != len(rows) or record["flagged"] != expected:
        raise RunError(
            f"stored {record['alerts']} of {len(rows)} alerts and {record['flagged']} of "
            f"{expected} FLAGS: a subject is not an :Entity in the graph"
        )


def store(driver: Driver, database: str, report: RunReport) -> None:
    """Load the run, its alerts, `PRODUCED` and `FLAGS` in one write transaction."""
    with driver.session(database=database) as session:
        session.execute_write(_store, report.node_properties(), report.alerts)


def _write_files(report: RunReport, *, alerts: bool) -> None:
    report.directory.mkdir(parents=True, exist_ok=True)
    if alerts:
        lines = "".join(alert.model_dump_json() + "\n" for alert in report.alerts)
        (report.directory / "alerts.jsonl").write_text(lines, encoding="utf-8")
    text = json.dumps(report.as_json(), indent=2, ensure_ascii=False) + "\n"
    (report.directory / "run.json").write_text(text, encoding="utf-8")


def run(
    driver: Driver,
    database: str,
    *,
    typology: str | None = None,
    run_id: str | None = None,
    runs_dir: Path = RUNS_DIR,
    catalog: Mapping[str, TypologyFile] | None = None,
    clock: Callable[[], datetime] = now_utc,
) -> RunReport:
    """One detection run; raises `RunError` when it cannot start or when it failed."""
    selected = select(load_catalog() if catalog is None else catalog, typology)
    started = clock()
    run_id = run_id or new_run_id(started)
    if not re.fullmatch(RUN_ID_PATTERN.removeprefix("^").removesuffix("$"), run_id):
        raise RunError(f"run id {run_id!r} must look like run-20261021T101500-7f3a")
    report = RunReport(run_id=run_id, directory=runs_dir / run_id, started_at=utc_text(started))
    report.typologies = [item.slug for item in selected]
    report.detectors = [
        {
            "name": DETECTORS[str(item.detector)].NAME,
            "version": DETECTORS[str(item.detector)].VERSION,
        }
        for item in selected
    ]
    try:
        for item in selected:
            module = DETECTORS[str(item.detector)]
            findings = module.detect(driver, database, item)
            created = clock()
            for found in findings:
                report.alerts.append(
                    build_alert(
                        found,
                        item,
                        detector_name=module.NAME,
                        detector_version=module.VERSION,
                        run_id=run_id,
                        created_at=created,
                    )
                )
            logger.info("%s: %d alerts", item.slug, len(findings))
        ids = [alert.alert_id for alert in report.alerts]
        if len(set(ids)) != len(ids):
            raise RunError("a detector reported the same evidence twice (duplicate alert ids)")
        report.status = "ok"
        report.finished_at = utc_text(clock())
        _write_files(report, alerts=True)
        store(driver, database, report)
    except Exception as error:
        _fail(driver, database, report, error)
        raise RunError(f"run {run_id} failed: {error}") from error
    return report


def _store_run(tx: ManagedTransaction, run: dict[str, Any]) -> None:
    tx.run(MERGE_RUN, run=run).consume()


def _fail(driver: Driver, database: str, report: RunReport, error: Exception) -> None:
    """Record a failed run: `run.json` and a `:DetectionRun` with `status: failed`, no alerts
    (and no `alerts.jsonl`)."""
    report.status = "failed"
    report.alerts = []
    report.error = f"{type(error).__name__}: {error}"
    report.finished_at = report.finished_at or utc_text(now_utc())
    (report.directory / "alerts.jsonl").unlink(missing_ok=True)
    _write_files(report, alerts=False)
    try:
        with driver.session(database=database) as session:
            session.execute_write(_store_run, report.node_properties())
    except (DriverError, Neo4jError) as store_error:
        logger.warning("could not record the failed run %s: %s", report.run_id, store_error)
