"""`neonradar ingest build`: C1 records from downloads (PHASE-2.md M2.2 deliverable 12).

Runs the gate for a real profile, then the registered builders in a fixed order (`DATASETS`:
`nr_synthetic` first, then Companies House, GLEIF, ICIJ, the four lists, Parliament and
OpenSanctions). Each dataset's records are validated in strict mode before they replace the old
folder. A builder that is not implemented yet is named with its milestone and skipped.
"""

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Build C1 records for a profile.", no_args_is_help=True)


def _validate(paths: list[Path]) -> int:
    """Strict validation of one dataset's new records; issues print masked (masking.py)."""
    from neonradar_cli import masking

    _, issues = masking.validate(paths, strict=True)
    for issue in issues[:20]:
        typer.echo(issue, err=True)
    return len(issues)


@app.command(name="build")
def build_command(
    profile: Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")],
    dataset: Annotated[str | None, typer.Option("--dataset", help="Only this dataset.")] = None,
    step: Annotated[
        list[str] | None, typer.Option("--step", help="A step of the dataset's builder (repeat).")
    ] = None,
    keep_work: Annotated[bool, typer.Option("--keep-work", help="Keep work indexes.")] = False,
    accept_size: Annotated[
        bool, typer.Option("--accept-size", help="Accept a list file outside its size bounds.")
    ] = False,
) -> None:
    """Run the gate, then each enabled dataset's builder; print and write the summary."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit, run_prechecks, selected
    from neonradar_ingest.data import gate, layout, sources
    from neonradar_ingest.data.build import build_dataset

    steps = tuple(step or ())
    if steps and dataset is None:
        typer.echo("FAIL  --step needs --dataset", err=True)
        raise typer.Exit(code=2)
    project, chosen = project_or_exit(), profile_or_exit(profile)
    with redact.guard(chosen, "ingest build") as where:
        where.step = "gate"
        gate.check_real_data(project, chosen, dataset)
        datasets = selected(project, chosen, dataset)
        run_id = layout.new_run_id("build")
        report: dict[str, object] = {
            "profile": chosen.profile,
            **project.summary_fields(),
            "run_id": run_id,
        }
        results: dict[str, object] = {}
        string_keys: set[str] = set()
        list_keys: set[str] = set()
        plan: list[tuple[str, sources.Builder, tuple[str, ...]]] = []
        for slug in datasets:
            builder = sources.builder_for(slug)
            if builder is None:
                status = f"not available until {sources.AVAILABLE_IN[slug]}"
                typer.echo(f"{slug}: {status}")
                results[slug] = {"status": status}
                continue
            unknown = [name for name in steps if name not in builder.steps]
            if unknown:
                typer.echo(f"FAIL  {slug} has no step {unknown[0]!r}", err=True)
                raise typer.Exit(code=2)
            chosen_steps = tuple(name for name in builder.steps if name in steps)
            # The gate for every dataset and every step that will run, before any builder:
            # the officers step's access rule (access.companies_house_key) is checked here.
            where.dataset = slug
            for name in chosen_steps or builder.steps or (None,):
                gate.check_real_data(project, chosen, slug, step=name)
            plan.append((slug, builder, chosen_steps))
        where.dataset = None
        run_prechecks(chosen, "ingest build", report, [slug for slug, _, _ in plan])
        for slug, builder, chosen_steps in plan:
            where.step, where.dataset = "build", slug
            result = build_dataset(
                builder,
                chosen,
                project,
                _validate,
                run_id=run_id,
                steps=chosen_steps,
                keep_work=keep_work,
                accept_size=accept_size,
            )
            results[slug] = {"status": "ok", **result.counts, **result.strings, **result.lists}
            string_keys.update(builder.string_keys)
            list_keys.update(builder.list_keys)
        report["datasets"] = results
        summary.emit(chosen, "ingest build", report, string_keys=string_keys, list_keys=list_keys)
