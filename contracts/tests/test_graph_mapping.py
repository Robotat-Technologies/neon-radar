"""Contract tests for C2, the graph schema (PHASE-1.md 5.2, 5.5): the mapping in
neonradar_contracts.graph against FollowTheMoney, C1 and the migration file."""

import re
from pathlib import Path

import pytest
from followthemoney import model, registry

from neonradar_contracts import graph, versions
from neonradar_contracts.records import (
    ALLOWED_SCHEMATA,
    NR_USED_ON,
    SYNTHETIC_TOPICS,
    NrExtension,
)

pytestmark = pytest.mark.contract

MIGRATION = Path(__file__).resolve().parents[2] / "graph/schema/migrations/0001_init.cypher"
CONSTRAINT_RE = re.compile(
    r"^CREATE CONSTRAINT (\w+) IF NOT EXISTS FOR (?:\(n:(\w+)\)|\(\)-\[r:(\w+)\]-\(\)) "
    r"REQUIRE [nr]\.(\w+) IS UNIQUE;$"
)
INDEX_RE = re.compile(
    r"^CREATE (FULLTEXT )?INDEX (\w+) IF NOT EXISTS FOR (?:\(n:([\w|]+)\)|\(\)-\[r:(\w+)\]-\(\)) "
    r"ON (?:EACH \[n\.(\w+)\]|\([nr]\.(\w+)\))"
)
PASCAL = re.compile(r"^[A-Z][A-Za-z]*$")
UPPER_SNAKE = re.compile(r"^[A-Z]+(_[A-Z]+)*$")
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
# The C2 label that stands for each FtM range used by the edge schemata.
RANGE_LABELS = {
    "LegalEntity": "LegalEntity",
    "Organization": "Organization",
    "Person": "Person",
    "BankAccount": "Account",
    "Position": "Position",
    "Address": "Address",
    "Thing": "Entity",
}
LEGAL_ENTITY_LABELS = ("LegalEntity", "Person", "Organization", "Company", "PublicBody")
RECORD_TYPES = set(graph.RELATIONSHIP_TYPES) - set(graph.SUPPORT_RELATIONSHIPS)


def migration() -> tuple[list[re.Match[str]], list[re.Match[str]]]:
    lines = [line for line in MIGRATION.read_text(encoding="utf-8").splitlines() if line]
    assert lines[0] == "// 0001_init: NeonRadar graph schema v1.0.0"
    constraints = [m for line in lines if (m := CONSTRAINT_RE.match(line))]
    indexes = [m for line in lines if (m := INDEX_RE.match(line))]
    assert len(constraints) + len(indexes) == len(lines) - 1, "every line is a known statement"
    return constraints, indexes


def node_properties(label: str) -> set[str]:
    """Every C2 property a node with this label can carry."""
    props = set(graph.SUPPORT_NODES.get(label, ())) | set(graph.RESERVED_PROPERTIES.get(label, ()))
    for mapping in graph.NODE_MAPPINGS.values():
        if label in mapping.labels:
            props |= set(graph.COMMON_NODE_PROPERTIES) | set(mapping.properties.values())
    return props


def relationship_properties(type_: str) -> set[str]:
    props = set(graph.SUPPORT_RELATIONSHIPS.get(type_, ()))
    for mappings in graph.RELATIONSHIP_MAPPINGS.values():
        for mapping in mappings:
            if mapping.type == type_:
                props |= set(graph.COMMON_RELATIONSHIP_PROPERTIES) | set(
                    mapping.properties.values()
                )
    return props


def check_sources(schema_name: str, properties: dict[str, str]) -> None:
    schema = model[schema_name]
    for source, target in properties.items():
        assert SNAKE.match(target), target
        if source.startswith("nr."):
            key = source.removeprefix("nr.")
            assert key in NrExtension.model_fields, source
            assert any(schema.is_a(s) for s in NR_USED_ON[key]), (schema_name, source)
        else:
            assert source in schema.properties, (schema_name, source)


