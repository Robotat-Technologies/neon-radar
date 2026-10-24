"""`neonradar graph`: commands for the Neo4j graph.

Two instances (C2 L17, PHASE-2.md M2.11): the default one holds synthetic data only; the
real-data instance (`--real`, or a load whose profile or manifests are real) is reached only
after the real-data gate of M2.2, inside the redaction guard, and every command on it prints
counts only.
"""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready
from neonradar_graph.instances import Instance, InstanceRefused
from neonradar_graph.migrate import MIGRATIONS_DIR, MigrationError, migrate
from neonradar_graph.smoke import run_smoke

if TYPE_CHECKING:  # imported inside the commands, so `neonradar --help` stays fast
    from neonradar_graph.loader import LoadReport
    from neonradar_ingest.data.profiles import Profile

app = typer.Typer(help="The Neo4j graph.", no_args_is_help=True)

Timeout = Annotated[float, typer.Option(help="Seconds to wait for Neo4j to accept connections.")]
Real = Annotated[
    bool,
    typer.Option(
        "--real",
        help="Address the real-data instance (neo4j-real): runs the real-data gate first and"
        " prints counts only.",
    ),
]
PASSWORDS = {Instance.DEFAULT: "NEO4J_PASSWORD", Instance.REAL: "NEO4J_REAL_PASSWORD"}


def _settings(instance: Instance = Instance.DEFAULT) -> Neo4jSettings:
    try:
        return instance.settings()
    except ValidationError:
        hint = "run `make up` (it creates .env) or export it" if instance is Instance.DEFAULT else (
            "set it on a machine listed in docs/data/real-data-machines.md"
        )  # fmt: skip
        typer.echo(f"FAIL  {PASSWORDS[instance]} is not set: {hint}")
        raise typer.Exit(code=1) from None
    except InstanceRefused as refused:
        typer.echo(f"FAIL  {refused}")
        raise typer.Exit(code=refused.exit_code) from None


@contextmanager
def _connected(settings: Neo4jSettings, timeout: float, *, real: bool = False) -> Iterator[Driver]:
    """A ready driver; exits 1 with one line when Neo4j cannot be reached or answers an error.
    On the real-data instance the line names the error class only (a server message could
    quote a value)."""
    where = "the real-data instance" if real else settings.uri
    try:
        with get_driver(settings) as driver:
            wait_until_ready(driver, timeout_s=timeout)
            yield driver
    except (DriverError, TimeoutError) as error:
        typer.echo(f"FAIL  Neo4j  not reachable at {where}: {_detail(error, real)}")
        raise typer.Exit(code=1) from None
    except Neo4jError as error:  # for example a wrong password or a failing statement
        typer.echo(f"FAIL  Neo4j  at {where} answered: {_detail(error, real)}")
        raise typer.Exit(code=1) from None


def _detail(error: Exception, real: bool) -> str:
    return type(error).__name__ if real else str(error)


@contextmanager
def _instance(real: bool, command: str) -> Iterator[Instance]:
    """The instance a command addresses. The real one: the real-data gate without a profile
    (M2.2 checks 3 to 5, refused while `access.real_data_profiles` is empty, exit 3) before any
    connection, then the redaction guard around the command."""
    if not real:
        yield Instance.DEFAULT
        return
    from neonradar_cli import redact
    from neonradar_cli.data import project_or_exit
    from neonradar_ingest.data import gate

    project = project_or_exit()
    with redact.guard(None, command, real=True) as where:
        where.step = "gate"
        gate.check_real_instance(project)
        where.step = command.split()[-1]
        yield Instance.REAL


@app.command(name="smoke")
def smoke_command(timeout: Timeout = 30) -> None:
    """Print the Neo4j version and edition, APOC and GDS; exit 1 if any is missing."""
    settings = _settings()
    with _connected(settings, timeout) as driver:
        report = run_smoke(driver, settings.database)
    for line in report.lines():
        typer.echo(line)
    if not report.ok:
        raise typer.Exit(code=1)


@app.command(name="migrate")
def migrate_command(
    directory: Annotated[
        Path,
        typer.Option(
            "--dir", exists=True, file_okay=False, help="Folder with NNNN_<name>.cypher files."
        ),
    ] = MIGRATIONS_DIR,
    real: Real = False,
    timeout: Timeout = 30,
) -> None:
    """Apply the pending schema migrations in order; re-running is a no-op."""
    with _instance(real, "graph migrate") as instance:
        settings = _settings(instance)
        with _connected(settings, timeout, real=real) as driver:
            try:
                report = migrate(driver, settings.database, directory)
            except MigrationError as error:
                typer.echo(f"FAIL  {error}")
                raise typer.Exit(code=1) from None
    for migration in report.applied:
        typer.echo(f"applied {migration.id} ({len(migration.statements)} statements)")
    if not report.applied:
        count = len(report.already_applied)
        typer.echo(f"nothing to apply ({count} migration{'s' * (count != 1)} already applied)")


