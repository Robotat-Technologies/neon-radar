"""`neonradar api`: the NeonRadar API (contract C3).

`api serve` connects through `Instance.DEFAULT` (database `neo4j`), which holds synthetic data
only. `api serve --real` (PHASE-2.md M2.12) serves the real-data instance to a person at a
terminal on an approved machine: it refuses (exit 2) unless standard input is a terminal, runs
conditions 3 to 5 of the real-data gate (M2.2) before any connection, binds 127.0.0.1 on
`REAL_PORT` and connects through `Instance.REAL`. Agents never run it (G9, G10).

Both start uvicorn without its own access log, which writes every query string, and with
`neonradar_api.hardening.log_config()` (PHASE-4.md M4.1, G15). `api serve` logs the API's access
lines (route templates only). A real request line holds ids and names, so `--real` logs warnings
only: errors name the route template and the class, and their tracebacks go to the redacted log
under data/cache/real/logs. `--dev` adds CORS for a UI served from another origin; `--host` is for
the API image only (it sets `NR_API_IN_IMAGE=1`) and is refused together with `--real`.
"""

import os
from functools import partial
from typing import Annotated, Any, Final

import typer

app = typer.Typer(help="The NeonRadar API.", no_args_is_help=True)

# The API serves only this machine (C3); Compose publishes the container on 127.0.0.1 too.
HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8000
REAL_PORT: Final = 8001
REAL_COMMAND: Final = "api serve --real"
IN_IMAGE: Final = "NR_API_IN_IMAGE"  # set by api/Dockerfile only


def warnings_only(config: dict[str, Any]) -> dict[str, Any]:
    """`config` with the API's loggers at WARNING: the real-data server keeps no access lines."""
    config["loggers"]["neonradar.api"]["level"] = "WARNING"
    return config


@app.command(name="serve")
def serve_command(
    port: Annotated[
        int | None,
        typer.Option(
            min=1,
            max=65535,
            help=f"Port on 127.0.0.1 (default {DEFAULT_PORT}); --real always uses {REAL_PORT}.",
        ),
    ] = None,
    real: Annotated[
        bool,
        typer.Option(
            "--real",
            help=f"Serve the real-data instance on 127.0.0.1:{REAL_PORT} to a person at this"
            " terminal (approved machines only; humans only).",
        ),
    ] = False,
    dev: Annotated[
        bool,
        typer.Option(
            "--dev", help="Send CORS headers for a UI on the Vite dev server's own origin."
        ),
    ] = False,
    host: Annotated[
        str | None,
        typer.Option(help="The interface to bind; for the API image only (default 127.0.0.1)."),
    ] = None,
) -> None:
    """Run the API on 127.0.0.1 until interrupted (http://127.0.0.1:<port>/api/v1)."""
    if real and (host is not None or dev):
        raise typer.BadParameter("--real always serves 127.0.0.1 without --host or --dev")
    if host not in (None, HOST) and os.environ.get(IN_IMAGE) != "1":
        raise typer.BadParameter(f"--host is for the API image only; the API serves {HOST}")
    # Imported here so that `neonradar --help` does not load FastAPI.
    import uvicorn

    from neonradar_api.hardening import log_config

    if not real:  # the app's default connection is Instance.DEFAULT (neonradar_api.graph)
        uvicorn.run(
            f"neonradar_api.main:{'create_dev_app' if dev else 'create_app'}",
            factory=True,
            host=host or HOST,
            port=port or DEFAULT_PORT,
            access_log=False,
            log_config=log_config(),
        )
        return
    if port is not None:
        typer.echo(f"--real always serves port {REAL_PORT}; leave out --port.", err=True)
        raise typer.Exit(code=2)
    from neonradar_api.graph import GraphConnection
    from neonradar_api.main import create_app
    from neonradar_cli import redact
    from neonradar_cli.data import project_or_exit
    from neonradar_cli.tty import require_terminal
    from neonradar_graph.instances import Instance
    from neonradar_ingest.data import gate

    with redact.guard(None, REAL_COMMAND, real=True) as where:
        where.step = "terminal"
        require_terminal(REAL_COMMAND)  # before anything is read or opened (G10)
        project = project_or_exit()
        where.step = "gate"
        gate.check_real_instance(project)
        where.step = "serve"
        report = partial(redact.report, command=REAL_COMMAND, step="request")
        served = create_app(GraphConnection(Instance.REAL.settings), report=report)
        typer.echo(
            f"Serving real data on this machine only, at http://{HOST}:{REAL_PORT}/api/v1;"
            " stop it with Ctrl+C."
        )
        uvicorn.run(
            served,
            host=HOST,
            port=REAL_PORT,
            access_log=False,
            log_config=warnings_only(log_config()),
            log_level="warning",
        )
