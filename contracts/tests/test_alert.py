"""Contract tests for C4, the alert (PHASE-1.md 5.4, 5.5)."""

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from neonradar_contracts import schemas, versions
from neonradar_contracts.alert import (
    EDGE_ID_PATTERN,
    ENTITY_ID_PATTERN,
    HEADLINE_MAX,
    Alert,
    compute_alert_id,
    default_priority,
    query_sha256,
)
from neonradar_contracts.records import ID_RE

pytestmark = pytest.mark.contract

CONTRACTS = Path(__file__).resolve().parents[1]
EXAMPLE = CONTRACTS / "examples" / "c4" / "circular_flow.json"
SCHEMA = CONTRACTS / "schemas" / "alert.v1.json"
EXAMPLE_ID = "alr-f82a84574538090f0624"
C4_DOC = CONTRACTS / "C4-alert.md"
NODES = ["syn-acct-0007", "syn-acct-0012", "syn-acct-0015", "syn-acct-0021"]
EDGES = ["syn-payment-000101", "syn-payment-000102", "syn-payment-000103", "syn-payment-000104"]
# A stand-in for a Companies House record, as M1.9b builds it in test code (never a fixture).
# `T0000001` is not a Companies House number format. Name checked on the Companies House
# company and officer searches on 21 October 2026: nothing found.
REAL_HOLDER = {
    "entity_id": "gbch-co-T0000001",
    "role": "origin_holder",
    "caption": "Quarrytide Holdings Ltd",
}
STRUCTURAL = "Funds returned to the originating account through 4 transfers within 7 days"
# A stand-in for a Companies House ownership relationship (an FtM interval id), as above.
REAL_EDGE = "gbch-own-T0000001"
FULLWIDTH_M = unicodedata.lookup("FULLWIDTH LATIN SMALL LETTER M")
FULLWIDTH_SYNTHETIC = unicodedata.lookup("FULLWIDTH LATIN SMALL LETTER S") + "ynthetic scenario"


def example() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    return data


def with_id(data: dict[str, Any]) -> dict[str, Any]:
    """Recompute alert_id after a change to the typology, detector version or evidence ids."""
    evidence = data["evidence"]
    data["alert_id"] = compute_alert_id(
        data["typology"], data["detector"]["version"], evidence["node_ids"], evidence["edge_ids"]
    )
    return data


def with_edge(data: dict[str, Any], edge: str) -> dict[str, Any]:
    """Add an evidence edge (and the ends of a composite id as evidence nodes); recompute the id."""
    nodes = data["evidence"]["node_ids"]
    nodes += [end for end in edge.split("|")[::2] if "|" in edge and end not in nodes]
    data["evidence"]["edge_ids"].append(edge)
    return with_id(data)


def as_structural(data: dict[str, Any], datasets: list[str]) -> dict[str, Any]:
    data["wording_class"] = "structural_pattern"
    data["headline"] = STRUCTURAL
    data["data_flags"] = {
        **data["data_flags"],
        "involves_real_entities": True,
        "datasets": datasets,
    }
    return data