SHOWN = 25  # issues printed per kind; the rest are counted


def _echo_some(lines: Sequence[object]) -> None:
    for line in lines[:SHOWN]:
        typer.echo(f"  {line}")
    if len(lines) > SHOWN:
        typer.echo(f"  ... and {len(lines) - SHOWN} more")


def _echo_counts(title: str, counts: Mapping[str, int]) -> None:
    typer.echo(f"{title}:")
    for name, count in sorted(counts.items()):
        typer.echo(f"  {name}: {count}")


def _fail(message: str, code: int) -> typer.Exit:
    typer.echo(f"FAIL  {message}")
    return typer.Exit(code=code)


def _resolution_dir(value: str | None, profile: Profile | None) -> Path | None:
    """`--resolution RUN_DIR`, or `latest` with `--profile`: the run whose id `er run` wrote last
    into LATEST, so an unfinished run is never loaded."""
    from neonradar_ingest.data import layout

    if value is None:
        return None
    if value != "latest":
        path = Path(value)
        if not path.is_dir():
            raise _fail(f"--resolution {value}: no such run folder", 2)
        return path
    if profile is None:
        raise _fail("--resolution latest needs --profile NAME", 2)
    run_id = layout.latest_run(profile)
    if run_id is None:
        raise _fail(
            f"profile {profile.profile} has no finished resolution run: run"
            f" `neonradar er run --profile {profile.profile}` first",
            2,
        )
    return layout.resolution_dir(profile, run_id)


def _instance_of(paths: Sequence[Path], profile: Profile | None) -> Instance:
    """L17: the profile's instance; without a profile, the real-data instance when every
    manifest of the files says the data is real (the loader checks every record again)."""
    from neonradar_graph import loader

    if profile is not None:
        return Instance.REAL if profile.real_data else Instance.DEFAULT
    try:
        manifests = [m for path in loader.collect_files(paths) if (m := loader.read_manifest(path))]
    except loader.LoadError as error:
        raise _fail(str(error), 1) from None
    real = bool(manifests) and not any(manifest.synthetic for manifest in manifests)
    return Instance.REAL if real else Instance.DEFAULT


def _echo_report(report: LoadReport) -> None:
    mode = "strict" if report.strict else "non-strict"
    typer.echo(f"{report.records} records from {len(report.files)} file(s), {mode}")
    for path in report.empty_files:
        typer.echo(f"WARN  {path} holds no records")
    _echo_counts("nodes by label", report.nodes_by_label)
    _echo_counts("relationships by type", report.relationships_by_type)
    written = report.written
    typer.echo(
        f"created {written['nodes_created']} nodes and {written['relationships_created']}"
        f" relationships; moved {written['relationships_deleted']} relationships; labels"
        f" {written['labels_added']} added and {written['labels_removed']} removed"
    )
    if report.resolution_run is not None:
        typer.echo(
            f"resolution run {report.resolution_run}: {report.canonical_entities} canonical"
            f" entities, {report.merged_entities} merged, {report.source_records} source"
            f" records, {report.possible_matches} possible matches (not confirmed)"
        )
    typer.echo(
        f"self-loops dropped: {report.self_loops_dropped}; duplicate relationships merged:"
        f" {report.duplicate_relationships_merged}; superseded nodes removed:"
        f" {report.superseded_removed}; references resolved through :SourceRecord:"
        f" {report.resolved_through_source_record}"
    )
    for title, items in (
        ("dangling references", report.dangling),
        ("records that failed C1, skipped", report.rejected),
        ("mapping issues, skipped", report.skipped),
    ):
        typer.echo(f"{title}: {len(items)}")
        _echo_some(items)


def _load_default(
    paths: Sequence[Path], run_dir: Path | None, replace: bool, strict: bool, timeout: float
) -> LoadReport:
    """A load into the default instance, with Phase 1's messages."""
    from neonradar_graph import loader
    from neonradar_graph.resolution import ResolutionError

    settings = _settings(Instance.DEFAULT)
    try:
        return loader.load(
            paths, run_dir, replace, Instance.DEFAULT, strict=strict, timeout_s=timeout
        )
    except loader.LoadRefused as refused:
        _echo_some([*refused.issues, *refused.skipped])
        typer.echo(f"REFUSED (strict): {refused}")
        raise typer.Exit(code=1) from None
    except (loader.LoadError, InstanceRefused, ResolutionError) as error:
        raise _fail(str(error), error.exit_code) from None
    except (DriverError, TimeoutError) as error:
        raise _fail(f"Neo4j  not reachable at {settings.uri}: {error}", 1) from None
    except Neo4jError as error:
        raise _fail(f"Neo4j  at {settings.uri} answered: {error}", 1) from None


