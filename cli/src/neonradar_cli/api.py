"""`neonradar api`: the NeonRadar API (contract C3)."""

from typing import Annotated, Final

import typer

app = typer.Typer(help="The NeonRadar API.", no_args_is_help=True)

# The API serves only this machine (C3); Compose publishes the container on 127.0.0.1 too.
HOST: Final = "127.0.0.1"


@app.command(name="serve")
def serve_command(
    port: Annotated[int, typer.Option(min=1, max=65535, help="Port on 127.0.0.1.")] = 8000,
) -> None:
    """Run the API on 127.0.0.1 until interrupted (http://127.0.0.1:<port>/api/v1)."""
    # Imported here so that `neonradar --help` does not load FastAPI.
    import uvicorn

    uvicorn.run("neonradar_api.main:create_app", factory=True, host=HOST, port=port)