def rejects(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Alert.model_validate(data)


# --- schema, example and version ------------------------------------------------------------


def test_committed_schema_equals_the_model() -> None:
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == Alert.model_json_schema()


def test_generated_files_have_no_drift() -> None:
    assert schemas.check() == []


def test_schema_patterns_are_portable() -> None:
    """JSON Schema patterns follow ECMA-262: no Python-only anchors or named groups, and no
    `\\d`, `\\w` or `\\s`, which Python reads as Unicode classes and ECMAScript as ASCII ones."""
    documents = schemas.documents()
    documents["openapi/v1.json"] = (CONTRACTS / "openapi" / "v1.json").read_text(encoding="utf-8")
    for relative, text in documents.items():
        for pattern in re.findall(r'"pattern": "([^"]*)"', text):
            assert not re.search(r"\\\\[zZAdDwWsS]|\(\?P<", pattern), (relative, pattern)


# The jsonschema package checks `pattern` with Python's re.search, where `$` also matches before
# a final newline; fixed-length fields carry their length so that the schema rejects it anyway.
FIXED_LENGTH: list[tuple[str, tuple[str | int, ...], str]] = [
    ("alert.v1.json", ("properties", "alert_id"), EXAMPLE_ID),
    ("alert.v1.json", ("properties", "run_id"), "run-20261021T101500-7f3a"),
    ("alert.v1.json", ("properties", "created_at"), "2026-10-21T10:15:02Z"),
    ("alert.v1.json", ("$defs", "Window", "properties", "start"), "2026-03-02T09:00:00Z"),
    ("alert.v1.json", ("$defs", "Window", "properties", "end"), "2026-03-08T16:40:00Z"),
    ("alert.v1.json", ("$defs", "Detector", "properties", "query_sha256"), "a" * 64),
    ("record-manifest.v1.json", ("properties", "created_at"), "2026-10-23T09:00:00Z"),
    (
        "record-manifest.v1.json",
        ("$defs", "Source", "properties", "retrieved_at", "anyOf", 0),
        "2026-10-23T09:00:00Z",
    ),
    ("record-manifest.v1.json", ("$defs", "ManifestFile", "properties", "sha256"), "0" * 64),
]


@pytest.mark.parametrize(("document", "path", "value"), FIXED_LENGTH)
def test_fixed_length_fields_reject_a_trailing_newline_in_the_json_schema(
    document: str, path: tuple[str | int, ...], value: str
) -> None:
    node: Any = json.loads((CONTRACTS / "schemas" / document).read_text(encoding="utf-8"))
    for key in path:
        node = node[key]

    def python_jsonschema_accepts(text: str) -> bool:
        length = node["minLength"] <= len(text) <= node["maxLength"]
        return length and re.search(node["pattern"], text) is not None

    assert node["minLength"] == node["maxLength"] == len(value)
    assert python_jsonschema_accepts(value)
    assert re.search(node["pattern"], value + "\n"), "the pattern alone lets the newline through"
    assert not python_jsonschema_accepts(value + "\n")


ARABIC_INDIC_DIGITS = str.maketrans("0123456789", "".join(chr(0x0660 + d) for d in range(10)))


def arabic_indic(text: str) -> str:
    return text.translate(ARABIC_INDIC_DIGITS)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("run_id",), "run-" + arabic_indic("20261021T101500") + "-7f3a"),
        (("typology_version",), arabic_indic("0.1.0")),
        (("detector", "version"), arabic_indic("0.1.0")),
        (("created_at",), arabic_indic("2026-10-21T10:15:02Z")),
        (("evidence", "window", "start"), arabic_indic("2026-03-02T09:00:00Z")),
        (("alert_id",), "alr-" + arabic_indic("00000000000000000000")),
    ],
)
def test_non_ascii_digits_are_rejected(path: tuple[str, ...], value: str) -> None:
    """Python's `\\d` matches any Unicode digit; ECMAScript's (the UI, OpenAPI) only 0 to 9."""
    data = example()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError, match=path[-1]):
        Alert.model_validate(data)


def test_example_validates_and_round_trips() -> None:
    alert = Alert.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    assert alert.model_dump(mode="json") == example()
    assert alert.contract_version == versions.ALERT
    assert alert.wording_class == "synthetic_scenario"
    assert all(subject.entity_id.startswith("syn-") for subject in alert.subjects)


def test_example_hashes_are_computed() -> None:
    data = example()
    cypher = data["evidence"]["query"]["cypher"].encode("utf-8")
    assert data["detector"]["query_sha256"] == hashlib.sha256(cypher).hexdigest()
    assert data["detector"]["query_sha256"] == query_sha256(data["evidence"]["query"]["cypher"])
    assert data["alert_id"] == compute_alert_id("circular_flow", "0.1.0", NODES, EDGES)


def test_c4_document_shows_the_golden_example() -> None:
    text = C4_DOC.read_text(encoding="utf-8")
    block = text.split("## Example", 1)[1].split("```json\n", 1)[1].split("```", 1)[0]
    assert json.loads(block) == example()


def test_query_sha256_must_hash_the_evidence_query() -> None:
    data = example()
    data["evidence"]["query"]["cypher"] += " LIMIT 1"
    rejects(data, "query_sha256 must be the SHA-256 of evidence.query.cypher")
    data["detector"]["query_sha256"] = query_sha256(data["evidence"]["query"]["cypher"])
    Alert.model_validate(data)


