"""Map C1 records to the parameter rows the C2 graph loader sends (PHASE-1.md 5.2, M1.7b;
C2 1.1.0 company properties and share-band flags, PHASE-2.md 5.2, M2.1b; entity resolution,
loader rules L10 to L15, M2.11).

Pure functions without database access. Labels and relationship types come only from
`neonradar_contracts.graph`: the loader writes them into its query text per schema or type and
sends these rows as parameters. Records must be C1-valid (the loader validates them first and
never maps a record that failed); what C1 accepts but C2 cannot represent is skipped and
reported as a `MappingIssue`, and a strict load fails on any of them.

Both functions take the whole load as a sequence (a list), never a one-shot iterator: each
reads it in full, and `to_relationship_rows` reads it twice. Record-level issues (not a C1
record, duplicate id) appear in both results; `MappingIssue` is hashable, so the loader merges
the two `skipped` lists with `dict.fromkeys`. See contracts/C2-graph-schema.md.

With a resolution run (`ResolutionMap`), the members of a merged entity become one node row
under its `nr-` id, merged with the rules of PHASE-2.md 7.1.6, plus one `:SourceRecord` row and
one `RESOLVED_TO` row per member; every relationship end is re-pointed to the canonical id, a
relationship whose two ends land on one node is dropped (`self_loops_dropped`), and HAS_ADDRESS
or SUBJECT_OF rows that land on the same two nodes become one row that keeps the smallest of
their record-built ids (`duplicate_relationships_merged`; C2 keeps those ids unchanged by
resolution). Without one, every record is its own entity, as in Phase 1.
"""

import json
import sys
from collections import Counter
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from functools import reduce
from typing import Any

from followthemoney import Schema, ValueEntity, model, registry
from followthemoney.exc import InvalidData

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.graph import (
    CERTAIN_METHODS,
    FLAG_LABELS,
    NAME_PROPERTIES,
    NAMES_SEPARATOR,
    NODE_MAPPINGS,
    POSSIBLY_SAME_AS_ID_INFIX,
    PROPERTY_KINDS,
    REFERENCE_MAPPINGS,
    RELATIONSHIP_ENDPOINTS,
    RELATIONSHIP_MAPPINGS,
    SYNTHETIC_LABEL,
    TOPIC_FLAGS,
    NodeMapping,
    ReferenceMapping,
    RelationshipMapping,
)
from neonradar_graph.resolution import CANONICAL_PREFIX, Member, ResolutionMap
from neonradar_keys.addresses import address_key, address_key_from_parts
from neonradar_keys.names import latin_forms

Record = Mapping[str, Any]
# The labels a node is MERGEd and MATCHed on with `{id: ...}`: each has a uniqueness constraint.
KEY_LABELS = frozenset(mapping.labels[0] for mapping in NODE_MAPPINGS.values())
# Relationships built from a reference property: their ids are derived from the two record ids.
DERIVED_TYPES = frozenset(ref.type for ref in REFERENCE_MAPPINGS)
# L12: the role a merged HAS_ADDRESS keeps, the first of these among its rows.
ROLE_ORDER = ("registered", "service", "residential", "business", "unknown")
MAX_NAMES = 50  # 7.1.6: a merged entity keeps at most 50 names
ADDRESS_PARTS = ("street", "street2", "city", "region", "state", "postalCode")


@dataclass(frozen=True, slots=True)
class MappingIssue:
    """A record, or one of its references, that C2 v1 cannot represent; it was skipped."""

    record_id: str
    message: str

    def __str__(self) -> str:
        return f"C2 {self.record_id}: {self.message}"


@dataclass(frozen=True, slots=True)
class NodeRow:
    """One node. The loader MERGEs on `labels[0]` and `id`, sets the other labels and flags."""

    schema: str
    id: str
    props: dict[str, Any]
    flags: tuple[str, ...]

    @property
    def labels(self) -> tuple[str, ...]:
        return NODE_MAPPINGS[self.schema].labels

    def as_param(self) -> dict[str, Any]:
        """The row for `UNWIND $rows AS row`; `row.flags.<Label>` drives each flag label."""
        flags = {label: label in self.flags for label in FLAG_LABELS}
        return {"id": self.id, "props": self.props, "flags": flags}


