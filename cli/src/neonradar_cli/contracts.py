"""`neonradar contracts ...`: contract checks (PHASE-1.md M1.7)."""

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Contract checks.", no_args_is_help=True)


@app.command(name="validate-records")
def validate_records(
    paths: Annotated[
        list[Path],
        typer.Argument(exists=True, dir_okay=False, help="C1 record files (.ftm.jsonl), one load."),
    ],
    strict: Annotated[
        bool, typer.Option("--strict", help="Also fail on dangling references (R4).")
    ] = False,
) -> None:
    """Validate C1 records: counts by schema, then every issue as `RULE id: message`."""
    # Imported here so that `neonradar --help` does not load FollowTheMoney.
    from neonradar_contracts import records

    try:
        counts, issues = records.validate_files(paths, strict)
    except records.RecordFileError as exc:
        typer.echo(f"FORMAT {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"{counts.total()} records in {len(paths)} file(s)")
    for schema, count in sorted(counts.items()):
        typer.echo(f"  {schema}: {count}")
    for issue in issues:
        typer.echo(str(issue))
    if issues:
        typer.echo(f"FAILED, {len(issues)} issue(s)")
        raise typer.Exit(code=1)
    typer.echo("OK, 0 issues")
