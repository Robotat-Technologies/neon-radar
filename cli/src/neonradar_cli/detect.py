"""`neonradar detect ...`: detection runs over the graph (PHASE-1.md M1.9b; PHASE-3.md M3.2).

`run` resolves what a run needs (the profile, the catalog and parameters, the source, the window),
then `neonradar_detect.runs.run` runs the detectors through the verbatim runner, validates every
alert against C4, writes the run folder and, on Neo4j, loads the results (C2 L19). Real profiles
come with M3.4: here they are refused before anything is read.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import ExitStack
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from neonradar_cli.graph import Timeout, _connected, _settings

if TYPE_CHECKING:
    from neonradar_detect.catalog import Typology
    from neonradar_detect.runs import RunRecord
    from neonradar_detect.source import Source, Window
    from neonradar_ingest.data.profiles import Profile

app = typer.Typer(help="Detection runs.", no_args_is_help=True)

QUERY_TIMEOUT_S = 600.0  # PHASE-3.md 7.1.2 rule 6


def _quiet_notifications() -> None:
    """The server's query notifications (for example 01N52, a property no node has on this
    graph) go to the driver's log at WARNING with the query text; the query-plan test checks
    them in CI (PHASE-3.md 7.1.6), so a run prints only errors."""
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)


def _fail(message: str, code: int = 1) -> typer.Exit:
    typer.echo(f"FAIL  {message}")
    return typer.Exit(code=code)


def _profile(name: str, engine: str) -> Profile:
    from neonradar_ingest.data.profiles import ProfileError, load_profile

    try:
        profile = load_profile(name)
    except ProfileError as error:
        raise _fail(str(error), 2) from None
    if profile.real_data:
        raise _fail(f"profile {name} is a real profile: detection on real data comes with M3.4", 2)
    if profile.detection is not None and not profile.detection.enabled:
        raise _fail(f"profile {name} turns detection off (detection.enabled: false)", 2)
    if engine == "memory" and profile.resolution.enabled:
        raise _fail(
            f"profile {name} resolves entities; the memory engine reads records one node per"
            " record, so it needs a profile without resolution (use --engine neo4j)",
            2,
        )
    return profile


def _overlay_folder(profile: Profile) -> Path | None:
    """The latest overlay of a profile with an enabled overlay block, else None."""
    from neonradar_ingest.data import layout

    if profile.overlay is None or not profile.overlay.enabled:
        return None
    overlay_id = layout.latest_overlay(profile)
    if overlay_id is None:
        raise _fail(f"no overlay for {profile.profile}: run `neonradar synth overlay` first", 2)
    return layout.overlay_dir(profile, overlay_id)


def _memory_source(profile: Profile | None, overlay: Path | None) -> Source:
    from neonradar_detect import runs
    from neonradar_detect.graphrows import from_records
    from neonradar_detect.memsource import MemSource
    from neonradar_ingest.data.profiles import ProfileError

    try:
        folders = [runs.DEMO_MINI] if profile is None else profile.record_dirs()
    except ProfileError as error:
        raise _fail(str(error), 2) from None
    records = runs.records_in([*folders, *([overlay] if overlay else [])])
    if not all(record.get("datasets") == ["nr_synthetic"] for record in records):
        raise _fail("the memory engine reads synthetic records only", 2)
    return MemSource(from_records(records))


def _window(
    source: Source, given: list[str] | None, profile: Profile | None, overlay: Path | None
) -> tuple[Window, bool]:
    """`--window`, else the profile's `detection.window`, else the PAID time range (whole days);
    the flag is False when there is nothing to read a window from."""
    from neonradar_detect import runs

    if given:
        return runs.window_of(given[0], given[1]), True
    kind = profile.detection.window if profile and profile.detection else "data"
    if kind == "overlay":
        if overlay is None:
            raise runs.RunError("detection.window is overlay, but the profile has no overlay")
        return runs.overlay_window(overlay / "overlay.json"), True
    return runs.data_window(source)


def _params(
    catalog: dict[str, Typology], chosen: list[str] | None, profile: Profile | None
) -> dict[str, Any]:
    """Each selected typology's Params: catalog defaults and the profile's overrides."""
    from neonradar_detect import catalog as catalog_module
    from neonradar_detect import runner

    try:  # a detector module missing, a SLUG that differs, a typology outside runner.ORDER
        modules = runner.detectors(catalog)
    except (ImportError, ValueError) as error:
        raise _fail(f"cannot load the detectors: {error}") from None
    if chosen:
        for slug in chosen:
            if slug not in catalog:
                known = ", ".join(sorted(catalog))
                raise _fail(f"unknown typology {slug!r}; known: {known}")
            if slug not in modules:
                raise _fail(f"typology {slug} has no detector yet (detector: null)")
    overrides = profile.detection.overrides if profile and profile.detection else {}
    unknown = sorted(set(overrides) - set(catalog))
    if unknown:
        raise _fail(f"detection.overrides names unknown typologies: {', '.join(unknown)}", 2)
    params: dict[str, Any] = {}
    for slug, module in modules.items():
        if chosen and slug not in chosen:
            continue
        try:
            params[slug] = catalog_module.params_for(catalog[slug], module, overrides.get(slug))
        except (KeyError, ValueError, TypeError) as error:
            raise _fail(f"detection.overrides: {error}", 2) from None
    return params


def _print(record: RunRecord) -> None:
    typer.echo(
        f"{record.run_id}  {len(record.alerts)} alerts  ({', '.join(record.typologies)})"
        f"  engine {record.engine}"
    )
    for slug, counts in record.summary.get("typologies", {}).items():
        withheld = sum(counts["withheld"].values())
        typer.echo(
            f"  {slug}: {counts['findings']} findings, {counts['alerts']} alerts,"
            f" {counts['duplicates']} duplicates, {withheld} withheld"
        )
    for alert in record.alerts:
        typer.echo(f"  {alert.alert_id}  {alert.priority:<6}  {alert.headline}")
    typer.echo(f"wrote {record.directory}")


@app.command(name="run")
def run_command(
    profile_name: Annotated[
        str | None,
        typer.Option(
            "--profile", help="A synthetic profile (ingest/profiles/) [default: none, demo-mini]."
        ),
    ] = None,
    typology: Annotated[
        list[str] | None,
        typer.Option(
            "--typology", help="Run this typology; repeat for more [default: every detector]."
        ),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            help="Run id, run-<UTC yyyymmddThhmmss>-<4 hex> [default: a new one]. Given again"
            " with --keep-previous, the run replaces that run's files and keeps in Neo4j only the"
            " alerts it finds now.",
        ),
    ] = None,
    engine: Annotated[
        str,
        typer.Option(
            "--engine",
            help="neo4j: the graph at NEO4J_URI, then the L19 load. memory: the oracle over the"
            " profile's records (demo-mini without a profile); writes the run folder only.",
        ),
    ] = "neo4j",
    window: Annotated[
        tuple[str, str] | None,
        typer.Option(
            "--window",
            help="START END as UTC dates or times, END excluded [default: the profile's"
            " detection.window, else the PAID time range in whole days].",
        ),
    ] = None,
    keep_previous: Annotated[
        bool,
        typer.Option(
            "--keep-previous", help="Keep earlier :Alert and :DetectionRun nodes (comparisons)."
        ),
    ] = False,
    timeout: Timeout = 30,
) -> None:
    """Run the detectors, write data/runs/<run_id>/ and, on Neo4j, replace the detection results."""
    from neonradar_detect import catalog, runs
    from neonradar_detect.neo4jsource import Neo4jSource
    from neonradar_ingest.data.project import load_project

    if engine not in ("neo4j", "memory"):
        raise _fail(f"--engine must be neo4j or memory, not {engine!r}", 2)
    profile = _profile(profile_name, engine) if profile_name else None
    try:
        typologies = catalog.load()
    except (catalog.CatalogError, OSError) as error:
        raise _fail(f"cannot read the typology catalog: {error}") from None
    params = _params(typologies, typology, profile)
    try:
        chosen_id = runs.check_run_id(run_id) if run_id else runs.new_run_id(runs.now_utc())
    except runs.RunError as error:
        raise _fail(str(error)) from None
    real_registry_alerts = load_project().access.real_registry_alerts
    overlay = _overlay_folder(profile) if profile else None
    with ExitStack() as stack:
        load: Callable[[RunRecord], None] | None = None
        if engine == "memory":
            source = _memory_source(profile, overlay)
        else:
            _quiet_notifications()
            settings = _settings()
            driver = stack.enter_context(_connected(settings, timeout))
            source = Neo4jSource(driver, settings.database, timeout_s=QUERY_TIMEOUT_S)
            load = partial(runs.store, driver, settings.database, keep_previous=keep_previous)
        try:
            span, known = _window(source, list(window) if window else None, profile, overlay)
            record = runs.run(
                source,
                params,
                span,
                typologies,
                run_id=chosen_id,
                engine="memory" if engine == "memory" else "neo4j",
                profile=profile.profile if profile else None,
                window_known=known,
                real_registry_alerts=real_registry_alerts,
                load=load,
            )
        except (runs.RunError, OSError) as error:
            raise _fail(str(error)) from None
    _print(record)


@app.command(name="list")
def list_command() -> None:
    """Every typology: version, status, tier, and its detector's version if it has one."""
    from importlib import import_module

    from neonradar_detect import catalog

    try:
        typologies = catalog.load_catalog()
    except catalog.CatalogError as error:
        raise _fail(str(error)) from None
    with_detector = 0
    for slug, item in sorted(typologies.items()):
        detector = "no detector"
        own = f"{catalog.DETECTOR_PACKAGE}.{slug}"
        if item.detector and item.detector != own:
            # Never import a module path read from a file: only the package's own module for
            # the slug, the one module catalog.load() lets the runner import (reconciliation C5).
            detector = f"detector must be {own}"
        elif item.detector:
            try:
                module = import_module(item.detector)
                detector = f"{item.detector} {module.VERSION}"
                with_detector += 1
            except ImportError, AttributeError:
                detector = f"{item.detector} missing"
        typer.echo(f"{slug}  {item.version}  {item.status}  {item.tier}  {detector}")
    typer.echo(f"{with_detector} of {len(typologies)} typologies have a detector")


