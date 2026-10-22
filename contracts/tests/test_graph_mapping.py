"""Contract tests for C2, the graph schema (PHASE-1.md 5.2, 5.5; PHASE-2.md 5.2, 5.4): the
mapping in neonradar_contracts.graph against FollowTheMoney, C1 and the migration files."""

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

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "graph/schema/migrations"
C2_DOC = REPO / "contracts/C2-graph-schema.md"
HEADERS = {
    "0001_init": "// 0001_init: NeonRadar graph schema v1.0.0",
    "0002_resolution": "// 0002_resolution: NeonRadar graph schema v1.1.0 (entity resolution)",
}
CONSTRAINT_RE = re.compile(
    r"^CREATE CONSTRAINT (\w+) IF NOT EXISTS FOR (?:\(n:(\w+)\)|\(\)-\[r:(\w+)\]-\(\)) "
    r"REQUIRE [nr]\.(\w+) IS UNIQUE;$"
)
INDEX_RE = re.compile(
    r"^CREATE (FULLTEXT )?INDEX (\w+) IF NOT EXISTS FOR (?:\(n:([\w|]+)\)|\(\)-\[r:(\w+)\]-\(\)) "
    r"ON (?:EACH \[((?:n\.\w+)(?:, n\.\w+)*)\]|\([nr]\.(\w+)\))"
)
DROP_RE = re.compile(r"^DROP INDEX (\w+) IF EXISTS;$")
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


def migration(
    name: str,
) -> tuple[list[re.Match[str]], list[re.Match[str]], list[re.Match[str]]]:
    """The constraints, indexes and dropped indexes of one migration file."""
    path = MIGRATIONS / f"{name}.cypher"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert lines[0] == HEADERS[name]
    constraints = [m for line in lines if (m := CONSTRAINT_RE.match(line))]
    indexes = [m for line in lines if (m := INDEX_RE.match(line))]
    drops = [m for line in lines if (m := DROP_RE.match(line))]
    known = len(constraints) + len(indexes) + len(drops)
    assert known == len(lines) - 1, "every line is a known statement"
    return constraints, indexes, drops


def schema_after_all_migrations() -> tuple[list[re.Match[str]], dict[str, re.Match[str]]]:
    """Constraints and indexes after applying every migration in order (a drop removes)."""
    assert sorted(p.stem for p in MIGRATIONS.glob("*.cypher")) == list(HEADERS)
    constraints: list[re.Match[str]] = []
    indexes: dict[str, re.Match[str]] = {}
    for name in HEADERS:
        added, created, drops = migration(name)
        constraints += added
        for drop in drops:
            indexes.pop(drop[1])
        for index in created:
            indexes[index[2]] = index
    return constraints, indexes


def node_properties(label: str) -> set[str]:
    """Every C2 property a node with this label can carry."""
    props = set(graph.SUPPORT_NODES.get(label, ())) | set(graph.RESERVED_PROPERTIES.get(label, ()))
    for mapping in graph.NODE_MAPPINGS.values():
        if label in mapping.labels:
            props |= set(graph.COMMON_NODE_PROPERTIES) | set(mapping.properties.values())
            if mapping.labels[0] == "Entity":
                props |= set(graph.ENTITY_RESOLUTION_PROPERTIES)
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
    assert graph.SCHEMA_VERSION == versions.GRAPH_SCHEMA == "1.2.0"
    # 1.2.0 changes C2 only (PHASE-3.md 5); the others keep Phase 2's versions.
    assert versions.CONTRACTS == "1.2.0"
    assert (versions.RECORD, versions.API, versions.ALERT) == ("1.1.0", "1.1.0", "1.0.0")
    changelog = (REPO / "contracts/CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.2.0" in changelog and "### C2: Graph schema 1.2.0" in changelog
    assert C2_DOC.read_text(encoding="utf-8").startswith("# C2: Graph schema v1.2.0\n")


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
        *graph.ENTITY_RESOLUTION_PROPERTIES,
        *(p for props in graph.SUPPORT_NODES.values() for p in props),
        *(p for props in graph.SUPPORT_RELATIONSHIPS.values() for p in props),
    ]
    for prop in every_property:
        assert SNAKE.match(prop), prop