@pytest.mark.parametrize(
    ("version", "message"),
    [
        ("1.0.1", "newer than this model"),
        ("1.1.0", "newer than this model"),
        ("2.0.0", "contract_version"),
        ("0.9.0", "contract_version"),
        ("1.01.0", "contract_version"),
    ],
)
def test_contract_version_is_1x_and_not_newer_than_the_model(version: str, message: str) -> None:
    rejects({**example(), "contract_version": version}, message)


def test_contract_version_pattern_accepts_later_1x_values() -> None:
    """A later 1.x model accepts every earlier 1.x value (the rule of the record's `nr.v`)."""
    pattern = Alert.model_json_schema()["properties"]["contract_version"]["pattern"]
    assert all(re.fullmatch(pattern, v) for v in ["1.0.0", "1.2.3", "1.10.0"])
    assert versions.ALERT == "1.0.0"


def test_unknown_keys_are_rejected() -> None:
    rejects({**example(), "risk": 1}, "Extra inputs are not permitted")
    data = example()
    data["detector"]["extra"] = "x"
    rejects(data, "Extra inputs are not permitted")


def test_disclaimer_id_is_standing_v1() -> None:
    rejects({**example(), "disclaimer_id": "real-data-v1"}, "disclaimer_id")


# --- alert_id -------------------------------------------------------------------------------


def test_alert_id_is_deterministic() -> None:
    assert compute_alert_id("circular_flow", "0.1.0", NODES, EDGES) == EXAMPLE_ID
    assert compute_alert_id("circular_flow", "0.1.0", NODES[::-1], EDGES[::-1]) == EXAMPLE_ID
    assert re.fullmatch(r"alr-[0-9a-f]{20}", EXAMPLE_ID)
    text = json.dumps(["circular_flow", "0.1.0", EDGES, NODES], separators=(",", ":"))
    assert text.startswith('["circular_flow","0.1.0",["syn-payment-000101",')
    digest = hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()
    assert f"alr-{digest[:20]}" == EXAMPLE_ID


def test_alert_id_marks_the_boundary_between_edges_and_nodes() -> None:
    """With a `|`-joined text these two would share an id; the JSON array keeps them apart."""
    first = compute_alert_id("circular_flow", "0.1.0", ["syn-n-2"], ["syn-e-1", "syn-n-1"])
    second = compute_alert_id("circular_flow", "0.1.0", ["syn-n-1", "syn-n-2"], ["syn-e-1"])
    assert first != second


@pytest.mark.parametrize(
    "args",
    [
        ("layering_chain", "0.1.0", NODES, EDGES),
        ("circular_flow", "0.2.0", NODES, EDGES),
        ("circular_flow", "0.1.0", NODES[:3], EDGES),
        ("circular_flow", "0.1.0", NODES, EDGES[:3]),
    ],
)
def test_alert_id_changes_with_its_inputs(args: tuple[str, str, list[str], list[str]]) -> None:
    assert compute_alert_id(*args) != EXAMPLE_ID


def test_alert_id_must_match_the_evidence() -> None:
    rejects({**example(), "alert_id": "alr-00000000000000000000"}, f"alert_id must be {EXAMPLE_ID}")
    data = example()
    data["evidence"]["edge_ids"] = EDGES[:3]
    data["explanation"]["steps"] = data["explanation"]["steps"][:3]
    rejects(data, "alert_id must be")
    Alert.model_validate(with_id(data))


# --- wording class and data flags (G1) ------------------------------------------------------


def test_non_synthetic_subject_must_be_structural_pattern() -> None:
    data = example()
    data["subjects"][1] = REAL_HOLDER
    rejects(data, "involves_real_entities must be true")
    alert = Alert.model_validate(as_structural(data, ["gb_companies_house", "nr_synthetic"]))
    assert alert.wording_class == "structural_pattern"
    assert alert.data_flags.involves_real_entities
    assert alert.data_flags.synthetic_activity


def test_non_synthetic_account_holder_must_be_structural_pattern() -> None:
    """A holder of an evidence account that is not a subject shows up in data_flags.datasets."""
    data = example()
    data["data_flags"]["datasets"] = ["gb_companies_house", "nr_synthetic"]
    rejects(data, r"non-synthetic data \(gb_companies_house\)")
    Alert.model_validate(as_structural(data, ["gb_companies_house", "nr_synthetic"]))


