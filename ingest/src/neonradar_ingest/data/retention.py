"""How long real data stays (PHASE-2.md M2.2 deliverable 8, 7.4 rule 3).

`expired(project)` lists files under `data/cache/real/` older than `access.real_data_days`
(label files: `access.label_days`), files under `data/cache/spikes/` older than
`access.spike_cache_days`, and leftover `duckdb-tmp/<run_id>/` folders of runs that have
finished, under `real/` and `synthetic/`: DuckDB spill files hold record values.

A run that uses `layout.duckdb_tmp_dir` opens it with `spill_dir`, which writes the run's
process id into the folder and deletes the folder when the run ends; a folder whose process
is gone is a leftover. Only file metadata and that process id are read, never a file's contents.
"""

import contextlib
import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import Project

DAY = 86_400
PID_FILE = "run.pid"


def _files(root: Path) -> Iterator[Path]:
    """Every file and symbolic link under `root`; symbolic links to folders are not followed."""
    for folder, _, names in os.walk(root):
        for name in names:
            yield Path(folder, name)


def _older(path: Path, days: int, now: float) -> bool:
    try:
        return now - path.lstat().st_mtime > days * DAY
    except FileNotFoundError:
        return False


def _running(folder: Path) -> bool:
    """Whether the process named in the folder's `run.pid` still runs on this machine."""
    try:
        pid = int((folder / PID_FILE).read_text(encoding="ascii").strip())
        os.kill(pid, 0)
    except PermissionError:  # it exists, under another user
        return True
    except OSError, ValueError:  # no pid file, no such process, or not a number
        return False
    return True


def leftover_spill_dirs() -> list[Path]:
    """`duckdb-tmp/<run_id>/` folders under `real/` and `synthetic/` whose run has ended."""
    found: list[Path] = []
    for root in layout.spill_roots():
        if root.is_dir():
            found.extend(p for p in sorted(root.iterdir()) if p.is_dir() and not _running(p))
    return found


@contextlib.contextmanager
def spill_dir(profile: Profile | str, run_id: str) -> Iterator[Path]:
    """`layout.duckdb_tmp_dir(profile, run_id)`, created for one run and deleted when it ends."""
    folder = layout.duckdb_tmp_dir(profile, run_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PID_FILE).write_text(f"{os.getpid()}\n", encoding="ascii")
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def expired(project: Project, now: float | None = None) -> list[Path]:
    """Every file and spill folder past its retention period, sorted."""
    now = time.time() if now is None else now
    access = project.access
    real, labels, spill = layout.real_root(), layout.real_labels_root(), layout.spill_roots()[0]
    found: list[Path] = []
    for path in _files(real):
        if path.is_relative_to(spill):
            continue  # spill folders go by their run, not their age
        days = access.label_days if path.is_relative_to(labels) else access.real_data_days
        if _older(path, days, now):
            found.append(path)
    found.extend(p for p in _files(layout.spikes_root()) if _older(p, access.spike_cache_days, now))
    found.extend(leftover_spill_dirs())
    return sorted(found)