def test_types_and_flags() -> None:
    built = {m.type for ms in graph.RELATIONSHIP_MAPPINGS.values() for m in ms}
    built |= {ref.type for ref in graph.REFERENCE_MAPPINGS}
    assert built == RECORD_TYPES
    assert len(graph.RELATIONSHIP_TYPES) == 20  # 1.1.0 adds POSSIBLY_SAME_AS
    assert len(RECORD_TYPES) == 16
    assert graph.FLAG_LABELS == ("Synthetic", "Sanctioned", "PEP", "RCA")
    # Synthetic records may carry exactly the topics that set the flags (C1 R9).
    assert {flag.topic for flag in graph.TOPIC_FLAGS} == SYNTHETIC_TOPICS
    subtopics = {flag.label: flag.subtopics for flag in graph.TOPIC_FLAGS}
    assert subtopics == {"Sanctioned": False, "PEP": True, "RCA": True}


def test_migration_constraints_match_the_mapping() -> None:
    constraints, indexes, drops = migration("0001_init")
    assert (len(constraints), len(indexes), len(drops)) == (22, 7, 0)  # GC-02
    constraints, after = schema_after_all_migrations()
    assert (len(constraints), len(after)) == (23, 9)  # PHASE-2.md 5.2: after 0001 and 0002
    nodes = {(m[2], m[4]) for m in constraints if m[2]}
    keys = {mapping.labels[0] for mapping in graph.NODE_MAPPINGS.values()}
    expected = {(label, "id") for label in keys}
    expected |= {(label, props[0]) for label, props in graph.SUPPORT_NODES.items()}
    assert nodes == expected
    relationships = {(m[3], m[4]) for m in constraints if m[3]}
    with_id = {t for t, props in graph.SUPPORT_RELATIONSHIPS.items() if "id" in props}
    assert with_id == {"POSSIBLY_SAME_AS"}
    assert relationships == {(type_, "id") for type_ in RECORD_TYPES | with_id}
    for m in constraints:  # entity_id, detection_run_id, owns_id, ...
        owner = re.sub(r"(?<!^)(?=[A-Z])", "_", m[2]).lower() if m[2] else m[3].lower()
        assert m[1] == f"{owner}_id"


def test_migration_indexes_name_mapped_properties() -> None:
    _, indexes = schema_after_all_migrations()
    seen = set()
    for m in indexes.values():
        fulltext, name, labels, type_, each, prop = m.groups()
        props = [p.removeprefix("n.") for p in each.split(", ")] if each else [prop]
        for prop in props:
            if type_:
                assert prop in relationship_properties(type_), (name, type_, prop)
                seen.add((type_, prop))
            for label in (labels or "").split("|") if labels else ():
                assert prop in node_properties(label), (name, label, prop)
                seen.add((label, prop))
        assert bool(fulltext) == (name == "entity_names")
    assert ("PAID", "ts") in seen and ("Address", "address_key") in seen
    assert graph.PROPERTY_KINDS["ts"] == "datetime"
    # 1.1.0: the full-text index keeps its name and covers both name texts.
    assert indexes["entity_names"][5] == "n.names_text, n.names_latin_text"
    assert {("SourceRecord", "canonical_id"), ("SourceRecord", "dataset")} <= seen


def test_migration_0002_is_additive_and_idempotent() -> None:
    constraints, indexes, drops = migration("0002_resolution")
    assert [m[1] for m in constraints] == ["possibly_same_as_id"]
    assert [m[2] for m in indexes] == [
        "source_record_canonical_id", "source_record_dataset", "entity_names",
    ]  # fmt: skip
    assert [m[1] for m in drops] == ["entity_names"]  # rebuilt under the same name
    text = (MIGRATIONS / "0002_resolution.cypher").read_text(encoding="utf-8")
    statements = [line for line in text.splitlines() if line and not line.startswith("//")]
    assert all(" IF NOT EXISTS " in s or s.endswith(" IF EXISTS;") for s in statements)