def test_non_synthetic_evidence_node_must_be_structural_pattern() -> None:
    data = example()
    data["evidence"]["node_ids"][1] = "gleif-TEST.LEI.0001"
    rejects(with_id(data), "involves_real_entities must be true")


@pytest.mark.parametrize(
    ("wording_class", "involves_real_entities"),
    [("synthetic_scenario", True), ("structural_pattern", False)],
)
def test_wording_class_follows_involves_real_entities(
    wording_class: str, involves_real_entities: bool
) -> None:
    data = example()
    data["wording_class"] = wording_class
    data["headline"] = STRUCTURAL
    data["data_flags"]["involves_real_entities"] = involves_real_entities
    rejects(data, "synthetic_scenario exactly when")


def test_structural_alert_never_says_synthetic_scenario() -> None:
    """B1: the example re-labelled structural keeps its synthetic headline and is refused."""
    data = example()
    data["subjects"][1] = REAL_HOLDER
    data["wording_class"] = "structural_pattern"
    data["data_flags"]["involves_real_entities"] = True
    data["data_flags"]["datasets"] = ["gb_companies_house", "nr_synthetic"]
    rejects(data, "only a synthetic_scenario alert may say 'synthetic scenario'.*headline")
    data["headline"] = STRUCTURAL
    Alert.model_validate(data)
    data["explanation"]["summary"] = "A Synthetic-Scenario cycle of four transfers."
    rejects(data, "explanation.summary")
    data = as_structural(example(), ["nr_synthetic", "gb_companies_house"])
    data["explanation"]["steps"][2]["text"] = "Synthetic_scenario step."
    rejects(data, "step 3")


@pytest.mark.parametrize("where", ["headline", "explanation.summary", "step 2"])
def test_structural_alert_never_says_synthetic_scenario_in_fullwidth(where: str) -> None:
    """The phrase check reads NFKC-normalised text, so a fullwidth "s" does not hide it."""
    data = as_structural(example(), ["nr_synthetic", "gb_companies_house"])
    text = f"A {FULLWIDTH_SYNTHETIC} of four transfers."
    if where == "headline":
        data["headline"] = text
    elif where == "explanation.summary":
        data["explanation"]["summary"] = text
    else:
        data["explanation"]["steps"][1]["text"] = text
    rejects(data, f"only a synthetic_scenario alert may say 'synthetic scenario'.*{where}")


def test_synthetic_scenario_alert_may_say_so() -> None:
    data = example()
    data["explanation"]["summary"] = "Synthetic scenario: " + data["explanation"]["summary"]
    assert Alert.model_validate(data).wording_class == "synthetic_scenario"


def test_all_synthetic_alert_has_synthetic_activity() -> None:
    data = example()
    data["data_flags"]["synthetic_activity"] = False
    rejects(data, "synthetic_activity must be true")


def test_canonical_ids_prove_nothing_either_way() -> None:
    """`nr-` ids (Phase 2 canonical entities) belong to no dataset; datasets decide."""
    data = example()
    data["subjects"][1] = {**REAL_HOLDER, "entity_id": "nr-6f1c2a"}
    Alert.model_validate(data)


def test_non_synthetic_evidence_edge_means_no_synthetic_activity() -> None:
    data = with_edge(example(), REAL_EDGE)
    rejects(
        data,
        r"synthetic_activity must be false: evidence relationships come from non-synthetic "
        r"data \(gbch-own-T0000001\)",
    )
    data = as_structural(data, ["gb_companies_house", "nr_synthetic"])
    rejects(data, "evidence relationships come from non-synthetic data")
    data["data_flags"]["synthetic_activity"] = False
    alert = Alert.model_validate(data)
    assert alert.wording_class == "structural_pattern"
    assert not alert.data_flags.synthetic_activity


@pytest.mark.parametrize(
    ("edge", "real_record"),
    [
        ("syn-co-0003|addr|gbch-addr-T0000001", False),  # built from the synthetic company
        ("gbch-co-T0000001|addr|gbch-addr-T0000001", True),  # built from the real company
        ("syn-co-0003|sanction|os-sanction-T0000001", True),  # built from the Sanction
    ],
)
def test_a_composite_edge_counts_as_the_record_it_was_built_from(
    edge: str, real_record: bool
) -> None:
    """C2: a relationship carries the dataset and synthetic flag of the record that built it."""
    datasets = ["gb_companies_house", "nr_synthetic", "opensanctions_default"]
    data = with_edge(as_structural(example(), datasets), edge)
    if real_record:
        rejects(data, f"non-synthetic data \\({re.escape(edge)}\\)")
        data["data_flags"]["synthetic_activity"] = False
    assert Alert.model_validate(data).data_flags.synthetic_activity is not real_record


