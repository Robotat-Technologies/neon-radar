"""The `project.yaml` keys the data manager reads (PHASE-2.md 1.3, M2.2 deliverable 1), and
the Phase 3 and Phase 4 keys (PHASE-3.md 1.3, M3.0 deliverable 7; PHASE-4.md 1.3, M4.0
deliverable 7) that later milestones read through it.

`load_project()` reads docs/build/project.yaml, or the file named in `NR_PROJECT_FILE` (for
tests and acceptance commands only). Other keys are allowed and ignored. Missing access keys
fail closed: no real profile, no data protection documents, no list, no PEP source, no real
overlay, no registry alert about a real organisation (G12's stricter option). Missing
schedule dates are None: they are informational (OD-1), and so is a missing held-out owner.
"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Literal, get_args

import yaml
from pydantic import BaseModel, ConfigDict, NonNegativeInt

REPO_ROOT = Path(__file__).resolve().parents[4]  # members are installed editable
DEFAULT_PROJECT_FILE = REPO_ROOT / "docs" / "build" / "project.yaml"

SanctionsList = Literal["gb_fcdo_sanctions", "us_ofac_sdn", "un_sc_sanctions", "eu_fsf"]
PepSource = Literal["gb_parliament_members", "opensanctions_default"]
SANCTIONS_LISTS: tuple[str, ...] = get_args(SanctionsList)


class Access(BaseModel):
    """`access`: what this installation may load (PHASE-1.md 1.2, PHASE-2.md 1.2)."""

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    companies_house_key: Literal["pending", "available"] = "pending"
    opensanctions: Literal["none", "evaluation", "licensed", "exempt"] = "none"
    spike_cache_days: NonNegativeInt = 7
    real_data_profiles: list[str] = []
    real_data_days: NonNegativeInt = 30
    label_days: NonNegativeInt = 30
    data_protection_filed: bool = False
    sanctions_lists: list[SanctionsList] = []
    pep_sources: list[PepSource] = []
    pep_former_months: NonNegativeInt = 12
    # Phase 3 (PHASE-3.md 1.2 and 1.3; values in operator-decisions.md OD-25)
    real_overlay_profiles: list[str] = []
    real_registry_alerts: bool = False


class People(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    er_labellers: list[str] = []
    er_senior_reviewers: list[str] = []
    freeze_deciders: list[str] = []  # ADR-0022 (PHASE-3.md M3.11)
    heldout_owner: str | None = None  # PHASE-4.md 1.1: outside the copilot squad (M4.9)


class Schedule(BaseModel):
    """`schedule`: the Phase 3 and Phase 4 dates (PHASE-3.md and PHASE-4.md 1.3), informational
    (OD-1)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    phase_3_start: date | None = None
    assignment_4_due: date | None = None
    detection_freeze: date | None = None
    holdout_run: date | None = None
    teach_back_detection: date | None = None
    # Phase 4 (PHASE-4.md 1.3)
    phase_4_start: date | None = None
    contracts_1_3_0: date | None = None
    assignment_5_due: date | None = None
    heldout_run: date | None = None
    teach_back_copilot: date | None = None


class Project(BaseModel):
    """The keys Phases 2 to 4 read, plus the file they came from and its SHA-256."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    access: Access = Access()
    people: People = People()
    schedule: Schedule = Schedule()
    path: Path
    sha256: str

    def summary_fields(self) -> dict[str, str]:
        """`project_file` (relative to the repository) and `project_sha256`, for every summary."""
        try:
            shown = self.path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = f"(outside the repository) {self.path.name}"
        return {"project_file": shown[:80], "project_sha256": self.sha256}

    def access_refusal(self, dataset: str, step: str | None = None) -> tuple[str, str] | None:
        """The access rule that refuses `dataset` (or its `step`) as (rule, message), else None.

        Registries, the leak database and synthetic data have no access rule; the Companies
        House key gates only the officers API (M2.3c), because the bulk files need no key.
        """
        access = self.access
        if dataset in SANCTIONS_LISTS and dataset not in access.sanctions_lists:
            return "access.sanctions_lists", f"{dataset} is not in access.sanctions_lists"
        if dataset == "gb_parliament_members" and dataset not in access.pep_sources:
            return "access.pep_sources", f"{dataset} is not in access.pep_sources"
        if dataset == "opensanctions_default" and access.opensanctions not in (
            "licensed",
            "exempt",
        ):
            return "access.opensanctions", (
                f"{dataset} needs access.opensanctions licensed or exempt"
                f" (it is {access.opensanctions})"
            )
        officers = dataset == "gb_companies_house" and step == "officers"
        if officers and access.companies_house_key != "available":
            return "access.companies_house_key", (
                "the officers API needs access.companies_house_key: available"
            )
        return None


def project_file() -> Path:
    """`NR_PROJECT_FILE` when it is set (the ingest settings object: the environment, then
    `.env`), else docs/build/project.yaml."""
    from neonradar_ingest.settings import IngestSettings

    named = IngestSettings().nr_project_file.strip()
    return Path(named) if named else DEFAULT_PROJECT_FILE


def load_project(path: Path | None = None) -> Project:
    """Read and check the project file. OSError if unreadable; ValueError if malformed."""
    path = path or project_file()
    raw = path.read_bytes()
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a YAML mapping")
    fields = {key: data.get(key) or {} for key in ("access", "people", "schedule")}
    return Project.model_validate(
        {**fields, "path": path, "sha256": hashlib.sha256(raw).hexdigest()}
    )