def test_company_properties_from_c1_1_1() -> None:
    company = graph.NODE_MAPPINGS["Company"].properties
    assert company["nr.psc_statements"] == "psc_statements"
    assert company["nr.accounts_category"] == "accounts_category"
    assert graph.PROPERTY_KINDS["psc_statements"] == "list"
    assert "accounts_category" not in graph.PROPERTY_KINDS  # a STRING
    for schema in ("Organization", "PublicBody"):  # C1 allows the keys on Company only
        assert "nr.psc_statements" not in graph.NODE_MAPPINGS[schema].properties


def mapping_of(type_: str) -> graph.RelationshipMapping:
    (found,) = [m for ms in graph.RELATIONSHIP_MAPPINGS.values() for m in ms if m.type == type_]
    return found


def test_owns_carries_bound_flags_and_nominee_false_when_absent() -> None:
    owns = mapping_of("OWNS")
    assert {k: v for k, v in owns.properties.items() if k.startswith("nr.")} == {
        "nr.share_pct_min": "share_pct_min",
        "nr.share_pct_max": "share_pct_max",
        "nr.share_pct_min_exclusive": "share_min_exclusive",
        "nr.share_pct_max_exclusive": "share_max_exclusive",
        "nr.natures_of_control": "natures_of_control",
        "nr.is_nominee": "is_nominee",
    }
    assert owns.defaults == {
        "share_min_exclusive": False, "share_max_exclusive": False, "is_nominee": False,
    }  # fmt: skip
    for name in ("share_min_exclusive", "share_max_exclusive", "is_nominee"):
        assert graph.PROPERTY_KINDS[name] == "boolean"
    for type_ in ("HOLDS_ACCOUNT", "CONSOLIDATES", "DIRECTOR_OF"):  # no new defaults there
        assert mapping_of(type_).defaults == {}


def test_controls_carries_the_voting_rights_band() -> None:
    controls = mapping_of("CONTROLS")
    band = {k: v for k, v in controls.properties.items() if k.startswith("nr.share_pct")}
    assert band == {
        "nr.share_pct_min": "share_pct_min",
        "nr.share_pct_max": "share_pct_max",
        "nr.share_pct_min_exclusive": "share_min_exclusive",
        "nr.share_pct_max_exclusive": "share_max_exclusive",
    }
    # The bounds are null when absent (no default); the flags are false.
    assert controls.defaults == {"share_min_exclusive": False, "share_max_exclusive": False}
    assert graph.PROPERTY_KINDS["share_pct_min"] == graph.PROPERTY_KINDS["share_pct_max"]
    assert graph.PROPERTY_KINDS["share_pct_min"] == "float"


def test_every_default_names_a_mapped_property() -> None:
    for mappings in graph.RELATIONSHIP_MAPPINGS.values():
        for mapping in mappings:
            assert set(mapping.defaults) <= set(mapping.properties.values()), mapping.type
    for name, node in graph.NODE_MAPPINGS.items():  # 1.2.0: empty lists, not absent values
        assert set(node.empty_lists) <= set(node.properties.values()), name
        assert all(graph.PROPERTY_KINDS[p] == "list" for p in node.empty_lists), name


def test_sanction_provisions_from_c2_1_2() -> None:
    sanction = graph.NODE_MAPPINGS["Sanction"]
    assert sanction.properties["provisions"] == "provisions"
    assert "provisions" in model["Sanction"].properties
    assert graph.PROPERTY_KINDS["provisions"] == "list"
    assert sanction.empty_lists == ("provisions",)
    assert all(m.empty_lists == () for n, m in graph.NODE_MAPPINGS.items() if n != "Sanction")


def test_detection_run_and_alert_properties_from_c2_1_2() -> None:
    run = graph.SUPPORT_NODES["DetectionRun"]
    new_run = ("profile", "params_sha256", "summary", "window_start", "window_end")
    assert run[-5:] == new_run and run[0] == "run_id"
    alert = graph.SUPPORT_NODES["Alert"]
    assert alert[-2:] == ("evidence_node_ids", "evidence_edge_ids") and alert[0] == "alert_id"
    kinds = graph.PROPERTY_KINDS
    assert kinds["evidence_node_ids"] == kinds["evidence_edge_ids"] == "list"
    assert not set(new_run) & set(kinds)  # STRING
    # Absent for a run without a profile, a failed run, a graph with no window to read, and a
    # run written under 1.1.0; `summary` is always set by a 1.2.0 detection load.
    nullable = graph.NULLABLE_PROPERTIES["DetectionRun"]
    assert nullable == ("profile", "params_sha256", "window_start", "window_end")
    assert "summary" not in nullable and set(nullable) <= set(new_run)
    # The C2 document's tables name every new property (PHASE-3.md 5.4).
    text = C2_DOC.read_text(encoding="utf-8")
    for prop in (*new_run, "evidence_node_ids", "evidence_edge_ids", "provisions"):
        assert f"`{prop}`" in text, prop
    for rule in ("L18", "L19", "I15", "I16", "I17"):
        assert f"**{rule}." in text or f"| {rule} |" in text, rule