@dataclass(frozen=True, slots=True)
class RelationshipRow:
    """One relationship between the nodes with ids `source` and `target` (canonical ids after
    resolution). PAID carries `props["ts"]`, a timezone-aware datetime in UTC, which Neo4j
    stores as a DATETIME. `resolving`: an end is not a node of this load, so the loader finds it
    in the database, also through a `:SourceRecord` (L13)."""

    type: str
    id: str
    source: str
    target: str
    props: dict[str, Any]
    resolving: bool = False

    @property
    def endpoint_labels(self) -> tuple[str, str]:
        """The label each end must carry (the From and To columns of C2)."""
        return RELATIONSHIP_ENDPOINTS[self.type]

    @property
    def endpoint_keys(self) -> tuple[str, str]:
        """The label to MATCH each end on with `{id: ...}`, so the uniqueness index is used:
        `(s:<key> {id: row.source}) WHERE s:<label>`."""
        source, target = (
            label if label in KEY_LABELS else "Entity" for label in self.endpoint_labels
        )
        return source, target

    def as_param(self) -> dict[str, Any]:
        return {"id": self.id, "source": self.source, "target": self.target, "props": self.props}


@dataclass(frozen=True, slots=True)
class SupportRow:
    """A row of a resolution query: its match keys (`id`; `record_id` and `canonical_id`; or
    `id`, `a` and `b`) and the properties to set."""

    keys: dict[str, str]
    props: dict[str, Any]

    def as_param(self) -> dict[str, Any]:
        return {**self.keys, "props": self.props}


@dataclass(slots=True)
class MappingResult[T]:
    """The rows to load, the records or references that were skipped, and counts (for
    relationships: `self_loops_dropped` and `duplicate_relationships_merged`)."""

    rows: list[T] = field(default_factory=list)
    skipped: list[MappingIssue] = field(default_factory=list)
    counts: Counter[str] = field(default_factory=Counter)


def _schema(record: Record) -> Schema | None:
    name = record.get("schema")
    return model.get(name) if isinstance(name, str) else None


def _values(record: Record, prop: str) -> list[str]:
    values = (record.get("properties") or {}).get(prop) or []
    return [value for value in values if isinstance(value, str)]


def _nr(record: Record) -> dict[str, Any]:
    nr = record.get("nr")
    return nr if isinstance(nr, dict) else {}


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _convert(values: Sequence[Any], kind: str) -> Any:
    match kind:
        case "list":
            return list(values)
        case "float":
            return float(values[0])
        case "integer":
            return int(values[0])
        case "boolean":  # never bool("false")
            return values[0] is True or str(values[0]).lower() == "true"
        case "datetime":  # C1 R5: UTC without an offset; never a string (I3)
            moment = datetime.fromisoformat(str(values[0]))
            return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
        case _:
            return str(values[0])


def _countries(values: Iterable[str]) -> list[str]:
    """Lower-case ISO codes, first-seen order; values FtM cannot read as a country are dropped."""
    return _unique(code for value in values if (code := registry.country.clean(value)))


def _mapped(
    properties: Mapping[str, str], record: Record, key: str | None = None
) -> dict[str, Any]:
    """C2 properties from FtM properties and `nr` keys; absent values are left out.

    Country-typed values become lower-case codes. `key` selects the entry of an object-valued
    `nr` key (the referenced id).
    """
    out: dict[str, Any] = {}
    nr = _nr(record)
    schema = _schema(record)
    for source, target in properties.items():
        kind = PROPERTY_KINDS.get(target, "string")
        if source.startswith("nr."):
            value = nr.get(source.removeprefix("nr."))
            if isinstance(value, dict):
                value = value.get(key) if key is not None else None
            if value is not None:
                out[target] = _convert(value if kind == "list" else [value], kind)
        else:
            values = _values(record, source)
            prop = schema.properties.get(source) if schema is not None else None
            if prop is not None and prop.type == registry.country:
                values = _countries(values)
            if values:
                out[target] = _convert(values, kind)
    return out


