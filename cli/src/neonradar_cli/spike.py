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
    import csv
    import zipfile
    import zlib

    from neonradar_ingest.http import HttpError
    from neonradar_ingest.sources.icij import spike as icij_spike

    try:
        result = icij_spike.run(rows=rows, cache_dir=cache_dir)
    except (HttpError, OSError, ValueError, zipfile.BadZipFile, zlib.error, csv.Error) as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    for line in icij_spike.summary_lines(result):
        typer.echo(line)
    report_output(result.output)


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


@app.command(name="gleif")
def gleif(
    lei: Annotated[str, typer.Option(help="The LEI to fetch.")] = "549300OWFMSO9NYV4H90",
    ch_number: Annotated[
        str | None,
        typer.Option(help="Companies House number to join (default: the record's registeredAs)."),
    ] = None,
    coverage: Annotated[
        bool, typer.Option("--coverage", help="Also count GB records (8 more requests).")
    ] = False,
) -> None:
    """GLEIF (M1.8b): an LEI record, its parents, children and the Companies House join."""
    import time

    from neonradar_contracts.records import Source
    from neonradar_ingest import spikes
    from neonradar_ingest.http import HttpError
    from neonradar_ingest.sources import gleif as source

    started = time.monotonic()
    try:
        with source.make_client() as client:
            result = source.run_spike(client, lei.strip().upper(), ch_number)
            counts = source.coverage(client) if coverage else {}
    except (HttpError, LookupError, ValueError) as exc:
        typer.echo(f"FAIL  GLEIF: {exc}")
        raise typer.Exit(code=1) from None
    for line in source.summary_lines(result):
        typer.echo(line)
    for label, count in counts.items():
        typer.echo(f"coverage: {label}: {count:,}")
    typer.echo(
        f"http: {client.requests} requests, {client.retried} retried, {client.throttled}"
        f" throttled (429), {time.monotonic() - started:.1f} s;"
        f" golden copy {result.publish_date}"
    )
    records, notes = source.build_records(result)
    retrieved = spikes.utc_timestamp()
    info = Source(urls=result.urls, retrieved_at=retrieved, source_version=result.publish_date)
    path = spikes.write_output(
        records, "gleif", dataset=source.DATASET, part=result.record["id"], source=info, notes=notes
    )
    report_output(path)


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
    import httpx

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
    except (CompanyNotFound, HttpError, httpx.HTTPError, ValueError) as exc:
        # httpx.HTTPError: errors the shared client does not retry (DecodingError,
        # TooManyRedirects); ValueError: a bad number or a body that is not JSON.
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    for line in result.summary():
        typer.echo(line)
    report_output(result.records_path)