def test_all_synthetic_relationships_mean_synthetic_activity() -> None:
    """Case F: a real holder next to synthetic payments; the activity is synthetic."""
    data = as_structural(example(), ["gb_companies_house", "nr_synthetic"])
    data["subjects"][1] = REAL_HOLDER
    data["data_flags"]["synthetic_activity"] = False
    rejects(data, "synthetic_activity must be true: every evidence relationship is synthetic")


def test_no_relationships_next_to_real_entities_means_no_synthetic_activity() -> None:
    data = as_structural(example(), ["gb_companies_house", "nr_synthetic"])
    data["subjects"][1] = REAL_HOLDER
    data["evidence"]["edge_ids"] = []
    for step in data["explanation"]["steps"]:
        step["edge_ids"] = []
    rejects(with_id(data), "synthetic_activity must be false for an alert with real entities")
    data["data_flags"]["synthetic_activity"] = False
    Alert.model_validate(data)


def test_datasets_list_every_dataset_the_ids_name() -> None:
    data = as_structural(example(), ["nr_synthetic"])
    data["subjects"][1] = REAL_HOLDER
    rejects(data, "data_flags.datasets must list gb_companies_house")
    data = with_edge(as_structural(example(), ["nr_synthetic"]), REAL_EDGE)
    data["data_flags"]["synthetic_activity"] = False
    rejects(data, "data_flags.datasets must list gb_companies_house")
    data["data_flags"]["datasets"].append("gb_companies_house")
    Alert.model_validate(data)


@pytest.mark.parametrize("edge", ["syn-acct-0007|addr|syn-addr-0001", "nr-7d2e9b"])
def test_synthetic_or_canonical_edges_keep_synthetic_activity(edge: str) -> None:
    alert = Alert.model_validate(with_edge(example(), edge))
    assert alert.wording_class == "synthetic_scenario"
    assert alert.data_flags.synthetic_activity


@pytest.mark.parametrize("datasets", [[], ["nr_synthetic", "nr_synthetic"], ["no_such_dataset"]])
def test_datasets_are_registered_and_distinct(datasets: list[str]) -> None:
    data = example()
    data["data_flags"]["datasets"] = datasets
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


# --- field rules ----------------------------------------------------------------------------


def test_headline_length() -> None:
    long = "Funds returned to the originating account" + " again" * 20
    rejects({**example(), "headline": long[: HEADLINE_MAX + 1]}, "at most 140 characters")
    Alert.model_validate({**example(), "headline": long[:HEADLINE_MAX]})
    rejects({**example(), "headline": ""}, "at least 1 character")


@pytest.mark.parametrize(
    "headline",
    [
        "Suspicious funds returned",
        "Laundered funds came back",
        "Mule accounts in a cycle",
        f"{FULLWIDTH_M}ule accounts in a cycle",
    ],
)
def test_headline_passes_the_wording_lint(headline: str) -> None:
    rejects({**example(), "headline": headline}, "wording lint")


@pytest.mark.parametrize("strength", [-0.01, 1.01, float("nan"), "0.79", True])
def test_pattern_strength_is_a_number_in_zero_to_one(strength: object) -> None:
    with pytest.raises(ValidationError):
        Alert.model_validate({**example(), "pattern_strength": strength})


@pytest.mark.parametrize("strength", [0, 0.0, 1, 1.0])
def test_pattern_strength_bounds_are_inclusive(strength: float) -> None:
    Alert.model_validate({**example(), "pattern_strength": strength})


@pytest.mark.parametrize(
    ("strength", "priority"),
    [
        (1.0, "high"),
        (0.75, "high"),
        (0.7499, "medium"),
        (0.5, "medium"),
        (0.4999, "low"),
        (0, "low"),
    ],
)
def test_default_priority(strength: float, priority: str) -> None:
    assert default_priority(strength) == priority