def test_version() -> None:
    assert graph.SCHEMA_VERSION == versions.GRAPH_SCHEMA == "1.0.0"


def test_every_allowed_schema_maps_to_labels_or_relationships() -> None:
    mapped = set(graph.NODE_MAPPINGS) | set(graph.RELATIONSHIP_MAPPINGS)
    assert mapped == ALLOWED_SCHEMATA
    assert not set(graph.NODE_MAPPINGS) & set(graph.RELATIONSHIP_MAPPINGS)
    for name in graph.RELATIONSHIP_MAPPINGS:
        assert model[name].edge, f"{name} is an FtM edge schema"


def test_labels_mirror_the_ftm_hierarchy() -> None:
    for name, mapping in graph.NODE_MAPPINGS.items():
        schema = model[name]
        if name == "Sanction":
            assert mapping.labels == ("Sanction",)  # an Interval, not a Thing
            continue
        assert schema.is_a("Thing") and mapping.labels[0] == "Entity"
        if schema.is_a("LegalEntity"):
            expected = [label for label in LEGAL_ENTITY_LABELS if schema.is_a(label)]
            assert sorted(mapping.labels[1:]) == sorted(expected), name
        else:
            assert mapping.labels[1:] == (RANGE_LABELS[name],), name


def test_node_properties_exist_in_ftm_and_c1() -> None:
    for name, mapping in graph.NODE_MAPPINGS.items():
        check_sources(name, mapping.properties)
        for prop in mapping.extra_names:
            assert prop in model[name].properties, (name, prop)
    for prop in graph.NAME_PROPERTIES:  # read where the schema has them
        assert prop in model["LegalEntity"].properties, prop


def test_relationships_follow_the_ftm_edge_direction() -> None:
    for name, mappings in graph.RELATIONSHIP_MAPPINGS.items():
        schema = model[name]
        for mapping in mappings:
            check_sources(name, mapping.properties)
            ends = (mapping.source_prop, mapping.target_prop)
            for prop in ends:
                assert schema.properties[prop].type == registry.entity, (name, prop)
            if name == "Payment":  # C2 joins the accounts, not the payer and beneficiary
                assert ends == ("payerAccount", "beneficiaryAccount")
            else:
                assert ends == (schema.edge_source, schema.edge_target), name


def test_relationship_endpoints_match_the_ftm_ranges() -> None:
    for name, mappings in graph.RELATIONSHIP_MAPPINGS.items():
        schema = model[name]
        for mapping in mappings:
            endpoints = graph.RELATIONSHIP_ENDPOINTS[mapping.type]
            if name == "Ownership":  # the asset decides the type
                continue
            ranges = tuple(
                RANGE_LABELS[schema.properties[prop].range.name]  # type: ignore[union-attr]
                for prop in (mapping.source_prop, mapping.target_prop)
            )
            assert endpoints == ranges, mapping.type
    ownership = {m.type: m.condition for m in graph.RELATIONSHIP_MAPPINGS["Ownership"]}
    assert list(ownership.items()) == [
        ("HOLDS_ACCOUNT", "asset_is_account"),  # first: wins over CONSOLIDATES
        ("CONSOLIDATES", "consolidation"),
        ("OWNS", None),
    ]
    assert graph.RELATIONSHIP_ENDPOINTS["HOLDS_ACCOUNT"] == ("LegalEntity", "Account")
    assert graph.RELATIONSHIP_ENDPOINTS["CONSOLIDATES"] == ("Organization", "Organization")
    assert graph.RELATIONSHIP_ENDPOINTS["OWNS"] == ("LegalEntity", "LegalEntity")


