"""`neonradar eval check` and `eval run` (PHASE-3.md M3.6, 7.6.1).

The settings come from the profile that `eval/seeds.yaml` names (`ingest/profiles/synth-eval.yaml`:
the world block, the overlay block and the detection overrides); each seed goes through the
verbatim `evaluate.run_seed`. `check` reruns the CI seed in memory and compares every count with
`eval/baselines/ci.json`. `run --split dev` writes the development figures into `eval_dir`.

`--split test` is the holdout run (G11): a person at a terminal, not CI, not Codespaces, after the
freeze. `--split` has no short form and no environment variable, and only the exact value `test`
selects it (reconciliation L6), so the agent hook sees every holdout call. Until M3.11 adds
`eval freeze --check` and wires it into `_holdout_gate`, the gate always refuses (exit 2).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Annotated, Any
from urllib.parse import urlsplit

import typer

from neonradar_cli import evaluate
from neonradar_cli.graph import Timeout, _connected, _settings
from neonradar_ingest.data.project import REPO_ROOT

if TYPE_CHECKING:
    from neo4j import Driver

    from neonradar_detect.catalog import Typology
    from neonradar_ingest.data.profiles import Profile

app = typer.Typer(help="Detection evaluation on synthetic worlds.", no_args_is_help=True)

SEEDS_FILE = REPO_ROOT / "eval" / "seeds.yaml"  # looked up per call, so tests can patch them
FREEZE_FILE = REPO_ROOT / "eval" / "freeze.json"
BASELINE_FILE = REPO_ROOT / "eval" / "baselines" / "ci.json"
HOLDOUT_SEEDS = 10
QUERY_TIMEOUT_S = 600.0  # PHASE-3.md 7.1.2 rule 6, as `detect run`
NON_SYNTHETIC_QUERY = "non_synthetic_nodes.cypher"  # in neonradar_graph's queries/
# The real-data instance (PHASE-2.md 1.1; `.env.example`): never wiped, never connected to here.
REAL_PORT = 7688
REAL_DATABASE = "realdata"
HOLDOUT_REFUSAL = "(G11)"  # the end of `evaluate.run_seed`'s holdout PermissionError


class EvalError(Exception):
    """A refusal or a failure; `exit_code` is the command's exit status."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class Seeds:
    profile: str
    dev: tuple[int, ...]
    ci: int
    test: frozenset[int]


def read_seeds() -> Seeds:
    import yaml

    try:
        data = yaml.safe_load(SEEDS_FILE.read_text(encoding="utf-8"))
        return Seeds(
            str(data["profile"]),
            tuple(int(s) for s in data["dev"]["seeds"]),
            int(data["ci"]["seed"]),
            evaluate.holdout_seeds(SEEDS_FILE),
        )
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as error:
        raise EvalError(f"cannot read {SEEDS_FILE.name}: {error}", 2) from None


def settings_from_profile(profile: Profile) -> evaluate.EvalSettings:
    """The world block, the overlay block and the detection overrides; `created_at` stays the
    fixed 2026-11-02T00:00:00Z of `EvalSettings`, so alert ids and texts never follow the clock."""
    world, block, detection = profile.world, profile.overlay, profile.detection
    if profile.real_data or world is None or block is None or not block.enabled:
        raise EvalError(f"profile {profile.profile} has no synthetic world and overlay", 2)
    if block.seed is not None:
        raise EvalError(f"profile {profile.profile}: the evaluation seeds the overlay too", 2)
    if detection is None or not detection.enabled or detection.window != "overlay":
        raise EvalError(f"profile {profile.profile}: evaluation needs detection.window overlay", 2)
    return evaluate.EvalSettings(
        profile.profile,
        world.config(),
        block.start,
        block.end,
        illicit=block.illicit,
        lookalikes=block.lookalikes,
        background=block.config(0).background,
        typologies=block.typology_slugs(),
        overrides=detection.overrides,
    )


def load_settings(name: str) -> evaluate.EvalSettings:
    from neonradar_ingest.data.profiles import ProfileError, load_profile

    try:
        return settings_from_profile(load_profile(name))
    except ProfileError as error:
        raise EvalError(str(error), 2) from None


def checked_params(cat: dict[str, Typology], settings: evaluate.EvalSettings) -> dict[str, Any]:
    unknown = sorted(set(settings.overrides) - set(cat))
    if unknown:
        raise EvalError(f"detection.overrides names unknown typologies: {', '.join(unknown)}", 2)
    try:
        return evaluate.detector_params(cat, settings.overrides)
    except (KeyError, ValueError) as error:
        raise EvalError(f"detection.overrides: {error}", 2) from None


