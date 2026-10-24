"""The OpenSanctions bulk loader (PHASE-2.md M2.7), only where `access.opensanctions` allows it.

`data fetch` reads the collection's `index.json` (following the 307 redirect) and downloads it
with `entities.ftm.json`, whose size it checks; `ingest build` checks the export's SHA-1 against
the downloaded index, streams it line by line through `mapping.map_entity` (C1 schemata only,
`os-` ids and references, `datasets: ["opensanctions_default"]`, topics as published) and
writes one record file with its manifest. Both refuse first, before any request or file, unless
`access.opensanctions` is `licensed` or `exempt` (the data manager's gate runs before them), and
`data fetch` stops the collection when `index.json` names a file outside data.opensanctions.org.

PEP data only by decision (deliverable 2): unless `opensanctions_default` is in
`access.pep_sources`, every `role.*` topic is removed, `Position` and `Occupancy` are skipped, and
so is an entity whose only flag topics (7.1.1) were `role.*` topics. Then a relationship (an FtM
edge, or a `Sanction`) with an end that is not written is dropped, and any other reference to a
record that is not written is removed, so the records pass C1 in strict mode. All counted.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from followthemoney import model, registry
from pydantic import BaseModel, ConfigDict, StrictBool

from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data import layout
from neonradar_ingest.data.download import DownloadError
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.project import Project, load_project
from neonradar_ingest.data.sources import (
    BuildContext,
    Builder,
    BuildError,
    BuildResult,
    RemoteFile,
    SourceSpec,
    register_builder,
    register_source,
)
from neonradar_ingest.http import HttpClient
from neonradar_ingest.sources.opensanctions.mapping import (
    DATASET,
    MALFORMED,
    NOT_JSON,
    MappingStats,
    flag_labels,
    map_lines,
)
from neonradar_ingest.sources.opensanctions.spike import (
    ENTITIES_FILE,
    HOST,
    IndexInfo,
    make_client,
    read_index,
)

INDEX_FILE = "index.json"
DOWNLOAD_RECORD = "download.json"  # data.download.RECORD
PINNED_HOST = httpx.URL(HOST).host  # every file comes from data.opensanctions.org
PEP_SCHEMATA = frozenset({"Position", "Occupancy"})
# 7.1.1: the purely descriptive topics; every other topic is a flag topic.
DESCRIPTIVE = frozenset({"corp.public", "fin", "gov", "pol.party", "pol.union", "rel", "mil"})
DESCRIPTIVE_PREFIXES = ("fin.", "gov.")


class OpenSanctionsSource(BaseModel):
    """The profile block: `collection` is `sanctions` (the default) or `default` (everything)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    collection: Literal["sanctions", "default"] = "sanctions"


def flag_topics(topics: list[str]) -> set[str]:
    """The topics that are not purely descriptive (PHASE-2.md 7.1.1)."""
    return {t for t in topics if t not in DESCRIPTIVE and not t.startswith(DESCRIPTIVE_PREFIXES)}


def is_role(topic: str) -> bool:
    return topic == "role" or topic.startswith("role.")


def refuse_unless_allowed(project: Project) -> None:
    """RealDataRefused (exit 3, the Phase 1 message) unless `licensed` or `exempt`."""
    refusal = project.access_refusal(DATASET)
    if refusal is not None:
        raise RealDataRefused(*refusal)


def discover_for(collection: str) -> Callable[[HttpClient], list[RemoteFile]]:
    def discover(client: HttpClient) -> list[RemoteFile]:
        project = load_project()
        refuse_unless_allowed(project)  # before any request
        info = read_index(client, collection, access=project.access.opensanctions)
        if {httpx.URL(url).host for url in (info.url, info.entities_url)} != {PINNED_HOST}:
            raise DownloadError(f"{collection}: a file outside {PINNED_HOST}", "host")
        version = info.version or datetime.now(UTC).strftime("%Y-%m-%d")
        return [
            RemoteFile(INDEX_FILE, info.url, version, None, None, product=collection),
            RemoteFile(ENTITIES_FILE, info.entities_url, version, info.size, None, collection),
        ]

    return discover


def products(profile: Profile) -> Mapping[str, Callable[[HttpClient], list[RemoteFile]]]:
    """Only the collection the profile names is downloaded (data minimisation)."""
    collection = profile.options(DATASET).collection
    return {collection: discover_for(collection)}


