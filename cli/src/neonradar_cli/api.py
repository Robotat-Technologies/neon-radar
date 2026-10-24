"""`neonradar api`: the NeonRadar API (contract C3).

`api serve` connects through `Instance.DEFAULT` (database `neo4j`), which holds synthetic data
only. `api serve --real` (PHASE-2.md M2.12) serves the real-data instance to a person at a
terminal on an approved machine: it refuses (exit 2) unless standard input is a terminal, runs
conditions 3 to 5 of the real-data gate (M2.2) before any connection, binds 127.0.0.1 on
`REAL_PORT` and connects through `Instance.REAL`. Agents never run it (G9, G10). A request line
holds ids and names, so it has no access log and logs warnings only: errors name the route
template and the class, and their tracebacks go to the redacted log under data/cache/real/logs.
"""

from functools import partial
from typing import Annotated, Final

import typer

app = typer.Typer(help="The NeonRadar API.", no_args_is_help=True)

# The API serves only this machine (C3); Compose publishes the container on 127.0.0.1 too.
HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8000
REAL_PORT: Final = 8001
REAL_COMMAND: Final = "api serve --real"


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
) -> None:
    """Run the API on 127.0.0.1 until interrupted (http://127.0.0.1:<port>/api/v1)."""
    # Imported here so that `neonradar --help` does not load FastAPI.
    import uvicorn

    if not real:  # the app's default connection is Instance.DEFAULT (neonradar_api.graph)
        uvicorn.run(
            "neonradar_api.main:create_app", factory=True, host=HOST, port=port or DEFAULT_PORT
        )
        return
    if port is not None:
        typer.echo(f"--real always serves port {REAL_PORT}; leave out --port.", err=True)
        raise typer.Exit(code=2)
    from neonradar_api.graph import GraphConnection
    from neonradar_api.main import create_app
    from neonradar_api.problems import Contained
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
            Contained(served), host=HOST, port=REAL_PORT, access_log=False, log_level="warning"
        )
