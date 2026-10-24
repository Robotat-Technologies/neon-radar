"""Detection runs: the run folder and the detection store (PHASE-3.md M3.2 deliverable 5; C2 L19).

`runner.run_detection` (verbatim) finds and builds the alerts and never writes. This module does
what a run does around it, as Phase 1's runner did (PHASE-1.md M1.9b), with Phase 3's additions:

1. Every alert is validated with C4's `Alert` before anything is written; a failure names the
   alert's typology and the fields, never their values. C4's model checks the ends of composite
   evidence edges only, so the run checks that both ends of every plain-id evidence edge are
   evidence nodes (C4 `evidence`, as Phase 1's builder did), naming the typology and a count.
2. The run folder: `alerts.jsonl` (one alert per line, sorted keys), `summary.json` (the runner's
   counts-only summary) and `run.json` (Phase 1's fields plus `profile`, `params_sha256`,
   `window`, `engine` and, by reconciliation A1, the SHA-256 of each detector's query files);
   last, `LATEST` in the folder above it. A graph with no window to read records none: no
   `window` in `run.json` or on the `:DetectionRun`, and `window: null` in the summary.
3. On Neo4j, the L19 load in one write transaction: every earlier `:Alert` and `:DetectionRun`
   is deleted (unless `keep_previous`), then the run, its alerts with their evidence lists,
   `PRODUCED` and `FLAGS` are merged.

A run that fails writes `run.json` with `status: failed` and no `alerts.jsonl`, and records a
failed `:DetectionRun` with no alerts, as Phase 1 did, without the L19 delete: a failed run has
no results to replace the earlier ones with, so it never wipes them (orchestrator decision under
OD-10, phase-3 reconciliation section 9). The one exception: a failed run given an earlier run's
id (`--run-id`) replaces that run, its folder and its `PRODUCED` alerts, as Phase 1 did.
Every alert's `detector.query_sha256` is the SHA-256 of its evidence query,
`queries/evidence.cypher`, as C4 1.0.0 requires (A1).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import partial
from importlib import resources
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import neo4j
from neo4j import Driver, ManagedTransaction
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_contracts.alert import RUN_ID_PATTERN, Alert, query_sha256
from neonradar_detect import alerts, policy, runner
from neonradar_detect.catalog import REPO_ROOT, Typology
from neonradar_detect.source import Source, Window
from neonradar_detect.wording import WordingError

logger = logging.getLogger(__name__)

RUNS_DIR = REPO_ROOT / "data" / "runs"
LATEST = "LATEST"
DEMO_MINI = REPO_ROOT / "data" / "fixtures" / "demo-mini"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
EVIDENCE_SHA256 = query_sha256(alerts.EVIDENCE_QUERY)
Engine = Literal["neo4j", "memory"]


class RunError(RuntimeError):
    """The run could not start, or it failed (the message says why, never with alert text)."""


def _store_text(name: str) -> str:
    return (
        resources.files("neonradar_detect.store")
        .joinpath(f"{name}.cypher")
        .read_text(encoding="utf-8")
    )


def _query_file(name: str) -> str:
    return resources.files("neonradar_detect.queries").joinpath(name).read_text(encoding="utf-8")


def utc_text(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_run_id(moment: datetime) -> str:
    """`run-<UTC yyyymmddThhmmss>-<4 hex>` (C4)."""
    return f"run-{moment.astimezone(UTC):%Y%m%dT%H%M%S}-{secrets.token_hex(2)}"


def check_run_id(run_id: str) -> str:
    """The C4 run id form, ASCII digits only (`\\d` would accept other scripts' digits)."""
    if not re.fullmatch(RUN_ID_PATTERN.removeprefix("^").removesuffix("$"), run_id, re.ASCII):
        raise RunError(f"run id {run_id!r} must look like run-20261021T101500-7f3a")
    return run_id


def queries_sha256(module: ModuleType) -> str:
    """The SHA-256 of the texts of a detector's `QUERIES` files, in order, joined with a newline
    (M3.2 deliverable 5); recorded in `run.json` (reconciliation A1)."""
    text = "\n".join(_query_file(name) for name in module.QUERIES)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# windows -------------------------------------------------------------------------------------


def parse_moment(text: str) -> datetime:
    """A UTC date (`2026-01-01`) or time (`2026-01-01T00:00:00Z`) from the command line."""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text, re.ASCII):
            return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text, re.ASCII):
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        pass
    raise RunError(f"{text!r} is not a UTC date (2026-01-01) or time (2026-01-01T00:00:00Z)")


