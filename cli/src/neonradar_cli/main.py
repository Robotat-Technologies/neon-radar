"""The `neonradar` command line."""

from typing import Annotated

import typer

from neonradar_cli import (
    __version__,
    api,
    contracts,
    data,
    detect,
    docs,
    doctor,
    er,
    gate,
    graph,
    ingest,
    onboarding,
    spike,
    synth,
)

app = typer.Typer(
    name="neonradar",
    help="NeonRadar: local-first graph investigation for AML and anti-corruption work.",
    no_args_is_help=True,
    add_completion=False,
    # Never print local variables (they can hold record values) and no Rich tracebacks: typer
    # 0.27.3 defaults to pretty_exceptions_enable=True, pretty_exceptions_show_locals=False.
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
)
app.add_typer(api.app, name="api")
app.add_typer(contracts.app, name="contracts")
app.add_typer(data.app, name="data")
app.add_typer(detect.app, name="detect")
app.add_typer(docs.app, name="docs")
app.add_typer(er.app, name="er")
app.add_typer(gate.app, name="gate")
app.add_typer(graph.app, name="graph")
app.add_typer(ingest.app, name="ingest")
app.add_typer(onboarding.app, name="onboarding")
app.add_typer(spike.app, name="spike")
app.add_typer(synth.app, name="synth")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_print_version, is_eager=True, help="Print the version and exit."
        ),
    ] = False,
) -> None:
    """NeonRadar command line."""


@app.command(name="doctor")
def doctor_command() -> None:
    """Check this machine: one line per check with OK, WARN or FAIL; exit 1 on any FAIL."""
    checks = doctor.run_checks()
    for check in checks:
        typer.echo(check.line())
    if any(check.status is doctor.Status.FAIL for check in checks):
        raise typer.Exit(code=1)
