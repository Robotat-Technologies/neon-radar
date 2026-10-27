"""`neonradar synth ...`: the synthetic data generator (PHASE-1.md M1.8e, PHASE-2.md M2.9;
generator v1, PHASE-3.md M3.3)."""

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from neonradar_ingest.synth import DEMO_SEED, ER_BENCH_SEED

if TYPE_CHECKING:
    from neonradar_ingest.synth.commands import Written

app = typer.Typer(help="Synthetic data generator.", no_args_is_help=True)

SeedOption = Annotated[
    int | None,
    typer.Option(min=0, help="Seed of the world and the overlay (default: the profile's)."),
]
OutOption = Annotated[
    Path | None,
    typer.Option(file_okay=False, help="Write into this folder (default: data/cache/synthetic/)."),
]


def _git_sha() -> str:
    """The checkout's commit for the manifests, or "unknown" outside a git checkout."""
    from neonradar_ingest.data.project import REPO_ROOT

    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return "unknown"
    sha = done.stdout.strip()
    return sha if done.returncode == 0 and len(sha) == 40 else "unknown"


def _report(
    profile: str, command: str, written: Written, extra: dict[str, object], *, real: bool = False
) -> None:
    from neonradar_cli import summary

    if not real:  # a real profile's output is counts only (PHASE-3.md 7.7 rule 6)
        typer.echo(f"wrote {written.records_file}")
    summary.emit(
        profile,
        command,
        {
            "profile": profile,
            "seed": written.seed,
            "records": sum(written.by_schema.values()),
            "records_by_schema": {k.lower(): n for k, n in written.by_schema.items()},
            "sha256": written.sha256,
            **extra,
        },
        string_keys=("sha256", "overlay_id"),
    )


@app.command(name="world")
def world_command(
    profile: Annotated[str, typer.Option("--profile", help="A synthetic profile with a world.")],
    seed: SeedOption = None,
    out: OutOption = None,
) -> None:
    """Generate a synthetic profile's register (the world): C1 records and their manifest."""
    from neonradar_cli.data import profile_or_exit
    from neonradar_ingest.synth.commands import SynthError, make_world

    chosen = profile_or_exit(profile)
    try:
        written = make_world(chosen, seed, out, git_sha=_git_sha())
    except SynthError as exc:
        typer.echo(f"FAIL  {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from None
    _report(chosen.profile, "synth world", written, {})


@app.command(name="overlay")
def overlay_command(
    profile: Annotated[str, typer.Option("--profile", help="A synthetic profile with an overlay.")],
    seed: SeedOption = None,
    base: Annotated[
        Path | None,
        typer.Option(
            exists=True, file_okay=False, help="Base record folder (default: the profile's)."
        ),
    ] = None,
    out: OutOption = None,
) -> None:
    """Generate an overlay: accounts and background for the base's organisations, scenarios and
    look-alikes among new synthetic entities, label files v2 and overlay.json. A real profile
    passes the real-data gate and access.real_overlay_profiles first, and prints counts only."""
    from neonradar_cli import redact
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data.profiles import ProfileError
    from neonradar_ingest.synth.commands import SynthError, make_overlay

    project, chosen = project_or_exit(), profile_or_exit(profile)
    with redact.guard(chosen, "synth overlay") as where:
        if chosen.real_data:  # the gate step keeps no traceback on an unapproved machine
            from neonradar_ingest.data import gate

            where.step = "gate"
            gate.check_real_overlay(project, chosen)  # make_overlay checks it again
        where.step = "overlay"
        try:
            written = make_overlay(chosen, seed, base, out, project=project, git_sha=_git_sha())
        except (SynthError, ProfileError) as exc:
            if chosen.real_data:
                raise
            typer.echo(f"FAIL  {exc}", err=True)
            raise typer.Exit(code=exc.exit_code) from None
        where.step = "summary"  # a real profile's summary is written inside the guard too
        stats = written.stats
        _report(
            chosen.profile,
            "synth overlay",
            written,
            {
                "overlay_id": written.overlay_id,
                "eligible_organisations": stats["eligible_organisations"],
                "active_organisations": stats["active_organisations"],
                "skipped_organisations": stats["skipped_organisations"],
                "scenarios": stats["scenarios"],
            },
            real=chosen.real_data,
        )


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
