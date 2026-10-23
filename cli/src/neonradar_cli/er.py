"""`neonradar er ...`: entity resolution runs, settings and the benchmark (PHASE-2.md M2.10a,
M2.10b).

`er run` resolves a profile's record folders into `resolution_dir(profile, run_id)`, with the
profile's decisions file (`decisions_file(profile)`) and the settings file the profile names,
and writes the run id into `LATEST` last. On a real profile it runs the real-data gate first
and works inside the redaction guard; every summary holds counts only (M2.2). `er blocking`
counts the comparisons of the Splink blocking rules; `er bench` checks the G2-05 gates and
`er calibrate` writes the threshold table, both on the synthetic benchmark with one DuckDB thread.
`er sample`, `er label`, `er review` and `er precision` (M2.10c) live in `er_labelling.py`.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from neonradar_cli import er_labelling

if TYPE_CHECKING:  # imported inside the commands, so `neonradar --help` stays fast
    from neonradar_resolve.run import RunConfig, RunResult

app = typer.Typer(
    help="Entity resolution: runs, settings, the benchmark, sampling, labelling and review.",
    no_args_is_help=True,
)
# M2.10c (PHASE-2.md 7.3): er_labelling.py; `er label` and `er review` are for people only
app.command(name="sample")(er_labelling.sample_command)
app.command(name="label")(er_labelling.label_command)
app.command(name="review")(er_labelling.review_command)
app.command(name="precision")(er_labelling.precision_command)

DEFAULT_CONFIG = Path("resolve/config/er.yaml")
BENCH_FIXTURE = Path("data/fixtures/er-bench")
BENCH_SIZES = ("small", "large")
TRUTH = Path("labels/er_truth.csv")
CALIBRATION = Path("docs/data/er/benchmark.md")
LIBRARIES = ("splink", "duckdb", "pyarrow")  # string keys of the summaries' `versions`


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
        decisions = layout.decisions_file(chosen)  # only counted with --no-decisions
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
                use_decisions=not no_decisions,
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
            "decisions_used": not no_decisions,
            "probabilistic": not no_probabilistic,
            "splink": result.probabilistic,
            "counts": _lower_keys(result.counts),
            "timings": result.timings,
        }
        summary.emit(chosen, "er run", report, string_keys=LIBRARIES)


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


def _resolve_bench(
    size: str, seed: int | None, command: str, candidate_threshold: float | None = None
) -> tuple[Path, RunResult]:
    """Resolve the benchmark with the Splink models on one DuckDB thread (7.1.5)."""
    from dataclasses import replace

    from neonradar_cli import redact
    from neonradar_ingest.data import layout, retention
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import run

    if size not in BENCH_SIZES:
        raise typer.BadParameter(
            f"size must be one of {', '.join(BENCH_SIZES)}", param_hint="--size"
        )
    pseudo = f"er-bench-{size}"
    run_id = layout.new_run_id("er")
    with redact.guard(None, command), retention.spill_dir(pseudo, run_id) as temp:
        config = _run_config(
            REPO_ROOT / DEFAULT_CONFIG, profile=pseudo, temp=temp, keep=False, seniors=[]
        )
        resolver = config.resolver.with_threads(1)
        if candidate_threshold is not None:  # er calibrate scores down to 0.50 (this run only)
            resolver = resolver.model_copy(update={"candidate_threshold": candidate_threshold})
        config = replace(config, resolver=resolver)
        folder = _bench_records(size, seed if seed is not None else resolver.seed)
        result = run.run([folder], layout.resolution_dir(pseudo, run_id), config)
    return folder, result


SizeOption = Annotated[str, typer.Option("--size", help="small (the committed fixture) or large.")]
SeedOption = Annotated[int | None, typer.Option("--seed", min=0, help="Benchmark seed.")]


@app.command(name="bench")
def bench_command(size: SizeOption = "small", seed: SeedOption = None) -> None:
    """Resolve the synthetic benchmark, print the measures and check the G2-05 gates."""
    from neonradar_cli import summary
    from neonradar_resolve import bench

    folder, result = _resolve_bench(size, seed, "er bench")
    score = bench.measure(
        bench.read_truth(folder / TRUTH),
        result.members,
        result.result.canonical,
        result.result.candidates,
    )
    for line in bench.lines(score):
        typer.echo(line)
    failures = bench.gate_failures(score)
    for failure in failures:
        typer.echo(f"FAIL  gate: {failure}")
    if not failures:
        typer.echo("gates passed (G2-05) at the thresholds in er.yaml")
    report = {
        "profile": f"er-bench-{size}",
        "run_id": result.run_id,
        "probabilistic": True,
        "measures": bench.as_counts(score),
        "gates_failed": len(failures),
        "splink": result.probabilistic,
        "counts": _lower_keys(result.counts),
        "timings": result.timings,
    }
    summary.emit(f"er-bench-{size}", "er bench", report, string_keys=LIBRARIES, echo=False)
    if failures or score.left_out:
        raise typer.Exit(code=1)


@app.command(name="blocking")
def blocking_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
) -> None:
    """Comparisons per Splink blocking rule and the sizes of the five largest blocks.

    On a real profile it prints sizes only, never a block key (they are names and postcodes).
    For a rule over a list (linked organisations, name symbols, registration numbers, aliases)
    the comparison count is per shared element, but a block is a group of identical lists.
    """
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data import gate, layout, retention
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import features, models, records, scoring

    project, chosen = project_or_exit(), profile_or_exit(profile)
    if not chosen.resolution.enabled:
        typer.echo(f"FAIL  profile {chosen.profile} has resolution.enabled: false", err=True)
        raise typer.Exit(code=2)
    report: dict[str, Any] = {"profile": chosen.profile, "comparisons_by_rule": {}}
    report["largest_blocks"] = {}
    with redact.guard(chosen, "er blocking") as where:
        where.step = "gate"
        gate.check_real_data(project, chosen)
        for dataset in chosen.enabled_sources(project):
            where.dataset = dataset
            gate.check_real_data(project, chosen, dataset)
        where.step, where.dataset = "blocking", None
        run_id = layout.new_run_id("er")
        with retention.spill_dir(chosen, run_id) as temp:
            config = _run_config(
                REPO_ROOT / chosen.resolution.config, profile=chosen.profile, temp=temp,
                keep=False, seniors=[],
            )  # fmt: skip
            corpus = records.read(chosen.record_dirs(project))
            members = features.members(corpus)
            tables = dict(zip(scoring.KINDS, features.feature_tables(corpus, members), strict=True))
            duck = config.resolver.duckdb
            con = models.connect(duck.threads, duck.memory_limit, str(temp / "splink"))
            try:
                for kind, table in tables.items():
                    counts = scoring.count_comparisons(con, kind, table) if len(table) > 1 else []
                    blocks = scoring.largest_blocks(con, kind, table) if counts else []
                    report["comparisons_by_rule"][kind] = {
                        f"rule_{n}": c for n, c in enumerate(counts, 1)
                    }
                    report["largest_blocks"][kind] = {
                        f"rule_{n}": [int(b["count_l"]) for b in found]
                        for n, found in enumerate(blocks, 1)
                    }
                    _echo_blocks(kind, counts, blocks, keys=not chosen.real_data)
            finally:
                con.close()
        summary.emit(chosen, "er blocking", _flatten_blocks(report), echo=False)


def _echo_blocks(
    kind: str, counts: list[int], blocks: list[list[dict[str, Any]]], *, keys: bool
) -> None:
    """One line per rule; the block keys only when `keys` (synthetic profiles: they help tune
    the rules; on a real profile they are names and postcodes)."""
    from neonradar_resolve import scoring

    lists = scoring.explodes(kind)  # type: ignore[arg-type]
    for n, (count, found) in enumerate(zip(counts, blocks, strict=True), 1):
        sizes = ", ".join(str(int(b["count_l"])) for b in found)
        whole = " (records with the same whole list)" if lists[n - 1] else ""
        typer.echo(f"{kind} rule {n}: {count} comparisons;"
                   f" largest blocks (records){whole}: {sizes or 'none'}")  # fmt: skip
        for b in found if keys else []:
            values = [str(v) for k, v in sorted(b.items()) if k.startswith("key_")]
            typer.echo(f"    {int(b['count_l'])}: {' | '.join(values)}")


def _flatten_blocks(report: dict[str, Any]) -> dict[str, Any]:
    """Summaries hold numbers in dicts, not lists: block sizes become block_1 to block_5."""
    blocks = {
        kind: {rule: {f"block_{i}": v for i, v in enumerate(sizes, 1)} for rule, sizes in r.items()}
        for kind, r in report["largest_blocks"].items()
    }
    return {**report, "largest_blocks": blocks}


@app.command(name="calibrate")
def calibrate_command(
    size: SizeOption = "large",
    seed: SeedOption = None,
    output: Annotated[
        Path, typer.Option("--output", help="Where to write the calibration table.")
    ] = CALIBRATION,
) -> None:
    """Score the benchmark once down to 0.50, re-cluster at each threshold of the sweep and
    write the table and the proposed thresholds (7.1.7). Never edits er.yaml."""
    from neonradar_cli import summary
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import bench, calibrate, scoring
    from neonradar_resolve.config import load_config

    folder, result = _resolve_bench(size, seed, "er calibrate", min(calibrate.SWEEP))
    resolver, sha = load_config(REPO_ROOT / DEFAULT_CONFIG)
    points = calibrate.sweep(
        bench.read_truth(folder / TRUTH),
        result.members,
        result.deterministic,
        scoring.read_pairs(result.run_dir / "pairs.parquet"),
        result.hints,
        resolver,
    )
    proposal = calibrate.propose(points)
    used = seed if seed is not None else resolver.seed
    text = calibrate.document(points, proposal, resolver, size, used, result.probabilistic or {})
    target = output if output.is_absolute() else REPO_ROOT / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    for line in calibrate.table(points):
        typer.echo(line)
    for name, value in proposal.items():
        typer.echo(f"proposed {name}: {'none passes' if value is None else value}")
    typer.echo(
        f"wrote {output} (er.yaml is not changed: the tech lead and the graph mentor set it)"
    )
    report = {
        "profile": f"er-bench-{size}",
        "run_id": result.run_id,
        "config_sha256": sha,
        "proposal": proposal,
        "splink": result.probabilistic,
        "timings": result.timings,
    }
    summary.emit(f"er-bench-{size}", "er calibrate", report, string_keys=LIBRARIES, echo=False)
