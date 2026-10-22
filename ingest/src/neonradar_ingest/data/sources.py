"""The plug-in interface every loader implements (PHASE-2.md M2.2 deliverable 6).

A loader module registers, at import time, a `SourceSpec` (how to find the current files of
each product, for `neonradar data fetch`) and a `Builder` (how to turn downloads into C1
records and manifests, for `neonradar ingest build`), and, for its profile block, a pydantic
model (`profiles.register_source_model`). Add the module to `PLUGINS` so the CLI imports it.
"""

import importlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_ingest.data.profiles import DATASETS, Profile
from neonradar_ingest.data.project import Project
from neonradar_ingest.http import HttpClient, RateLimiter

PLUGINS: tuple[str, ...] = (
    "neonradar_ingest.data.synthetic",
    "neonradar_ingest.sources.companies_house.build",
)
# Where each dataset's loader arrives; `data fetch` and `ingest build` name it until then.
AVAILABLE_IN = {
    "nr_synthetic": "M2.2",
    "gb_companies_house": "M2.3a",
    "gleif_lei": "M2.4",
    "icij_offshore_leaks": "M2.5",
    "gb_fcdo_sanctions": "M2.6a",
    "us_ofac_sdn": "M2.6b",
    "un_sc_sanctions": "M2.6c",
    "eu_fsf": "M2.6d",
    "gb_parliament_members": "M2.6e",
    "opensanctions_default": "M2.7",
}


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """One file of the current version of a product.

    Products: `companies` and `psc` for gb_companies_house, `golden-copy` for gleif_lei, `main`
    for every other dataset. `version` is the source's own version, else the download date.
    """

    name: str
    url: str
    version: str
    size: int | None
    sha256: str | None
    product: str = "main"


def default_client() -> HttpClient:
    """The shared client (timeouts, retries, User-Agent) at one request per second."""
    return HttpClient("", follow_redirects=True, limiter=RateLimiter(1.0))


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """`discover(client)` lists the files of the current version of each product.

    `client` builds the source's HTTP client (its rate limit and redirect rule).
    """

    dataset: str
    discover: Callable[[HttpClient], list[RemoteFile]]
    client: Callable[[], HttpClient] = default_client


@dataclass(frozen=True, slots=True)
class BuildContext:
    """What a builder gets: it writes records and manifests only into `out_dir`.

    `out_dir` is a temporary folder next to `layout.records_dir(profile, dataset)`, which
    `ingest build` validates in strict mode and only then swaps in; `work_dir` holds the
    build's intermediate files. `steps` empty means all, in the builder's order.
    """

    project: Project
    run_id: str
    out_dir: Path
    work_dir: Path
    steps: tuple[str, ...] = ()
    keep_work: bool = False
    accept_size: bool = False


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Counts (numbers or nested dicts of numbers), plus short strings and lists of short
    strings under the builder's `string_keys` and `list_keys`, for the counts-only summary."""

    counts: Mapping[str, Any] = field(default_factory=dict)
    strings: Mapping[str, str] = field(default_factory=dict)
    lists: Mapping[str, Sequence[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Builder:
    """`cleanup`, when given, runs only after a successful build and swap (for example to
    delete work indexes), so a failed validation leaves the work files in place. `plan`,
    when given, names the steps a build of a profile runs for the requested ones (empty: all),
    so `ingest build` gates only those."""

    dataset: str
    build: Callable[[Profile, BuildContext], BuildResult]
    steps: tuple[str, ...] = ()
    string_keys: tuple[str, ...] = ()
    list_keys: tuple[str, ...] = ()
    cleanup: Callable[[Profile, BuildContext, BuildResult], None] | None = None
    plan: Callable[[Profile, tuple[str, ...]], tuple[str, ...]] | None = None

    def planned(self, profile: Profile, steps: tuple[str, ...]) -> tuple[str, ...]:
        """The steps a build runs: `plan`'s answer, else the requested ones, else all."""
        return self.plan(profile, steps) if self.plan else steps or self.steps


class BuildError(Exception):
    """A build that must stop; the previous records stay in place.

    On a real profile the redaction guard prints the message only when `counts_only` is true:
    set it only for a message made of counts, rule ids, dataset slugs and file names.
    """

    exit_code = 1

    def __init__(self, message: str, rule: str | None = None, *, counts_only: bool = False) -> None:
        super().__init__(message)
        self.rule, self.counts_only = rule, counts_only


_SOURCES: dict[str, SourceSpec] = {}
_BUILDERS: dict[str, Builder] = {}


def _known(dataset: str) -> None:
    if dataset not in DATASETS:
        raise ValueError(f"{dataset!r} is not a dataset the data manager knows")


def register_source(spec: SourceSpec) -> None:
    _known(spec.dataset)
    _SOURCES[spec.dataset] = spec


def register_builder(builder: Builder) -> None:
    _known(builder.dataset)
    _BUILDERS[builder.dataset] = builder


def source_spec(dataset: str) -> SourceSpec | None:
    return _SOURCES.get(dataset)


def builder_for(dataset: str) -> Builder | None:
    return _BUILDERS.get(dataset)


def load_plugins() -> None:
    """Import every loader module in `PLUGINS`, which registers its spec and builder."""
    for module in PLUGINS:
        importlib.import_module(module)