def test_reference_mappings() -> None:
    refs = {ref.type: ref for ref in graph.REFERENCE_MAPPINGS}
    assert set(refs) == {"HAS_ADDRESS", "SUBJECT_OF"}
    for ref in refs.values():
        prop = model[ref.schema].properties[ref.prop]
        assert prop.type == registry.entity
        assert prop.range is not None
        check_sources(ref.schema, ref.properties)
        record_label = graph.NODE_MAPPINGS[ref.schema].labels[-1]
        other_label = RANGE_LABELS[prop.range.name]
        expected = (
            (record_label, other_label)
            if ref.record_end == "source"
            else (other_label, record_label)
        )
        assert graph.RELATIONSHIP_ENDPOINTS[ref.type] == expected
    assert (refs["HAS_ADDRESS"].id_infix, refs["SUBJECT_OF"].id_infix) == ("addr", "sanction")
    assert refs["HAS_ADDRESS"].defaults == {"role": "unknown"}


def test_names_follow_the_conventions() -> None:
    for label in (*graph.NODE_LABELS, *graph.FLAG_LABELS):
        assert PASCAL.match(label), label
    for type_ in graph.RELATIONSHIP_TYPES:
        assert UPPER_SNAKE.match(type_), type_
    every_property = [
        *graph.COMMON_NODE_PROPERTIES,
        *graph.COMMON_RELATIONSHIP_PROPERTIES,
        *graph.PROPERTY_KINDS,
        *(p for props in graph.SUPPORT_NODES.values() for p in props),
        *(p for props in graph.SUPPORT_RELATIONSHIPS.values() for p in props),
    ]
    for prop in every_property:
        assert SNAKE.match(prop), prop


def test_types_and_flags() -> None:
    built = {m.type for ms in graph.RELATIONSHIP_MAPPINGS.values() for m in ms}
    built |= {ref.type for ref in graph.REFERENCE_MAPPINGS}
    assert built == RECORD_TYPES
    assert len(graph.RELATIONSHIP_TYPES) == 19
    assert graph.FLAG_LABELS == ("Synthetic", "Sanctioned", "PEP", "RCA")
    # Synthetic records may carry exactly the topics that set the flags (C1 R9).
    assert {flag.topic for flag in graph.TOPIC_FLAGS} == SYNTHETIC_TOPICS
    subtopics = {flag.label: flag.subtopics for flag in graph.TOPIC_FLAGS}
    assert subtopics == {"Sanctioned": False, "PEP": True, "RCA": True}


def test_migration_constraints_match_the_mapping() -> None:
    constraints, indexes = migration()
    assert (len(constraints), len(indexes)) == (22, 7)  # GC-02
    nodes = {(m[2], m[4]) for m in constraints if m[2]}
    keys = {mapping.labels[0] for mapping in graph.NODE_MAPPINGS.values()}
    expected = {(label, "id") for label in keys}
    expected |= {(label, props[0]) for label, props in graph.SUPPORT_NODES.items()}
    assert nodes == expected
    relationships = {(m[3], m[4]) for m in constraints if m[3]}
    assert relationships == {(type_, "id") for type_ in RECORD_TYPES}
    for m in constraints:  # entity_id, detection_run_id, owns_id, ...
        owner = re.sub(r"(?<!^)(?=[A-Z])", "_", m[2]).lower() if m[2] else m[3].lower()
        assert m[1] == f"{owner}_id"


def test_migration_indexes_name_mapped_properties() -> None:
    _, indexes = migration()
    seen = set()
    for m in indexes:
        fulltext, name, labels, type_, each, prop = m.groups()
        prop = each or prop
        if type_:
            assert prop in relationship_properties(type_), (name, type_, prop)
            seen.add((type_, prop))
        for label in (labels or "").split("|") if labels else ():
            assert prop in node_properties(label), (name, label, prop)
            seen.add((label, prop))
        assert bool(fulltext) == (name == "entity_names")
    assert ("PAID", "ts") in seen and ("Address", "address_key") in seen
    assert graph.PROPERTY_KINDS["ts"] == "datetime"
