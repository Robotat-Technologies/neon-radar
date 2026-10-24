"""`neonradar data ...`: profiles, downloads, status and purge (PHASE-2.md M2.2 deliverable 11).

Every command that touches a real profile runs the real-data gate first and prints counts only
(`summary.emit`); its errors go through `redact.guard`.
"""

from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:  # imported inside the commands, so `neonradar --help` stays fast
    from neonradar_ingest.data.profiles import Profile
    from neonradar_ingest.data.project import Project

app = typer.Typer(help="Data manager: profiles, downloads, status and purge.", no_args_is_help=True)

GB = 1000**3
ProfileOption = Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")]
DatasetOption = Annotated[
    str | None, typer.Option("--dataset", help="Only this dataset (a slug of contracts/datasets).")
]


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def project_or_exit() -> Project:
    from neonradar_ingest.data.project import load_project

    try:
        return load_project()
    except (OSError, ValueError) as exc:
        typer.echo(f"FAIL  project file: {exc}", err=True)
        raise typer.Exit(code=2) from None


def profile_or_exit(name: str) -> Profile:
    from neonradar_ingest.data.profiles import ProfileError, load_profile

    try:
        return load_profile(name)
    except ProfileError as exc:
        typer.echo(f"FAIL  {exc}", err=True)
        raise typer.Exit(code=2) from None


def selected(project: Project, profile: Profile, dataset: str | None) -> list[str]:
    """The datasets a command runs: every enabled one, or `dataset` if the profile enables it."""
    enabled = profile.enabled_sources(project)
    if dataset is None:
        return enabled
    if dataset not in enabled:
        refused = profile.refused_sources(project).get(dataset)
        reason = refused or f"{dataset} is not enabled in profile {profile.profile}"
        typer.echo(f"FAIL  {reason}", err=True)
        raise typer.Exit(code=2)
    return [dataset]


def run_prechecks(
    profile: Profile, command: str, report: dict[str, object], datasets: list[str]
) -> None:
    """Each dataset's `SourceSpec.precheck` (the UN list's written permission), after the gate
    and before any request or build. A refusal prints the dataset, the rule and the message,
    writes the summary with the refused datasets and exits 3: nothing is fetched or built."""
    from neonradar_cli import summary
    from neonradar_ingest.data import sources
    from neonradar_ingest.data.gate import RealDataRefused

    refused: dict[str, RealDataRefused] = {}
    for slug in datasets:
        spec = sources.source_spec(slug)
        if spec is not None and spec.precheck is not None:
            try:
                spec.precheck()
            except RealDataRefused as refusal:
                refused[slug] = refusal
    if not refused:
        return
    for slug, error in refused.items():
        typer.echo(f"{slug}: refused (rule {error.rule}): {error.message}", err=True)
    datasets_report = {slug: {"status": "refused", "rule": e.rule} for slug, e in refused.items()}
    summary.emit(profile, command, {**report, "datasets": datasets_report})
    raise typer.Exit(code=RealDataRefused.exit_code)


@app.command(name="profiles")
def profiles_command() -> None:
    """The profiles, whether each may run on this machine, and the datasets each enables."""
    from neonradar_ingest.data import gate
    from neonradar_ingest.data.profiles import profile_names

    project = project_or_exit()
    for name in profile_names():
        profile = profile_or_exit(name)
        if not profile.real_data:
            typer.echo(f"{name}: synthetic data; may run on this machine: yes")
        else:
            checks = gate.conditions(project, name)
            allowed = all(check.passed for check in checks)
            typer.echo(f"{name}: real data; may run on this machine: {_yes_no(allowed)}")
            for check in checks:
                typer.echo(f"  {check.label}: {_yes_no(check.passed)}")
        typer.echo(f"  datasets: {', '.join(profile.enabled_sources(project)) or 'none'}")
        for message in profile.refused_sources(project).values():
            typer.echo(f"  not allowed: {message}")


