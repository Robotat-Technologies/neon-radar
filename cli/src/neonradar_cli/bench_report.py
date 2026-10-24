"""`neonradar bench report`: the newest load and bench-queries summaries of a profile as Markdown
(PHASE-2.md M2.13 deliverable 4). It reads only `data/cache/reports/<profile>/`, which holds
counts only, and ends with the sources-and-licences footer of 7.3 rule 8."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

LOAD_TARGET_S = 600  # the plan: a graph load under 10 minutes
QUERY_TARGET_MS = 2000  # the plan: demo queries under 2 seconds


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


def targets(load: dict[str, Any] | None, queries: dict[str, Any] | None) -> str:
    """The line comparing the run with the plan's targets."""
    parts = []
    if load is not None:
        total = sum(step["duration_s"] for step in load.get("steps", {}).values())
        met = "met" if total < LOAD_TARGET_S and load.get("status") == "ok" else "not met"
        parts.append(f"whole load {total / 60:.1f} min, graph load under 10 minutes: {met}")
    if queries is not None:
        slowest = [e["max_ms"] for e in queries.get("endpoints", {}).values() if e["max_ms"]]
        worst = max(slowest, default=0.0)
        met = "met" if worst < QUERY_TARGET_MS else "not met"
        parts.append(f"slowest query {worst / 1000:.2f} s, demo queries under 2 seconds: {met}")
    return "Targets (the plan): " + ("; ".join(parts) or "no summary to compare") + "."


def render(profile: str, load: dict[str, Any] | None, queries: dict[str, Any] | None) -> str:
    from neonradar_resolve.precision import _sources  # the 7.3 rule 8 footer

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
    if queries is not None:
        lines += ["## Queries", "", f"{queries.get('picked')} of {queries.get('eligible')}"
                  f" eligible entities, seed {queries.get('seed')}.", ""]  # fmt: skip
        head = ("Endpoint", "Calls", "p50 ms", "p95 ms", "Max ms", "Results", "Timeouts", "Errors")
        keys = ("calls", "p50_ms", "p95_ms", "max_ms", "results", "timeouts", "errors")
        endpoints = queries.get("endpoints", {})
        lines += table(head, [(name, *(e.get(k) for k in keys)) for name, e in endpoints.items()])
    datasets = (load or {}).get("records", {})
    lines.append(f"Sources and licences: {_sources(datasets) or 'no dataset loaded.'}")
    return "\n".join(lines) + "\n"


def report_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    out: Annotated[
        Path | None, typer.Option("--out", help="Default: docs/data/benchmarks/<date>-<name>.md")
    ] = None,
) -> None:
    """Render the newest load and bench-queries summaries of a profile (counts only)."""
    from neonradar_cli.data import profile_or_exit
    from neonradar_ingest.data import layout
    from neonradar_ingest.data.project import REPO_ROOT

    chosen = profile_or_exit(profile)
    folder = layout.reports_dir(chosen)
    load, queries = newest(folder, "load"), newest(folder, "bench-queries")
    if load is None and queries is None:
        typer.echo(f"FAIL  no load or bench-queries summary for {chosen.profile}", err=True)
        raise typer.Exit(code=1)
    day = datetime.now(UTC).date().isoformat()
    path = out or REPO_ROOT / "docs" / "data" / "benchmarks" / f"{day}-{chosen.profile}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(chosen.profile, load, queries), encoding="utf-8")
    typer.echo(f"wrote {path}")
