"""The OpenSanctions spike: `index.json`, then a slice of `entities.ftm.json` (M1.8d step 4).

`run_spike` checks the licence gate before it sends anything. When access allows it, it reads
the collection's `index.json` (the `datasets/latest/...` paths answer 307 since 17 August 2026,
so the client must follow redirects), logs the version and the checksum of `entities.ftm.json`,
streams the first `rows` lines, maps them to C1 in memory and counts schemata, topics and
flags. Only `licensed` access writes the records and their manifest, to the spike cache.
"""

import json
import logging
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import httpx

from neonradar_contracts.records import Producer, Source, validate_record, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.sources.opensanctions.access import (
    REPO_ROOT,
    Access,
    may_write,
    require_access,
)
from neonradar_ingest.sources.opensanctions.mapping import DATASET, MappingStats, map_lines

logger = logging.getLogger(__name__)

BASE_URL = "https://data.opensanctions.org/datasets/latest"
ENTITIES_FILE = "entities.ftm.json"
# Collections on the OpenSanctions datasets index (research note A.1). `all` is left out on
# purpose: OpenSanctions calls it "a strictly inferior data product" and says to use `default`.
COLLECTIONS = (
    "default", "sanctions", "peps", "crime", "debarment", "regulatory", "maritime", "securities",
)  # fmt: skip
CACHE_DIR = REPO_ROOT / "data" / "cache" / "spikes" / "opensanctions"
PRODUCER = "neonradar_ingest.sources.opensanctions"
INVALID = "<C1 issues>"  # manifest counts.skipped key for mapped records that fail validation


def _text(meta: Mapping[str, Any], key: str) -> str | None:
    value = meta.get(key)
    return value if isinstance(value, str) else None


@dataclass(frozen=True)
class IndexInfo:
    """What `index.json` says about the collection and its `entities.ftm.json`."""

    url: str  # the URL that answered, after redirects
    redirects: tuple[int, ...]
    version: str | None
    last_export: str | None
    entities_url: str
    checksum: str | None  # SHA-1 of entities.ftm.json
    size: int | None

    @classmethod
    def from_body(
        cls, body: Mapping[str, Any], collection: str, url: str, redirects: tuple[int, ...]
    ) -> Self:
        """Parse an `index.json` body.

        The metadata documentation groups `version`, `last_export` and `resources` under a
        `dataset` section without saying whether that is a JSON key, so both shapes work.
        """
        meta = body["dataset"] if isinstance(body.get("dataset"), dict) else body
        resources = meta.get("resources") or body.get("resources") or []
        entry: Mapping[str, Any] = next(
            (r for r in resources if isinstance(r, dict) and r.get("name") == ENTITIES_FILE), {}
        )
        size = entry.get("size")
        return cls(
            url=url,
            redirects=redirects,
            version=_text(meta, "version"),
            last_export=_text(meta, "last_export"),
            entities_url=_text(entry, "url") or f"{BASE_URL}/{collection}/{ENTITIES_FILE}",
            checksum=_text(entry, "checksum"),
            size=size if isinstance(size, int) else None,
        )


@dataclass
class SpikeResult:
    """Counts only: no names or other values from the data."""

    access: Access
    collection: str
    index: IndexInfo
    entities_url: str = ""  # the URL that answered, after redirects
    entities_redirects: tuple[int, ...] = ()
    stats: MappingStats = field(default_factory=MappingStats)
    issues: Counter[str] = field(default_factory=Counter)  # C1 rule -> issues
    invalid: int = 0  # mapped records with at least one C1 issue; never written
    records_file: Path | None = None
    seconds: float = 0.0


def index_url(collection: str) -> str:
    """`https://data.opensanctions.org/datasets/latest/<collection>/index.json`."""
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}; use one of {', '.join(COLLECTIONS)}")
    return f"{BASE_URL}/{collection}/index.json"


def _history(response: httpx.Response) -> tuple[int, ...]:
    return tuple(step.status_code for step in response.history)


