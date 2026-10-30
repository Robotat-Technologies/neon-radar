"""Data profiles: which sources a named profile loads (PHASE-2.md M2.2 deliverable 2, 7.8).

A profile is `ingest/profiles/<name>.yaml`. Each source entry has `enabled` plus the block its
loader milestone defines; a loader registers a pydantic model for that block with
`register_source_model` (unknown keys then fail; the validation context `sources` holds the
profile's other blocks), and until it does the block is kept as a dict. Whether an enabled
source runs is decided by `project.yaml` (`Project.access_refusal`).
"""

import dataclasses
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    StrictBool,
    TypeAdapter,
    field_validator,
    model_validator,
)

from neonradar_ingest.data.project import REPO_ROOT, Project, load_project

if TYPE_CHECKING:
    from neonradar_ingest.synth.overlay import OverlayConfig
    from neonradar_ingest.synth.world import WorldConfig

PROFILES_DIR = REPO_ROOT / "ingest" / "profiles"  # looked up per call, so tests can patch it
PROFILE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
RESERVED_NAMES = ("er-bench-small", "er-bench-large", "all-profiles")  # layout's pseudo-profiles
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


# World companies are numbered SY6 and SY7 plus five digits, and parents and listed companies SY8
# (world.py), so a world holds at most 200,000 ordinary companies.
MAX_COMPANIES = 200_000


class World(BaseModel):
    """`sources.nr_synthetic.world`: a synthetic register (PHASE-3.md 7.11): the fields of
    `world.WorldConfig`, plus the world's `name` (its folder) and default `seed`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    seed: NonNegativeInt
    companies: Annotated[int, Field(gt=0, le=MAX_COMPANIES)] = 600
    people: PositiveInt = 900
    today: date = date(2026, 7, 1)
    agent_every: PositiveInt = 300
    professional_every: PositiveInt = 200
    dissolved_share: float = 0.05
    dormant_share: float = 0.08
    corporate_owner_share: float = 0.15
    parent_owner_share: float = 0.85
    no_owner_share: float = 0.06
    listed: NonNegativeInt = 6
    peps: NonNegativeInt = 4
    districts: PositiveInt = 30

    @field_validator("name")
    @classmethod
    def _plain(cls, name: str) -> str:
        if not PROFILE_NAME.fullmatch(name):
            raise ValueError(f"world name {name!r} is not lower-case words joined by hyphens")
        return name

    def config(self) -> WorldConfig:
        from neonradar_ingest.synth.world import WorldConfig

        return WorldConfig(**self.model_dump(exclude={"name", "seed"}))


class SyntheticSource(BaseModel):
    """The `nr_synthetic` block: committed fixture folders, each validated as one load, and
    (synthetic profiles of Phase 3) a world the generator makes from a seed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    fixtures: list[str]
    world: World | None = None

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
    config: str | None = None  # required when enabled (PHASE-3.md M3.3)

    @model_validator(mode="after")
    def _config_when_enabled(self) -> Self:
        if self.enabled and not self.config:
            raise ValueError("resolution.config is required when resolution.enabled is true")
        return self


class Overlay(BaseModel):
    """The `overlay` block (PHASE-3.md 7.11): the fields of `overlay.OverlayConfig` but `split`;
    `seed: null` means the world's seed, `typologies: all` every scenario module, and
    `background` holds `background.BackgroundConfig` overrides."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    seed: NonNegativeInt | None = None
    start: date = date(2025, 1, 1)
    end: date = date(2026, 7, 1)
    illicit: NonNegativeInt = 10
    lookalikes: NonNegativeInt = 10
    typologies: Literal["all"] | list[str] = "all"
    background: dict[str, Any] = {}

    @field_validator("typologies")
    @classmethod
    def _known_typologies(cls, value: Literal["all"] | list[str]) -> Literal["all"] | list[str]:
        if value != "all":
            from neonradar_ingest.synth.overlay import SCENARIOS

            unknown = sorted(set(value) - set(SCENARIOS))
            if unknown:
                raise ValueError(f"no scenario module for {', '.join(unknown)}")
        return value

    @field_validator("background")
    @classmethod
    def _known_background(cls, value: dict[str, Any]) -> dict[str, Any]:
        from neonradar_ingest.synth.background import BackgroundConfig

        known = {f.name for f in dataclasses.fields(BackgroundConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ValueError(f"unknown background settings: {', '.join(unknown)}")
        TypeAdapter(BackgroundConfig).validate_python(value)  # the types of the dataclass
        for key, share in value.items():  # every share is a fraction (M3.4)
            parts = share if isinstance(share, list | tuple) else [share]
            if key.endswith("share") and not all(0 <= part <= 1 for part in parts):
                raise ValueError(f"background.{key} must lie between 0 and 1")
        return value

    @model_validator(mode="after")
    def _period(self) -> Self:
        if self.end <= self.start:
            raise ValueError("overlay.end must come after overlay.start")
        return self

    def typology_slugs(self) -> tuple[str, ...]:
        """The scenario modules this overlay runs, in catalog order."""
        from neonradar_ingest.synth.overlay import SCENARIOS

        return tuple(s for s in SCENARIOS if self.typologies == "all" or s in self.typologies)

    def config(self, seed: int) -> OverlayConfig:
        """The generator's configuration for `seed` (split `dev`: the overlay has no split)."""
        from neonradar_ingest.synth.background import BackgroundConfig
        from neonradar_ingest.synth.overlay import OverlayConfig

        background = TypeAdapter(BackgroundConfig).validate_python(self.background)
        return OverlayConfig(
            seed,
            start=self.start,
            end=self.end,
            illicit=self.illicit,
            lookalikes=self.lookalikes,
            typologies=self.typology_slugs(),
            background=background,
        )


