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


@app.command(name="companies-house")
def companies_house(
    company: Annotated[str, typer.Option("--company", help="Companies House company number.")],
    max_pages: Annotated[
        int, typer.Option("--max-pages", min=1, help="At most this many pages per list.")
    ] = 5,
) -> None:
    """One company, its officers and its PSCs from the Companies House API (needs CH_API_KEY).

    Prints counts and field names only; the records hold personal data and stay in
    data/cache/spikes/companies_house/ until `neonradar spike clean`.
    """
    from neonradar_ingest.http import HttpError
    from neonradar_ingest.settings import IngestSettings
    from neonradar_ingest.sources.companies_house.client import CompaniesHouseClient
    from neonradar_ingest.sources.companies_house.spike import CompanyNotFound, run_spike

    key = IngestSettings().companies_house_key()
    if key is None:
        typer.echo("FAIL  CH_API_KEY is not set: the operator adds it to .env (OD-14)")
        raise typer.Exit(code=1)
    try:
        with CompaniesHouseClient(key) as client:
            result = run_spike(client, company, max_pages=max_pages)
    except (CompanyNotFound, HttpError, ValueError) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    for line in result.summary():
        typer.echo(line)
    report_output(result.records_path)
