"""Delete real data by scope (PHASE-2.md M2.2 deliverable 8).

`targets(scope, ...)` lists what a scope covers; `delete(paths)` removes files and folders and
counts files and bytes. Only paths under `data/cache/` are ever deleted, and symbolic links are
removed, never followed. The real-data Neo4j volume (`--graph`) is deleted by the CLI
(`neonradar_cli.real_graph`), so `ingest` does not depend on Docker or `graph`.
"""

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from neonradar_ingest.data import layout, retention
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import Project


class Scope(StrEnum):
    EXPIRED = "expired"
    DATASET = "dataset"
    PROFILE = "profile"
    LABELS = "labels"
    DECISIONS = "decisions"
    LOGS = "logs"
    ALL_REAL = "all-real"


@dataclass(slots=True)
class Deleted:
    files: int = 0
    bytes: int = 0


def targets(
    scope: Scope,
    project: Project,
    *,
    dataset: str | None = None,
    profile: Profile | None = None,
    now: float | None = None,
) -> list[Path]:
    """What `scope` deletes: files and folders, which may not exist."""
    match scope:
        case Scope.EXPIRED:
            return retention.expired(project, now)
        case Scope.DATASET:
            if dataset is None:
                raise ValueError("--dataset needs a dataset")
            return layout.dataset_dirs(dataset)
        case Scope.PROFILE:
            if profile is None:
                raise ValueError("--profile needs a profile")
            return layout.profile_dirs(profile)
        case Scope.LABELS:
            return [layout.real_labels_root()]
        case Scope.DECISIONS:
            return [layout.real_decisions_file()]
        case Scope.LOGS:
            return [layout.logs_dir()]
        case Scope.ALL_REAL:
            return [layout.real_root(), layout.spikes_root()]


def _remove(path: Path, deleted: Deleted) -> None:
    """Delete a file or link, or a folder's contents and the folder.

    A folder given through a symbolic link (for example `data/cache/real/` on an encrypted
    volume) is emptied and the link kept; links inside are removed, never followed.
    """
    if not path.is_dir():
        deleted.files += 1
        deleted.bytes += path.lstat().st_size
        path.unlink()
        return
    for folder, subfolders, names in os.walk(path, topdown=False):
        for name in [*names, *(s for s in subfolders if Path(folder, s).is_symlink())]:
            item = Path(folder, name)
            deleted.files += 1
            deleted.bytes += item.lstat().st_size
            item.unlink()
        if Path(folder) != path:
            Path(folder).rmdir()
    if not path.is_symlink():
        path.rmdir()


def _prune(root: Path) -> None:
    """Remove empty folders under `root` (kept itself)."""
    for folder, _, _ in os.walk(root, topdown=False):
        if Path(folder) != root and not any(Path(folder).iterdir()):
            Path(folder).rmdir()


def delete(paths: list[Path]) -> Deleted:
    """Delete every path (file or folder) under `data/cache/`; count files and bytes."""
    # Lexical containment (normpath removes `..` without following links), so a symbolic link
    # to an encrypted volume inside the cache still counts as inside; it is emptied, not followed.
    cache = Path(os.path.normpath(layout.CACHE_ROOT.absolute()))
    deleted = Deleted()
    for path in paths:
        if not Path(os.path.normpath(path.absolute())).is_relative_to(cache):
            raise ValueError(f"{path} is outside {cache}: not deleted")
        if path.is_symlink() or path.exists():
            _remove(path, deleted)
    for root in (layout.real_root(), layout.spikes_root()):
        if root.is_dir():
            _prune(root)
    return deleted