def _dataset_synthetic(record: Record) -> bool | None:
    datasets = record.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 1:
        return None
    dataset = load_registry().get(datasets[0])
    return None if dataset is None else dataset.synthetic


def _caption(record: Record) -> str:
    """The record's own caption, else FtM's (first caption property, else the schema label)."""
    caption = record.get("caption")
    if isinstance(caption, str) and caption:
        return caption
    return str(ValueEntity.from_dict(dict(record)).caption)


def _flags(topics: Sequence[str], synthetic: bool, mapping: NodeMapping) -> tuple[str, ...]:
    flags = [SYNTHETIC_LABEL] if synthetic else []
    if mapping.labels[0] == "Entity":
        for flag in TOPIC_FLAGS:
            prefix = f"{flag.topic}."
            if any(t == flag.topic or (flag.subtopics and t.startswith(prefix)) for t in topics):
                flags.append(flag.label)
    return tuple(flags)


def _names(record: Record, mapping: NodeMapping) -> list[str]:
    return _unique(
        value
        for prop in (*NAME_PROPERTIES, *mapping.extra_names)
        for value in _values(record, prop)
    )


def _address_key(record: Record) -> str | None:
    """L15: the key from `full`, else from the address parts, as the resolver's rule D6 reads it."""
    full = _values(record, "full")
    if full:
        return address_key(full[0])
    parts = [value for prop in ADDRESS_PARTS for value in _values(record, prop)]
    return address_key_from_parts([*parts, *_values(record, "country")[:1]])


def _resolution_props(
    names: list[str], mapping: NodeMapping, cluster_size: int, resolution: str
) -> dict[str, Any]:
    """C2 1.1.0 properties of every :Entity, computed at load time (L15)."""
    if mapping.labels[0] != "Entity":
        return {}
    latin = latin_forms(names)
    return {
        "cluster_size": cluster_size,
        "resolution": resolution,
        "names_latin": latin,
        "names_latin_text": NAMES_SEPARATOR.join(latin),
    }


def _node_row(record: Record, schema: Schema, mapping: NodeMapping, synthetic: bool) -> NodeRow:
    rid = str(record["id"])
    names = _names(record, mapping)
    countries = sorted(
        _countries(
            value
            for name, prop in schema.properties.items()
            if prop.type == registry.country
            for value in _values(record, name)
        )
    )
    topics = _values(record, "topics")
    props: dict[str, Any] = {
        "id": rid,
        "schema": schema.name,
        "caption": _caption(record),
        "names": names,
        "names_text": NAMES_SEPARATOR.join(names),
        "countries": countries,
        "topics": topics,
        "datasets": list(record["datasets"]),
        "referents": [rid],  # a single-record entity keeps its record id (ADR-0016)
        "synthetic": synthetic,
    }
    for key in ("first_seen", "last_seen"):
        if isinstance(record.get(key), str):
            props[key] = record[key]
    props |= _mapped({"sourceUrl": "source_url", **mapping.properties}, record)
    props |= _resolution_props(names, mapping, 1, "identity")
    if "Address" in mapping.labels and (found := _address_key(record)):
        props["address_key"] = found
    return NodeRow(schema.name, rid, props, _flags(topics, synthetic, mapping))


Usable = tuple[Record, Schema, bool]


def _first_records(records: Iterable[Record], skipped: list[MappingIssue]) -> Iterator[Usable]:
    """Records with a known schema and dataset, the first of each id (C1 R4 rejects the rest)."""
    seen: set[str] = set()
    for record in records:
        rid, schema, synthetic = record.get("id"), _schema(record), _dataset_synthetic(record)
        if not isinstance(rid, str) or schema is None or synthetic is None:
            skipped.append(MappingIssue(str(rid), "not a C1 record (id, schema or dataset)"))
        elif rid in seen:
            skipped.append(MappingIssue(rid, "duplicate id in this load; the first record is kept"))
        else:
            seen.add(rid)
            yield record, schema, synthetic


def _priority(record: Record) -> int:
    """The anchor priority of the record's dataset (contracts/datasets.yaml, 7.1.6)."""
    datasets = record.get("datasets") or []
    entry = load_registry().get(str(datasets[0])) if datasets else None
    priority = entry.anchor_priority if entry is not None else None
    return priority if priority is not None else sys.maxsize