def latest_download(collection: str) -> tuple[Path, dict[str, Any]]:
    """The newest complete download of `collection` with both files, and its `download.json`."""
    product_dir = layout.sources_dir(DATASET, collection, "latest").parent
    found: list[tuple[str, str, Path, dict[str, Any]]] = []
    for folder in sorted(product_dir.iterdir()) if product_dir.is_dir() else []:
        try:
            record = json.loads((folder / DOWNLOAD_RECORD).read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        names = {entry.get("name") for entry in record.get("files", [])}
        if record.get("complete") and {INDEX_FILE, ENTITIES_FILE} <= names:
            found.append((str(record.get("completed_at", "")), folder.name, folder, record))
    if not found:
        raise BuildError(
            f"{DATASET}: no complete download of the {collection} collection; run"
            " `neonradar data fetch` first",
            "download",
            counts_only=True,
        )
    _, _, folder, record = max(found)
    return folder, record


def _hashed_lines(path: Path, digest: Any) -> Iterator[bytes]:
    with path.open("rb") as handle:
        for line in handle:
            digest.update(line)
            yield line


def _known(name: str) -> bool:
    """A schema or topic, or `Schema:property`, exactly as FollowTheMoney names it."""
    schema_name, colon, prop = name.partition(":")
    schema = model.get(schema_name)
    if colon:
        return schema is not None and prop in schema.properties
    return schema is not None or name in registry.topic.names


def _vocab(counter: Mapping[str, int]) -> dict[str, int]:
    """Counts keyed by lower-case FtM vocabulary (schemata, topics, properties) for the summary;
    a name FollowTheMoney does not know is counted under `unknown`, never shown."""
    out: Counter[str] = Counter()
    special = {NOT_JSON: "not_json", MALFORMED: "malformed"}
    for name, count in counter.items():
        out[special.get(name) or (name.lower() if _known(name) else "unknown")] += count
    return dict(sorted(out.items()))


class _Pep:
    """Deliverable 2 on one mapped record; returns False when the record is skipped."""

    def __init__(self) -> None:
        self.topics_removed: Counter[str] = Counter()
        self.schemata_skipped: Counter[str] = Counter()
        self.pep_only_skipped: Counter[str] = Counter()
        self.skipped_ids: set[str] = set()

    def keep(self, record: dict[str, Any]) -> bool:
        schema, props = record["schema"], record["properties"]
        if schema in PEP_SCHEMATA:
            self.schemata_skipped[schema] += 1
            self.skipped_ids.add(record["id"])
            return False
        topics: list[str] = props.get("topics", [])
        flags = flag_topics(topics)
        if flags and all(is_role(topic) for topic in flags):
            self.pep_only_skipped[schema] += 1
            self.skipped_ids.add(record["id"])
            return False
        removed = [topic for topic in topics if is_role(topic)]
        if removed:
            self.topics_removed.update(removed)
            kept = [topic for topic in topics if not is_role(topic)]
            if kept:
                props["topics"] = kept
            else:
                del props["topics"]
        return True


def _ends(schema_name: str) -> tuple[str, ...]:
    schema = model[schema_name]
    if schema.edge and schema.edge_source and schema.edge_target:
        return (schema.edge_source, schema.edge_target)
    return ("entity",) if schema_name == "Sanction" else ()


def _references(
    record: dict[str, Any], kept: set[str], removed: Counter[str]
) -> dict[str, Any] | None:
    """The record without references to records not written, or None for a relationship whose
    end is not written."""
    schema, props = model[record["schema"]], record["properties"]
    ends = _ends(schema.name)
    for name in [p for p in props if schema.properties[p].type == registry.entity]:
        values = [value for value in props[name] if value in kept]
        if len(values) < len(props[name]):
            if name in ends:
                return None
            removed[f"{schema.name}:{name}"] += len(props[name]) - len(values)
            if values:
                props[name] = values
            else:
                del props[name]
    return record


def _map(entities: Path, work: Path, pep: _Pep | None, stats: MappingStats) -> tuple[set[str], str]:
    """Pass 1: map every line to the work file; return the written ids and the SHA-1."""
    digest = hashlib.sha1(usedforsecurity=False)
    kept: set[str] = set()
    with work.open("w", encoding="utf-8", newline="\n") as out:
        for record in map_lines(_hashed_lines(entities, digest), stats):
            if pep is None or pep.keep(record):
                kept.add(record["id"])
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
    return kept, digest.hexdigest()


def _write(work: Path, path: Path, kept: set[str], pep_ids: set[str]) -> dict[str, Counter[str]]:
    """Pass 2: drop or trim the references of each record, write it, count what it holds;
    `pep_dropped` counts the dropped relationships with an end the PEP rule skipped."""
    keys = ("written", "dropped", "pep_dropped", "removed", "topics", "flags")
    counts = {key: Counter[str]() for key in keys}
    with (
        work.open(encoding="utf-8") as lines,
        path.open("w", encoding="utf-8", newline="\n") as out,
    ):
        for line in lines:
            data = json.loads(line)
            record = _references(data, kept, counts["removed"])
            if record is None:
                schema, props = data["schema"], data["properties"]
                counts["dropped"][schema] += 1
                if pep_ids & {value for end in _ends(schema) for value in props.get(end, [])}:
                    counts["pep_dropped"][schema] += 1
                continue
            topics = record["properties"].get("topics", [])
            counts["written"][record["schema"]] += 1
            counts["topics"].update(topics)
            counts["flags"].update(flag_labels(topics))
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    return counts


def build(profile: Profile, context: BuildContext) -> BuildResult:
    project = context.project
    refuse_unless_allowed(project)
    collection = profile.options(DATASET).collection
    folder, download = latest_download(collection)
    index = json.loads((folder / INDEX_FILE).read_text(encoding="utf-8"))
    checksum = IndexInfo.from_body(index, collection, "", ()).checksum
    if not checksum:
        raise BuildError(f"{DATASET}: index.json gives no checksum", "checksum", counts_only=True)
    pep_decision = DATASET in project.access.pep_sources
    stats, pep = MappingStats(), None if pep_decision else _Pep()
    context.work_dir.mkdir(parents=True, exist_ok=True)
    work = context.work_dir / f"{context.run_id}.mapped.jsonl"
    path = context.out_dir / f"{DATASET}-{collection}.ftm.jsonl"
    try:
        kept, sha1 = _map(folder / ENTITIES_FILE, work, pep, stats)
        if sha1 != checksum.lower():
            message = f"{DATASET}: the SHA-1 of {ENTITIES_FILE} does not match index.json"
            raise BuildError(message, "checksum", counts_only=True)
        counts = _write(work, path, kept, pep.skipped_ids if pep else set())
    finally:
        if not context.keep_work:
            work.unlink(missing_ok=True)
    files = download.get("files", [])
    stamps = [str(entry["downloaded_at"]) for entry in files if entry.get("downloaded_at")]
    pep = pep or _Pep()
    write_manifest(
        path,
        dataset=DATASET,
        producer=Producer(name=__name__, version=__version__),
        source=Source(
            urls=[str(entry["url"]) for entry in files if entry.get("url")],
            retrieved_at=max(stamps, default=None),
            source_version=folder.name,
        ),
        skipped=dict(
            stats.skipped + pep.schemata_skipped + pep.pep_only_skipped + counts["dropped"]
        ),
        notes=[
            f"collection {collection}",
            "PEP data kept: opensanctions_default is in access.pep_sources"
            if pep_decision
            else "PEP data removed: opensanctions_default is not in access.pep_sources",
        ],
    )
    return BuildResult(
        counts={
            "lines": stats.lines,
            "records": counts["written"].total(),
            "records_by_schema": _vocab(counts["written"]),
            "skipped_by_schema": _vocab(stats.skipped),
            "pep_role_topics_removed": _vocab(pep.topics_removed),
            "pep_schemata_skipped": _vocab(pep.schemata_skipped),
            "pep_only_entities_skipped": _vocab(pep.pep_only_skipped),
            "relationships_dropped": _vocab(counts["dropped"]),  # both causes
            "pep_relationships_dropped": _vocab(counts["pep_dropped"]),
            "references_removed": _vocab(counts["removed"]),
            "topics": _vocab(counts["topics"]),
            "flags": {label.lower(): n for label, n in sorted(counts["flags"].items())},
            "dropped_keys": stats.dropped_keys.total(),
            "dropped_properties": stats.dropped_properties.total(),
            "dropped_values": stats.dropped_values.total(),
        },
        strings={
            "collection": collection,
            "source_version": folder.name,
            "pep_data": "kept" if pep_decision else "removed",
        },
    )


register_source_model(DATASET, OpenSanctionsSource)
register_source(SourceSpec(DATASET, discover_for("sanctions"), make_client, products))
register_builder(Builder(DATASET, build, string_keys=("collection", "source_version", "pep_data")))
