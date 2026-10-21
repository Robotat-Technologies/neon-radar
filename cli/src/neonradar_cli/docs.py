"""`neonradar docs ...`: generated documentation."""

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Generated documentation.", no_args_is_help=True)


@app.command(name="typology-index")
def typology_index(
    check: Annotated[
        bool, typer.Option("--check", help="Fail if the file is out of date; write nothing.")
    ] = False,
    typologies: Annotated[
        Path | None,
        typer.Option(file_okay=False, help="Typology folder [default: detect/typologies]."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(dir_okay=False, help="Index file [default: docs/typologies/README.md]."),
    ] = None,
) -> None:
    """Render the typology catalog index (docs/typologies/README.md) from the catalog."""
    from neonradar_detect import catalog

    output = output or catalog.INDEX_PATH
    try:
        text = catalog.render_index(catalog.load_catalog(typologies or catalog.TYPOLOGY_DIR))
    except catalog.CatalogError as exc:
        typer.echo(f"FAIL  {exc}")
        raise typer.Exit(code=1) from None
    current = output.read_text(encoding="utf-8") if output.is_file() else None
    if check:
        if current != text:
            command = "uv run neonradar docs typology-index"
            typer.echo(f"FAIL  {output.name} is out of date: run `{command}`")
            raise typer.Exit(code=1)
        typer.echo(f"OK  {output.name} matches the catalog")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    typer.echo(f"wrote {output}")
