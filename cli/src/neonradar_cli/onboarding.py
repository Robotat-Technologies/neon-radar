"""`neonradar onboarding`: the Assignment 1 sandbox (PHASE-1.md M1.11a)."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready
from neonradar_graph.onboarding import (
    CSV_PATH,
    QUERIES_PATH,
    OnboardingError,
    check_queries,
    expected_counts,
    load,
    parse_first_queries,
    read_rows,
    reset,
)

app = typer.Typer(
    help="Assignment 1 sandbox: the Onb* labels, separate from the real schema.",
    no_args_is_help=True,
)

Timeout = Annotated[float, typer.Option(help="Seconds to wait for Neo4j to accept connections.")]


@contextmanager
def _connected(timeout: float) -> Iterator[tuple[Driver, str]]:
    try:
        settings = Neo4jSettings()
    except ValidationError:
        typer.echo("FAIL  NEO4J_PASSWORD is not set: run `make up` (it creates .env) or export it")
        raise typer.Exit(code=1) from None
    try:
        with get_driver(settings) as driver:
            wait_until_ready(driver, timeout_s=timeout)
            yield driver, settings.database
    except (DriverError, Neo4jError, TimeoutError) as error:
        typer.echo(f"FAIL  Neo4j at {settings.uri}: {error}")
        raise typer.Exit(code=1) from None


@app.command(name="check")
def check_command(
    csv_path: Annotated[
        Path, typer.Option("--csv", dir_okay=False, help="The onboarding CSV.")
    ] = CSV_PATH,
    queries: Annotated[
        Path, typer.Option(dir_okay=False, help="The first-queries file.")
    ] = QUERIES_PATH,
    timeout: Timeout = 30,
) -> None:
    """Load the CSV into the Onb* labels, then run every first query read-only (10 s each)."""
    try:
        rows = read_rows(csv_path)
        entries = parse_first_queries(queries.read_text(encoding="utf-8"))
    except (OSError, OnboardingError) as error:
        typer.echo(f"FAIL  {error}")
        raise typer.Exit(code=1) from None
    with _connected(timeout) as (driver, database):
        counts = load(driver, rows, database)
        results = check_queries(driver, entries, database)
    typer.echo(
        f"loaded {csv_path.name}: {counts.companies} OnbCompany, {counts.people} OnbPerson, "
        f"{counts.addresses} OnbAddress nodes in the graph"
    )
    expected = expected_counts(rows)
    if counts != expected:
        typer.echo(
            f"WARN  the CSV makes {expected.companies}, {expected.people} and "
            f"{expected.addresses}: other Onb* nodes are in the graph (perhaps a load with other "
            "property names). Run `neonradar onboarding reset`, then this check again."
        )
    for result in results:
        typer.echo(result.line())
    failed = sum(result.error is not None for result in results)
    typer.echo(f"{len(results)} queries: {len(results) - failed} ran, {failed} failed")
    if failed or not results:
        raise typer.Exit(code=1)


@app.command(name="reset")
def reset_command(timeout: Timeout = 30) -> None:
    """Delete every Onb* node and its relationships; nothing else is touched."""
    with _connected(timeout) as (driver, database):
        removed = reset(driver, database)
    typer.echo(f"removed {removed} Onb* nodes")