def window_of(start: str, end: str) -> Window:
    try:
        return Window(parse_moment(start), parse_moment(end))
    except ValueError as error:
        raise RunError(f"--window: {error}") from None


def day_window(first: datetime, last: datetime) -> Window:
    """The whole UTC days from the first payment to the last: [first day, day after the last)."""
    start = datetime.combine(first.astimezone(UTC).date(), datetime.min.time(), UTC)
    end = datetime.combine(last.astimezone(UTC).date(), datetime.min.time(), UTC)
    return Window(start, end + timedelta(days=1))


def data_window(source: Source, now: datetime | None = None) -> tuple[Window, bool]:
    """The PAID time range in whole days, and True; on a graph without payments (registry
    only), the time up to `now` and False, so the run records no window (C2 1.2.0)."""
    found = source.paid_time_range()
    if found is None:
        return Window(EPOCH, (now or now_utc()).replace(microsecond=0)), False
    return day_window(*found), True


def overlay_window(overlay_json: Path) -> Window:
    """The period an overlay was generated for (`overlay.json`: dates, end exclusive)."""
    try:
        period = json.loads(overlay_json.read_text(encoding="utf-8"))["period"]
        return window_of(str(period["start"]), str(period["end"]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RunError(f"cannot read the overlay period from {overlay_json}: {error}") from None


def records_in(folders: Iterable[Path]) -> list[dict[str, Any]]:
    """Every record of the `*.ftm.jsonl` files in `folders` (not their subfolders), in order."""
    out: list[dict[str, Any]] = []
    for folder in folders:
        files = sorted(folder.glob("*.ftm.jsonl")) if folder.is_dir() else [folder]
        for path in files:
            with path.open(encoding="utf-8") as lines:
                out.extend(json.loads(line) for line in lines if line.strip())
    return out


# the run record ------------------------------------------------------------------------------


@dataclass(slots=True)
class RunRecord:
    """What a run did. `run.json` is `as_json()`; the `:DetectionRun` is `node_properties()`."""

    run_id: str
    directory: Path
    started_at: str
    engine: Engine
    profile: str | None = None
    window: Window | None = None  # None: the graph had no window to read
    finished_at: str = ""
    status: Literal["ok", "failed"] = "failed"
    typologies: list[str] = field(default_factory=list)
    detectors: list[dict[str, str]] = field(default_factory=list)
    queries_sha256: dict[str, str] = field(default_factory=dict)
    params_sha256: str | None = None
    alerts: list[Alert] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def _window(self) -> dict[str, str] | None:
        if self.window is None:
            return None
        return {"start": utc_text(self.window.start), "end": utc_text(self.window.end)}

    def as_json(self) -> dict[str, Any]:
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
            "profile": self.profile,
            "params_sha256": self.params_sha256,
            "window": self._window(),
            "engine": self.engine,
            "queries_sha256": self.queries_sha256,
        }

    def node_properties(self) -> dict[str, Any]:
        """The `:DetectionRun` properties (C2 1.0.0 and 1.2.0; null leaves one absent)."""
        window = self._window()
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "typologies": self.typologies,
            "detectors": json.dumps(self.detectors, separators=(",", ":")),
            "alert_count": len(self.alerts),
            "status": self.status,
            "profile": self.profile,
            "params_sha256": self.params_sha256 if self.status == "ok" else None,
            "summary": json.dumps(self.summary or empty_summary(self.run_id), sort_keys=True),
            "window_start": window["start"] if window else None,
            "window_end": window["end"] if window else None,
        }


