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
    """Validate C1 records: counts by schema, then every issue as `<file>:<line>: RULE ...`.

    Issues of records that are not synthetic show no values and no record id (masking.py).
    """
    # Imported here so that `neonradar --help` does not load FollowTheMoney.
    from neonradar_cli import masking
    from neonradar_contracts import records

    try:
        counts, issues = masking.validate(paths, strict)
    except records.RecordFileError as exc:
        typer.echo(f"FORMAT {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"{counts.total()} records in {len(paths)} file(s)")
    for schema, count in sorted(counts.items()):
        typer.echo(f"  {schema}: {count}")
    for issue in issues:
        typer.echo(issue)
    if issues:
        typer.echo(f"FAILED, {len(issues)} issue(s)")
        raise typer.Exit(code=1)
    typer.echo("OK, 0 issues")


def _documents() -> dict[str, str]:
    """Every generated contract file: the JSON Schemas and the API's OpenAPI snapshot (C3)."""
    from neonradar_api.main import create_app
    from neonradar_contracts import schemas

    openapi = schemas.render_json(create_app().openapi())
    return {**schemas.documents(), schemas.OPENAPI_SNAPSHOT: openapi}


@app.command(name="export")
def export_command() -> None:
    """Write the generated contract files (JSON Schemas and contracts/openapi/v1.json)."""
    from neonradar_contracts import schemas

    for path in schemas.export(docs=_documents()):
        typer.echo(f"wrote {path.relative_to(schemas.CONTRACTS_DIR.parent).as_posix()}")


@app.command(name="check")
def check_command() -> None:
    """Export to a temporary folder and fail on any difference from the committed files."""
    from neonradar_contracts import schemas

    docs = _documents()
    problems = schemas.check(docs=docs)
    for problem in problems:
        typer.echo(f"DRIFT contracts/{problem}")
    if problems:
        typer.echo(f"FAILED, {len(problems)} difference(s)")
        raise typer.Exit(code=1)
    typer.echo(f"OK, {len(docs)} generated files match the models")
