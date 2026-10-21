"""Contract tests for the C3 API models (PHASE-1.md 5.3, contracts/C3-api.md)."""

import copy
import json
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from neonradar_contracts import api, graph
from neonradar_contracts.alert import Alert

pytestmark = pytest.mark.contract

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
C3 = EXAMPLES / "c3"


def _load(name: str) -> Any:
    return json.loads((C3 / name).read_text(encoding="utf-8"))


def _alert() -> Alert:
    return Alert.model_validate_json((EXAMPLES / "c4" / "circular_flow.json").read_bytes())


def test_the_examples_validate() -> None:
    api.Subgraph.model_validate(_load("subgraph.json"))
    api.EntityDetail.model_validate(_load("entity-detail.json"))
    problem = api.Problem.model_validate(_load("problem-501.json"))
    assert problem.type == "about:blank"


def test_the_examples_round_trip_by_their_json_names() -> None:
    data = _load("subgraph.json")
    assert api.Subgraph.model_validate(data).model_dump(mode="json") == data


def test_alert_detail_carries_the_c4_alert_and_its_evidence() -> None:
    detail = api.AlertDetail(
        alert=_alert(), evidence=api.Subgraph.model_validate(_load("subgraph.json"))
    )
    assert detail.alert.typology == "circular_flow"


def test_alert_detail_needs_every_evidence_node_edge_and_subject() -> None:
    data = _load("subgraph.json")
    for drop in ("syn-co-0003", "syn-acct-0012"):  # a subject that is no evidence node; a node
        cut = copy.deepcopy(data)
        cut["nodes"] = [node for node in cut["nodes"] if node["id"] != drop]
        cut["edges"] = [e for e in cut["edges"] if drop not in (e["source"], e["target"])]
        with pytest.raises(ValidationError, match="lacks alert evidence or subjects"):
            api.AlertDetail(alert=_alert(), evidence=api.Subgraph.model_validate(cut))


def test_subgraph_edges_need_both_endpoints_and_unique_ids() -> None:
    data = _load("subgraph.json")
    loose = copy.deepcopy(data)
    loose["nodes"] = loose["nodes"][1:]
    with pytest.raises(ValidationError, match="outside the subgraph"):
        api.Subgraph.model_validate(loose)
    twice = copy.deepcopy(data)
    twice["edges"].append(twice["edges"][0])
    with pytest.raises(ValidationError, match="edge ids must not repeat"):
        api.Subgraph.model_validate(twice)
    small = copy.deepcopy(data)
    small["limits"] = {"max_nodes": 2, "max_edges": 4}
    with pytest.raises(ValidationError, match="larger than its limits"):
        api.Subgraph.model_validate(small)


def test_edges_use_c2_ids_never_element_ids() -> None:
    edge = _load("subgraph.json")["edges"][0]
    with pytest.raises(ValidationError):
        api.GraphEdge.model_validate({**edge, "id": "5:0b1c2d3e-0000-0000-0000-000000000000:17"})
    composite = {**edge, "id": "syn-co-0003|addr|syn-addr-0003", "type": "HAS_ADDRESS"}
    assert api.GraphEdge.model_validate(composite).id == composite["id"]


def test_graph_node_field_is_schema_in_json() -> None:
    node = _load("subgraph.json")["nodes"][0]
    parsed = api.GraphNode.model_validate(node)
    assert parsed.schema_ == "BankAccount"
    assert parsed.model_dump(mode="json")["schema"] == "BankAccount"
    assert "schema" in api.GraphNode.model_json_schema()["properties"]
    with pytest.raises(ValidationError):  # the Python name is not accepted as input
        api.GraphNode.model_validate(
            {**{k: v for k, v in node.items() if k != "schema"}, "schema_": "BankAccount"}
        )


