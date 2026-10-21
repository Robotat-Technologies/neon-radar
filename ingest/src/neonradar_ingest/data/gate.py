"""The real-data gate (PHASE-2.md M2.2 deliverable 5, 7.4 rule 1).

Every command and builder step that reads real downloads or real records, or calls a real API,
runs `check_real_data` first, before any network request or file write. For a profile with
`real_data: true` it checks, in this order:

1. the dataset's access rule (skipped when `dataset` is None: `er`, `graph`, `load`, ...);
2. the profile is in `access.real_data_profiles`;
3. `access.data_protection_filed` is true;
4. neither `CI` nor `CODESPACES` is set (from the environment only);
5. `NR_REAL_DATA_MACHINE=approved`, from the environment or the repository's `.env`.

A command that addresses the real-data instance without a profile runs `check_real_instance`:
conditions 3 to 5, after refusing while `access.real_data_profiles` is empty.
"""

import os
from pathlib import Path
from typing import NamedTuple

from neonradar_ingest.data.profiles import SYNTHETIC, Profile
from neonradar_ingest.data.project import REPO_ROOT, Project
from neonradar_ingest.settings import IngestSettings

ENV_FILE = REPO_ROOT / ".env"  # looked up per call, so tests can point it at a temporary file
MACHINES_DOC = "docs/data/real-data-machines.md"


class RealDataRefused(Exception):
    """A gate condition failed. The CLI prints the message and exits with code 3."""

    exit_code = 3
    counts_only = True  # the message names rules, profiles and datasets, never a record value

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(message)
        self.rule, self.message = rule, message


def ci_variable() -> str | None:
    """`CI` or `CODESPACES` when either exists in the environment, whatever its value."""
    return next((name for name in ("CI", "CODESPACES") if name in os.environ), None)


def machine_approved(env_file: Path | None = None) -> bool:
    """`NR_REAL_DATA_MACHINE=approved`: a real environment variable wins over `.env`."""
    settings = IngestSettings(_env_file=env_file or ENV_FILE)
    return settings.nr_real_data_machine.strip() == "approved"


class Condition(NamedTuple):
    rule: str  # what a refusal names
    label: str  # what `neonradar data profiles` shows
    passed: bool
    message: str  # the refusal's message


def conditions(project: Project, profile: str | None) -> list[Condition]:
    """Conditions 2 to 5, in order; `profile` None for a command on the real-data instance."""
    access = project.access
    ci = ci_variable()
    if profile is None:
        listed = bool(access.real_data_profiles)
        unlisted = "access.real_data_profiles is empty: no real profile may run on this machine"
    else:
        listed = profile in access.real_data_profiles
        unlisted = f"{profile} is not in access.real_data_profiles"
    return [
        Condition(
            "access.real_data_profiles", "listed in access.real_data_profiles", listed, unlisted
        ),
        Condition(
            "access.data_protection_filed",
            "access.data_protection_filed is true",
            access.data_protection_filed,
            "access.data_protection_filed is false: the data steward files the data protection"
            " documents in docs/data/dpia/ first (PHASE-2.md 1.1)",
        ),
        Condition(
            ci or "CI",
            "not in CI or Codespaces",
            ci is None,
            f"{ci} is set: real data never runs in CI or Codespaces",
        ),
        Condition(
            "NR_REAL_DATA_MACHINE",
            "NR_REAL_DATA_MACHINE=approved",
            machine_approved(),
            f"NR_REAL_DATA_MACHINE is not approved: only a machine listed in {MACHINES_DOC}"
            " runs real profiles",
        ),
    ]


def _refuse_first(checks: list[Condition]) -> None:
    for check in checks:
        if not check.passed:
            raise RealDataRefused(check.rule, check.message)


def check_real_data(
    project: Project, profile: Profile, dataset: str | None = None, *, step: str | None = None
) -> None:
    """Raise `RealDataRefused` on the first failing condition.

    Only a synthetic profile with no dataset or `nr_synthetic` passes unchecked: a real dataset
    always takes every check, whatever the profile says.
    """
    if not profile.real_data and dataset in (None, SYNTHETIC):
        return
    if dataset is not None:
        refusal = project.access_refusal(dataset, step)
        if refusal is not None:
            raise RealDataRefused(*refusal)
    _refuse_first(conditions(project, profile.profile))


def check_real_instance(project: Project) -> None:
    """The gate for a command that addresses the real-data instance without a profile."""
    _refuse_first(conditions(project, None))