def test_priority_values() -> None:
    rejects({**example(), "priority": "urgent"}, "priority")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("created_at", "2026-10-21T10:15:02+00:00"),
        ("created_at", "2026-10-21T10:15:02Z\n"),
        ("created_at", "2026-13-21T10:15:02Z"),
        ("run_id", "run-20261021-7f3a"),
        ("run_id", "run-20261021T101500-7f3a\n"),
        ("alert_id", EXAMPLE_ID + "\n"),
        ("typology", "Circular-Flow"),
        ("typology_version", "0.1"),
    ],
)
def test_scalar_formats(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Alert.model_validate({**example(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "circular_flow"),
        ("version", "v0.1.0"),
        ("query_sha256", "<hex>"),
    ],
)
def test_detector_fields(field: str, value: str) -> None:
    data = example()
    data["detector"][field] = value
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


def test_composite_edges_need_their_endpoints_in_the_evidence() -> None:
    data = example()
    data["evidence"]["edge_ids"].append("syn-acct-0007|addr|syn-addr-0001")
    rejects(with_id(data), r"needs its endpoints in node_ids: \['syn-addr-0001'\]")
    data["evidence"]["node_ids"].append("syn-addr-0001")
    Alert.model_validate(with_id(data))


@pytest.mark.parametrize("role", ["mule_account", "front_company_holder", "suspect"])
def test_subject_roles_pass_the_wording_lint(role: str) -> None:
    data = example()
    data["subjects"][0]["role"] = role
    rejects(data, f"role {role}")


def test_typology_slug_passes_the_wording_lint() -> None:
    data = example()
    data["typology"] = data["explanation"]["typology_reference"]["slug"] = "laundering_cycle"
    rejects(with_id(data), "typology: ")


def test_false_positive_notes_pass_the_wording_lint() -> None:
    data = example()
    data["explanation"]["false_positive_notes"].append("Not every cycle is fraud.")
    rejects(data, r"false_positive_notes\[1\]")


@pytest.mark.parametrize("key", ["fatf", "FATF_pml_2018", "fatf-pml-2018"])
def test_citations_are_bibliography_keys(key: str) -> None:
    data = example()
    data["explanation"]["typology_reference"]["citations"] = [key]
    rejects(data, "citations")


def test_subjects_are_required() -> None:
    rejects({**example(), "subjects": []}, "at least 1 item")
    data = example()
    data["subjects"][0]["role"] = "Origin Account"
    rejects(data, "role")


def test_subjects_do_not_repeat_an_entity() -> None:
    """C2 FLAGS carries one role per alert and entity."""
    data = example()
    data["subjects"][1] = {**data["subjects"][0], "role": "origin_holder"}
    rejects(data, "subjects must not repeat an entity_id")


def test_metrics_are_numbers_or_strings() -> None:
    data = example()
    data["metrics"]["closed"] = True
    rejects(data, "metrics")
    data["metrics"]["closed"] = [1, 2]
    rejects(data, "metrics")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_metrics_and_query_parameters_are_finite(value: float) -> None:
    """JSON has no NaN or infinity; they used to pass and dump as null."""
    data = example()
    data["metrics"]["return_ratio"] = value
    rejects(data, "finite number")
    data = example()
    data["evidence"]["query"]["parameters"]["max_window_days"] = [14, {"days": value}]
    rejects(data, "finite number")


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("field", ['"return_ratio": 0.96', '"max_window_days": 14'])
def test_json_text_with_nan_or_infinity_is_rejected(literal: str, field: str) -> None:
    """Pydantic's JSON parser reads these literals, so the model must refuse them."""
    text = EXAMPLE.read_text(encoding="utf-8")
    assert field in text
    changed = text.replace(field, field.split(": ")[0] + ": " + literal)
    with pytest.raises(ValidationError, match="finite number"):
        Alert.model_validate_json(changed)


# --- evidence and explanation ---------------------------------------------------------------


def test_entity_id_pattern_agrees_with_record_rule_r1() -> None:
    """C4 node ids are C1 ids (R1 as changed by OD-11), written without named groups."""
    unnamed = re.sub(r"\(\?P<\w+>|\)(?=-|\\Z)", "", ID_RE.pattern).replace(r"\Z", "$")
    assert unnamed == ENTITY_ID_PATTERN
    samples = ["syn-co-0001", "gbch-off-TEST.officer-0001", "syn-co_1", "x-1", "syn-co-"]
    for sample in samples:
        assert bool(re.fullmatch(ENTITY_ID_PATTERN, sample)) is bool(ID_RE.fullmatch(sample))


@pytest.mark.parametrize(
    ("node_id", "valid"),
    [("syn-acct-0007", True), ("gbch-off-TEST.officer-0001", True), ("4:a1b2:12", False)],
)
def test_node_ids_are_c2_ids(node_id: str, valid: bool) -> None:
    assert bool(re.fullmatch(ENTITY_ID_PATTERN, node_id)) is valid


@pytest.mark.parametrize(
    ("edge_id", "valid"),
    [
        ("syn-payment-000101", True),
        ("syn-co-0001|addr|syn-addr-0001", True),
        ("syn-co-0001|sanction|syn-sanction-0001", True),
        ("syn-co-0001|owns|syn-co-0002", False),
        ("5:a1b2:99", False),
    ],
)
def test_edge_ids_are_c2_ids(edge_id: str, valid: bool) -> None:
    assert bool(re.fullmatch(EDGE_ID_PATTERN, edge_id)) is valid


def test_evidence_ids_are_distinct_and_present() -> None:
    data = example()
    data["evidence"]["node_ids"] = NODES + NODES[:1]
    rejects(with_id(data), "must not repeat an id")
    data = example()
    data["evidence"]["node_ids"] = []
    rejects(with_id(data), "at least 1 item")
    data = example()
    data["evidence"]["node_ids"][0] = "4:a1b2:12"
    rejects(with_id(data), "node_ids")


def test_window_is_ordered_and_nullable() -> None:
    data = example()
    data["evidence"]["window"] = {"start": "2026-03-08T16:40:00Z", "end": "2026-03-02T09:00:00Z"}
    rejects(data, "must not be after")
    data["evidence"]["window"] = None
    assert Alert.model_validate(data).evidence.window is None
    del data["evidence"]["window"]
    rejects(data, r"evidence\.window\n  Field required")


def test_window_is_required_in_the_json_schema() -> None:
    """Every field is present, nullable ones as null (the rule C3's OpenAPI relies on)."""
    evidence = Alert.model_json_schema()["$defs"]["Evidence"]
    assert "window" in evidence["required"]
    assert {"type": "null"} in evidence["properties"]["window"]["anyOf"]


def test_steps_are_numbered_in_order() -> None:
    data = example()
    data["explanation"]["steps"][1]["order"] = 3
    rejects(data, "numbered 1, 2, 3")


def test_steps_cite_evidence_edges() -> None:
    data = example()
    data["explanation"]["steps"][0]["edge_ids"] = ["syn-payment-999999"]
    rejects(data, "not in the evidence")


def test_step_text_length() -> None:
    data = copy.deepcopy(example())
    data["explanation"]["steps"][0]["text"] = "x" * 281
    rejects(data, "at most 280 characters")


def test_typology_reference_matches_the_typology() -> None:
    data = example()
    data["explanation"]["typology_reference"]["slug"] = "layering_chain"
    rejects(data, "typology_reference.slug must equal typology")
    data = example()
    data["explanation"]["typology_reference"]["citations"] = []
    rejects(data, "citations")


# --- generated files ------------------------------------------------------------------------


def test_check_reports_missing_changed_and_stray_files(tmp_path: Path) -> None:
    docs = schemas.documents()
    assert sorted(docs) == [
        "schemas/alert.v1.json",
        "schemas/record-manifest.v1.json",
        "schemas/record-nr.v1.json",
    ]
    schemas.export(tmp_path, docs)
    (tmp_path / "schemas" / ".DS_Store").write_text("", encoding="utf-8")
    assert schemas.check(tmp_path, docs) == []
    (tmp_path / "schemas" / "alert.v1.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "schemas" / "record-nr.v1.json").unlink()
    (tmp_path / "schemas" / "alert.v0.json").write_text("{}\n", encoding="utf-8")
    assert schemas.check(tmp_path, docs) == [
        "schemas/alert.v1.json: differs from the models; run `make contracts`",
        "schemas/record-nr.v1.json: missing; run `make contracts`",
        "schemas/alert.v0.json: not generated by `neonradar contracts export`",
    ]


def test_render_json_is_stable() -> None:
    assert schemas.render_json({"b": 1, "a": "é"}) == '{\n  "a": "é",\n  "b": 1\n}\n'