def test_literals_follow_the_c2_mapping() -> None:
    record_types = set(graph.RELATIONSHIP_TYPES) - set(graph.SUPPORT_RELATIONSHIPS)
    assert set(get_args(api.RelationshipType)) == record_types
    mapped_labels = {label for m in graph.NODE_MAPPINGS.values() for label in m.labels}
    assert set(get_args(api.NodeLabel)) == mapped_labels
    assert set(get_args(api.NodeSchema)) == set(graph.NODE_MAPPINGS)
    assert set(get_args(api.SearchLabel)) <= mapped_labels
    assert not set(get_args(api.NodeLabel)) & set(graph.FLAG_LABELS)


def test_citation_year_may_be_null_for_living_sources() -> None:
    living = {
        "key": "fatf_glossary",
        "title": "FATF Glossary",
        "publisher": "FATF",
        "url": "https://example.org/",
    }
    assert api.Citation.model_validate({**living, "year": None}).year is None
    assert api.Citation.model_validate({**living, "year": 2018}).year == 2018
    with pytest.raises(ValidationError):
        api.Citation.model_validate(living)  # present, even when null


def test_timestamps_are_utc_with_z_and_seconds() -> None:
    record = {"dataset": "nr_synthetic", "record_id": "syn-co-0003", "source_url": None}
    assert api.ProvenanceRecord.model_validate({**record, "retrieved_at": "2026-10-21T10:15:02Z"})
    for bad in ("2026-10-21T10:15:02+00:00", "2026-10-21T10:15:02.5Z", "2026-10-21"):
        with pytest.raises(ValidationError):
            api.ProvenanceRecord.model_validate({**record, "retrieved_at": bad})


def test_identifier_lists_are_non_empty_and_distinct() -> None:
    data = _load("entity-detail.json")
    for values in ([], ["SYN00003", "SYN00003"]):
        with pytest.raises(ValidationError):
            api.EntityDetail.model_validate(
                {**data, "identifiers": {"registration_number": values}}
            )


HEALTH_OK = {
    "status": "ok",
    "neo4j": {"connected": True, "version": "5.26.32", "edition": "community"},
    "apoc_version": "5.26.32",
    "gds_version": "2.13.4",
}


def test_health_is_ok_exactly_when_neo4j_apoc_and_gds_answer() -> None:
    api.HealthResponse.model_validate(HEALTH_OK)
    with pytest.raises(ValidationError, match="exactly when"):
        api.HealthResponse.model_validate({**HEALTH_OK, "gds_version": None})
    with pytest.raises(ValidationError, match="exactly when"):
        api.HealthResponse.model_validate({**HEALTH_OK, "status": "degraded"})


ANSWERED = {
    "status": "answered",
    "answer_text": "syn-p-0002 owns syn-co-0001 (25 to 50 percent).",
    "template_id": "who_owns",
    "cypher": "MATCH (o:LegalEntity)-[:OWNS]->(c:Entity {id: $id}) RETURN o LIMIT 25",
    "parameters": {"id": "syn-co-0001"},
    "subgraph": {
        "nodes": [],
        "edges": [],
        "truncated": False,
        "limits": {"max_nodes": 1, "max_edges": 2},
    },
    "refusal_reason": None,
}
REFUSED = {**ANSWERED, "status": "refused", "answer_text": None, "refusal_reason": "Out of scope."}


def test_copilot_answers_carry_evidence_and_refusals_a_reason() -> None:
    api.CopilotAnswer.model_validate(ANSWERED)
    api.CopilotAnswer.model_validate(REFUSED)
    api.CopilotAnswer.model_validate({**REFUSED, "status": "unsupported"})
    for broken in (
        {**ANSWERED, "subgraph": None},
        {**ANSWERED, "cypher": None},
        {**ANSWERED, "refusal_reason": "no"},
        {**REFUSED, "refusal_reason": None},
        {**REFUSED, "answer_text": "text"},
    ):
        with pytest.raises(ValidationError):
            api.CopilotAnswer.model_validate(broken)