def empty_summary(run_id: str) -> dict[str, Any]:
    """The summary of a run that produced nothing (a failed run): the runner's shape, zero."""
    zero = {d.value: 0 for d in policy.Decision if d is not policy.Decision.EMIT}
    return {"run_id": run_id, "typologies": {}, "alerts": 0, "withheld": zero}


def alert_row(alert: Alert) -> dict[str, Any]:
    """The `:Alert` properties (C2 1.0.0 and 1.2.0) and the subjects for `FLAGS`."""
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
            "evidence_node_ids": list(alert.evidence.node_ids),
            "evidence_edge_ids": list(alert.evidence.edge_ids),
        },
        "subjects": [
            {"entity_id": subject.entity_id, "role": subject.role} for subject in alert.subjects
        ],
    }


def _fields(error: ValidationError) -> str:
    """The field paths a validation error names, never the values."""
    paths = {".".join(str(p) for p in e["loc"]) or "(alert)" for e in error.errors()}
    return ", ".join(sorted(paths))


def validate(built: list[dict[str, Any]]) -> list[Alert]:
    """Every alert against C4; a failure names the typology and the fields, never values."""
    out = []
    for item in built:
        try:
            out.append(Alert.model_validate(item))
        except ValidationError as error:
            typology = item.get("typology", "?")
            raise RunError(
                f"a {typology} alert does not validate against C4: {_fields(error)}"
            ) from None
    return out


def check_edge_ends(source: Source, found: list[Alert]) -> None:
    """C4: both ends of every evidence edge are evidence nodes. The model checks composite ids
    (`a|addr|b`, `a|sanction|b`); for plain ids the detector side checks it (C4 `evidence`,
    PHASE-1.md M1.9b), here from the source's `edge_info`. A plain id the source does not know
    cannot be checked and fails too. The error names the typologies and counts, never an id."""
    plain = sorted({e for alert in found for e in alert.evidence.edge_ids if "|" not in e})
    edges = source.edge_info(plain) if plain else {}
    bad: Counter[str] = Counter()
    for alert in found:
        nodes = set(alert.evidence.node_ids)
        ends = [edges.get(e) for e in alert.evidence.edge_ids if "|" not in e]
        if any(info is None or not {info.source, info.target} <= nodes for info in ends):
            bad[alert.typology] += 1
    if bad:
        counts = ", ".join(f"{slug} {n}" for slug, n in sorted(bad.items()))
        raise RunError(
            "alerts with an evidence relationship that does not end at two of their evidence"
            f" nodes (C4), by typology: {counts}"
        )


# the run folder ------------------------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    partial = path.with_name(path.name + ".tmp")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)


def write_folder(record: RunRecord) -> None:
    """`alerts.jsonl`, `summary.json`, `run.json`, then `LATEST` in the folder above."""
    record.directory.mkdir(parents=True, exist_ok=True)
    if record.status == "ok":
        lines = "".join(
            json.dumps(alert.model_dump(mode="json"), sort_keys=True, ensure_ascii=False) + "\n"
            for alert in record.alerts
        )
        _write(record.directory / "alerts.jsonl", lines)
        _write(
            record.directory / "summary.json", json.dumps(record.summary, indent=2, sort_keys=True)
        )
    else:
        (record.directory / "alerts.jsonl").unlink(missing_ok=True)
        (record.directory / "summary.json").unlink(missing_ok=True)
    _write(
        record.directory / "run.json",
        json.dumps(record.as_json(), indent=2, ensure_ascii=False) + "\n",
    )
    _write(record.directory.parent / LATEST, record.run_id + "\n")


def latest(runs_dir: Path | None = None) -> str:
    """The run id in `LATEST` of the runs folder (written last by every run)."""
    runs_dir = runs_dir or RUNS_DIR
    try:
        run_id = (runs_dir / LATEST).read_text(encoding="utf-8").strip()
    except OSError:
        raise RunError(f"no {runs_dir / LATEST}: run `neonradar detect run` first") from None
    return check_run_id(run_id)


