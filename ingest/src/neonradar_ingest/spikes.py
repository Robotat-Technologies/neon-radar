"""What every spike shares (PHASE-1.md M1.8): C1 records, output files and their retention.

Spike output can hold personal data (Companies House, ICIJ). It goes only to
`data/cache/spikes/<spike>/` (gitignored) as C1 records plus manifest, which the spike then
checks in strict mode; `neonradar spike clean` deletes it after `access.spike_cache_days`.
"""

import json
import re
import time
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from followthemoney import ValueEntity, model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__

REPO_ROOT = Path(__file__).resolve().parents[3]  # members are installed editable
SPIKE_ROOT = REPO_ROOT / "data" / "cache" / "spikes"
PROJECT_FILE = REPO_ROOT / "docs" / "build" / "project.yaml"
PATH_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")  # one file name part: no / or ..


def utc_timestamp(when: datetime | None = None) -> str:
    """`YYYY-MM-DDTHH:MM:SSZ` in UTC, the form of the manifest's `source.retrieved_at`."""
    return (when or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def entity_record(
    schema: str, record_id: str, dataset: str, properties: Mapping[str, Sequence[str | None]]
) -> dict[str, Any]:
    """A C1 record from FtM's `ValueEntity`, never `model.make_entity` (PHASE-1.md 3.2).

    Values are NFC-normalised (R10) and empty ones skipped; FtM cleans the rest and drops what
    it cannot parse. Add `nr` to the result yourself: `{"v": "1.0", ...}`.
    """
    entity = ValueEntity(model[schema], {"id": record_id, "datasets": [dataset]})
    for prop, values in properties.items():
        entity.add(prop, [unicodedata.normalize("NFC", value) for value in values if value])
    return entity.to_dict()


def write_output(
    records: Iterable[Mapping[str, Any]],
    spike: str,
    *,
    dataset: str,
    part: str,
    source: Source | None = None,
    skipped: Mapping[str, int] | None = None,
    notes: Sequence[str] = (),
    root: Path | None = None,
) -> Path:
    """Write `<root>/<spike>/<dataset>-<yyyymmdd>-<part>.ftm.jsonl` and its manifest (5.1, 4.4).

    Returns the record file. A second run on the same day replaces both files. `spike`,
    `dataset` and `part` must each be one plain name, and `dataset` a registry slug; nothing is
    written otherwise, and a record file whose manifest fails is deleted again.
    """
    for name, value in (("spike", spike), ("dataset", dataset), ("part", part)):
        if not PATH_PART.fullmatch(value):
            raise ValueError(f"{name} {value!r} must be letters, digits, '_', '.' or '-'")
    if load_registry().get(dataset) is None:
        raise ValueError(f"dataset {dataset!r} is not in contracts/datasets.yaml")
    folder = (root or SPIKE_ROOT) / spike  # SPIKE_ROOT looked up per call, so tests can patch it
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{dataset}-{datetime.now(UTC):%Y%m%d}-{part}.ftm.jsonl"
    producer = Producer(name=f"neonradar_ingest.sources.{spike}", version=__version__)
    try:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
        write_manifest(
            path, dataset=dataset, producer=producer, source=source, skipped=skipped, notes=notes
        )
    except BaseException:
        path.unlink(missing_ok=True)  # no record file without its manifest
        raise
    return path


def cache_days(project_file: Path | None = None) -> int:
    """`access.spike_cache_days` from docs/build/project.yaml: whole days, 0 or more."""
    project_file = project_file or PROJECT_FILE  # looked up per call, like SPIKE_ROOT
    data = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    access = data.get("access") if isinstance(data, dict) else None
    days = access.get("spike_cache_days") if isinstance(access, dict) else None
    if type(days) is not int or days < 0:
        raise ValueError(f"access.spike_cache_days is {days!r}, not a whole number of days")
    return days


def clean_expired(days: int, root: Path | None = None) -> list[Path]:
    """Delete files under `root` last modified more than `days` days ago, then empty folders.

    Symbolic links inside `root` are deleted, never followed; if `root` itself is a symbolic
    link, its target folder is cleaned. `root` defaults to `SPIKE_ROOT`. Returns the deleted files.
    """
    root = root or SPIKE_ROOT
    if not root.is_dir():
        return []
    cutoff = time.time() - days * 86_400
    deleted: list[Path] = []
    for path in sorted(root.rglob("*"), reverse=True):  # a folder's contents come before it
        if path.is_dir() and not path.is_symlink():
            if not any(path.iterdir()):
                path.rmdir()
        elif path.lstat().st_mtime < cutoff:
            path.unlink()
            deleted.append(path)
    return sorted(deleted)
