"""`neonradar detect ...`: detection runs over the graph (PHASE-1.md M1.9b)."""

from typing import Annotated

import typer

from neonradar_cli.graph import Timeout, _connected, _settings

app = typer.Typer(help="Detection runs.", no_args_is_help=True)


@app.command(name="run")
def run_command(
    typology: Annotated[
        str | None,
        typer.Option("--typology", help="Run one typology [default: every one with a detector]."),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            help="Run id, run-<UTC yyyymmddThhmmss>-<4 hex> [default: a new one]. Given again,"
            " the run replaces that run's files and keeps in Neo4j only the alerts it finds now"
            " (PRODUCED from earlier attempts and alerts no run produces any more are removed).",
        ),
    ] = None,
    timeout: Timeout = 30,
) -> None:
    """Run the detectors, write data/runs/<run_id>/ and load the alerts into Neo4j."""
    from neonradar_detect import catalog, runner

    settings = _settings()
    with _connected(settings, timeout) as driver:
        try:
            report = runner.run(driver, settings.database, typology=typology, run_id=run_id)
        except (runner.RunError, catalog.CatalogError, OSError) as error:
            typer.echo(f"FAIL  {error}")
            raise typer.Exit(code=1) from None
    typer.echo(f"{report.run_id}  {len(report.alerts)} alerts  ({', '.join(report.typologies)})")
    for alert in report.alerts:
        typer.echo(f"  {alert.alert_id}  {alert.priority:<6}  {alert.headline}")
    typer.echo(f"wrote {report.directory}")


@app.command(name="list")
def list_command() -> None:
    """List the typologies that have a detector, with their status and detector version."""
    from neonradar_detect import catalog, runner

    try:
        typologies = catalog.load_catalog()
    except catalog.CatalogError as error:
        typer.echo(f"FAIL  {error}")
        raise typer.Exit(code=1) from None
    with_detector = [item for _, item in sorted(typologies.items()) if item.detector]
    for item in with_detector:
        module = runner.DETECTORS.get(str(item.detector))
        version = module.VERSION if module else "unknown detector"
        typer.echo(f"{item.slug}  {item.version}  {item.status}  {item.detector} {version}")
    typer.echo(f"{len(with_detector)} of {len(typologies)} typologies have a detector")
