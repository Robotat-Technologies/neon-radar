"""The `neonradar` command line."""

from typing import Annotated

import typer

from neonradar_cli import __version__, contracts, docs, doctor, graph, spike, synth

app = typer.Typer(
    name="neonradar",
    help="NeonRadar: local-first graph investigation for AML and anti-corruption work.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(contracts.app, name="contracts")
app.add_typer(docs.app, name="docs")
app.add_typer(graph.app, name="graph")
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
