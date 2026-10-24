"""`neonradar load --profile NAME`: one profile end to end (PHASE-2.md M2.13 deliverable 1).

`STEPS` run in order (`plan` picks them) and the first failing one stops the load. Each step
calls the command's own function, so its gate, redaction guard and counts-only summary hold;
the load writes one counts-only summary with each step's duration and the counts they returned.
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
    """The numbers (and `status`) of a step's summary: no string key of the step is needed."""
    if isinstance(value, Mapping):
        kept = {name: counts(item, name) for name, item in value.items()}
        return {name: item for name, item in kept.items() if item is not ...}
    if value is None or isinstance(value, bool | int | float) or key == "status":
        return value
    return ...


def _lower(found: Mapping[str, int]) -> dict[str, int]:
    return {name.lower(): number for name, number in sorted(found.items())}


def gate_step(run: Run) -> None:
    """A real profile: the real-data gate for it and each dataset; the real instance answers."""
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
    """`graph verify` (I1 to I14) and the graph's counts, kept even when an invariant fails."""
    from neonradar_cli import graph
    from neonradar_graph import loader
    from neonradar_graph.verify import verify

    with graph._instance(run.real, "graph verify") as instance:
        settings = graph._settings(instance)
        with graph._connected(settings, TIMEOUT_S, real=run.real) as driver:
            invariants = verify(driver, settings.database)
            found = loader.stats(driver, settings.database)
    run.report["invariants"] = _lower(invariants)
    typer.echo(f"graph verify: {sum(invariants.values())} violation(s) of I1 to I14")
    run.report["graph"] = {
        "nodes": found.nodes,
        "relationships": found.relationships,
        "nodes_by_label": _lower(found.labels),
        "relationships_by_type": _lower(found.relationship_types),
    }
    if any(invariants.values()):
        raise typer.Exit(code=1)


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
    """Each step in order, inside the redaction guard; the name of the first that failed."""
    from neonradar_cli import redact

    steps: dict[str, Any] = run.report.setdefault("steps", {})
    for name in names:
        started, status, key = time.monotonic(), "failed", name.replace(" ", "_")
        try:
            with redact.guard(run.profile, "load") as where:  # an error becomes typer.Exit
                where.step = key
                STEPS[name](run)
            status = "ok"
        except typer.Exit as stopped:
            status = "ok" if stopped.exit_code == 0 else "failed"
        except Exception:  # a synthetic profile's unexpected error keeps its traceback
            typer.echo(f"FAIL  load stopped at step {name}", err=True)
            raise
        finally:
            steps[key] = {"status": status, "duration_s": round(time.monotonic() - started, 3)}
        if status == "failed":
            return name
    return None


def load_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    skip_fetch: Annotated[bool, typer.Option("--skip-fetch", help="Reuse downloads.")] = False,
    skip_officers: Annotated[bool, typer.Option("--skip-officers", help="Cache only.")] = False,
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
