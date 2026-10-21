"""What every spike shares (PHASE-1.md M1.8): C1 records, output files and their retention.

Spike output can hold personal data (Companies House, ICIJ). It goes only to
`data/cache/spikes/<spike>/` (gitignored) as C1 records plus manifest, which the spike then
checks in strict mode; `neonradar spike clean` deletes it after `access.spike_cache_days`.
"""

import json
import time
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from followthemoney import ValueEntity, model

from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__

REPO_ROOT = Path(__file__).resolve().parents[3]  # members are installed editable
SPIKE_ROOT = REPO_ROOT / "data" / "cache" / "spikes"
PROJECT_FILE = REPO_ROOT / "docs" / "build" / "project.yaml"


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
    root: Path = SPIKE_ROOT,
) -> Path:
    """Write `<root>/<spike>/<dataset>-<yyyymmdd>-<part>.ftm.jsonl` and its manifest (5.1, 4.4).

    Returns the record file. A second run on the same day replaces both files.
    """
    folder = root / spike
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{dataset}-{datetime.now(UTC):%Y%m%d}-{part}.ftm.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    producer = Producer(name=f"neonradar_ingest.sources.{spike}", version=__version__)
    write_manifest(
        path, dataset=dataset, producer=producer, source=source, skipped=skipped, notes=notes
    )
    return path


def cache_days(project_file: Path = PROJECT_FILE) -> int:
    """`access.spike_cache_days` from docs/build/project.yaml: whole days, 0 or more."""
    data = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    access = data.get("access") if isinstance(data, dict) else None
    days = access.get("spike_cache_days") if isinstance(access, dict) else None
    if type(days) is not int or days < 0:
        raise ValueError(f"access.spike_cache_days is {days!r}, not a whole number of days")
    return days


def clean_expired(days: int, root: Path = SPIKE_ROOT) -> list[Path]:
    """Delete files under `root` last modified more than `days` days ago, then empty folders.

    Symbolic links are deleted, never followed. Returns the deleted files.
    """
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
