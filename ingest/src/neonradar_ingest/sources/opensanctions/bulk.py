"""The OpenSanctions bulk loader (PHASE-2.md M2.7), only where `access.opensanctions` allows it.

The download: `data fetch` reads the collection's `index.json` (following the 307
redirect) and downloads it with `entities.ftm.json`, whose size it checks. The loader refuses
first, before any request, unless `access.opensanctions` is `licensed` or `exempt` (the data
manager's gate runs before it). It sends no request, redirects included, outside
data.opensanctions.org, and stops the collection when `index.json` names a file elsewhere.

The build checks the SHA-1 against that `index.json`, streams the export through
`mapping.map_entity` and writes one record file with its manifest, after the same refusal.
Unless `opensanctions_default` is in `access.pep_sources`, PEP data is removed (`_Pep`). So that
the records pass C1 in strict mode, a record that fails C1 on its own is skipped, then
relationships whose end is not written or not of its range are dropped, then BankAccounts no
written Ownership holds (R8), and every other such reference is removed; all of it counted.
"""

import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any, Literal

import httpx
from followthemoney import model, registry
from pydantic import BaseModel, ConfigDict, StrictBool

from neonradar_contracts.records import (
    REFERENCE_RANGES,
    Producer,
    Source,
    validate_record,
    write_manifest,
)
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
    """A request hook: no request or redirect hop off https://data.opensanctions.org (port 443)
    is ever sent."""
    url = request.url
    if (url.scheme, url.host) != ("https", PINNED_HOST) or url.port not in (None, 443):
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


@cache
def _ends(schema_name: str) -> tuple[str, ...]:
    """The required references: an edge's two ends, or a Sanction's entity."""
    schema = model[schema_name]
    return tuple(sorted(n for n in schema.required if schema.properties[n].type == registry.entity))


@cache
def _in_range(schema_name: str, prop: str, target: str) -> bool:
    """`schema_name:prop` may point to a `target` record (R4 in strict mode, REFERENCE_RANGES)."""
    prop_range = model[schema_name].properties[prop].range
    names = REFERENCE_RANGES.get((schema_name, prop)) or ((prop_range.name,) if prop_range else ())
    return not names or any(model[target].is_a(name) for name in names)


def _fits(schema: str, prop: str, value: str, kinds: Mapping[str, str]) -> bool:
    """The reference is to a written record of the property's range."""
    target = kinds.get(value)
    return target is not None and _in_range(schema, prop, target)


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


Counts = defaultdict[str, Counter[str]]


def _map(
    entities: Path, work: Path, pep: _Pep | None, stats: MappingStats, counts: Counts
) -> tuple[dict[str, str], str]:
    """Pass 1: map every line to the work file, skipping a record that fails C1 on its own or
    repeats an id (counted by schema and by rule); return the written ids' schemata, the SHA-1."""
    digest = hashlib.sha1(usedforsecurity=False)
    kinds: dict[str, str] = {}
    with work.open("w", encoding="utf-8", newline="\n") as out:
        for record in map_lines(_hashed_lines(entities, digest), stats):
            if pep is not None and not pep.keep(record):
                continue
            rules = {issue.rule for issue in validate_record(record)}
            if rules or record["id"] in kinds:  # a repeated id is R4
                counts["invalid"][record["schema"]] += 1
                counts["rules"].update(rules or {"R4"})
                continue
            kinds[record["id"]] = sys.intern(record["schema"])  # one string per schema
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    return kinds, digest.hexdigest()


def _resolve(work: Path, kinds: dict[str, str], pep: _Pep, counts: Counts) -> None:
    """Pass 2: take out of `kinds` every relationship with an end that is not written or not of
    its range (R4), then every BankAccount no Ownership left holds (R8) and every relationship
    that ends at one. No end can be a relationship (tested), so nothing else follows."""
    held: set[str] = set()
    at_accounts: dict[str, tuple[str, set[str]]] = {}  # relationship id: schema, accounts
    with work.open(encoding="utf-8") as lines:
        for line in lines:
            record = json.loads(line)
            schema, props = record["schema"], record["properties"]
            ends = {(name, value) for name in _ends(schema) for value in props.get(name, [])}
            if not all(_fits(schema, name, value, kinds) for name, value in ends):
                del kinds[record["id"]]
                counts["dropped"][schema] += 1
                if any(value in pep.skipped_ids for _, value in ends):
                    counts["pep_dropped"][schema] += 1
            elif schema == "Ownership":  # its owner is a written LegalEntity (range)
                held.update(props["asset"])
            elif accounts := {value for _, value in ends if kinds[value] == "BankAccount"}:
                at_accounts[record["id"]] = (schema, accounts)
    unheld = {id_ for id_, schema in kinds.items() if schema == "BankAccount"} - held
    for id_ in unheld:
        del kinds[id_]
        counts["invalid"]["BankAccount"] += 1
        counts["rules"]["R8"] += 1
    for id_, (schema, accounts) in at_accounts.items():
        if accounts & unheld:
            del kinds[id_]
            counts["dropped"][schema] += 1


def _write(work: Path, path: Path, kinds: Mapping[str, str], pep: _Pep, counts: Counts) -> None:
    """Pass 3: write the records left in `kinds` without any reference to a record that is not
    written or not of the property's range (counted), and count what is written."""
    linked: dict[str, str] = {}  # written, no flag topic, referenced by a skipped PEP record
    referenced: set[str] = set()  # what the written records reference
    with (
        work.open(encoding="utf-8") as lines,
        path.open("w", encoding="utf-8", newline="\n") as out,
    ):
        for line in lines:
            record = json.loads(line)
            schema, props = record["schema"], record["properties"]
            if record["id"] not in kinds:  # dropped in pass 2, and counted there
                continue
            for name, values in _links(record).items():
                kept = [value for value in values if _fits(schema, name, value, kinds)]
                if len(kept) < len(values):
                    counts["removed"][f"{schema}:{name}"] += len(values) - len(kept)
                    props[name] = kept
                    if not kept:
                        del props[name]
                referenced.update(kept)
            topics = props.get("topics", [])
            if record["id"] in pep.referenced and not flag_topics(topics):
                linked[record["id"]] = schema
            counts["written"][schema] += 1
            counts["topics"].update(topics)
            counts["flags"].update(flag_labels(topics))
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    counts["pep_linked"].update(s for id_, s in linked.items() if id_ not in referenced)


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
    stats, pep, counts = MappingStats(), _Pep(), Counts(Counter)
    context.work_dir.mkdir(parents=True, exist_ok=True)
    work = context.work_dir / f"{context.run_id}.mapped.jsonl"
    path = context.out_dir / f"{DATASET}-{collection}.ftm.jsonl"
    try:
        entities, maybe_pep = folder / ENTITIES_FILE, None if pep_decision else pep
        kinds, sha1 = _map(entities, work, maybe_pep, stats, counts)
        if sha1 != checksum.lower():
            message = f"{DATASET}: the SHA-1 of {ENTITIES_FILE} does not match index.json"
            raise BuildError(message, "checksum", counts_only=True)
        _resolve(work, kinds, pep, counts)
        _write(work, path, kinds, pep, counts)
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
            stats.skipped
            + pep.schemata_skipped
            + pep.pep_only_skipped
            + counts["dropped"]
            + counts["invalid"]
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
            "c1_records_skipped": _vocab(counts["invalid"]),
            "c1_issues": {rule.lower(): n for rule, n in sorted(counts["rules"].items())},  # r1-r10
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