def parse_seeds(text: str) -> list[int]:
    """`1-5`, `1,3,7` or a mix; sorted, each once."""
    seeds: set[int] = set()
    for part in text.split(","):
        found = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
        if not found or (found[2] and int(found[2]) < int(found[1])):
            raise EvalError(f"--seeds {text!r}: give seeds as 1-5 or 1,3,7", 2)
        seeds.update(range(int(found[1]), int(found[2] or found[1]) + 1))
    return sorted(seeds)


def neo4j_factory(driver: Driver, database: str) -> evaluate.SourceFactory:
    """Each seed: its records into a temporary folder, the default instance wiped and migrated,
    the folder loaded strictly by the project loader, and a `Neo4jSource` (7.6.1). Refuses
    before the wipe when the instance holds any non-synthetic node, or a record is not synthetic."""
    from neo4j import RoutingControl

    from neonradar_detect.neo4jsource import Neo4jSource
    from neonradar_graph import loader
    from neonradar_graph.migrate import migrate
    from neonradar_ingest.synth import writer

    guard = resources.files("neonradar_graph.queries").joinpath(NON_SYNTHETIC_QUERY)
    non_synthetic = guard.read_text(encoding="utf-8")

    def make(records: list[evaluate.Record]) -> Neo4jSource:
        if any(record.get("datasets") != ["nr_synthetic"] for record in records):
            raise EvalError("the seed has a non-synthetic record: nothing loaded (C2 L17)", 3)
        found, _, _ = driver.execute_query(
            non_synthetic, database_=database, routing_=RoutingControl.READ
        )
        if found[0]["n"]:
            raise EvalError(
                f"the default instance holds {found[0]['n']} non-synthetic nodes: eval run"
                " --engine neo4j wipes it, so it refuses (C2 L17)",
                3,
            )
        with TemporaryDirectory(prefix="nr-eval-") as tmp:
            Path(tmp, "nr_synthetic-eval.ftm.jsonl").write_text(
                writer.record_lines(records), encoding="utf-8"
            )
            loader.wipe(driver, database)
            migrate(driver, database)
            try:
                report = loader.load_files(driver, [Path(tmp)], strict=True, database=database)
            except (loader.LoadRefused, loader.LoadError) as error:
                raise EvalError(f"the loader refused the seed: {error}", 1) from None
        left_out = (len(report.dangling), len(report.rejected), len(report.skipped))
        if any(left_out):
            raise EvalError(
                f"the loader left records out (dangling, rejected, skipped: {left_out})", 1
            )
        return Neo4jSource(driver, database, timeout_s=QUERY_TIMEOUT_S)

    return make


def refuse_real_instance(uri: str, database: str) -> None:
    """`--engine neo4j` wipes NEO4J_URI: refuse (exit 3) when NEO4J_URI or NEO4J_DATABASE names
    the real-data instance (C2 L17, L18). Only the strings are compared, before any connection,
    so a misconfigured URI never reaches that instance even when it is empty."""
    from neonradar_ingest.settings import IngestSettings

    def port(text: str) -> int | None:
        try:
            return urlsplit(text.strip()).port
        except ValueError:  # a port that is not a number: nothing to compare
            return None

    real = IngestSettings().nr_neo4j_real_uri.strip()  # the environment, then `.env`
    ports = {REAL_PORT, port(real)} - {None}
    if (
        database.strip().lower() == REAL_DATABASE
        or port(uri) in ports
        or (real and uri.strip().rstrip("/") == real.rstrip("/"))
    ):
        raise EvalError(
            "NEO4J_URI or NEO4J_DATABASE names the real-data instance: eval run --engine neo4j"
            " wipes the graph it loads into, so it refuses (C2 L17)",
            3,
        )


@contextmanager
def _source_factory(engine: str, timeout: float) -> Iterator[evaluate.SourceFactory]:
    if engine == "memory":
        yield evaluate.memory_source
        return
    import logging

    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
    settings = _settings()
    refuse_real_instance(settings.uri, settings.database)
    with _connected(settings, timeout) as driver:
        yield neo4j_factory(driver, settings.database)


def alert_lines(alerts: Sequence[dict[str, Any]]) -> str:
    """`seed-<n>/alerts.jsonl`: each alert with `detector.query_sha256` set to the SHA-256 of the
    evidence query, as `detect run` sets it (reconciliation A1; the field is outside the alert id),
    and validated against C4 (PHASE-3.md 5.3); a failure names the fields, never a value."""
    from neonradar_detect import runs

    stamped = [
        {**alert, "detector": {**alert["detector"], "query_sha256": runs.EVIDENCE_SHA256}}
        for alert in alerts
    ]
    try:
        runs.validate(stamped)
    except runs.RunError as error:
        raise EvalError(str(error), 1) from None
    return "".join(json.dumps(alert, sort_keys=True) + "\n" for alert in stamped)


