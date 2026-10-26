"""`neonradar bench report`: the newest load and bench-queries summaries of a profile as Markdown
(PHASE-2.md M2.13 deliverable 4). It reads only `data/cache/reports/<profile>/`, which holds
counts only, and ends with the sources-and-licences footer of 7.3 rule 8."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

LOAD_TARGET_S = 600  # G2-09: the graph load under 10 minutes
QUERY_TARGET_MS = 2000  # G2-09: ownership and paths queries p95 under 2 seconds
TARGET_ENDPOINTS = ("ownership_up", "ownership_down", "paths")
POSSIBLE = "Possible matches are not confirmed and were not merged."


def newest(folder: Path, command: str) -> dict[str, Any] | None:
    """The newest `<command>-<UTC timestamp>[-n].json` summary in `folder`, or None."""
    paths = [path for path in folder.glob(f"{command}-*.json") if path.is_file()]
    if not paths:
        return None
    found = max(paths, key=lambda path: (path.stat().st_mtime_ns, path.name))
    data: dict[str, Any] = json.loads(found.read_text(encoding="utf-8"))
    return data


def flat(value: Any, prefix: str = "") -> dict[str, Any]:
    """Nested counts as `a.b` keys."""
    if not isinstance(value, dict):
        return {prefix: value}
    out: dict[str, Any] = {}
    for key, item in value.items():
        out |= flat(item, f"{prefix}.{key}" if prefix else str(key))
    return out


def table(head: tuple[str, ...], rows: list[tuple[Any, ...]]) -> list[str]:
    def cell(value: Any) -> str:
        return "-" if value is None else str(value)

    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return [*lines, *("| " + " | ".join(cell(v) for v in row) + " |" for row in rows), ""]


def _met(met: bool) -> str:
    return "met" if met else "not met"


def targets(load: dict[str, Any] | None, queries: dict[str, Any] | None) -> str:
    """The line comparing the run with G2-09: the `graph load` step (an ok load) under 10
    minutes, and the p95 of /ownership and /paths under 2 seconds with no timeout or error on
    any endpoint. The whole load and the slowest call follow as information only."""
    parts, extra = [], []
    if load is not None:
        steps = load.get("steps", {})
        step, whole = steps.get("graph_load", {}), sum(s["duration_s"] for s in steps.values())
        took = step.get("duration_s")
        ok = load.get("status") == step.get("status") == "ok"
        met = ok and took is not None and took < LOAD_TARGET_S
        shown = "missing" if took is None else f"{took / 60:.1f} min"
        parts.append(f"graph load {shown}, under 10 minutes: {_met(met)}")
        extra.append(f"whole load {whole / 60:.1f} min")
    if queries is not None:
        endpoints = queries.get("endpoints", {})
        p95 = [endpoints.get(name, {}).get("p95_ms") for name in TARGET_ENDPOINTS]
        failed = sum((e.get("timeouts") or 0) + (e.get("errors") or 0) for e in endpoints.values())
        met = not failed and all(ms is not None and ms < QUERY_TARGET_MS for ms in p95)
        worst = max((ms for ms in p95 if ms is not None), default=None)
        shown = "missing" if worst is None else f"{worst / 1000:.2f} s"
        note = f" ({failed} calls timed out or failed)" if failed else ""
        parts.append(f"ownership and paths p95 {shown}, under 2 seconds: {_met(met)}{note}")
        slowest = [e["max_ms"] for e in endpoints.values() if e.get("max_ms") is not None]
        if slowest:
            extra.append(f"slowest call {max(slowest) / 1000:.2f} s")
    line = "Targets (G2-09): " + ("; ".join(parts) or "no summary to compare") + "."
    return line + (f" Information only: {'; '.join(extra)}." if extra else "")


def render(
    profile: str,
    load: dict[str, Any] | None,
    queries: dict[str, Any] | None,
    datasets: list[str],
) -> str:
    """The report; `datasets` name the 7.3 rule 8 footer when the load summary has no records."""
    from neonradar_resolve.precision import sources_footer

    lines = [f"# Load benchmark: {profile}", "", targets(load, queries), ""]
    if load is not None:
        lines += [f"Load run {load.get('run_id')}: {load.get('status')}"
                  f" (real data: {load.get('real_data')}).", "", "## Steps", ""]  # fmt: skip
        steps = load.get("steps", {})
        rows: list[tuple[Any, ...]] = [
            (name.replace("_", " "), s["status"], s["duration_s"]) for name, s in steps.items()
        ]
        lines += table(("Step", "Status", "Seconds"), rows)
        records = load.get("records", {})
        rows = [(d, r.get("version"), schema, n) for d, r in sorted(records.items())
                for schema, n in sorted(r.get("by_schema", {}).items())]  # fmt: skip
        lines += ["## Records", "", *table(("Dataset", "Version", "Schema", "Records"), rows)]
        for title, key in (("Resolution", "resolution"), ("Graph", "graph"),
                           ("Invariants", "invariants"), ("Hardware", "hardware")):  # fmt: skip
            rows = list(sorted(flat(load.get(key, {})).items()))
            lines += [f"## {title}", "", *table(("Count", "Value"), rows)]
            lines += [POSSIBLE, ""] if key == "resolution" else []
    if queries is not None:
        lines += ["## Queries", "", f"{queries.get('picked')} of {queries.get('eligible')}"
                  f" eligible entities, seed {queries.get('seed')}.", ""]  # fmt: skip
        head = ("Endpoint", "Calls", "p50 ms", "p95 ms", "Max ms", "Results", "Timeouts", "Errors")
        keys = ("calls", "p50_ms", "p95_ms", "max_ms", "results", "timeouts", "errors")
        endpoints = queries.get("endpoints", {})
        lines += table(head, [(name, *(e.get(k) for k in keys)) for name, e in endpoints.items()])
    footer = sources_footer(list((load or {}).get("records", {})) or datasets)
    lines.append(f"Sources and licences: {footer or 'no dataset loaded.'}")
    return "\n".join(lines) + "\n"


def report_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    out: Annotated[
        Path | None, typer.Option("--out", help="Default: docs/data/benchmarks/<date>-<name>.md")
    ] = None,
) -> None:
    """Render the newest load and bench-queries summaries of a profile (counts only)."""
    from neonradar_cli import summary
    from neonradar_cli.data import profile_or_exit
    from neonradar_cli.load import STRING_KEYS
    from neonradar_ingest.data import layout
    from neonradar_ingest.data.project import REPO_ROOT

    chosen = profile_or_exit(profile)
    folder = layout.reports_dir(chosen)
    load, queries = newest(folder, "load"), newest(folder, "bench-queries")
    if load is None and queries is None:
        typer.echo(f"FAIL  no load or bench-queries summary for {chosen.profile}", err=True)
        raise typer.Exit(code=1)
    try:  # checked again, so a summary edited by hand never reaches docs/
        load = None if load is None else summary.clean(load, string_keys=STRING_KEYS)
        queries = None if queries is None else summary.clean(queries)
    except summary.SummaryRefused as refused:  # the message names the key, never the value
        typer.echo(f"FAIL  {refused}", err=True)
        raise typer.Exit(code=1) from None
    enabled = [name for name, source in chosen.sources.items() if source.enabled]
    day = datetime.now(UTC).date().isoformat()
    path = out or REPO_ROOT / "docs" / "data" / "benchmarks" / f"{day}-{chosen.profile}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(chosen.profile, load, queries, enabled), encoding="utf-8")
    typer.echo(f"wrote {path}")
