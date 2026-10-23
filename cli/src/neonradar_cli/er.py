"""`neonradar er ...`: entity resolution runs, settings and the benchmark (PHASE-2.md M2.10a).

`er run` resolves a profile's record folders into `resolution_dir(profile, run_id)`, with the
profile's decisions file (`decisions_file(profile)`) and the settings file the profile names,
and writes the run id into `LATEST` last. On a real profile it runs the real-data gate first
and works inside the redaction guard; every summary holds counts only (M2.2).
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:  # imported inside the commands, so `neonradar --help` stays fast
    from neonradar_resolve.run import RunConfig

app = typer.Typer(help="Entity resolution: runs, settings and the benchmark.", no_args_is_help=True)

DEFAULT_CONFIG = Path("resolve/config/er.yaml")
BENCH_FIXTURE = Path("data/fixtures/er-bench")
BENCH_SIZES = ("small", "large")
TRUTH = Path("labels/er_truth.csv")


def _lower_keys(value: Any) -> Any:
    """Summary keys are lower-case names (M2.2), so rule ids such as D1 are written d1."""
    if isinstance(value, Mapping):
        return {str(k).lower(): _lower_keys(v) for k, v in value.items()}
    return value


def _run_config(
    config_path: Path,
    *,
    profile: str,
    temp: Path,
    keep: bool,
    seniors: list[str],
    reviewers: frozenset[str] | None = None,
) -> RunConfig:
    from neonradar_resolve.config import load_config
    from neonradar_resolve.run import RunConfig

    try:
        resolver, sha = load_config(config_path)
    except (OSError, ValueError) as exc:
        typer.echo(f"FAIL  settings file {config_path.name}: {exc}", err=True)
        raise typer.Exit(code=2) from None
    return RunConfig(
        resolver,
        sha,
        senior_reviewers=frozenset(seniors),
        reviewers=reviewers,
        profile=profile,
        temp_directory=temp,
        keep_features=keep,
    )


def _reviewers(project: Any) -> frozenset[str]:
    """Who may decide on a real profile: people.er_labellers and er_senior_reviewers (fail
    closed: while both hold only placeholders, every decision line is refused)."""
    from neonradar_resolve.rules import handle

    people = project.people
    listed = [*people.er_labellers, *people.er_senior_reviewers]
    return frozenset(h for value in listed if (h := handle(value)))


def _thresholds(config: RunConfig) -> dict[str, Any]:
    resolver = config.resolver
    return {
        "merge_threshold": dict(sorted(resolver.merge_threshold.items())),
        "candidate_threshold": resolver.candidate_threshold,
        "cluster_cap": resolver.cluster_cap,
        "name_check_jaro_winkler": resolver.name_check_jaro_winkler,
    }


@app.command(name="run")
def run_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    no_probabilistic: Annotated[
        bool, typer.Option("--no-probabilistic", help="Deterministic rules and decisions only.")
    ] = False,
    no_decisions: Annotated[
        bool, typer.Option("--no-decisions", help="Ignore the decisions file (evaluation runs).")
    ] = False,
    keep_features: Annotated[
        bool, typer.Option("--keep-features", help="Keep features.duckdb in the run folder.")
    ] = False,
) -> None:
    """Resolve a profile's records; print and write a counts-only summary."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data import gate, layout, retention
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import __version__ as resolver_version
    from neonradar_resolve import run

    project, chosen = project_or_exit(), profile_or_exit(profile)
    if not chosen.resolution.enabled:
        typer.echo(f"FAIL  profile {chosen.profile} has resolution.enabled: false", err=True)
        raise typer.Exit(code=2)
    with redact.guard(chosen, "er run") as where:
        where.step = "gate"
        gate.check_real_data(project, chosen)
        for dataset in chosen.enabled_sources(project):
            where.dataset = dataset
            gate.check_real_data(project, chosen, dataset)
        where.step, where.dataset = "resolve", None
        run_id = layout.new_run_id("er")
        run_dir = layout.resolution_dir(chosen, run_id)
        decisions = None if no_decisions else layout.decisions_file(chosen)
        with retention.spill_dir(chosen, run_id) as temp:
            config = _run_config(
                REPO_ROOT / chosen.resolution.config,
                profile=chosen.profile,
                temp=temp,
                keep=keep_features,
                seniors=project.people.er_senior_reviewers,
                reviewers=_reviewers(project) if chosen.real_data else None,
            )
            result = run.run(
                chosen.record_dirs(project),
                run_dir,
                config,
                decisions_file=decisions,
                probabilistic=not no_probabilistic,
            )
        (run_dir.parent / layout.LATEST).write_text(f"{run_id}\n", encoding="utf-8")
        report = {
            "profile": chosen.profile,
            **project.summary_fields(),
            "run_id": run_id,
            "resolver_version": resolver_version,
            "config_sha256": config.config_sha256,
            "thresholds": _thresholds(config),
            "seed": config.resolver.seed,
            "decisions_used": decisions is not None,
            "probabilistic": False,
            "counts": _lower_keys(result.counts),
            "timings": result.timings,
        }
        summary.emit(chosen, "er run", report)


