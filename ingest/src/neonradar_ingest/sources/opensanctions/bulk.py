"""The OpenSanctions bulk loader (PHASE-2.md M2.7), only where `access.opensanctions` allows it.

The download: `data fetch` reads the collection's `index.json` (following the 307
redirect) and downloads it with `entities.ftm.json`, whose size it checks. The loader refuses
first, before any request, unless `access.opensanctions` is `licensed` or `exempt` (the data
manager's gate runs before it). It sends no request, redirects included, outside
data.opensanctions.org, and stops the collection when `index.json` names a file elsewhere.

The build checks the SHA-1 against that `index.json`, streams the export through
`mapping.map_entity` and writes one record file with its manifest, after the same refusal.
Unless `opensanctions_default` is in `access.pep_sources`, PEP data is removed (`_Pep`); then
dangling references are dropped or removed so that the records pass C1 in strict mode.
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


def _pinned(request: httpx.Request) -> None:
    """A request hook: no request or redirect hop off data.opensanctions.org is ever sent."""
    if (request.url.scheme, request.url.host) != ("https", PINNED_HOST):
        raise DownloadError(f"a request outside {PINNED_HOST}", "host")


def discover_for(collection: str) -> Callable[[HttpClient], list[RemoteFile]]:
    def discover(client: HttpClient) -> list[RemoteFile]:
        project = load_project()
        refuse_unless_allowed(project)  # before any request
        if _pinned not in client.event_hooks["request"]:  # also for the downloads that follow
            client.event_hooks["request"].append(_pinned)
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


def _ends(schema_name: str) -> tuple[str, ...]:
    schema = model[schema_name]
    if schema.edge and schema.edge_source and schema.edge_target:
        return (schema.edge_source, schema.edge_target)
    return ("entity",) if schema_name == "Sanction" else ()


def _links(record: dict[str, Any]) -> dict[str, list[str]]:
    schema, props = model[record["schema"]], record["properties"]
    return {name: props[name] for name in props if schema.properties[name].type == registry.entity}


class _Pep:
    """Deliverable 2 on one mapped record; returns False when the record is skipped."""

    def __init__(self) -> None:
        self.topics_removed: Counter[str] = Counter()
        self.schemata_skipped: Counter[str] = Counter()
        self.pep_only_skipped: Counter[str] = Counter()
        self.skipped_ids: set[str] = set()
        self.referenced: set[str] = set()  # what the skipped records referenced

    def keep(self, record: dict[str, Any]) -> bool:
        schema, props = record["schema"], record["properties"]
        topics: list[str] = props.get("topics", [])
        flags = flag_topics(topics)
        if schema in PEP_SCHEMATA or (flags and all(is_role(topic) for topic in flags)):
            skipped = self.schemata_skipped if schema in PEP_SCHEMATA else self.pep_only_skipped
            skipped[schema] += 1
            self.skipped_ids.add(record["id"])
            self.referenced.update(value for values in _links(record).values() for value in values)
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


def _write(work: Path, path: Path, kept: set[str], pep: _Pep) -> dict[str, Counter[str]]:
    """Pass 2: drop a relationship with an end that is not written (before counting anything
    else in it), remove every other reference to a record not written, write, count."""
    counts = {key: Counter[str]() for key in ("written", "dropped", "removed", "topics", "flags")}
    counts["pep_dropped"] = Counter()  # dropped relationships with an end the PEP rule skipped
    linked: dict[str, str] = {}  # written, no flag topic, referenced by a skipped PEP record
    referenced: set[str] = set()  # what the written records reference
    with (
        work.open(encoding="utf-8") as lines,
        path.open("w", encoding="utf-8", newline="\n") as out,
    ):
        for line in lines:
            record = json.loads(line)
            schema, props, links = record["schema"], record["properties"], _links(record)
            ends = {value for end in _ends(schema) for value in links.get(end, [])}
            if ends - kept:  # a relationship with an end that is not written is dropped
                counts["dropped"][schema] += 1
                if ends & pep.skipped_ids:
                    counts["pep_dropped"][schema] += 1
                continue
            for name, values in links.items():  # any other reference to one is removed
                if dangling := [value for value in values if value not in kept]:
                    counts["removed"][f"{schema}:{name}"] += len(dangling)
                    props[name] = [value for value in values if value in kept]
                    if not props[name]:
                        del props[name]
            referenced.update(value for values in links.values() for value in values)
            topics = props.get("topics", [])
            if record["id"] in pep.referenced and not flag_topics(topics):
                linked[record["id"]] = schema
            counts["written"][schema] += 1
            counts["topics"].update(topics)
            counts["flags"].update(flag_labels(topics))
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    counts["pep_linked"] = Counter(s for id_, s in linked.items() if id_ not in referenced)
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
    stats, pep = MappingStats(), _Pep()
    context.work_dir.mkdir(parents=True, exist_ok=True)
    work = context.work_dir / f"{context.run_id}.mapped.jsonl"
    path = context.out_dir / f"{DATASET}-{collection}.ftm.jsonl"
    try:
        kept, sha1 = _map(folder / ENTITIES_FILE, work, None if pep_decision else pep, stats)
        if sha1 != checksum.lower():
            message = f"{DATASET}: the SHA-1 of {ENTITIES_FILE} does not match index.json"
            raise BuildError(message, "checksum", counts_only=True)
        counts = _write(work, path, kept, pep)
    finally:
        if not context.keep_work:
            work.unlink(missing_ok=True)
    files = download.get("files", [])
    stamps = [str(entry["downloaded_at"]) for entry in files if entry.get("downloaded_at")]
    write_manifest(
        path,
        dataset=DATASET,
        producer=Producer(name=__name__, version=__version__),
        source=Source(
            urls=[str(entry["url"]) for entry in files if entry.get("url")],
            retrieved_at=max(stamps, default=None),
            source_version=folder.name,
        ),
        skipped=_vocab(  # FtM vocabulary only, as in the summary
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
            "relationships_dropped": _vocab(counts["dropped"]),
            "pep_relationships_dropped": _vocab(counts["pep_dropped"]),
            "pep_linked_entities_kept": _vocab(counts["pep_linked"]),
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
