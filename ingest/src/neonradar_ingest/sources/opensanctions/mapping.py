"""Map lines of OpenSanctions' `entities.ftm.json` to C1 records (C1-record.md, M1.8d).

Per entity:

- parse it with `ValueEntity.from_dict`; a schema the pinned FollowTheMoney does not know, a
  schema outside C1 v1, or a Payment (synthetic only in C1 v1, rule R7) is skipped and counted;
- drop the legacy `target` key and every other top-level key C1 does not allow (counted);
- keep exactly one dataset, `opensanctions_default`, instead of OpenSanctions' source datasets
  (counted in `MappingStats.source_datasets`);
- prefix the id, every reference and every referent with the dataset's `os` prefix through
  `make_id`, with one kind (`ent`) for every schema, so a reference gets the same id as the
  entity it points to without knowing its schema; keep the OpenSanctions id in `nr.source_ref`;
- add every value through FollowTheMoney's cleaning, which drops values it rejects (counted),
  normalise strings to NFC (R10), and write timestamps in UTC without an offset.
"""

import json
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any

from followthemoney import ValueEntity, registry
from followthemoney.exc import InvalidData

from neonradar_contracts import versions
from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import ALLOWED_SCHEMATA, OPTIONAL_KEYS, make_id
from neonradar_ingest.spikes import entity_record

DATASET = "opensanctions_default"
ID_KIND = "ent"
NR_VERSION = ".".join(versions.RECORD.split(".")[:2])  # nr.v is the contract's major.minor
TIMESTAMP_KEYS = ("first_seen", "last_seen", "last_change")
KEPT_KEYS = frozenset({"id", "schema", "properties", "datasets", *OPTIONAL_KEYS}) - {"nr"}
NOT_LOADED = frozenset({"Payment"})  # C1 v1: Payment records are synthetic only (R7)
NOT_JSON = "<not JSON>"
MALFORMED = "<malformed>"
# The C2 flag labels and the topics that set them (PHASE-1.md 5.2). The keys equal
# neonradar_contracts.records.SYNTHETIC_TOPICS (tested); `sanction.linked` and other topics set
# no flag.
FLAG_LABELS: Mapping[str, str] = {"sanction": "Sanctioned", "role.pep": "PEP", "role.rca": "RCA"}


@dataclass
class MappingStats:
    """What a mapping run saw. Counts and field names only, never names or other values."""

    lines: int = 0
    mapped: Counter[str] = field(default_factory=Counter)  # records by schema
    skipped: Counter[str] = field(default_factory=Counter)  # entities by schema, NOT_JSON...
    unknown_schemata: Counter[str] = field(default_factory=Counter)  # unknown to FtM; in skipped
    topics: Counter[str] = field(default_factory=Counter)
    flags: Counter[str] = field(default_factory=Counter)  # C2 flag labels, per record
    source_datasets: Counter[str] = field(default_factory=Counter)
    dropped_keys: Counter[str] = field(default_factory=Counter)  # top-level keys, e.g. target
    dropped_properties: Counter[str] = field(default_factory=Counter)  # "Schema:prop" unknown
    dropped_values: Counter[str] = field(default_factory=Counter)  # "Schema:prop" FtM rejected


@cache
def id_prefix() -> str:
    """The `os` prefix, read from contracts/datasets.yaml (G7)."""
    dataset = load_registry().get(DATASET)
    if dataset is None:
        raise LookupError(f"{DATASET} is not in contracts/datasets.yaml")
    return dataset.id_prefix


def record_id(native: str) -> str:
    """The C1 id for an OpenSanctions id: `os-ent-<id>` through make_id (C1-record.md)."""
    return make_id(id_prefix(), ID_KIND, native)


