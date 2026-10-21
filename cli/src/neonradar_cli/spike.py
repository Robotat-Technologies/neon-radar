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


@app.command(name="opensanctions")
def opensanctions(
    collection: Annotated[str, typer.Option(help="sanctions, peps, default, crime, ...")] = (
        "sanctions"
    ),
    rows: Annotated[int, typer.Option(min=1, help="Lines of entities.ftm.json to read.")] = 1000,
) -> None:
    """Stream a slice of OpenSanctions if access.opensanctions allows it; exit 3 if it does not.

    Only `licensed` access writes output; a slice has dangling references, so it is validated
    without --strict.
    """
    from neonradar_contracts.records import RecordFileError, validate_files
    from neonradar_ingest.http import HttpError
    from neonradar_ingest.sources.opensanctions import access
    from neonradar_ingest.sources.opensanctions import spike as source

    route = access.read_access()
    try:
        access.require_access(route)  # before any client exists: `none` sends nothing
    except access.LicenceRequired as refusal:
        typer.echo(str(refusal))
        raise typer.Exit(code=3) from None
    try:
        with source.make_client() as client:
            result = source.run_spike(client, access=route, collection=collection, rows=rows)
    except (HttpError, ValueError) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    for line in source.summary_lines(result):
        typer.echo(line)
    if result.records_file is not None:
        try:
            _, issues = validate_files([result.records_file], strict=False)
        except RecordFileError as exc:
            typer.echo(f"FORMAT {exc}")
            raise typer.Exit(code=1) from None
        for issue in issues:
            typer.echo(str(issue))
        typer.echo(f"validate-records (a slice, not strict): {len(issues)} issue(s)")
        if issues:
            raise typer.Exit(code=1)