def _common_schema(schemas: Iterable[Schema]) -> Schema | None:
    """The most specific FtM schema common to every member (cannot-link rule X2), or None."""
    try:
        return reduce(model.common_schema, schemas)
    except InvalidData:
        return None


def _resolution_of(members: Iterable[Member]) -> str:
    """`deterministic`, `probabilistic` or `human` when the member links share one method,
    else `mixed` (7.1.6)."""
    methods = {member.method for member in members if member.method != "anchor"}
    return methods.pop() if len(methods) == 1 else "mixed"


def _merged_row(canonical_id: str, group: list[Usable], members: Sequence[Member]) -> NodeRow:
    """L10: one node row from the members of a merged entity (7.1.6)."""
    anchor = canonical_id.removeprefix(CANONICAL_PREFIX)
    group = sorted(group, key=lambda g: (g[0]["id"] != anchor, _priority(g[0]), str(g[0]["id"])))
    schema = _common_schema(member_schema for _, member_schema, _ in group)
    mapping = NODE_MAPPINGS.get(schema.name) if schema is not None else None
    if schema is None or mapping is None:
        raise _Skip("the members of a merged entity have no common schema in C2 (X2)")
    if len({synthetic for _, _, synthetic in group}) != 1:
        raise _Skip("a merged entity mixes synthetic and real records (X1)")
    rows = [_node_row(r, s, NODE_MAPPINGS[s.name], synthetic) for r, s, synthetic in group]
    names = _unique(name for row in rows for name in row.props["names"])[:MAX_NAMES]
    topics = sorted({topic for row in rows for topic in row.props["topics"]})
    synthetic = group[0][2]
    props: dict[str, Any] = {
        "id": canonical_id,
        "schema": schema.name,
        "caption": rows[0].props["caption"],
        "names": names,
        "names_text": NAMES_SEPARATOR.join(names),
        "countries": sorted({c for row in rows for c in row.props["countries"]}),
        "topics": topics,
        "datasets": sorted({d for row in rows for d in row.props["datasets"]}),
        "referents": sorted(row.id for row in rows),
        "synthetic": synthetic,
    }
    first = [row.props["first_seen"] for row in rows if "first_seen" in row.props]
    last = [row.props["last_seen"] for row in rows if "last_seen" in row.props]
    if first:
        props["first_seen"] = min(first)
    if last:
        props["last_seen"] = max(last)
    for prop in ("source_url", *mapping.properties.values(), "address_key"):
        values = [row.props[prop] for row in rows if prop in row.props]
        if not values or (prop == "address_key" and "Address" not in mapping.labels):
            continue
        if PROPERTY_KINDS.get(prop) == "list":
            props[prop] = sorted({value for found in values for value in found})
        elif prop == "birth_date":  # the most precise value; X5 makes them compatible
            props[prop] = max(values, key=len)
        else:  # the anchor's value, else the first in member order
            props[prop] = values[0]
    props |= _resolution_props(names, mapping, len(rows), _resolution_of(members))
    return NodeRow(schema.name, canonical_id, props, _flags(topics, synthetic, mapping))


def to_node_rows(
    records: Sequence[Record], resolution: ResolutionMap | None = None
) -> MappingResult[NodeRow]:
    """One node row per entity (5.2 node table); edge schemata give none.

    A single-record entity streams through with its record id, `cluster_size` 1 and
    `resolution` "identity"; the members of a merged entity are buffered under its canonical id
    and merged (L10). A merged entity that cannot be built is skipped with a MappingIssue.
    """
    result: MappingResult[NodeRow] = MappingResult()
    merged: dict[str, list[Usable]] = {}
    for record, schema, synthetic in _first_records(records, result.skipped):
        mapping = NODE_MAPPINGS.get(schema.name)
        rid = str(record["id"])
        canonical_id = resolution.canonical(rid) if resolution is not None else rid
        if mapping is None:
            if schema.name not in RELATIONSHIP_MAPPINGS:
                message = f"schema {schema.name} has no C2 v1 mapping"
                result.skipped.append(MappingIssue(rid, message))
        elif canonical_id != rid:
            merged.setdefault(canonical_id, []).append((record, schema, synthetic))
        else:
            result.rows.append(_node_row(record, schema, mapping, synthetic))
    clusters = resolution.clusters() if resolution is not None else {}
    for canonical_id, group in merged.items():
        try:
            result.rows.append(_merged_row(canonical_id, group, clusters[canonical_id]))
        except _Skip as skip:
            result.skipped.append(MappingIssue(canonical_id, str(skip)))
    return result