@app.command(name="show-config")
def show_config_command(
    profile: Annotated[
        str | None, typer.Option("--profile", help="Show the file this profile names.")
    ] = None,
) -> None:
    """Print the validated resolver settings (resolve/config/er.yaml) and their SHA-256."""
    from neonradar_cli.data import profile_or_exit
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve.config import load_config

    relative = profile_or_exit(profile).resolution.config if profile else str(DEFAULT_CONFIG)
    try:
        config, sha = load_config(REPO_ROOT / relative)
    except (OSError, ValueError) as exc:
        typer.echo(f"FAIL  settings file {relative}: {exc}", err=True)
        raise typer.Exit(code=2) from None
    shown = {"file": relative, "sha256": sha, **config.model_dump()}
    typer.echo(json.dumps(shown, indent=2, sort_keys=True))


def _bench_records(size: str, seed: int) -> Path:
    """The committed fixture for `small` with its seed; otherwise a generated benchmark."""
    from neonradar_ingest.data.layout import bench_dir
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_ingest.synth import ER_BENCH_SEED
    from neonradar_ingest.synth.erbench import write_er_bench

    if size == "small" and seed == ER_BENCH_SEED:
        return REPO_ROOT / BENCH_FIXTURE
    folder = bench_dir(size)
    write_er_bench(folder, size, seed)
    return folder


@app.command(name="bench")
def bench_command(
    size: Annotated[str, typer.Option("--size", help="small (the committed fixture) or large.")] = (
        "small"
    ),
    seed: Annotated[int | None, typer.Option("--seed", min=0, help="Benchmark seed.")] = None,
) -> None:
    """Resolve the synthetic benchmark and print precision, recall and policy measures."""
    from neonradar_cli import summary
    from neonradar_ingest.data import layout, retention
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import bench, run

    if size not in BENCH_SIZES:
        raise typer.BadParameter(
            f"size must be one of {', '.join(BENCH_SIZES)}", param_hint="--size"
        )
    pseudo = f"er-bench-{size}"
    run_id = layout.new_run_id("er")
    with retention.spill_dir(pseudo, run_id) as temp:
        config = _run_config(
            REPO_ROOT / DEFAULT_CONFIG, profile=pseudo, temp=temp, keep=False, seniors=[]
        )
        folder = _bench_records(size, seed if seed is not None else config.resolver.seed)
        result = run.run(
            [folder], layout.resolution_dir(pseudo, run_id), config, probabilistic=False
        )
    score = bench.measure(
        bench.read_truth(folder / TRUTH),
        result.members,
        result.result.canonical,
        result.result.candidates,
    )
    measures = bench.as_counts(score)
    for line in bench.lines(score):
        typer.echo(line)
    report = {
        "profile": pseudo,
        "run_id": run_id,
        "probabilistic": False,
        "measures": measures,
        "counts": _lower_keys(result.counts),
    }
    summary.emit(pseudo, "er bench", report, echo=False)
    if score.hard_negatives_merged or score.left_out:
        raise typer.Exit(code=1)