def read_run(run_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    path = (runs_dir or RUNS_DIR) / check_run_id(run_id) / "run.json"
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RunError(f"cannot read {path}: {error}") from None
    return data


# the detection store (C2 L19) ----------------------------------------------------------------


def _store(
    tx: ManagedTransaction, run: dict[str, Any], found: list[Alert], keep_previous: bool
) -> None:
    if not keep_previous:
        tx.run(_store_text("delete_detections")).consume()
    tx.run(_store_text("merge_run"), run=run).consume()
    ids = [alert.alert_id for alert in found]
    tx.run(_store_text("prune_run"), run_id=run["run_id"], alert_ids=ids).consume()
    rows = [alert_row(alert) for alert in found]
    record = tx.run(_store_text("merge_alerts"), run_id=run["run_id"], rows=rows).single(
        strict=True
    )
    expected = sum(len(row["subjects"]) for row in rows)
    if record["alerts"] != len(rows) or record["flagged"] != expected:
        raise RunError(
            f"stored {record['alerts']} of {len(rows)} alerts and {record['flagged']} of "
            f"{expected} FLAGS: a subject is not an :Entity in the graph"
        )


def store(driver: Driver, database: str, record: RunRecord, *, keep_previous: bool) -> None:
    """The L19 load of one run, in one write transaction. A failed run records its failed
    `:DetectionRun` and deletes nothing: the earlier results stay (OD-10, see the module),
    except a failed run given an earlier run's id, which replaces that run (F11)."""
    ok = record.status == "ok"
    with driver.session(database=database) as session:
        session.execute_write(
            _store,
            record.node_properties(),
            record.alerts if ok else [],
            keep_previous or not ok,
        )


# a run ---------------------------------------------------------------------------------------


def _error_text(error: Exception) -> str:
    if isinstance(error, RunError | WordingError):
        return str(error)
    return f"{type(error).__name__}: {error}"


def run(
    source: Source,
    params: Mapping[str, Any],
    window: Window,
    catalog: Mapping[str, Typology],
    *,
    run_id: str,
    engine: Engine,
    runs_dir: Path | None = None,
    profile: str | None = None,
    window_known: bool = True,
    real_registry_alerts: bool = False,
    clock: Callable[[], datetime] = now_utc,
    load: Callable[[RunRecord], None] | None = None,
) -> RunRecord:
    """One detection run of the typologies in `params`; `load` is the L19 store (Neo4j engine).
    Raises RunError when the run failed, after recording the failure."""
    started = clock()
    check_run_id(run_id)
    record = RunRecord(
        run_id,
        (runs_dir or RUNS_DIR) / run_id,
        utc_text(started),
        engine,
        profile,
        window if window_known else None,
    )
    modules = {s: m for s, m in runner.detectors(catalog).items() if s in params}
    record.typologies = list(modules)
    record.detectors = [{"name": m.__name__, "version": m.VERSION} for m in modules.values()]
    record.queries_sha256 = {slug: queries_sha256(m) for slug, m in modules.items()}
    record.params_sha256 = runner.params_sha256(params)
    try:
        result = runner.run_detection(
            source,
            params,
            window,
            catalog,
            run_id=run_id,
            created_at=started,
            query_sha256={slug: EVIDENCE_SHA256 for slug in modules},
            real_registry_alerts=real_registry_alerts,
        )
        record.alerts = validate(result.alerts)
        check_edge_ends(source, record.alerts)
        # The runner's summary carries the span it ran over; without a window to read (no
        # PAID) that is a stand-in, and the run records no window (C2 1.2.0).
        record.summary = result.summary if window_known else {**result.summary, "window": None}
        record.status = "ok"
        record.finished_at = utc_text(clock())
        write_folder(record)
        if load is not None:
            load(record)
    except Exception as error:
        _fail(record, error, clock(), load)
        raise RunError(f"run {run_id} failed: {_error_text(error)}") from error
    return record


def _fail(
    record: RunRecord, error: Exception, now: datetime, load: Callable[[RunRecord], None] | None
) -> None:
    record.status = "failed"
    record.alerts = []
    record.summary = {}
    record.error = _error_text(error)
    record.finished_at = record.finished_at or utc_text(now)
    try:
        write_folder(record)
    except OSError as write_error:
        logger.warning(
            "could not write run.json for the failed run %s: %s", record.run_id, write_error
        )
    if load is not None:
        try:
            load(record)
        except (DriverError, Neo4jError, RunError) as store_error:
            logger.warning("could not record the failed run %s: %s", record.run_id, store_error)


def detect_on_graph(
    driver: Driver,
    database: str,
    *,
    typologies: Iterable[str] | None = None,
    run_id: str | None = None,
    runs_dir: Path | None = None,
    keep_previous: bool = False,
    real_registry_alerts: bool = False,
    timeout_s: float = 600.0,
) -> RunRecord:
    """A run on Neo4j with the catalog's defaults over the PAID time range, then the L19 load:
    what `neonradar detect run` does without a profile, with Phase 1's call shape (tests)."""
    from neonradar_detect import catalog
    from neonradar_detect.neo4jsource import Neo4jSource

    cat = catalog.load()
    chosen = set(typologies) if typologies is not None else None
    params = {
        slug: catalog.params_for(cat[slug], module)
        for slug, module in runner.detectors(cat).items()
        if chosen is None or slug in chosen
    }
    source = Neo4jSource(driver, database, timeout_s=timeout_s)
    window, known = data_window(source)
    return run(
        source,
        params,
        window,
        cat,
        run_id=run_id or new_run_id(now_utc()),
        engine="neo4j",
        runs_dir=runs_dir,
        window_known=known,
        real_registry_alerts=real_registry_alerts,
        load=partial(store, driver, database, keep_previous=keep_previous),
    )


# verify-alert ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Check:
    alert_id: str
    nodes: int
    edges: int
    missing_nodes: int
    missing_edges: int
    own_query: bool  # the payload's evidence query is queries/evidence.cypher

    @property
    def ok(self) -> bool:
        return self.own_query and not self.missing_nodes and not self.missing_edges


def _read(
    driver: Driver, database: str, text: str, timeout_s: float, **params: Any
) -> list[dict[str, Any]]:
    with driver.session(database=database, default_access_mode=neo4j.READ_ACCESS) as session:
        result = session.run(neo4j.Query(text, timeout=timeout_s), params)
        return [row.data() for row in result]


def run_alert_ids(
    driver: Driver, database: str, run_id: str, timeout_s: float = 600.0
) -> list[str]:
    rows = _read(driver, database, _store_text("run_alert_ids"), timeout_s, run_id=run_id)
    return [str(row["alert_id"]) for row in rows]


def verify(
    driver: Driver, database: str, alert_ids: list[str], timeout_s: float = 600.0
) -> Iterator[Check]:
    """For each alert: its stored payload, then the committed evidence query with its ids; every
    evidence node and relationship must come back. A payload whose query is not the committed
    `queries/evidence.cypher` fails without running anything from it."""
    rows = _read(
        driver, database, _store_text("alert_payloads"), timeout_s, alert_ids=sorted(set(alert_ids))
    )
    found = {str(row["alert_id"]): str(row["payload"]) for row in rows}
    missing = sorted(set(alert_ids) - set(found))
    if missing:
        raise RunError(f"{len(missing)} alert id(s) are not in the graph")
    for alert_id in sorted(found):
        try:
            alert = Alert.model_validate_json(found[alert_id])
        except ValidationError as error:  # the fields, never the stored values
            raise RunError(
                f"alert {alert_id}: the stored payload does not validate against C4:"
                f" {_fields(error)}"
            ) from None
        evidence = alert.evidence
        own = evidence.query.cypher == alerts.EVIDENCE_QUERY
        back: dict[str, Any] = {"node_ids": [], "edge_ids": []}
        if own:
            [back] = _read(
                driver,
                database,
                alerts.EVIDENCE_QUERY,
                timeout_s,
                node_ids=list(evidence.node_ids),
                edge_ids=list(evidence.edge_ids),
            )
        yield Check(
            alert_id,
            len(evidence.node_ids),
            len(evidence.edge_ids),
            len(set(evidence.node_ids) - set(back["node_ids"])),
            len(set(evidence.edge_ids) - set(back["edge_ids"])),
            own,
        )
