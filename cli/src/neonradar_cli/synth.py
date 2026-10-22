"""`neonradar synth ...`: the synthetic data generator (PHASE-1.md M1.8e, PHASE-2.md M2.9)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from neonradar_ingest.synth import DEMO_SEED, ER_BENCH_SEED

app = typer.Typer(help="Synthetic data generator.", no_args_is_help=True)


@app.command(name="demo-mini")
def demo_mini(
    seed: Annotated[
        int, typer.Option(min=0, help="Root seed; the same seed gives the same bytes.")
    ] = DEMO_SEED,
    out: Annotated[Path, typer.Option(help="Output folder.")] = Path("data/fixtures/demo-mini"),
) -> None:
    """Generate demo-mini: C1 records, their manifest and the label files."""
    # Imported here so that `neonradar --help` does not load Faker and FollowTheMoney.
    from neonradar_ingest.synth.demo import write_demo_mini

    _summary(write_demo_mini(out, seed), seed)


def _summary(path: Path, seed: int) -> None:
    from neonradar_contracts.records import manifest_path

    manifest = json.loads(manifest_path(path).read_text(encoding="utf-8"))
    entry = manifest["files"][0]
    typer.echo(f"{entry['records']} records, seed {seed}: {path}")
    for schema, count in manifest["counts"]["by_schema"].items():
        typer.echo(f"  {schema}: {count}")
    typer.echo(f"sha256 {entry['sha256']}")
    typer.echo(f"labels: {path.parent / 'labels'}")


@app.command(name="er-bench")
def er_bench(
    size: Annotated[str, typer.Option(help="small (600 people, 300 organisations) or large.")] = (
        "small"
    ),
    seed: Annotated[
        int, typer.Option(min=0, help="Root seed; the same seed gives the same bytes.")
    ] = ER_BENCH_SEED,
    out: Annotated[
        Path | None,
        typer.Option(help="Output folder [default: data/cache/synthetic/er-bench-<size>]."),
    ] = None,
) -> None:
    """Generate the entity resolution benchmark: records, manifest and labels/er_truth.csv."""
    from neonradar_ingest.data.layout import bench_dir
    from neonradar_ingest.synth.erbench import SIZES, write_er_bench

    if size not in SIZES:
        raise typer.BadParameter(f"size must be one of {', '.join(SIZES)}", param_hint="--size")
    _summary(write_er_bench(out or bench_dir(size), size, seed), seed)


@app.command(name="check-names")
def check_names(
    paths: Annotated[
        list[Path], typer.Argument(exists=True, dir_okay=False, help="Synthetic record files.")
    ],
    against: Annotated[
        list[Path] | None,
        typer.Option(exists=True, dir_okay=False, help="Other C1 files, such as spike output."),
    ] = None,
) -> None:
    """List synthetic names; fail on a denylisted name or one that equals a name in --against."""
    from neonradar_ingest.synth.namecheck import check_names as run_check

    names, denied, collisions = run_check(paths, against or [])
    for rid, name in names:
        typer.echo(f"{rid}\t{name}")
    typer.echo(f"{len(names)} names; {len(denied)} denylisted; {len(collisions)} equal a name in"
               f" {len(against or [])} other file(s)")  # fmt: skip
    for rid, name in denied:
        typer.echo(f"DENYLIST {rid}: {name}")
    for rid, _ in collisions:
        typer.echo(f"COLLISION {rid}: its name equals a name in --against; change the word lists")
    if denied or collisions:
        raise typer.Exit(code=1)