class _Skip(Exception):
    """A record or reference that cannot become a relationship; the message says why."""


def _check_end(type_: str, end: int, rid: str, prop: str, index: Mapping[str, Schema]) -> None:
    """Raise when the record `rid` is in the load but is not a node with the required label."""
    schema = index.get(rid)
    if schema is None:
        return  # not in this load: the loader counts it as dangling if the graph lacks it
    mapping = NODE_MAPPINGS.get(schema.name)
    label = RELATIONSHIP_ENDPOINTS[type_][end]
    if mapping is None or label not in mapping.labels:
        raise _Skip(f"{type_} needs a :{label} node as {prop}; {rid} has schema {schema.name}")


def _common(record: Record, synthetic: bool) -> dict[str, Any]:
    props: dict[str, Any] = {"datasets": list(record["datasets"]), "synthetic": synthetic}
    return props | _mapped({"sourceUrl": "source_url"}, record)


def _choose(
    mappings: Sequence[RelationshipMapping],
    record: Record,
    target: str,
    index: Mapping[str, Schema],
) -> RelationshipMapping:
    target_schema = index.get(target)
    holds = {
        None: True,
        "asset_is_account": target_schema is not None and target_schema.is_a("BankAccount"),
        "consolidation": _nr(record).get("consolidation") is not None,
    }
    for mapping in mappings:
        if holds[mapping.condition]:
            return mapping
    raise _Skip("no relationship mapping applies")  # unreachable: the last has no condition


def _edge_row(
    record: Record,
    mappings: Sequence[RelationshipMapping],
    synthetic: bool,
    index: Mapping[str, Schema],
) -> RelationshipRow:
    first = mappings[0]
    sources, targets = _values(record, first.source_prop), _values(record, first.target_prop)
    if len(sources) != 1 or len(targets) != 1:
        raise _Skip(
            f"one relationship needs exactly one {first.source_prop} and one {first.target_prop}"
            f" (has {len(sources)} and {len(targets)})"
        )
    mapping = _choose(mappings, record, targets[0], index)
    _check_end(mapping.type, 0, sources[0], mapping.source_prop, index)
    _check_end(mapping.type, 1, targets[0], mapping.target_prop, index)
    # Defaults first, so a value the record has wins (OWNS and CONTROLS flags: false, C2 1.1.0).
    props = {"id": str(record["id"]), **_common(record, synthetic), **mapping.defaults}
    props |= _mapped(mapping.properties, record)
    return RelationshipRow(mapping.type, str(record["id"]), sources[0], targets[0], props)


def _reference_rows(
    record: Record,
    schema: Schema,
    ref: ReferenceMapping,
    synthetic: bool,
    index: Mapping[str, Schema],
    skipped: list[MappingIssue],
) -> Iterator[RelationshipRow]:
    rid = str(record["id"])
    values = _unique(_values(record, ref.prop))
    if values and not schema.is_a(ref.schema):
        message = (
            f"{ref.prop} on {schema.name} records is not mapped"
            f" ({ref.type} starts at a {ref.schema})"
        )
        skipped.append(MappingIssue(rid, message))
        return
    other_end = 1 if ref.record_end == "source" else 0
    for other in values:
        source, target = (rid, other) if ref.record_end == "source" else (other, rid)
        try:
            _check_end(ref.type, other_end, other, ref.prop, index)
        except _Skip as skip:
            skipped.append(MappingIssue(rid, str(skip)))
            continue
        rel_id = f"{source}|{ref.id_infix}|{target}"
        props = {"id": rel_id, **_common(record, synthetic), **ref.defaults}
        props |= _mapped(ref.properties, record, key=other)
        yield RelationshipRow(ref.type, rel_id, source, target, props)