def test_overlay_constants_from_c2_1_2() -> None:
    assert graph.OVERLAY_ID_PREFIX == "syn-ov-"
    assert graph.OVERLAY_DATASET == "nr_synthetic"
    holder, type_, account = graph.BRIDGE_RELATIONSHIP
    assert (holder, type_, account) == ("Organization", "HOLDS_ACCOUNT", "Account")
    assert graph.RELATIONSHIP_ENDPOINTS[type_] == ("LegalEntity", account)
    assert holder in graph.NODE_LABELS


def test_resolution_nodes_and_relationships_as_data() -> None:
    assert graph.SUPPORT_NODES["SourceRecord"] == (
        "id", "dataset", "schema", "caption", "names", "topics", "canonical_id", "synthetic",
        "retrieved_at", "source_url", "run_id",
    )  # fmt: skip
    assert graph.SUPPORT_RELATIONSHIPS["RESOLVED_TO"] == (
        "match_probability", "method", "resolver_version", "decided_at", "rule", "run_id",
        "features",
    )  # fmt: skip
    assert graph.SUPPORT_RELATIONSHIPS["POSSIBLY_SAME_AS"] == (
        "id", "match_probability", "match_weight", "method", "rule", "reasons", "features",
        "run_id", "resolver_version", "datasets", "synthetic",
    )  # fmt: skip
    assert graph.RELATIONSHIP_ENDPOINTS["RESOLVED_TO"] == ("SourceRecord", "Entity")
    assert graph.RELATIONSHIP_ENDPOINTS["POSSIBLY_SAME_AS"] == ("LegalEntity", "LegalEntity")
    assert graph.POSSIBLY_SAME_AS_ID_INFIX == "psa"
    nullable = graph.NULLABLE_PROPERTIES
    assert set(nullable) == {"SourceRecord", "RESOLVED_TO", "POSSIBLY_SAME_AS", "DetectionRun"}
    assert {"match_probability", "rule"} <= set(nullable["POSSIBLY_SAME_AS"])
    assert nullable["SourceRecord"] == ("retrieved_at", "source_url")
    for owner, props in nullable.items():
        declared = graph.SUPPORT_RELATIONSHIPS.get(owner) or graph.SUPPORT_NODES[owner]
        assert set(props) <= set(declared), owner
        assert declared[0] not in props, owner  # a key or first property is always set
    assert graph.RESOLVED_TO_METHODS == ("anchor", "deterministic", "probabilistic", "human")
    assert graph.POSSIBLY_SAME_AS_METHODS == ("probabilistic", "deterministic", "source_hint")
    assert graph.ENTITY_RESOLUTIONS == (
        "identity", "deterministic", "probabilistic", "human", "mixed",
    )  # fmt: skip
    assert set(graph.CERTAIN_METHODS) == set(graph.RESOLVED_TO_METHODS) - {"probabilistic"}
    assert graph.ENTITY_RESOLUTION_PROPERTIES == (
        "cluster_size", "resolution", "names_latin", "names_latin_text",
    )  # fmt: skip
    kinds = graph.PROPERTY_KINDS
    assert (kinds["cluster_size"], kinds["names_latin"], kinds["reasons"]) == (
        "integer", "list", "list",
    )  # fmt: skip
    assert kinds["match_weight"] == kinds["match_probability"] == "float"
    # Resolution properties are computed, never mapped from a record property.
    mapped = {v for m in graph.NODE_MAPPINGS.values() for v in m.properties.values()}
    assert not mapped & set(graph.ENTITY_RESOLUTION_PROPERTIES)
