"""Map C1 records to the parameter rows the C2 graph loader sends (PHASE-1.md 5.2, M1.7b;
C2 1.1.0 company properties and share-band flags, PHASE-2.md 5.2, M2.1b).

Pure functions without database access. Labels and relationship types come only from
`neonradar_contracts.graph`: the loader writes them into its query text per schema or type and
sends these rows as parameters. Records must be C1-valid (the loader validates them first and
never maps a record that failed); what C1 accepts but C2 cannot represent is skipped and
reported as a `MappingIssue`, and a strict load fails on any of them.

Both functions take the whole load as a sequence (a list), never a one-shot iterator: each
reads it in full, and `to_relationship_rows` reads it twice. Record-level issues (not a C1
record, duplicate id) appear in both results; `MappingIssue` is hashable, so the loader merges
the two `skipped` lists with `dict.fromkeys`. See contracts/C2-graph-schema.md.
"""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from followthemoney import Schema, ValueEntity, model, registry

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.graph import (
    FLAG_LABELS,
    NAME_PROPERTIES,
    NAMES_SEPARATOR,
    NODE_MAPPINGS,
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

Record = Mapping[str, Any]
# The labels a node is MERGEd and MATCHed on with `{id: ...}`: each has a uniqueness constraint.
KEY_LABELS = frozenset(mapping.labels[0] for mapping in NODE_MAPPINGS.values())


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
    """One relationship between the nodes with ids `source` and `target`.

    `ts` is set for PAID only: `<Payment date>Z`, which the loader turns into a DATETIME.
    """

    type: str
    id: str
    source: str
    target: str
    props: dict[str, Any]
    ts: str | None = None

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
        row: dict[str, Any] = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "props": self.props,
        }
        if self.ts is not None:
            row["ts"] = self.ts
        return row


@dataclass(slots=True)
class MappingResult[T]:
    """The rows to load and the records or references that were skipped."""

    rows: list[T] = field(default_factory=list)
    skipped: list[MappingIssue] = field(default_factory=list)


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
        case "datetime":
            return f"{values[0]}Z"
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


def _node_row(record: Record, schema: Schema, mapping: NodeMapping, synthetic: bool) -> NodeRow:
    rid = str(record["id"])
    names = _unique(
        value
        for prop in (*NAME_PROPERTIES, *mapping.extra_names)
        for value in _values(record, prop)
    )
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
        "referents": [rid],  # Phase 1: one record per node
        "synthetic": synthetic,
    }
    for key in ("first_seen", "last_seen"):
        if isinstance(record.get(key), str):
            props[key] = record[key]
    props |= _mapped({"sourceUrl": "source_url", **mapping.properties}, record)
    for name in mapping.empty_lists:  # C2 1.2.0: `Sanction.provisions` is [] when absent
        props.setdefault(name, [])
    return NodeRow(schema.name, rid, props, _flags(topics, synthetic, mapping))


def _first_records(
    records: Iterable[Record], skipped: list[MappingIssue]
) -> Iterator[tuple[Record, Schema, bool]]:
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


def to_node_rows(records: Sequence[Record]) -> MappingResult[NodeRow]:
    """One node row per record of a node schema (5.2 node table); edge schemata give none."""
    result: MappingResult[NodeRow] = MappingResult()
    for record, schema, synthetic in _first_records(records, result.skipped):
        mapping = NODE_MAPPINGS.get(schema.name)
        if mapping is not None:
            result.rows.append(_node_row(record, schema, mapping, synthetic))
        elif schema.name not in RELATIONSHIP_MAPPINGS:
            message = f"schema {schema.name} has no C2 v1 mapping"
            result.skipped.append(MappingIssue(str(record["id"]), message))
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
    ts = props.pop("ts", None)
    return RelationshipRow(mapping.type, str(record["id"]), sources[0], targets[0], props, ts)


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


def to_relationship_rows(records: Sequence[Record]) -> MappingResult[RelationshipRow]:
    """Relationship rows from edge schemata, `addressEntity` and `Sanction.entity` (5.2).

    Reads the whole load first: the Ownership case and the endpoint checks need the schema of
    the referenced records. An endpoint outside the load is not checked here; the loader counts
    it as dangling when the graph does not have it either.
    """
    result: MappingResult[RelationshipRow] = MappingResult()
    usable = list(_first_records(records, result.skipped))
    index = {str(record["id"]): schema for record, schema, _ in usable}
    for record, schema, synthetic in usable:
        mappings = RELATIONSHIP_MAPPINGS.get(schema.name)
        if mappings:
            try:
                result.rows.append(_edge_row(record, mappings, synthetic, index))
            except _Skip as skip:
                result.skipped.append(MappingIssue(str(record["id"]), str(skip)))
        for ref in REFERENCE_MAPPINGS:
            result.rows.extend(
                _reference_rows(record, schema, ref, synthetic, index, result.skipped)
            )
    return result