@app.command(name="verify-alert")
def verify_alert_command(
    alert_id: Annotated[str | None, typer.Argument(help="One alert id.")] = None,
    run: Annotated[
        str | None,
        typer.Option(
            "--run", help="Every alert of a run: a run id, or `latest` (data/runs/LATEST)."
        ),
    ] = None,
    profile_name: Annotated[
        str | None,
        typer.Option("--profile", help="A synthetic profile (its runs are in data/runs/)."),
    ] = None,
    timeout: Timeout = 30,
) -> None:
    """Run each alert's evidence query; exit 1 unless all its evidence nodes and edges exist."""
    from neonradar_detect import runs

    if (alert_id is None) == (run is None):
        raise _fail("give one ALERT_ID or --run RUN_ID (or --run latest)", 2)
    if profile_name:
        _profile(profile_name, "neo4j")
    _quiet_notifications()
    settings = _settings()
    with _connected(settings, timeout) as driver:
        try:
            if run is not None:
                run_id = runs.latest() if run == "latest" else runs.check_run_id(run)
                meta = runs.read_run(run_id)
                if meta.get("status") != "ok":  # LATEST names a run even when it failed
                    raise _fail(f"run {run_id} failed: nothing to verify")
                if meta.get("engine") == "memory":
                    raise _fail(f"run {run_id} ran in memory: its alerts are not in the graph", 2)
                ids = runs.run_alert_ids(driver, settings.database, run_id)
                if len(ids) != meta.get("alert_count"):
                    raise _fail(
                        f"run {run_id}: the graph holds {len(ids)} of its"
                        f" {meta.get('alert_count')} alerts (a later run replaced them?)"
                    )
            else:
                ids = [str(alert_id)]
            checks = list(runs.verify(driver, settings.database, ids))
        except runs.RunError as error:
            raise _fail(str(error)) from None
    failed = 0
    for check in checks:
        if check.ok:
            typer.echo(f"OK    {check.alert_id}  {check.nodes} nodes, {check.edges} relationships")
            continue
        failed += 1
        reason = (
            "its evidence query is not queries/evidence.cypher"
            if not check.own_query
            else f"{check.missing_nodes} of {check.nodes} nodes and {check.missing_edges} of"
            f" {check.edges} relationships missing"
        )
        typer.echo(f"FAIL  {check.alert_id}  {reason}")
    typer.echo(f"{len(checks) - failed} of {len(checks)} alerts verified")
    if failed:
        raise typer.Exit(code=1)
