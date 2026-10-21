"""Data profiles: which sources a named profile loads (PHASE-2.md M2.2 deliverable 2, 7.8).

A profile is `ingest/profiles/<name>.yaml`. Each source entry has `enabled` plus the block its
loader milestone defines; a loader registers a pydantic model for that block with
`register_source_model` (unknown keys then fail), and until it does the block is kept as a
dict. Whether an enabled source runs is decided by `project.yaml` (`Project.access_refusal`).
"""

import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator

from neonradar_ingest.data.project import REPO_ROOT, Project, load_project

PROFILES_DIR = REPO_ROOT / "ingest" / "profiles"  # looked up per call, so tests can patch it
PROFILE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SYNTHETIC = "nr_synthetic"
# Every dataset a profile may name, in the order `neonradar ingest build` runs their builders
# (deliverable 12): synthetic first, Companies House before GLEIF (GLEIF's slice depends on it).
DATASETS: tuple[str, ...] = (
    SYNTHETIC,
    "gb_companies_house",
    "gleif_lei",
    "icij_offshore_leaks",
    "gb_fcdo_sanctions",
    "us_ofac_sdn",
    "un_sc_sanctions",
    "eu_fsf",
    "gb_parliament_members",
    "opensanctions_default",
)


class ProfileError(ValueError):
    """A profile that does not exist or does not validate."""

    exit_code = 2
    counts_only = True  # names profiles, datasets and keys only


class SyntheticSource(BaseModel):
    """The `nr_synthetic` block: committed fixture folders, each validated as one load."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    fixtures: list[str]

    @field_validator("fixtures")
    @classmethod
    def _under_fixtures(cls, folders: list[str]) -> list[str]:
        for folder in folders:
            path = PurePosixPath(folder)
            if path.parts[:2] != ("data", "fixtures") or ".." in path.parts or len(path.parts) < 3:
                raise ValueError(f"{folder!r} is not a folder under data/fixtures/")
        return folders


_SOURCE_MODELS: dict[str, type[BaseModel]] = {SYNTHETIC: SyntheticSource}


def register_source_model(dataset: str, model: type[BaseModel]) -> None:
    """Validate the profile block of `dataset` with `model` (with `enabled`; extra="forbid")."""
    if dataset not in DATASETS:
        raise ValueError(f"{dataset!r} is not a dataset the data manager knows")
    _SOURCE_MODELS[dataset] = model


class SourceConfig(BaseModel):
    """`enabled` plus the source's own keys (`options`), checked by its registered model."""

    model_config = ConfigDict(extra="allow", frozen=True)

    enabled: StrictBool

    @property
    def options(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    enabled: bool
    config: str


class Profile(BaseModel):
    """One `ingest/profiles/<name>.yaml` file (extra keys fail)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    description: str
    real_data: StrictBool
    sources: dict[str, SourceConfig]
    resolution: Resolution

    @field_validator("profile")
    @classmethod
    def _name(cls, name: str) -> str:
        if not PROFILE_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not lower-case words joined by hyphens")
        return name

    @field_validator("sources")
    @classmethod
    def _known(cls, sources: dict[str, SourceConfig]) -> dict[str, SourceConfig]:
        for dataset, config in sources.items():
            if dataset not in DATASETS:
                raise ValueError(f"unknown dataset {dataset!r}; known: {', '.join(DATASETS)}")
            model = _SOURCE_MODELS.get(dataset)
            if model is not None:
                model.model_validate({"enabled": config.enabled, **config.options})
        return sources

    def options(self, dataset: str) -> Any:
        """The source's block: its registered model's instance, else a dict."""
        config = self.sources[dataset]
        model = _SOURCE_MODELS.get(dataset)
        data = {"enabled": config.enabled, **config.options}
        return model.model_validate(data) if model is not None else data

    def enabled_sources(self, project: Project) -> list[str]:
        """Datasets enabled here and allowed by `project.yaml`, in build order."""
        return [
            dataset
            for dataset in DATASETS
            if dataset in self.sources
            and self.sources[dataset].enabled
            and project.access_refusal(dataset) is None
        ]

    def refused_sources(self, project: Project) -> dict[str, str]:
        """Datasets enabled here that `project.yaml` refuses, with the access rule's message."""
        refused: dict[str, str] = {}
        for dataset in DATASETS:
            config = self.sources.get(dataset)
            refusal = project.access_refusal(dataset) if config and config.enabled else None
            if refusal is not None:
                refused[dataset] = refusal[1]
        return refused

    def record_dirs(self, project: Project | None = None) -> list[Path]:
        """The folders the resolver and the graph loader read for this profile.

        `layout.records_dir(profile, dataset)` for every enabled dataset, and for
        `nr_synthetic` the fixture folders the profile lists.
        """
        from neonradar_ingest.data import layout  # layout reads profiles: import at call time

        folders: list[Path] = []
        for dataset in self.enabled_sources(project or load_project()):
            if dataset == SYNTHETIC:
                options: SyntheticSource = self.options(dataset)
                folders.extend(REPO_ROOT / folder for folder in options.fixtures)
            else:
                folders.append(layout.records_dir(self, dataset))
        return folders


def profile_names() -> list[str]:
    """The profiles in `ingest/profiles/`, sorted."""
    return sorted(path.stem for path in PROFILES_DIR.glob("*.yaml"))


def load_profile(name: str) -> Profile:
    """Read `ingest/profiles/<name>.yaml` after the loaders have registered their models."""
    from neonradar_ingest.data import sources  # the loaders register at import time

    if not PROFILE_NAME.fullmatch(name):
        raise ProfileError(f"{name!r} is not a profile name")
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise ProfileError(f"no profile {name!r}; profiles: {', '.join(profile_names())}")
    sources.load_plugins()
    try:
        profile = Profile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (ValueError, yaml.YAMLError) as exc:  # pydantic's ValidationError is a ValueError
        raise ProfileError(f"ingest/profiles/{name}.yaml: {exc}") from None
    if profile.profile != name:
        raise ProfileError(f"ingest/profiles/{name}.yaml says profile: {profile.profile}")
    return profile