def ci_counts(seeds: Seeds, settings: evaluate.EvalSettings) -> dict[str, Any]:
    """The CI seed in memory, as a baseline document (`evaluate.baseline`)."""
    from neonradar_detect import catalog
    from neonradar_ingest.synth.namesource import default_names

    cat = catalog.load()
    checked_params(cat, settings)
    with TemporaryDirectory(prefix="nr-eval-check-") as tmp:
        run = evaluate.run_seed(
            seeds.ci, settings, default_names(), cat, "dev", Path(tmp), seeds_file=SEEDS_FILE
        )
    return evaluate.baseline(run)


def _guarded(body: Callable[[], None]) -> None:
    from neonradar_detect.catalog import CatalogError
    from neonradar_ingest.synth.commands import SynthError

    try:
        body()
    except (EvalError, SynthError) as error:
        typer.echo(f"FAIL  {error}", err=True)
        raise typer.Exit(code=error.exit_code) from None
    except PermissionError as error:
        # run_seed's holdout refusal (G11) exits 2 like the CLI's own; any other (the generator's
        # G1 guard, a file the system refuses) is a failure, exit 1.
        holdout = error.errno is None and str(error).endswith(HOLDOUT_REFUSAL)
        typer.echo(f"FAIL  {error}", err=True)
        raise typer.Exit(code=2 if holdout else 1) from None
    except CatalogError as error:
        typer.echo(f"FAIL  {error}", err=True)
        raise typer.Exit(code=1) from None


