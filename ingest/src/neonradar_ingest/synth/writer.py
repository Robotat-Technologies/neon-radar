"""C1 record files for generator v1 (PHASE-3.md 7.2.8; PHASE-1.md 5.1).

One `.ftm.jsonl` file per part with its sibling `.manifest.json` (C1 1.1.0). Lines are the records
in id order, as compact JSON with sorted keys, so the same seed gives the same bytes; the manifest
differs only in `created_at`. `write_part` streams the lines to the file and hashes them as it
goes, so a scale world never holds its whole text in memory. The CLI validates every record with
`neonradar_contracts.records.validate_record` in strict mode before writing (M3.3).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRODUCER = "neonradar_ingest.synth"
GENERATOR_VERSION = "1.0.0"


def line(record: Mapping[str, Any]) -> str:
    """One record as its C1 line, without the newline."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def items(records: Iterable[Mapping[str, Any]]) -> Iterator[tuple[str, str]]:
    """(schema, line) for each record, in id order."""
    for r in sorted(records, key=lambda r: r["id"]):
        yield str(r["schema"]), line(r)


def record_lines(records: Iterable[Mapping[str, Any]]) -> str:
    return "".join(text + "\n" for _, text in items(records))


def manifest(
    name: str,
    sha256: str,
    count: int,
    by_schema: Mapping[str, int],
    *,
    seed: int,
    git_sha: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "record_contract": "1.1.0",
        "dataset": "nr_synthetic",
        "files": [{"path": name, "sha256": sha256, "records": count}],
        "created_at": (created_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": {"name": PRODUCER, "version": GENERATOR_VERSION, "git_sha": git_sha},
        "source": {"urls": [], "retrieved_at": None, "source_version": None},
        "licence": {"id": "Apache-2.0", "attribution": None},
        "counts": {"by_schema": dict(sorted(by_schema.items())), "skipped": {}},
        "dependencies": {"followthemoney": "4.11.0"},
        "synthetic": True,
        "seed": seed,
        "notes": [],
    }


def write_part(
    directory: Path, name: str, lines: Iterable[tuple[str, str]], *, seed: int, git_sha: str
) -> str:
    """Write `<name>.ftm.jsonl` from (schema, line) pairs in id order, and its manifest; return
    the records file's SHA-256."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.ftm.jsonl"
    digest = hashlib.sha256()
    by_schema: Counter[str] = Counter()
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for schema, text in lines:
            data = text + "\n"
            fh.write(data)
            digest.update(data.encode("utf-8"))
            by_schema[schema] += 1
            count += 1
    meta = manifest(path.name, digest.hexdigest(), count, by_schema, seed=seed, git_sha=git_sha)
    (directory / f"{name}.manifest.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return digest.hexdigest()
