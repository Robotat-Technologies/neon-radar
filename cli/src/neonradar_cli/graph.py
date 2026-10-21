"""`neonradar graph`: commands for the Neo4j graph."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready
from neonradar_graph.migrate import MIGRATIONS_DIR, MigrationError, migrate
from neonradar_graph.smoke import run_smoke

app = typer.Typer(help="The Neo4j graph.", no_args_is_help=True)

Timeout = Annotated[float, typer.Option(help="Seconds to wait for Neo4j to accept connections.")]


def _settings() -> Neo4jSettings:
    try:
        return Neo4jSettings()
    except ValidationError:
        typer.echo("FAIL  NEO4J_PASSWORD is not set: run `make up` (it creates .env) or export it")
        raise typer.Exit(code=1) from None


@contextmanager
def _connected(settings: Neo4jSettings, timeout: float) -> Iterator[Driver]:
    """A ready driver; exits 1 with one line when Neo4j cannot be reached or answers an error."""
    try:
        with get_driver(settings) as driver:
            wait_until_ready(driver, timeout_s=timeout)
            yield driver
    except (DriverError, TimeoutError) as error:
        typer.echo(f"FAIL  Neo4j  not reachable at {settings.uri}: {error}")
        raise typer.Exit(code=1) from None
    except Neo4jError as error:  # for example a wrong password or a failing statement
        typer.echo(f"FAIL  Neo4j  at {settings.uri} answered: {error}")
        raise typer.Exit(code=1) from None


@app.command(name="smoke")
def smoke_command(timeout: Timeout = 30) -> None:
    """Print the Neo4j version and edition, APOC and GDS; exit 1 if any is missing."""
    settings = _settings()
    with _connected(settings, timeout) as driver:
        report = run_smoke(driver, settings.database)
    for line in report.lines():
        typer.echo(line)
    if not report.ok:
        raise typer.Exit(code=1)


@app.command(name="migrate")
def migrate_command(
    directory: Annotated[
        Path,
        typer.Option(
            "--dir", exists=True, file_okay=False, help="Folder with NNNN_<name>.cypher files."
        ),
    ] = MIGRATIONS_DIR,
    timeout: Timeout = 30,
) -> None:
    """Apply the pending schema migrations in order; re-running is a no-op."""
    settings = _settings()
    with _connected(settings, timeout) as driver:
        try:
            report = migrate(driver, settings.database, directory)
        except MigrationError as error:
            typer.echo(f"FAIL  {error}")
            raise typer.Exit(code=1) from None
    for migration in report.applied:
        typer.echo(f"applied {migration.id} ({len(migration.statements)} statements)")
    if not report.applied:
        count = len(report.already_applied)
        typer.echo(f"nothing to apply ({count} migration{'s' * (count != 1)} already applied)")