def read_index(client: httpx.Client, collection: str) -> IndexInfo:
    """GET the collection's `index.json` and log its version and the entities checksum."""
    response = client.get(index_url(collection))
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError(f"{response.url}: index.json is not a JSON object")
    info = IndexInfo.from_body(body, collection, str(response.url), _history(response))
    logger.info(
        "OpenSanctions %s version %s, %s sha1 %s", collection, info.version, ENTITIES_FILE,
        info.checksum,
    )  # fmt: skip
    return info


def run_spike(
    client: httpx.Client,
    *,
    access: Access,
    collection: str = "sanctions",
    rows: int = 1000,
    out_dir: Path = CACHE_DIR,
    licence_file: Path | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> SpikeResult:
    """Run the spike if `access` allows it; raise LicenceRequired before any request if not."""
    require_access(access, licence_file)
    if rows < 1:
        raise ValueError("rows must be at least 1")
    started = clock()
    result = SpikeResult(access=access, collection=collection, index=read_index(client, collection))
    kept: list[dict[str, Any]] = []
    with client.stream("GET", result.index.entities_url) as response:
        response.raise_for_status()
        result.entities_url = str(response.url)
        result.entities_redirects = _history(response)
        for record in map_lines(response.iter_lines(), result.stats, limit=rows):
            issues = validate_record(record)
            result.issues.update(issue.rule for issue in issues)
            result.invalid += bool(issues)
            if not issues and may_write(access):
                kept.append(record)
    if may_write(access):
        result.records_file = _write(kept, result, out_dir)
    result.seconds = clock() - started
    return result


def _write(records: list[dict[str, Any]], result: SpikeResult, out_dir: Path) -> Path:
    """Licensed access only: write the records and their manifest into the spike cache."""
    now = datetime.now(UTC)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{DATASET}-{now:%Y%m%d}-{result.collection}.ftm.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_manifest(
        path,
        dataset=DATASET,
        producer=Producer(name=PRODUCER, version=__version__),
        source=Source(
            urls=[result.index.url, result.entities_url],
            retrieved_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            source_version=result.index.version,
        ),
        skipped={**result.stats.skipped, **({INVALID: result.invalid} if result.invalid else {})},
        notes=[
            f"collection {result.collection}; the first {result.stats.lines} lines only",
            "a slice: references to entities outside it dangle, so validate without --strict",
        ],
    )
    return path


def _counts(counter: Counter[str], top: int | None = None) -> str:
    items = counter.most_common(top)
    return ", ".join(f"{key} {count}" for key, count in items) if items else "none"


def summary_lines(result: SpikeResult) -> list[str]:
    """What the command prints: counts and field names only, never names or values."""
    stats, index = result.stats, result.index
    redirects = ", ".join(str(code) for code in index.redirects) or "none"
    if result.records_file is None:
        written = f"wrote nothing (access {result.access} writes nothing)"
    else:
        written = f"wrote {result.records_file} and its manifest"
    return [
        f"OpenSanctions spike: collection {result.collection}, access {result.access}",
        f"index.json: {index.url} (redirects: {redirects})",
        f"version {index.version or 'unknown'}, last export {index.last_export or 'unknown'}",
        f"{ENTITIES_FILE}: {result.entities_url}, sha1 {index.checksum or 'unknown'},"
        f" {index.size if index.size is not None else 'unknown'} bytes",
        f"read {stats.lines} lines in {result.seconds:.1f} s: {stats.mapped.total()} C1 records,"
        f" {stats.skipped.total()} skipped",
        f"  by schema: {_counts(stats.mapped)}",
        f"  skipped: {_counts(stats.skipped)}",
        f"  unknown to FollowTheMoney: {_counts(stats.unknown_schemata)}",
        f"  topics (top 15): {_counts(stats.topics, 15)}",
        f"  C2 flags: {_counts(stats.flags)}",
        f"  dropped keys: {_counts(stats.dropped_keys)}",
        f"  dropped properties: {_counts(stats.dropped_properties)}",
        f"  dropped values: {_counts(stats.dropped_values)}",
        f"  source datasets: {len(stats.source_datasets)}",
        f"C1 issues: {_counts(result.issues)} ({result.invalid} records)",
        written,
    ]
