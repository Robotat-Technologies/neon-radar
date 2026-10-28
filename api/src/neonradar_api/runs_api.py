"""Detection runs (PHASE-4.md 5.3): `GET /runs` and `GET /runs/{run_id}`.

PHASE-3.md left the run summary for Phase 4's complete API. A run is the `:DetectionRun` node the
detection load writes (C2 1.2.0, L19), and its summary holds counts only on every profile, so these
routes are safe on the real-data instance too. Both queries run through the read helper, and
database errors become the copilot routes' fixed problems (`copilot_api.read_errors`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi import Path as PathParam
from neo4j import Driver
from neonradar_contracts.api import (
    DetectorVersion,
    Problem,
    RunDetail,
    RunSummary,
    TypologyRunCounts,
)
from neonradar_graph.readonly import run_read

from neonradar_api.copilot_api import read_errors

router = APIRouter(tags=["runs"])
QUERIES = Path(__file__).parent / "queries"
RUNS_LIMIT = 50
RUN_ID = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$"


def _text(name: str) -> str:
    return (QUERIES / f"{name}.cypher").read_text(encoding="utf-8")


def _iso(value: Any) -> str | None:
    """A stored moment as a UTC ISO string, whether the run node holds a string (Phase 3 writes
    strings) or a Neo4j temporal value."""
    if value is None or isinstance(value, str):
        return value
    to_native = getattr(value, "to_native", None)
    moment = to_native() if callable(to_native) else value
    if isinstance(moment, datetime):
        moment = moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(moment)


def summary_of(row: dict[str, Any]) -> RunSummary:
    detectors = json.loads(row["detectors"]) if row.get("detectors") else []
    return RunSummary(
        run_id=row["run_id"],
        status=row.get("status") or "ok",
        started_at=_iso(row.get("started_at")),
        finished_at=_iso(row.get("finished_at")),
        profile=row.get("profile"),
        window_start=_iso(row.get("window_start")),
        window_end=_iso(row.get("window_end")),
        typologies=list(row.get("typologies") or []),
        detectors=[DetectorVersion(name=d["name"], version=d["version"]) for d in detectors],
        alert_count=int(row.get("alert_count") or 0),
        params_sha256=row.get("params_sha256"),
    )


def detail_of(row: dict[str, Any]) -> RunDetail:
    summary = json.loads(row["summary"]) if row.get("summary") else {}
    return RunDetail(
        run=summary_of(row),
        typologies={
            slug: TypologyRunCounts(
                findings=int(c.get("findings", 0)),
                alerts=int(c.get("alerts", 0)),
                duplicates=int(c.get("duplicates", 0)),
                withheld={k: int(v) for k, v in (c.get("withheld") or {}).items()},
                stats=dict(c.get("stats") or {}),
            )
            for slug, c in sorted((summary.get("typologies") or {}).items())
        },
        alerts=int(summary.get("alerts", row.get("alert_count") or 0)),
        withheld={k: int(v) for k, v in (summary.get("withheld") or {}).items()},
    )


@dataclass
class RunsService:
    driver: Driver
    database: str | None = None

    def list(self) -> list[RunSummary]:
        result = run_read(
            self.driver,
            "api/runs_list",
            _text("runs_list"),
            {"limit": RUNS_LIMIT},
            max_rows=RUNS_LIMIT,
            database=self.database,
        )
        return [summary_of(r) for r in result.rows]

    def get(self, run_id: str) -> RunDetail | None:
        result = run_read(
            self.driver,
            "api/run_detail",
            _text("run_detail"),
            {"run_id": run_id},
            max_rows=1,
            database=self.database,
        )
        return detail_of(result.rows[0]) if result.rows else None


def runs_service(request: Request) -> RunsService:
    service = getattr(request.app.state, "runs", None)
    if not isinstance(service, RunsService):
        raise HTTPException(501, detail="Detection runs are not configured yet (PHASE-4.md M4.5).")
    return service


PROBLEMS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (404, 422, 500, 501, 503)
}


@router.get("/runs", response_model=list[RunSummary], responses=PROBLEMS, operation_id="runs_list")
def runs_list(request: Request) -> list[RunSummary]:
    """The detection runs in the graph, newest first (at most 50)."""
    service = runs_service(request)
    with read_errors():
        return service.list()


@router.get(
    "/runs/{run_id}", response_model=RunDetail, responses=PROBLEMS, operation_id="run_detail"
)
def run_detail(request: Request, run_id: Annotated[str, PathParam(pattern=RUN_ID)]) -> RunDetail:
    """One detection run with its counts: findings, alerts and withheld findings by typology."""
    service = runs_service(request)
    with read_errors():
        found = service.get(run_id)
    if found is None:
        raise HTTPException(404, detail="No detection run has this id.")
    return found
