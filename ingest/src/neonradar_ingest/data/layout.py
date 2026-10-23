"""Every folder under data/cache/ (PHASE-2.md 4.5, M2.2 deliverable 4).

No other module builds these paths by hand. A profile's folders lie under `real/` or
`synthetic/` as the profile's `real_data` says, so a synthetic profile never gets a path under
`data/cache/real/`. The resolution, label, decision and DuckDB folders also accept the
synthetic pseudo-profiles `er-bench-small` and `er-bench-large` (M2.10a, M2.10b).
Profiles are given as a `Profile` or by name; a name is read from `ingest/profiles/`.
"""

import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

from neonradar_ingest.data.profiles import (
    DATASETS,
    PROFILE_NAME,
    SYNTHETIC,
    Profile,
    load_profile,
)
from neonradar_ingest.data.project import REPO_ROOT

CACHE_ROOT = REPO_ROOT / "data" / "cache"  # looked up per call, so tests can patch it
PSEUDO_PROFILES = ("er-bench-small", "er-bench-large")
ALL_PROFILES = "all-profiles"  # the reports folder of commands about every profile (data status)
PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,99}\Z")  # one folder or file name: no / or ..
LATEST = "LATEST"
DECISIONS = "decisions.jsonl"


def safe_name(what: str, value: str) -> str:
    """`value` if it is one plain folder or file name (no `/`, no `..`), else ValueError."""
    if not PART.fullmatch(value) or ".." in value:
        raise ValueError(f"{what} {value!r} must be letters, digits, '_', '.', '+' or '-'")
    return value


def _dataset(dataset: str) -> str:
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}")
    return dataset


def _profile(profile: Profile | str, *, pseudo: bool = False) -> tuple[str, Path]:
    """The profile's name and its tree (`real/` or `synthetic/`)."""
    name = profile if isinstance(profile, str) else profile.profile
    if name in PSEUDO_PROFILES:
        if not pseudo:
            raise ValueError(f"{name} only has resolution, label, decision and DuckDB folders")
        return name, CACHE_ROOT / "synthetic"
    if not PROFILE_NAME.fullmatch(name):
        raise ValueError(f"{name!r} is not a profile name")
    real = (load_profile(name) if isinstance(profile, str) else profile).real_data
    return name, CACHE_ROOT / ("real" if real else "synthetic")


def real_root() -> Path:
    """`data/cache/real/`: real data; the agent never reads anything here (G9)."""
    return CACHE_ROOT / "real"


def spikes_root() -> Path:
    """`data/cache/spikes/`: Phase 1 spike output (real data, `access.spike_cache_days`)."""
    return CACHE_ROOT / "spikes"


def spill_roots() -> tuple[Path, Path]:
    """The two `duckdb-tmp/` folders, under `real/` and `synthetic/`."""
    return CACHE_ROOT / "real" / "duckdb-tmp", CACHE_ROOT / "synthetic" / "duckdb-tmp"


def sources_dir(dataset: str, product: str, version: str) -> Path:
    """Downloads of one version of a product, shared by every real profile."""
    return (
        real_root()
        / "sources"
        / _dataset(dataset)
        / safe_name("product", product)
        / safe_name("version", version)
    )


def _dataset_tree(profile: Profile | str, dataset: str) -> tuple[str, Path]:
    """A dataset's tree: `real/` for a real profile, and for every dataset but `nr_synthetic`
    whatever the profile says, so real records never land under `synthetic/`."""
    name, tree = _profile(profile)
    if _dataset(dataset) != SYNTHETIC:
        tree = real_root()
    if dataset != SYNTHETIC and not tree.is_relative_to(real_root()):
        raise AssertionError(f"{dataset} would be written outside data/cache/real/")
    return name, tree


def records_dir(profile: Profile | str, dataset: str) -> Path:
    name, tree = _dataset_tree(profile, dataset)
    return tree / "records" / name / dataset


def work_dir(profile: Profile | str, dataset: str) -> Path:
    """A build's intermediate files (indexes, slice.csv)."""
    name, tree = _dataset_tree(profile, dataset)
    return tree / "work" / name / dataset


def resolution_dir(profile: Profile | str, run_id: str) -> Path:
    name, tree = _profile(profile, pseudo=True)
    return tree / "resolution" / name / safe_name("run id", run_id)


def latest_run(profile: Profile | str) -> str | None:
    """The run id in `resolution/<profile>/LATEST` (written last by `er run`), else None."""
    name, tree = _profile(profile, pseudo=True)
    try:
        run_id = (tree / "resolution" / name / LATEST).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return safe_name("run id", run_id)


def labels_dir(profile: Profile | str, run_id: str) -> Path:
    name, tree = _profile(profile, pseudo=True)
    return tree / "labels" / name / safe_name("run id", run_id)