class Detection(BaseModel):
    """The `detection` block (PHASE-3.md 7.11): `window` is `overlay` (the overlay period) or
    `data` (the `PAID` time range); `overrides` are parameter values per typology, which the
    detection commands check against the typology files' bounds (M3.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    window: Literal["overlay", "data"] = "overlay"
    overrides: dict[str, dict[str, Any]] = {}


class Profile(BaseModel):
    """One `ingest/profiles/<name>.yaml` file (extra keys fail)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    description: str
    real_data: StrictBool
    sources: dict[str, SourceConfig]
    resolution: Resolution
    overlay: Overlay | None = None
    detection: Detection | None = None

    @field_validator("profile")
    @classmethod
    def _name(cls, name: str) -> str:
        if not PROFILE_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not lower-case words joined by hyphens")
        if name in RESERVED_NAMES:
            raise ValueError(f"{name!r} is reserved for the data manager's own folders")
        return name

    @field_validator("sources")
    @classmethod
    def _known(cls, sources: dict[str, SourceConfig]) -> dict[str, SourceConfig]:
        for dataset, config in sources.items():
            if dataset not in DATASETS:
                raise ValueError(f"unknown dataset {dataset!r}; known: {', '.join(DATASETS)}")
            model = _SOURCE_MODELS.get(dataset)
            if model is not None:  # the context lets a block read another (M2.5)
                data = {"enabled": config.enabled, **config.options}
                model.model_validate(data, context={"sources": sources})
        return sources

    @model_validator(mode="after")
    def _synthetic_only(self) -> Self:
        """A synthetic profile enables only synthetic data, so it can never skip the gate."""
        if not self.real_data:
            real = [d for d, c in self.sources.items() if c.enabled and d != SYNTHETIC]
            if real:
                raise ValueError(
                    f"real_data is false, so the profile may enable only {SYNTHETIC};"
                    f" it enables {', '.join(real)}"
                )
        return self

    def options(self, dataset: str) -> Any:
        """The source's block: its registered model's instance, else a dict."""
        config = self.sources[dataset]
        model = _SOURCE_MODELS.get(dataset)
        data = {"enabled": config.enabled, **config.options}
        if model is None:
            return data
        return model.model_validate(data, context={"sources": self.sources})

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

    @property
    def world(self) -> World | None:
        """The world block of a synthetic profile, else None."""
        config = self.sources.get(SYNTHETIC)
        if self.real_data or config is None or not config.enabled:
            return None
        options: SyntheticSource = self.options(SYNTHETIC)
        return options.world

    def world_seed(self, seed: int | None = None) -> int:
        """`seed`, else the world's own seed; ProfileError when the profile has no world."""
        world = self.world
        if world is None:
            raise ProfileError(f"profile {self.profile} has no world (sources.nr_synthetic.world)")
        return world.seed if seed is None else seed

    def overlay_seed(self, seed: int | None = None) -> int:
        """`seed`, else `overlay.seed`, else the world's seed (PHASE-3.md M3.3 deliverable 4)."""
        if seed is not None:
            return seed
        if self.overlay is not None and self.overlay.seed is not None:
            return self.overlay.seed
        return self.world_seed()

    def record_dirs(self, project: Project | None = None, *, seed: int | None = None) -> list[Path]:
        """The folders the resolver and the graph loader read for this profile.

        `layout.records_dir(profile, dataset)` for every enabled dataset, and for
        `nr_synthetic` the fixture folders the profile lists and, with a world block, the
        world's folder for `seed` (the world's own seed by default). A world folder without
        records is a ProfileError (exit 2) that names the command that makes it.
        """
        from neonradar_ingest.data import layout  # layout reads profiles: import at call time

        folders: list[Path] = []
        for dataset in self.enabled_sources(project or load_project()):
            if dataset == SYNTHETIC:
                options: SyntheticSource = self.options(dataset)
                folders.extend(REPO_ROOT / folder for folder in options.fixtures)
                if options.world is not None:
                    world_seed = self.world_seed(seed)
                    folder = layout.worlds_dir(options.world.name, world_seed)
                    if not any(folder.glob("*.ftm.jsonl")):
                        raise ProfileError(
                            f"no world for seed {world_seed}: run `neonradar synth world"
                            f" --profile {self.profile} --seed {world_seed}` first"
                        )
                    folders.append(folder)
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