def flag_labels(topics: Iterable[str]) -> frozenset[str]:
    """The C2 flag labels (`Sanctioned`, `PEP`, `RCA`) that these FtM topics set."""
    return frozenset(FLAG_LABELS[topic] for topic in topics if topic in FLAG_LABELS)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def seen_timestamp(value: object) -> str | None:
    """An ISO timestamp in UTC without an offset; a date-only value is kept; else None."""
    if not isinstance(value, str) or not registry.date.validate(value):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value  # a valid partial date such as 2025 or 2025-08
    if parsed.tzinfo is None:
        return value
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _well_formed(data: Mapping[str, Any]) -> bool:
    props = data.get("properties", {})
    return (
        isinstance(data.get("id"), str)
        and bool(data["id"])
        and isinstance(data.get("schema"), str)
        and isinstance(props, dict)
        and all(
            isinstance(values, list) and all(isinstance(v, str) for v in values)
            for values in props.values()
        )
    )


def map_entity(data: Mapping[str, Any], stats: MappingStats) -> dict[str, Any] | None:
    """Map one OpenSanctions entity to a C1 record, or return None if it is skipped."""
    if not _well_formed(data):
        stats.skipped[MALFORMED] += 1
        return None
    name: str = data["schema"]
    try:
        parsed = ValueEntity.from_dict(dict(data))  # a copy: FollowTheMoney pops keys
    except InvalidData:
        stats.skipped[name] += 1
        stats.unknown_schemata[name] += 1
        return None
    schema = parsed.schema
    if schema.name not in ALLOWED_SCHEMATA or schema.name in NOT_LOADED:
        stats.skipped[schema.name] += 1
        return None
    stats.dropped_keys.update(key for key in data if key not in KEPT_KEYS)
    unknown = [prop for prop in data.get("properties", {}) if prop not in schema.properties]
    stats.dropped_properties.update(f"{schema.name}:{prop}" for prop in unknown)
    stats.source_datasets.update(parsed.datasets)

    offered: dict[str, list[str]] = {}
    for prop_name, values in parsed.properties.items():
        if schema.properties[prop_name].type == registry.entity:
            values = [record_id(value) for value in values]
        offered[prop_name] = list(dict.fromkeys(values))  # keeps the order
    rid = record_id(data["id"])
    cleaned = entity_record(schema.name, rid, DATASET, offered)  # FtM cleaning, NFC
    record: dict[str, Any] = {
        "id": rid,
        "schema": schema.name,
        "properties": cleaned["properties"],
        "datasets": [DATASET],
    }
    for prop_name, values in offered.items():
        rejected = len(values) - len(record["properties"].get(prop_name, []))
        if rejected > 0:  # dropped or merged by FollowTheMoney's cleaning
            stats.dropped_values[f"{schema.name}:{prop_name}"] += rejected
    referents = sorted({record_id(ref) for ref in parsed.referents if ref} - {rid})
    if referents:
        record["referents"] = referents
    caption = data.get("caption")
    if isinstance(caption, str) and caption.strip():
        record["caption"] = _nfc(caption)
    for key in TIMESTAMP_KEYS:
        stamp = seen_timestamp(data.get(key))
        if stamp is not None:
            record[key] = stamp
    record["nr"] = {"v": NR_VERSION, "source_ref": _nfc(data["id"])}

    topics = record["properties"].get("topics", [])
    stats.topics.update(topics)
    stats.flags.update(flag_labels(topics))
    stats.mapped[schema.name] += 1
    return record


def map_lines(
    lines: Iterable[str | bytes], stats: MappingStats, limit: int | None = None
) -> Iterator[dict[str, Any]]:
    """Map the lines of an `entities.ftm.json` stream; stop after `limit` non-blank lines."""
    for line in lines:
        text = line.decode("utf-8") if isinstance(line, bytes) else line
        if not text.strip():
            continue
        stats.lines += 1
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            record = map_entity(data, stats)
            if record is not None:
                yield record
        else:
            stats.skipped[NOT_JSON] += 1
        if limit is not None and stats.lines >= limit:
            return