def _landing_schemas(
    usable: Sequence[Usable], resolution: ResolutionMap | None
) -> dict[str, Schema]:
    """Each record id of the load with the schema of the node it lands on: its own, or for a
    member of a merged entity the merged schema, so the label checks see the merged node."""
    index = {str(record["id"]): schema for record, schema, _ in usable}
    if resolution is None:
        return index
    groups: dict[str, list[str]] = {}
    for rid in index:
        if (canonical_id := resolution.canonical(rid)) != rid:
            groups.setdefault(canonical_id, []).append(rid)
    for rids in groups.values():
        merged = _common_schema(index[rid] for rid in rids)
        if merged is not None:
            index.update(dict.fromkeys(rids, merged))
    return index


def _merge_duplicate(kept: RelationshipRow, other: RelationshipRow) -> RelationshipRow:
    """Two HAS_ADDRESS or SUBJECT_OF rows on the same two nodes: the smaller id, the first role
    of ROLE_ORDER among them, the union of datasets (L12)."""
    first, second = sorted((kept, other), key=lambda row: row.id)
    props = {
        **first.props,
        "datasets": sorted({*first.props["datasets"], *second.props["datasets"]}),
    }
    roles = [row.props["role"] for row in (first, second) if "role" in row.props]
    if roles:
        props["role"] = min(roles, key=lambda r: ROLE_ORDER.index(r) if r in ROLE_ORDER else 99)
    return replace(first, props=props)


def to_relationship_rows(
    records: Sequence[Record],
    resolution: ResolutionMap | None = None,
    loaded_ids: Collection[str] | None = None,
) -> MappingResult[RelationshipRow]:
    """Relationship rows from edge schemata, `addressEntity` and `Sanction.entity` (5.2).

    Reads the whole load first: the Ownership case and the endpoint checks need the schema of
    the referenced records. An endpoint outside the load is not checked here; the loader checks
    it in the database and counts it as dangling when the graph does not have it either.

    With `resolution`, both ends are re-pointed to canonical ids (L12): a row whose two ends
    land on one node is dropped (`self_loops_dropped`), and HAS_ADDRESS or SUBJECT_OF rows on
    the same two nodes become one (`duplicate_relationships_merged`). With `loaded_ids` (the
    node ids this load writes), a row with an end outside them is marked `resolving` (L13);
    SUBJECT_OF, which ends at a :Sanction, always takes the direct query.
    """
    result: MappingResult[RelationshipRow] = MappingResult()
    usable = list(_first_records(records, result.skipped))
    index = _landing_schemas(usable, resolution)
    loaded = frozenset(loaded_ids) if loaded_ids is not None else None
    built: list[RelationshipRow] = []
    for record, schema, synthetic in usable:
        mappings = RELATIONSHIP_MAPPINGS.get(schema.name)
        if mappings:
            try:
                built.append(_edge_row(record, mappings, synthetic, index))
            except _Skip as skip:
                result.skipped.append(MappingIssue(str(record["id"]), str(skip)))
        for ref in REFERENCE_MAPPINGS:
            built.extend(_reference_rows(record, schema, ref, synthetic, index, result.skipped))
    seen: dict[tuple[str, str, str], int] = {}
    for row in built:
        if resolution is not None:
            row = replace(
                row,
                source=resolution.canonical(row.source),
                target=resolution.canonical(row.target),
            )
        if row.source == row.target and resolution is not None:
            result.counts["self_loops_dropped"] += 1
            continue
        if loaded is not None and row.endpoint_keys[1] == "Entity":
            row = replace(row, resolving=row.source not in loaded or row.target not in loaded)
        key = (row.type, row.source, row.target)
        if row.type in DERIVED_TYPES and key in seen:
            position = seen[key]
            result.rows[position] = _merge_duplicate(result.rows[position], row)
            result.counts["duplicate_relationships_merged"] += 1
            continue
        if row.type in DERIVED_TYPES:
            seen[key] = len(result.rows)
        result.rows.append(row)
    return result


