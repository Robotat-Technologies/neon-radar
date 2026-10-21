"""`neonradar spike ...`: data source spikes (PHASE-1.md M1.8); output in data/cache/spikes/.

Each spike adds one command here that parses options, calls its source module in
`neonradar_ingest.sources`, prints what it fetched and ends with `report_output(path)`.
"""

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Data source spikes: a small slice of each source.", no_args_is_help=True)


def report_output(path: Path) -> None:
    """Print where the output is and its strict validation (as `contracts validate-records`).

    Exits 1 on any issue.
    """
    from neonradar_contracts.records import RecordFileError, validate_files  # loads FtM

    try:
        counts, issues = validate_files([path], strict=True)
    except RecordFileError as exc:
        typer.echo(f"FORMAT {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"wrote {path} and its manifest: {counts.total()} records")
    for schema, count in sorted(counts.items()):
        typer.echo(f"  {schema}: {count}")
    for issue in issues:
        typer.echo(str(issue))
    if issues:
        typer.echo(f"FAILED, {len(issues)} issue(s)")
        raise typer.Exit(code=1)
    typer.echo("OK, 0 issues (strict)")


@app.command(name="clean")
def clean(
    days: Annotated[int | None, typer.Option(min=0, help="Default: project.yaml")] = None,
) -> None:
    """Delete spike output older than access.spike_cache_days; it can hold personal data.

    It only ever cleans data/cache/spikes/, so it has no option for another folder.
    """
    from neonradar_ingest import spikes  # not at import time: `neonradar --help` stays fast

    try:
        keep = spikes.cache_days() if days is None else days
    except (OSError, ValueError) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    root = spikes.SPIKE_ROOT  # never anywhere else: the command deletes files
    deleted = spikes.clean_expired(keep, root)
    for path in deleted:
        typer.echo(f"deleted {path}")
    typer.echo(f"{len(deleted)} file(s) older than {keep} day(s) deleted from {root}")


@app.command(name="icij")
def icij(
    rows: Annotated[int, typer.Option(min=1, help="Entities that seed the slice.")] = 1000,
    cache_dir: Annotated[
        Path | None,
        typer.Option(
            help="Archive copy, only if byte ranges are refused. Default: inside the output"
        ),
    ] = None,
) -> None:
    """ICIJ Offshore Leaks: a closed slice of the bulk archive as C1 records."""
    from neonradar_ingest.http import HttpError
    from neonradar_ingest.sources.icij import spike as icij_spike

    try:
        result = icij_spike.run(rows=rows, cache_dir=cache_dir)
    except (HttpError, OSError, ValueError) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    for line in icij_spike.summary_lines(result):
        typer.echo(line)
    report_output(result.output)