def test_copilot_request_limits() -> None:
    assert api.CopilotRequest(question="who owns syn-co-0001?").context_entity_ids == []
    for bad in (
        {"question": ""},
        {"question": "x" * 501},
        {"question": "q", "context_entity_ids": ["syn-co-0001"] * 21},
        {"question": "q", "context_entity_ids": ["not an id"]},
        {"question": "q", "extra": 1},
    ):
        with pytest.raises(ValidationError):
            api.CopilotRequest.model_validate(bad)


def _models() -> list[type[BaseModel]]:
    return [
        value
        for value in vars(api).values()
        if isinstance(value, type)
        and issubclass(value, BaseModel)
        and value.__module__ == api.__name__
        and not value.__name__.startswith("_")
    ]


def test_response_fields_have_no_defaults() -> None:
    """Nullable fields are present as null, so generated TypeScript says `T | null`."""
    with_defaults = {
        f"{model.__name__}.{name}"
        for model in _models()
        for name, field in model.model_fields.items()
        if not field.is_required()
    }
    assert with_defaults == {"CopilotRequest.context_entity_ids"}


def test_every_model_is_closed_and_strict() -> None:
    for model in _models():
        assert model.model_config.get("extra") == "forbid", model
        assert model.model_config.get("strict") is True, model
    with pytest.raises(ValidationError):
        api.NodeFlags.model_validate(
            {"synthetic": 1, "sanctioned": False, "pep": False, "rca": False}
        )


# Review fixes (PR #24): what property maps may hold, labels, limits and paths ----------------


def _node() -> dict[str, Any]:
    node: dict[str, Any] = _load("subgraph.json")["nodes"][-1]  # the holder company
    return node


@pytest.mark.parametrize("key", sorted(api.NODE_PROPERTIES_LEFT_OUT))
def test_node_properties_leave_out_top_level_fields_topics_and_referents(key: str) -> None:
    node = _node()
    with pytest.raises(ValidationError, match="must not hold"):
        api.GraphNode.model_validate({**node, "properties": {**node["properties"], key: "x"}})


@pytest.mark.parametrize("key", sorted(api.DETAIL_PROPERTIES_LEFT_OUT))
def test_entity_properties_leave_out_what_has_its_own_field(key: str) -> None:
    data = _load("entity-detail.json")
    with pytest.raises(ValidationError, match="must not hold"):
        api.EntityDetail.model_validate({**data, "properties": {**data["properties"], key: "x"}})


@pytest.mark.parametrize("key", sorted(api.EDGE_PROPERTIES_LEFT_OUT))
def test_edge_properties_leave_out_id_and_topics(key: str) -> None:
    edge = _load("subgraph.json")["edges"][0]
    with pytest.raises(ValidationError, match="must not hold"):
        api.GraphEdge.model_validate({**edge, "properties": {**edge["properties"], key: "x"}})


def test_labels_follow_the_c2_mapping_of_the_schema() -> None:
    node = _node()
    with pytest.raises(ValidationError, match="C2 mapping"):
        api.GraphNode.model_validate({**node, "labels": ["Entity", "Company"]})
    summary = _load("entity-detail.json")["entity"]
    with pytest.raises(ValidationError, match="C2 mapping"):
        api.EntitySummary.model_validate({**summary, "schema": "Person"})
    sanction = {**node, "id": "syn-sanction-0001", "labels": ["Sanction"], "schema": "Sanction"}
    assert api.GraphNode.model_validate(sanction).labels == ["Sanction"]


def test_max_edges_is_twice_max_nodes() -> None:
    with pytest.raises(ValidationError, match="2 x"):
        api.SubgraphLimits.model_validate({"max_nodes": 200, "max_edges": 300})


def test_alert_evidence_is_never_truncated_and_needs_every_evidence_edge() -> None:
    data = _load("subgraph.json")
    truncated = api.Subgraph.model_validate({**data, "truncated": True})
    with pytest.raises(ValidationError, match="never truncated"):
        api.AlertDetail(alert=_alert(), evidence=truncated)
    edgeless = {**data, "edges": [e for e in data["edges"] if e["id"] != "syn-payment-000102"]}
    with pytest.raises(ValidationError, match="syn-payment-000102"):  # every node still present
        api.AlertDetail(alert=_alert(), evidence=api.Subgraph.model_validate(edgeless))