@app.command(name="fetch")
def fetch_command(profile: ProfileOption, dataset: DatasetOption = None) -> dict[str, Any]:
    """Run the gate, then download the current files of every enabled source."""
    from neonradar_cli import redact, summary
    from neonradar_ingest.data import download, gate, sources
    from neonradar_ingest.data.profiles import SYNTHETIC

    project, chosen = project_or_exit(), profile_or_exit(profile)
    failed = 0
    with redact.guard(chosen, "data fetch") as where:
        where.step = "gate"
        gate.check_real_data(project, chosen, dataset)
        datasets = [slug for slug in selected(project, chosen, dataset) if slug != SYNTHETIC]
        for slug in datasets:  # every dataset passes the gate before the first request
            where.dataset = slug
            gate.check_real_data(project, chosen, slug)
        where.dataset = None
        report: dict[str, object] = {"profile": chosen.profile, **project.summary_fields()}
        run_prechecks(chosen, "data fetch", report, datasets)
        results: dict[str, object] = {}
        for slug in datasets:
            where.step, where.dataset = "fetch", slug
            spec = sources.source_spec(slug)
            if spec is None:
                status = f"not available until {sources.AVAILABLE_IN[slug]}"
                typer.echo(f"{slug}: {status}")
                results[slug] = {"status": status}
                continue
            try:
                with spec.client() as client:
                    fetched = download.fetch(spec, client, profile=chosen)
                if fetched.get("products_stopped"):  # the other products downloaded
                    typer.echo(
                        f"{slug}: {fetched['products_stopped']} product(s) stopped", err=True
                    )
                    failed += 1
                results[slug] = {"status": "partial" if fetched.get("products_stopped") else "ok",
                                 **fetched}  # fmt: skip
            except download.DownloadError as exc:  # stop this dataset, keep what it downloaded
                typer.echo(f"{slug}: stopped: {exc}", err=True)
                results[slug] = {"status": "stopped", "rule": exc.rule}
                failed += 1
        if not datasets:
            typer.echo(f"{chosen.profile} has no dataset to download")
        report["datasets"] = results
        written = summary.emit(chosen, "data fetch", report)
    if failed:
        raise typer.Exit(code=1)
    return written


@app.command(name="status")
def status_command(
    profile: Annotated[str | None, typer.Option("--profile", help="Only this profile.")] = None,
) -> None:
    """Downloads per dataset and product, and each profile's folders: counts, sizes and ages."""
    from neonradar_cli import redact, summary
    from neonradar_ingest.data import layout, status
    from neonradar_ingest.data.profiles import profile_names

    project = project_or_exit()
    profiles = [profile_or_exit(name) for name in ([profile] if profile else profile_names())]
    with redact.guard(None, "data status", real=True):  # it lists the real-data folders
        versions = status.downloads(project)
        days = project.access.real_data_days
        typer.echo(f"downloads: {len(versions)} version(s); retention {days} day(s)")
        downloads: dict[str, dict[str, dict[str, int]]] = {}
        for v in versions:
            past = "; past retention" if v.past_retention else ""
            partial = f"; {v.partial} partial" if v.partial else ""
            typer.echo(
                f"  {v.dataset}/{v.product}/{v.version}: {v.files} file(s),"
                f" {v.bytes / GB:.2f} GB, {v.age_days} day(s) old{partial}{past}"
            )
            product = downloads.setdefault(v.dataset, {}).setdefault(v.product, {})
            for key, value in (("version_count", 1), ("file_count", v.files),
                               ("bytes", v.bytes), ("partial_files", v.partial),
                               ("versions_past_retention", int(v.past_retention))):  # fmt: skip
                product[key] = product.get(key, 0) + value
            product["oldest_days"] = max(product.get("oldest_days", 0), v.age_days)
        folders: dict[str, dict[str, int]] = {}
        for chosen in profiles:
            s = status.profile_status(chosen)
            kind = "real data" if s.real_data else "synthetic"
            typer.echo(
                f"{s.profile} ({kind}): {s.record_folders} record folder(s) with"
                f" {s.record_files} file(s), {s.resolution_runs} resolution run(s),"
                f" {s.label_files} label file(s)"
            )
            folders[s.profile] = {
                "record_folders": s.record_folders,
                "record_files": s.record_files,
                "resolution_runs": s.resolution_runs,
                "label_files": s.label_files,
            }
        spill = status.spill_leftovers()
        typer.echo(
            f"DuckDB spill folders left behind: real {spill['real']},"
            f" synthetic {spill['synthetic']}"
        )
        name = profile or layout.ALL_PROFILES
        report = {
            "profile": name,
            **project.summary_fields(),
            "real_data_days": days,
            "downloads": downloads,
            "profiles": folders,
            "spill_leftovers": spill,
        }
        summary.emit(name, "data status", report, echo=False)  # the same counts, as a file