def _source_url(record: Record) -> str | None:
    found = _values(record, "sourceUrl")
    return found[0] if found else None


def to_source_record_rows(
    records: Sequence[Record],
    resolution: ResolutionMap,
    retrieved_at: Mapping[str, str] | None = None,
) -> MappingResult[SupportRow]:
    """L11: one `:SourceRecord` row per member of a merged entity (C2 1.1.0 properties).

    `retrieved_at` maps record ids to the `source.retrieved_at` of their file's manifest.
    """
    result: MappingResult[SupportRow] = MappingResult()
    for record, schema, synthetic in _first_records(records, result.skipped):
        rid = str(record["id"])
        canonical_id = resolution.canonical(rid)
        mapping = NODE_MAPPINGS.get(schema.name)
        if canonical_id == rid or mapping is None:
            continue
        props = {
            "id": rid,
            "dataset": str(record["datasets"][0]),
            "schema": schema.name,
            "caption": _caption(record),
            "names": _names(record, mapping),
            "topics": _values(record, "topics"),
            "canonical_id": canonical_id,
            "synthetic": synthetic,
            "retrieved_at": (retrieved_at or {}).get(rid),
            "source_url": _source_url(record),
            "run_id": resolution.run_id,
        }
        result.rows.append(SupportRow({"id": rid}, props))
    return result


def to_resolved_to_rows(
    resolution: ResolutionMap, record_ids: Collection[str] | None = None
) -> list[SupportRow]:
    """L11: one RESOLVED_TO row per member of a merged entity (of `record_ids` when given), with
    its `canonical.csv` row; `match_probability` is 1.0 for anchor, deterministic and human
    members, and `features` is kept for probabilistic members only."""
    rows = []
    for canonical_id, members in resolution.clusters().items():
        for member in members:
            if record_ids is not None and member.record_id not in record_ids:
                continue
            probabilistic = member.method == "probabilistic"
            props = {
                "method": member.method,
                "rule": member.rule,
                "match_probability": (
                    1.0 if member.method in CERTAIN_METHODS else member.match_probability
                ),
                "features": member.features if probabilistic else None,
                "run_id": resolution.run_id,
                "resolver_version": resolution.resolver_version,
                "decided_at": resolution.decided_at,
            }
            rows.append(
                SupportRow({"record_id": member.record_id, "canonical_id": canonical_id}, props)
            )
    return rows


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def to_possibly_same_as_rows(
    resolution: ResolutionMap, nodes: Mapping[str, NodeRow]
) -> MappingResult[SupportRow]:
    """L14: one POSSIBLY_SAME_AS row per line of `candidates.jsonl` whose two canonical ids are
    nodes of this load (`nodes` by id), from the smaller id to the larger. The probability is
    null for `deterministic` and `source_hint` possible matches; nothing else of either node is
    copied, apart from the union of their datasets."""
    result: MappingResult[SupportRow] = MappingResult()
    for line in resolution.candidates:
        a, b = str(line["a"]), str(line["b"])
        if a not in nodes or b not in nodes:
            result.counts["outside_this_load"] += 1
            continue
        synthetic = nodes[a].props["synthetic"]
        if nodes[b].props["synthetic"] != synthetic:
            result.skipped.append(MappingIssue(a, "a possible match across synthetic and real"))
            continue
        method = str(line["method"])
        rel_id = f"{a}|{POSSIBLY_SAME_AS_ID_INFIX}|{b}"
        props = {
            "id": rel_id,
            "match_probability": (
                None
                if method in ("deterministic", "source_hint")
                else _number(line.get("match_probability"))
            ),
            "match_weight": _number(line.get("match_weight")),
            "method": method,
            "rule": line.get("rule") or None,
            "reasons": [str(reason) for reason in line["reasons"]],
            "features": json.dumps(line["features"], sort_keys=True, separators=(",", ":")),
            "run_id": resolution.run_id,
            "resolver_version": resolution.resolver_version,
            "datasets": sorted({*nodes[a].props["datasets"], *nodes[b].props["datasets"]}),
            "synthetic": synthetic,
        }
        result.rows.append(SupportRow({"id": rel_id, "a": a, "b": b}, props))
    return result
