"""What is on this machine, in counts (PHASE-2.md M2.2 deliverable 11, `data status`).

Reads file metadata only (names of dataset, product, version and run folders, sizes, ages),
never a file's contents.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import Project
from neonradar_ingest.data.retention import DAY, leftover_spill_dirs


@dataclass(frozen=True, slots=True)
class VersionStatus:
    dataset: str
    product: str
    version: str
    files: int
    bytes: int
    age_days: int
    partial: int  # `.part` files of an unfinished download
    past_retention: bool


@dataclass(frozen=True, slots=True)
class ProfileStatus:
    profile: str
    real_data: bool
    record_folders: int
    record_files: int
    resolution_runs: int
    label_files: int


def _sizes(folder: Path) -> tuple[int, int, float, int]:
    """Files, bytes, newest modification time and `.part` files under `folder`."""
    files = size = partial = 0
    newest = 0.0
    for root, _, names in os.walk(folder):
        for name in names:
            info = Path(root, name).lstat()
            files, size, newest = files + 1, size + info.st_size, max(newest, info.st_mtime)
            partial += name.endswith(".part")
    return files, size, newest, partial


def _subfolders(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []


def downloads(project: Project, now: float | None = None) -> list[VersionStatus]:
    """Every downloaded version of every dataset and product, with its age and retention."""
    now = time.time() if now is None else now
    found: list[VersionStatus] = []
    for dataset in _subfolders(layout.real_root() / "sources"):
        for product in _subfolders(dataset):
            for version in _subfolders(product):
                files, size, newest, partial = _sizes(version)
                age = int((now - newest) // DAY) if files else 0
                past = files > 0 and now - newest > project.access.real_data_days * DAY
                found.append(
                    VersionStatus(
                        dataset.name, product.name, version.name, files, size, age, partial, past
                    )
                )
    return found


def profile_status(profile: Profile) -> ProfileStatus:
    """Counts of a profile's record folders and files, resolution runs and label files."""
    records, _, resolution, labels = layout.profile_dirs(profile)
    folders = _subfolders(records)
    return ProfileStatus(
        profile.profile,
        profile.real_data,
        len(folders),
        sum(_sizes(folder)[0] for folder in folders),
        sum(1 for run in _subfolders(resolution) if not run.name.startswith(".")),
        _sizes(labels)[0] if labels.is_dir() else 0,
    )


def spill_leftovers() -> dict[str, int]:
    """Leftover DuckDB spill folders under `real/` and `synthetic/`."""
    real_root = layout.spill_roots()[0]
    leftovers = leftover_spill_dirs()
    real = sum(1 for path in leftovers if path.is_relative_to(real_root))
    return {"real": real, "synthetic": len(leftovers) - real}