def decisions_file(profile: Profile | str) -> Path:
    """Human same and different decisions: one file per tree, shared by its profiles (4.5)."""
    return _profile(profile, pseudo=True)[1] / DECISIONS


def real_decisions_file() -> Path:
    return real_root() / DECISIONS


def duckdb_tmp_dir(profile: Profile | str, run_id: str) -> Path:
    """DuckDB spill files of one run; the run deletes the folder when it ends."""
    return _profile(profile, pseudo=True)[1] / "duckdb-tmp" / safe_name("run id", run_id)


def reports_dir(profile: Profile | str) -> Path:
    """Counts-only summaries of every command: the one folder the agent reads for real data.

    `ALL_PROFILES` names the folder of commands that are about every profile.
    """
    name = ALL_PROFILES if profile == ALL_PROFILES else _profile(profile, pseudo=True)[0]
    return CACHE_ROOT / "reports" / name


def logs_dir() -> Path:
    """Full tracebacks of failed real-profile commands (the redaction guard)."""
    return real_root() / "logs"


def officer_cache_dir() -> Path:
    return real_root() / "api" / "gb_companies_house" / "officers"


def parliament_cache_dir() -> Path:
    return real_root() / "api" / "gb_parliament_members"


def bench_dir(size: str) -> Path:
    """The generated entity resolution benchmark (M2.9)."""
    return CACHE_ROOT / "synthetic" / f"er-bench-{safe_name('size', size)}"


def real_labels_root() -> Path:
    return real_root() / "labels"


def dataset_dirs(dataset: str) -> list[Path]:
    """A dataset's downloads, and its record and work folders in every real profile."""
    _dataset(dataset)
    real = real_root()
    found = [real / "sources" / dataset]
    for kind in ("records", "work"):
        found.extend(sorted((real / kind).glob(f"*/{dataset}")))
    if dataset == "gb_companies_house":
        found.append(officer_cache_dir())
    if dataset == "gb_parliament_members":
        found.append(parliament_cache_dir())
    return found


def profile_dirs(profile: Profile | str) -> list[Path]:
    """A profile's record, work, resolution and label folders (downloads are shared)."""
    name, tree = _profile(profile)
    return [tree / kind / name for kind in ("records", "work", "resolution", "labels")]


def worlds_dir(world: str, seed: int) -> Path:
    """A synthetic world (`neonradar synth world`, PHASE-3.md 4.5): `synthetic/` only."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError(f"seed {seed!r} must be a whole number of at least 0")
    return CACHE_ROOT / "synthetic" / "worlds" / safe_name("world", world) / str(seed)


def _overlay_root(profile: Profile | str) -> Path:
    name, tree = _profile(profile)
    return tree / "overlay" / name


def overlay_dir(profile: Profile | str, overlay_id: str) -> Path:
    """One overlay of a profile, under `real/` or `synthetic/` as the profile says (4.5)."""
    return _overlay_root(profile) / safe_name("overlay id", overlay_id)


def latest_overlay(profile: Profile | str) -> str | None:
    """The overlay id in `overlay/<profile>/LATEST` (written last by `synth overlay`)."""
    try:
        overlay_id = (_overlay_root(profile) / LATEST).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return safe_name("overlay id", overlay_id)


def runs_dir(profile: Profile | str, run_id: str) -> Path:
    """One detection run of a profile, under `real/` or `synthetic/` (PHASE-3.md 4.5, M3.4);
    its parent holds the profile's runs and `LATEST`."""
    name, tree = _profile(profile)
    return tree / "runs" / name / safe_name("run id", run_id)


def latest_detection_run(profile: Profile | str) -> str | None:
    """The run id in `runs/<profile>/LATEST` (written last by `detect run`)."""
    name, tree = _profile(profile)
    try:
        run_id = (tree / "runs" / name / LATEST).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return safe_name("run id", run_id)


def eval_dir(eval_id: str) -> Path:
    """A development evaluation (`neonradar eval run`, M3.6): synthetic only."""
    return CACHE_ROOT / "synthetic" / "eval" / safe_name("evaluation id", eval_id)


def holdout_dir(eval_id: str) -> Path:
    """The human holdout run's folder (M3.12); closed to the build agent (G11)."""
    return CACHE_ROOT / "holdout" / safe_name("evaluation id", eval_id)


def new_run_id(prefix: str) -> str:
    """`<prefix>-<UTC yyyymmddThhmmss>-<4 hex>`, as resolution run ids (4.4)."""
    return f"{safe_name('prefix', prefix)}-{datetime.now(UTC):%Y%m%dT%H%M%S}-{secrets.token_hex(2)}"