@app.command(name="purge")
def purge_command(
    expired: Annotated[bool, typer.Option("--expired", help="Everything past retention.")] = False,
    dataset: DatasetOption = None,
    profile: Annotated[
        str | None, typer.Option("--profile", help="A profile's records, runs and labels.")
    ] = None,
    labels: Annotated[bool, typer.Option("--labels", help="Every real label file.")] = False,
    decisions: Annotated[bool, typer.Option("--decisions", help="Real decisions.")] = False,
    logs: Annotated[bool, typer.Option("--logs", help="Real-profile tracebacks.")] = False,
    all_real: Annotated[
        bool, typer.Option("--all-real", help="Everything under data/cache/real/ and spikes/.")
    ] = False,
    graph: Annotated[
        bool, typer.Option("--graph", help="Also delete the real-data Neo4j instance's volume.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm: purged data is gone.")] = False,
) -> None:
    """Delete real data by scope; prints what it deleted (counts and bytes)."""
    from neonradar_cli import real_graph, redact
    from neonradar_ingest.data import purge
    from neonradar_ingest.data.profiles import DATASETS

    chosen = [
        scope
        for scope, on in (
            (purge.Scope.EXPIRED, expired),
            (purge.Scope.DATASET, dataset is not None),
            (purge.Scope.PROFILE, profile is not None),
            (purge.Scope.LABELS, labels),
            (purge.Scope.DECISIONS, decisions),
            (purge.Scope.LOGS, logs),
            (purge.Scope.ALL_REAL, all_real),
        )
        if on
    ]
    if len(chosen) > 1 or not (chosen or graph):
        typer.echo(
            "FAIL  choose one of --expired, --dataset, --profile, --labels, --decisions, --logs"
            " or --all-real (with or without --graph), or --graph alone",
            err=True,
        )
        raise typer.Exit(code=2)
    if dataset is not None and dataset not in DATASETS:
        typer.echo(f"FAIL  unknown dataset {dataset!r}", err=True)
        raise typer.Exit(code=2)
    if not yes:
        typer.echo("FAIL  purge deletes data for good: add --yes to confirm", err=True)
        raise typer.Exit(code=2)
    project = project_or_exit()
    target = profile_or_exit(profile) if profile is not None else None
    with redact.guard(target, "data purge", real=target is None or target.real_data) as where:
        for scope in chosen:
            where.step = f"purge-{scope}"
            paths = purge.targets(scope, project, dataset=dataset, profile=target)
            deleted = purge.delete(paths)
            typer.echo(f"purge --{scope}: deleted {deleted.files} file(s), {deleted.bytes} bytes")
        if graph:
            where.step = "purge-graph"
            containers, volumes = real_graph.wipe()
            typer.echo(
                f"purge --graph: removed {containers} real-data container(s) and deleted"
                f" {volumes} volume(s); the default instance is untouched"
            )
