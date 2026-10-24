"""`neonradar load --profile NAME`: one profile end to end (PHASE-2.md M2.13 deliverable 1).

The steps run in order and the first failing one stops the load: for a real profile the
real-data gate and a check that the real-data instance answers, then `data fetch` (real
profiles only, unless `--skip-fetch`), `ingest build`, `er run` (when `resolution.enabled`),
`graph migrate`, `graph load --profile NAME [--resolution latest]` and `graph verify`, with
`--real` for a real profile. Each step is the command's own function, so its gate, redaction
and counts-only summary hold. The load writes one counts-only summary (`summary.emit`) with each
step's duration, the counts the steps returned, the graph's node and relationship counts and the
invariant results.
"""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from neonradar_ingest.data.profiles import Profile
    from neonradar_ingest.data.project import Project

COMPANIES_HOUSE = "gb_companies_house"
TIMEOUT_S = 30.0
STRING_KEYS = ("failed_step",)


@dataclass(slots=True)
class Run:
    """One load: the profile as this run sees it, and the summary the steps fill."""

    profile: Profile
    project: Project
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def real(self) -> bool:
        return self.profile.real_data


def without_officer_requests(profile: Profile) -> Profile:
    """`--skip-officers`: the profile with `officers.request_budget` 0, in memory only."""
    from neonradar_ingest.data.profiles import SourceConfig

    config = profile.sources.get(COMPANIES_HOUSE)
    if config is None:
        return profile
    officers = {**config.options.get("officers", {}), "request_budget": 0}
    block = SourceConfig.model_validate({"enabled": config.enabled, **config.options,
                                         "officers": officers})  # fmt: skip
    return profile.model_copy(update={"sources": {**profile.sources, COMPANIES_HOUSE: block}})


def counts(value: Any, key: str = "") -> Any:
    """The numbers (and `status`) of a step's summary: its strings and lists stay out, so the
    load summary needs none of the step's registered keys."""
    if isinstance(value, Mapping):
        kept = {name: counts(item, name) for name, item in value.items()}
        return {name: item for name, item in kept.items() if item is not ...}
    if value is None or isinstance(value, bool | int | float) or key == "status":
        return value
    return ...


def _lower(found: Mapping[str, int]) -> dict[str, int]:
    return {name.lower(): number for name, number in sorted(found.items())}


def gate_step(run: Run) -> None:
    """A real profile: the real-data gate for the profile and each dataset, then the real-data
    instance must answer (`make up-real`)."""
    from neonradar_cli import graph
    from neonradar_graph.instances import Instance
    from neonradar_ingest.data import gate

    gate.check_real_data(run.project, run.profile)
    for dataset in run.profile.enabled_sources(run.project):
        gate.check_real_data(run.project, run.profile, dataset)
    with graph._connected(graph._settings(Instance.REAL), TIMEOUT_S, real=True):
        pass


def fetch_step(run: Run) -> None:
    from neonradar_cli import data

    run.report["fetch"] = counts(data.fetch_command(profile=run.profile.profile)["datasets"])


def build_step(run: Run) -> None:
    from neonradar_cli import ingest

    run.report["build"] = counts(ingest.run_build(run.profile)["datasets"])


def resolve_step(run: Run) -> None:
    from neonradar_cli import er

    report = er.run_command(profile=run.profile.profile)
    run.report["resolution"] = counts({"counts": report["counts"], "seed": report["seed"]})


def migrate_step(run: Run) -> None:
    from neonradar_cli import graph

    graph.migrate_command(real=run.real)


def graph_load_step(run: Run) -> None:
    from neonradar_cli import graph

    latest = "latest" if run.profile.resolution.enabled else None
    loaded = graph.load_command(profile=run.profile.profile, resolution=latest)
    run.report["graph_load"] = counts(loaded)


def verify_step(run: Run) -> None:
    """`graph verify`, then the graph's node and relationship counts from the same instance."""
    from neonradar_cli import graph
    from neonradar_graph import loader

    run.report["invariants"] = _lower(graph.verify_command(real=run.real))
    with graph._instance(run.real, "graph stats") as instance:
        settings = graph._settings(instance)
        with graph._connected(settings, TIMEOUT_S, real=run.real) as driver:
            found = loader.stats(driver, settings.database)
    run.report["graph"] = {
        "nodes": found.nodes,
        "relationships": found.relationships,
        "nodes_by_label": _lower(found.labels),
        "relationships_by_type": _lower(found.relationship_types),
    }


Step = Callable[[Run], None]
STEPS: dict[str, Step] = {
    "gate": gate_step,
    "data fetch": fetch_step,
    "ingest build": build_step,
    "er run": resolve_step,
    "graph migrate": migrate_step,
    "graph load": graph_load_step,
    "graph verify": verify_step,
}


def plan(profile: Profile, *, skip_fetch: bool) -> list[str]:
    """The steps of a load, in order: a synthetic profile never fetches and never gates."""
    return [
        name
        for name in STEPS
        if (name not in ("gate", "data fetch") or profile.real_data)
        and not (name == "data fetch" and skip_fetch)
        and (name != "er run" or profile.resolution.enabled)
    ]


def run_steps(run: Run, names: list[str]) -> str | None:
    """Each step in order; the name of the first that failed, else None."""
    steps: dict[str, Any] = {}
    run.report["steps"] = steps
    for name in names:
        started, status = time.monotonic(), "failed"
        try:
            STEPS[name](run)
            status = "ok"
        except typer.Exit as stopped:
            status = "ok" if stopped.exit_code == 0 else "failed"
        except Exception:  # unexpected: named here, then redacted by the guard on a real profile
            typer.echo(f"FAIL  load stopped at step {name}", err=True)
            raise
        finally:
            duration = round(time.monotonic() - started, 3)
            steps[name.replace(" ", "_")] = {"status": status, "duration_s": duration}
        if status == "failed":
            return name
    return None


def load_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    skip_fetch: Annotated[
        bool, typer.Option("--skip-fetch", help="Use the downloads already present.")
    ] = False,
    skip_officers: Annotated[
        bool,
        typer.Option(
            "--skip-officers",
            help="Officers request budget 0 for this run: officer records from the cache only.",
        ),
    ] = False,
) -> None:
    """Fetch (real profiles), build, resolve, migrate, load and verify one profile; write one
    counts-only summary; stop at the first failing step and exit 1."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data import layout

    project, chosen = project_or_exit(), profile_or_exit(profile)
    if skip_officers:
        chosen = without_officer_requests(chosen)
    run = Run(chosen, project)
    with redact.guard(chosen, "load") as where:
        where.step = "load"
        run.report |= {"profile": chosen.profile, **project.summary_fields(),
                       "run_id": layout.new_run_id("load"), "real_data": chosen.real_data,
                       "skip_fetch": skip_fetch, "skip_officers": skip_officers}  # fmt: skip
        failed = run_steps(run, plan(chosen, skip_fetch=skip_fetch))
        run.report |= {"status": "failed" if failed else "ok", "failed_step": failed}
        where.step = "summary"
        summary.emit(chosen, "load", run.report, string_keys=STRING_KEYS)
    if failed:
        typer.echo(f"FAIL  load stopped at step {failed}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"OK  {chosen.profile} loaded in {len(run.report['steps'])} steps")