@app.command(name="load")
def load_command(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            exists=True,
            help="C1 record files, or folders of *.ftm.jsonl files; one load. Without paths,"
            " --profile loads the profile's record folders.",
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="A profile in ingest/profiles/: its records and instance."),
    ] = None,
    resolution: Annotated[
        str | None,
        typer.Option(
            "--resolution",
            help="A resolution run folder, or `latest` with --profile (the run `er run` finished"
            " last).",
        ),
    ] = None,
    no_replace: Annotated[
        bool,
        typer.Option(
            "--no-replace",
            help="An additive load: keep what an earlier resolved load wrote (no L9 purge).",
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Strict (default): any C1 issue or mapping issue refuses the load before anything"
            " is written, and a dangling reference found while writing fails it (exit 1)."
            " Non-strict: skip and report.",
        ),
    ] = True,
    timeout: Timeout = 30,
) -> dict[str, Any]:
    """Load C1 records into the graph, through a resolution run when given; nodes before
    relationships; loading the same records twice leaves every count unchanged."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_graph import loader
    from neonradar_ingest.data import gate, layout

    if not paths and profile is None:
        raise _fail("give record paths or --profile NAME", 2)
    chosen = profile_or_exit(profile) if profile is not None else None
    project = project_or_exit() if chosen is not None else None
    folders = list(paths) if paths else chosen.record_dirs(project) if chosen else []
    instance = _instance_of(folders, chosen)
    if instance is Instance.DEFAULT:
        run_dir = _resolution_dir(resolution, chosen)
        report = _load_default(folders, run_dir, not no_replace, strict, timeout)
        _echo_report(report)
    else:
        with redact.guard(chosen, "graph load", real=True) as where:
            where.step = "gate"
            project = project or project_or_exit()
            if chosen is not None:
                gate.check_real_data(project, chosen)
                for dataset in chosen.enabled_sources(project):
                    where.dataset = dataset
                    gate.check_real_data(project, chosen, dataset)
            else:
                gate.check_real_instance(project)
            where.step, where.dataset = "load", None
            run_dir = _resolution_dir(resolution, chosen)
            _settings(Instance.REAL)
            report = loader.load(
                folders, run_dir, not no_replace, Instance.REAL, strict=strict, timeout_s=timeout
            )
            where.step = "summary"
            counts = {
                "profile": chosen.profile if chosen else None,
                "run_id": report.resolution_run,
            }
            name = chosen if chosen is not None else layout.ALL_PROFILES
            summary.emit(name, "graph load", {**counts, "instance_real": True, **report.counts()})
    if report.failed:
        typer.echo(
            f"FAILED (strict): {len(report.dangling)} dangling reference(s); the rest of the load"
            " was written: fix the input and load again"
        )
        raise typer.Exit(code=1)
    if instance is Instance.DEFAULT:
        warned = report.dangling or report.rejected or report.skipped or report.empty_files
        typer.echo(f"{'WARN' if warned else 'OK'} in {report.duration_s:.1f} s")
    return report.counts()


@app.command(name="verify")
def verify_command(real: Real = False, timeout: Timeout = 30) -> dict[str, int]:
    """Check the graph invariants I1 to I14: one line per invariant with its violation count
    (exit 1 on any violation)."""
    from neonradar_graph.verify import verify

    with _instance(real, "graph verify") as instance:
        settings = _settings(instance)
        with _connected(settings, timeout, real=real) as driver:
            counts = verify(driver, settings.database)
    for name, count in counts.items():
        typer.echo(f"{name}: {count}")
    total = sum(counts.values())
    typer.echo(f"{'FAIL' if total else 'OK'}  {total} violation(s) of {len(counts)} invariants")
    if total:
        raise typer.Exit(code=1)
    return counts


@app.command(name="stats")
def stats_command(real: Real = False, timeout: Timeout = 30) -> None:
    """Print node counts by label and relationship counts by type (apoc.meta.stats)."""
    from neonradar_graph import loader

    with _instance(real, "graph stats") as instance:
        settings = _settings(instance)
        with _connected(settings, timeout, real=real) as driver:
            counted = loader.stats(driver, settings.database)
    typer.echo(f"nodes: {counted.nodes}")
    for name, count in counted.labels.items():
        typer.echo(f"  {name}: {count}")
    typer.echo(f"relationships: {counted.relationships}")
    for name, count in counted.relationship_types.items():
        typer.echo(f"  {name}: {count}")


@app.command(name="wipe")
def wipe_command(
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm: delete every node except :SchemaMigration.")
    ] = False,
    real: Real = False,
    timeout: Timeout = 30,
) -> None:
    """Delete every node except :SchemaMigration; the schema stays. Refuses without --yes."""
    if not yes:
        typer.echo(
            "REFUSED  graph wipe deletes every node except :SchemaMigration; add --yes to confirm"
        )
        raise typer.Exit(code=1)
    from neonradar_graph import loader

    with _instance(real, "graph wipe") as instance:
        settings = _settings(instance)
        with _connected(settings, timeout, real=real) as driver:
            deleted = loader.wipe(driver, settings.database)
    where = "the real-data instance" if real else settings.uri
    typer.echo(f"deleted {deleted} nodes from {where} (database {settings.database})")