@app.command(name="check")
def check_command(
    baseline: Annotated[
        Path, typer.Option("--baseline", help="The CI baseline to compare with.")
    ] = BASELINE_FILE,
) -> None:
    """Rerun the CI seed in memory and compare every count with the baseline; exit 1 on any
    difference. Rows whose typology has no detector yet are pending, never failures."""

    def body() -> None:
        try:
            expected = json.loads(baseline.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise EvalError(f"cannot read the baseline {baseline}: {error}", 2) from None
        seeds = read_seeds()
        actual = ci_counts(seeds, load_settings(seeds.profile))
        differences, pending = evaluate.compare(actual, expected)
        for slug, counts in sorted(actual["typologies"].items()):
            own = [d for d in differences if d.startswith((f"{slug}.", f"{slug}:"))]
            shown = ", ".join(f"{key} {value}" for key, value in sorted(counts.items()))
            typer.echo(f"{'DIFF' if own else 'OK':<5} {slug}: {shown}")
            for line in own:
                typer.echo(f"      {line}")
        for line in differences:
            if line.startswith("seed "):
                typer.echo(f"DIFF  {line}")
        for slug in pending:
            typer.echo(f"PEND  {slug}: no detector yet (M3.5)")
        typer.echo(
            f"seed {seeds.ci}: checked {len(actual['typologies'])}, differences"
            f" {len(differences)}, pending {len(pending)}"
        )
        if differences:
            raise typer.Exit(code=1)

    _guarded(body)


def _holdout_gate() -> frozenset[int]:
    """The checks before a holdout run (G11), in order; the holdout seeds when all pass."""
    from neonradar_cli import tty

    try:
        tty.require_terminal("eval run --split test")
    except tty.TerminalRequired as error:
        raise EvalError(str(error), 2) from None
    if os.environ.get("CI") or os.environ.get("CODESPACES"):
        raise EvalError("the holdout run never runs in CI or in Codespaces (G11)", 2)
    if not FREEZE_FILE.is_file():
        raise EvalError(
            "no eval/freeze.json: the holdout runs only after the detection freeze (M3.11)", 2
        )
    differs = freeze_differences()
    if differs:
        raise EvalError(f"the configuration does not match the freeze: {'; '.join(differs)}", 2)
    return read_seeds().test


def freeze_differences() -> list[str]:
    """What differs from eval/freeze.json. M3.11 replaces this with `eval freeze --check`;
    until then nothing can show that the configuration equals the freeze, so it fails closed."""
    return ["the freeze check (`eval freeze --check`) comes with M3.11"]


def _write_run(
    folder: Path,
    runs: list[evaluate.SeedRun],
    params: dict[str, Any],
    cat: dict[str, Typology],
    meta: dict[str, Any],
) -> str:
    from neonradar_detect import runner
    from neonradar_detect.evaluation import harness, report
    from neonradar_detect.evaluation.match import RULES_VERSION
    from neonradar_ingest.synth import labels, writer

    modules = runner.detectors(cat)
    figures, bands = evaluate.figures(runs, list(modules))
    info = report.ReportMeta(
        **meta,
        seeds=tuple(r.seed for r in runs),
        generated_at=f"{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ}",
        generator_version=writer.GENERATOR_VERSION,
        label_schema=labels.LABEL_SCHEMA,
        rules_version=RULES_VERSION,
        params_sha256=runner.params_sha256(params),
        detectors={slug: module.VERSION for slug, module in modules.items()},
    )
    text = report.markdown(figures, bands, info)
    (folder / "report.md").write_text(text, encoding="utf-8")
    as_json = report.to_json(figures, bands, info)
    (folder / "report.json").write_text(json.dumps(as_json, indent=2) + "\n", encoding="utf-8")
    per_seed = {
        str(r.seed): {
            "record_sha256": r.record_sha256,
            "counts": r.counts,
            "seconds": r.seconds,
            "typologies": {s: harness.counts(o) for s, o in r.result.outcomes.items()},
        }
        for r in runs
    }
    (folder / "seeds.json").write_text(json.dumps(per_seed, indent=2) + "\n", encoding="utf-8")
    return text


@app.command(name="run")
def run_command(
    split: Annotated[
        str,
        typer.Option("--split", help="dev: development seeds. test: the holdout (a person only)."),
    ],
    seeds_text: Annotated[
        str | None,
        typer.Option("--seeds", help="Development seeds, 1-5 or 1,3,7 [default: every one]."),
    ] = None,
    engine: Annotated[
        str | None,
        typer.Option(
            "--engine",
            help="memory (the oracle; the default for dev) or neo4j (wipes NEO4J_URI first).",
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", file_okay=False, help="Folder [default: eval_dir(eval_id)]."),
    ] = None,
    timeout: Timeout = 30,
) -> None:
    """Run seeds and write the per-typology table of recall and precision with intervals."""

    def body() -> None:
        from neonradar_detect import catalog
        from neonradar_ingest.data import layout
        from neonradar_ingest.synth.commands import refuse_protected
        from neonradar_ingest.synth.namesource import default_names

        if split not in ("dev", "test"):
            raise EvalError(f"--split must be dev or test, not {split!r}", 2)
        holdout = split == "test"
        source = engine or ("neo4j" if holdout else "memory")
        if source not in ("memory", "neo4j"):
            raise EvalError(f"--engine must be memory or neo4j, not {engine!r}", 2)
        seeds = read_seeds()
        if holdout:
            if seeds_text is not None or out is not None or source != "neo4j":
                raise EvalError("the holdout run takes --engine neo4j and no --seeds or --out", 2)
            chosen = sorted(_holdout_gate())
            if len(chosen) != HOLDOUT_SEEDS:
                raise EvalError(f"eval/seeds.yaml must list {HOLDOUT_SEEDS} holdout seeds", 2)
        else:
            chosen = parse_seeds(seeds_text) if seeds_text else list(seeds.dev)
            outside = [s for s in chosen if s not in seeds.dev or s in seeds.test]
            if outside:
                raise EvalError(
                    f"not development seeds of eval/seeds.yaml: {', '.join(map(str, outside))}", 2
                )
        refuse_protected("--out", out)
        settings = load_settings(seeds.profile)
        cat = catalog.load()
        params = checked_params(cat, settings)
        eval_id = layout.new_run_id(f"eval-{split}")
        folder = out or (layout.holdout_dir if holdout else layout.eval_dir)(eval_id)
        if folder.exists() and any(folder.iterdir()):
            raise EvalError(f"{folder} is not empty", 2)
        names, runs = default_names(), []
        with _source_factory(source, timeout) as factory:
            folder.mkdir(parents=True, exist_ok=True)  # after the engine's refusals
            for seed in chosen:
                run = evaluate.run_seed(
                    seed, settings, names, cat, split, folder, factory,
                    allow_holdout=holdout, seeds_file=SEEDS_FILE,
                )  # fmt: skip
                alerts = alert_lines(run.alerts)
                (folder / f"seed-{seed}" / "alerts.jsonl").write_text(alerts, encoding="utf-8")
                # The holdout's figures stay in holdout_dir (M3.12 publishes them): no alert count
                shown = "" if holdout else f", {run.counts['alerts']} alerts"
                typer.echo(
                    f"seed {seed}: {run.counts['records']:,} records{shown}"
                    f" ({', '.join(f'{k} {v} s' for k, v in run.seconds.items())})"
                )
                runs.append(run)
        title = "Detection evaluation: " + ("holdout figures" if holdout else "development figures")
        meta = {"title": title, "split": split, "engine": source, "profile": settings.profile}
        table = _write_run(folder, runs, params, cat, meta)
        if not holdout:  # only the development run prints its table (M3.6 deliverable 3)
            typer.echo(table)
        typer.echo(f"wrote {folder}")

    _guarded(body)