def _cycle_path(**changes: Any) -> dict[str, Any]:
    path = {
        "node_ids": ["syn-acct-0007", "syn-acct-0012", "syn-acct-0015"],
        "edge_ids": ["syn-payment-000101", "syn-payment-000102"],
        "effective_share_min": None,
        "effective_share_max": None,
    }
    return {**path, **changes}


def test_a_path_has_one_edge_fewer_than_nodes() -> None:
    api.PathRef.model_validate(_cycle_path())
    with pytest.raises(ValidationError, match="one edge fewer"):
        api.PathRef.model_validate(_cycle_path(edge_ids=["syn-payment-000101"]))


def test_paths_start_and_end_where_asked_and_stay_in_the_subgraph() -> None:
    subgraph = _load("subgraph.json")
    paths = {"from_id": "syn-acct-0007", "to_id": "syn-acct-0015", "subgraph": subgraph}
    api.PathsResponse.model_validate({**paths, "paths": [_cycle_path()]})
    wrong_edge = ["syn-payment-000101", "syn-payment-000104"]
    unknown_edge = ["syn-payment-000101", "syn-payment-009999"]
    for broken, match in (
        ({"to_id": "syn-acct-0021"}, "runs from"),
        ({"paths": [_cycle_path(edge_ids=wrong_edge)]}, "does not join"),
        ({"paths": [_cycle_path(edge_ids=unknown_edge)]}, "missing"),
    ):
        with pytest.raises(ValidationError, match=match):
            api.PathsResponse.model_validate({**paths, "paths": [_cycle_path()], **broken})
    owners = {"root_id": "syn-acct-0012", "direction": "up", "subgraph": subgraph}
    with pytest.raises(ValidationError, match="runs from syn-acct-0012"):
        api.OwnershipResponse.model_validate({**owners, "paths": [_cycle_path()]})


def test_app_version_is_a_pep_440_version_and_contract_versions_are_semver() -> None:
    meta = {
        "contracts_version": "1.0.0",
        "schema_version": "1.0.0",
        "datasets": [],
        "disclaimers": {"standing": "s", "synthetic_demo": "d", "real_data": "r"},
        "counts": {"nodes_by_label": {}, "relationships_by_type": {}},
    }
    for version in ("0.1.0", "1.0.0rc1", "0.2.0.dev3+g1a2b3c"):
        assert api.MetaResponse.model_validate({**meta, "app_version": version})
    with pytest.raises(ValidationError):
        api.MetaResponse.model_validate(
            {**meta, "app_version": "0.1.0", "contracts_version": "1.0"}
        )


def test_numbers_are_finite_in_fields_and_property_maps() -> None:
    edge = _load("subgraph.json")["edges"][0]
    nan_amount = '{"amount": NaN}'
    with pytest.raises(ValidationError, match="finite"):  # JSON text: NaN through JsonValue
        api.GraphEdge.model_validate_json(
            json.dumps({**edge, "properties": {}}).replace(
                '"properties": {}', f'"properties": {nan_amount}'
            )
        )
    with pytest.raises(ValidationError):
        api.GraphEdge.model_validate({**edge, "properties": {"amount": float("inf")}})
    hit = {"entity": _load("entity-detail.json")["entity"], "matched_name": "x"}
    with pytest.raises(ValidationError):
        api.SearchHit.model_validate({**hit, "score": float("nan")})


def test_alert_summary_subject_ids_are_distinct() -> None:
    summary = _load("entity-detail.json")["alerts"][0]
    with pytest.raises(ValidationError, match="must not repeat"):
        api.AlertSummary.model_validate({**summary, "subject_ids": ["syn-co-0003", "syn-co-0003"]})
    schema = api.AlertSummary.model_json_schema()["properties"]["subject_ids"]
    assert schema["uniqueItems"] is True
