"""`neonradar graph`: commands for the Neo4j graph."""

from collections.abc import Iterator, Mapping, Sequence
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


SHOWN = 25  # issues printed per kind; the rest are counted


def _echo_some(lines: Sequence[object]) -> None:
    for line in lines[:SHOWN]:
        typer.echo(f"  {line}")
    if len(lines) > SHOWN:
        typer.echo(f"  ... and {len(lines) - SHOWN} more")


def _echo_counts(title: str, counts: Mapping[str, int]) -> None:
    typer.echo(f"{title}:")
    for name, count in sorted(counts.items()):
        typer.echo(f"  {name}: {count}")


@app.command(name="load")
def load_command(
    paths: Annotated[
        list[Path],
        typer.Argument(
            exists=True, help="C1 record files, or folders of *.ftm.jsonl files; one load."
        ),
    ],
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Strict (default): any C1 issue, mapping issue or dangling reference fails the"
            " load, and nothing is written before the checks pass. Non-strict: skip and report.",
        ),
    ] = True,
    timeout: Timeout = 30,
) -> None:
    """Load C1 records into the graph, nodes before relationships; loading twice changes nothing."""
    from neonradar_graph import loader  # FollowTheMoney loads only for this command

    settings = _settings()
    with _connected(settings, timeout) as driver:
        try:
            report = loader.load_files(driver, paths, strict=strict, database=settings.database)
        except loader.LoadRefused as refused:
            _echo_some([*refused.issues, *refused.skipped])
            typer.echo(f"REFUSED (strict): {refused}")
            raise typer.Exit(code=1) from None
        except loader.LoadError as error:
            typer.echo(f"FAIL  {error}")
            raise typer.Exit(code=1) from None
    mode = "strict" if report.strict else "non-strict"
    typer.echo(f"{report.records} records from {len(report.files)} file(s), {mode}")
    _echo_counts("nodes by label", report.nodes_by_label)
    _echo_counts("relationships by type", report.relationships_by_type)
    written = report.written
    typer.echo(
        f"created {written['nodes_created']} nodes and {written['relationships_created']}"
        f" relationships; moved {written['relationships_deleted']} relationships; labels"
        f" {written['labels_added']} added and {written['labels_removed']} removed"
    )
    for title, items in (
        ("dangling references", report.dangling),
        ("records that failed C1, skipped", report.rejected),
        ("mapping issues, skipped", report.skipped),
    ):
        typer.echo(f"{title}: {len(items)}")
        _echo_some(items)
    if report.failed:
        typer.echo(f"FAILED (strict): {len(report.dangling)} dangling reference(s)")
        raise typer.Exit(code=1)
    warned = report.dangling or report.rejected or report.skipped
    typer.echo(f"{'WARN' if warned else 'OK'} in {report.duration_s:.1f} s")


@app.command(name="stats")
def stats_command(timeout: Timeout = 30) -> None:
    """Print node counts by label and relationship counts by type (apoc.meta.stats)."""
    from neonradar_graph import loader

    settings = _settings()
    with _connected(settings, timeout) as driver:
        counted = loader.stats(driver, settings.database)
    typer.echo(f"nodes: {counted.nodes}")
    for name, count in counted.labels.items():
        typer.echo(f"  {name}: {count}")
    typer.echo(f"relationships: {counted.relationships}")
    for name, count in counted.relationship_types.items():
        typer.echo(f"  {name}: {count}")


@app.command(name="wipe")
def wipe_command(
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm: delete every node except :SchemaMigration.")
    ] = False,
    timeout: Timeout = 30,
) -> None:
    """Delete every node except :SchemaMigration; the schema stays. Refuses without --yes."""
    if not yes:
        typer.echo(
            "REFUSED  graph wipe deletes every node except :SchemaMigration; add --yes to confirm"
        )
        raise typer.Exit(code=1)
    from neonradar_graph import loader

    settings = _settings()
    with _connected(settings, timeout) as driver:
        deleted = loader.wipe(driver, settings.database)
    typer.echo(f"deleted {deleted} nodes from {settings.uri} (database {settings.database})")
