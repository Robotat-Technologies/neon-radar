"""Run one builder and swap its records in (PHASE-2.md M2.2 deliverable 12).

The builder writes into a temporary folder next to `layout.records_dir(profile, dataset)`;
the records are validated in strict mode, and only then does the folder replace the old one,
so a rebuild never leaves stale files and a failed build leaves the previous records in place.
A builder that writes nothing (`nr_synthetic`, which validates its fixtures where they are)
changes no folder.
"""

import shutil
from collections.abc import Callable
from pathlib import Path

from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import Project
from neonradar_ingest.data.sources import BuildContext, Builder, BuildError, BuildResult

# Validates the record files of one dataset as one load (strict) and returns the number of issues.
Validate = Callable[[list[Path]], int]


def build_dataset(
    builder: Builder,
    profile: Profile,
    project: Project,
    validate: Validate,
    *,
    run_id: str,
    steps: tuple[str, ...] = (),
    keep_work: bool = False,
    accept_size: bool = False,
) -> BuildResult:
    final = layout.records_dir(profile, builder.dataset)
    temporary = final.parent / f".{builder.dataset}.{run_id}.tmp"
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)
    work = layout.work_dir(profile, builder.dataset)
    context = BuildContext(project, run_id, temporary, work, steps, keep_work, accept_size)
    try:
        result = builder.build(profile, context)
        if not any(temporary.iterdir()):
            return _finished(builder, profile, context, result)
        issues = validate(sorted(temporary.glob("*.ftm.jsonl")))
        if issues:
            raise BuildError(
                f"{builder.dataset}: {issues} C1 issue(s) in strict mode; the previous records"
                " stay in place",
                "C1",
                counts_only=True,
            )
        old = final.parent / f".{builder.dataset}.{run_id}.old"
        if final.exists():
            final.rename(old)
        try:
            temporary.rename(final)
        except OSError:
            if old.exists():
                old.rename(final)  # the previous records stay in place
            raise
        shutil.rmtree(old, ignore_errors=True)
        return _finished(builder, profile, context, result)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
        if not any(final.parent.iterdir()):
            final.parent.rmdir()


def _finished(
    builder: Builder, profile: Profile, context: BuildContext, result: BuildResult
) -> BuildResult:
    """Run the builder's cleanup: only here, after a successful build and swap."""
    if builder.cleanup is not None:
        builder.cleanup(profile, context, result)
    return result
