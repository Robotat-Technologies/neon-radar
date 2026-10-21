"""`neonradar graph`: commands for the Neo4j graph."""

from typing import Annotated

import typer
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready
from neonradar_graph.smoke import run_smoke

app = typer.Typer(help="The Neo4j graph.", no_args_is_help=True)


@app.command(name="smoke")
def smoke_command(
    timeout: Annotated[
        float, typer.Option(help="Seconds to wait for Neo4j to accept connections.")
    ] = 30,
) -> None:
    """Print the Neo4j version and edition, APOC and GDS; exit 1 if any is missing."""
    try:
        settings = Neo4jSettings()
    except ValidationError:
        typer.echo("FAIL  NEO4J_PASSWORD is not set: run `make up` (it creates .env) or export it")
        raise typer.Exit(code=1) from None
    try:
        with get_driver(settings) as driver:
            wait_until_ready(driver, timeout_s=timeout)
            report = run_smoke(driver, settings.database)
    except (DriverError, Neo4jError, TimeoutError) as error:
        typer.echo(f"FAIL  Neo4j  not reachable at {settings.uri}: {error}")
        raise typer.Exit(code=1) from None
    for line in report.lines():
        typer.echo(line)
    if not report.ok:
        raise typer.Exit(code=1)
