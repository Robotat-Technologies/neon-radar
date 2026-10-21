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
    from neonradar_contracts.records import validate_files  # loads FollowTheMoney

    counts, issues = validate_files([path], strict=True)
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
    folder: Annotated[Path | None, typer.Option("--dir", help="Default: data/cache/spikes")] = None,
    days: Annotated[int | None, typer.Option(min=0, help="Default: project.yaml")] = None,
) -> None:
    """Delete spike output older than access.spike_cache_days; it can hold personal data."""
    from neonradar_ingest import spikes  # not at import time: `neonradar --help` stays fast

    try:
        keep = spikes.cache_days() if days is None else days
    except (OSError, ValueError) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    root = folder or spikes.SPIKE_ROOT
    deleted = spikes.clean_expired(keep, root)
    for path in deleted:
        typer.echo(f"deleted {path}")
    typer.echo(f"{len(deleted)} file(s) older than {keep} day(s) deleted from {root}")
