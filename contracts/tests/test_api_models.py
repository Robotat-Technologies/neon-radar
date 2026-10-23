"""Contract tests for the C3 API models (PHASE-1.md 5.3, contracts/C3-api.md)."""

import copy
import json
import re
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from neonradar_contracts import api, graph
from neonradar_contracts.alert import EDGE_ID_PATTERN, Alert

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
    # C3 1.1.0 also shows the unconfirmed POSSIBLY_SAME_AS (PHASE-2.md 5.2), never the others.
    assert set(get_args(api.RelationshipType)) == record_types | {"POSSIBLY_SAME_AS"}
    assert not {"FLAGS", "PRODUCED", "RESOLVED_TO"} & set(get_args(api.RelationshipType))
    assert set(api.PATHS_DEFAULT_TYPES) == record_types - {"HAS_ADDRESS", "LINKED_TO"}
    assert set(get_args(api.MemberMethod)) == {"identity", *graph.RESOLVED_TO_METHODS}
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
        "effective_share_min_exclusive": None,
        "effective_share_max_exclusive": None,
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


# C3 1.1.0 (PHASE-2.md 5.3) ---------------------------------------------------------------


def _owned(low: float | None, high: float | None, **flags: bool | None) -> dict[str, Any]:
    return _cycle_path(
        effective_share_min=low,
        effective_share_max=high,
        effective_share_min_exclusive=flags.get("low_open", None if low is None else True),
        effective_share_max_exclusive=flags.get("high_open", None if high is None else False),
    )


def test_effective_share_flags_are_null_exactly_when_their_bound_is() -> None:
    path = api.PathRef.model_validate(_owned(9.375, 37.5, low_open=True, high_open=True))
    assert (path.effective_share_min_exclusive, path.effective_share_max_exclusive) == (True, True)
    api.PathRef.model_validate(_owned(None, None))
    api.PathRef.model_validate(_owned(None, 50.0))
    for broken in (_owned(18.75, 50.0, low_open=None), _owned(None, None, high_open=False)):
        with pytest.raises(ValidationError, match="null exactly when"):
            api.PathRef.model_validate(broken)


def test_effective_share_fields_say_they_are_a_neonradar_calculation() -> None:
    properties = api.PathRef.model_json_schema()["properties"]
    for name in ("min", "max", "min_exclusive", "max_exclusive"):
        assert api.EFFECTIVE_SHARE_NOTE in properties[f"effective_share_{name}"]["description"]


def test_the_resolution_example_validates_and_round_trips() -> None:
    data = _load("resolution.json")
    parsed = api.ResolutionResponse.model_validate(data)
    assert parsed.canonical and parsed.cluster_size == len(parsed.members) == 3
    assert [m.method for m in parsed.members] == ["anchor", "deterministic", "probabilistic"]
    assert all(api.NOT_CONFIRMED in m.explanation for m in parsed.possible_matches)
    assert parsed.model_dump(mode="json") == data


def _resolution(**changes: Any) -> dict[str, Any]:
    return {**_load("resolution.json"), **changes}


def test_a_single_record_entity_has_one_identity_member() -> None:
    data = _load("resolution.json")
    member = {**data["members"][0], "method": "identity", "explanation": "Built from one record."}
    single = {"canonical": False, "resolution": "identity", "cluster_size": 1}
    entity_id = member["record_id"]
    api.ResolutionResponse.model_validate(
        _resolution(entity_id=entity_id, members=[member], possible_matches=[], **single)
    )
    for broken, match in (
        ({"members": [data["members"][0]]}, "one member with method identity"),
        ({"members": [member], "canonical": True}, "canonical is true exactly"),
        ({"members": [member], "resolution": "deterministic"}, "resolution is identity"),
    ):
        with pytest.raises(ValidationError, match=match):
            api.ResolutionResponse.model_validate(
                _resolution(entity_id=entity_id, possible_matches=[], **{**single, **broken})
            )


def test_a_merged_entity_has_one_anchor_and_one_member_per_record() -> None:
    members = _load("resolution.json")["members"]
    second_anchor = [members[0], {**members[1], "method": "anchor", "rule": None}, members[2]]
    for broken, match in (
        ({"members": members[:2]}, "one member per source record"),
        ({"members": [members[0], members[1], members[1]]}, "must not repeat"),
        ({"members": second_anchor}, "exactly one anchor"),
        ({"run_id": "run-20261021T101500-7f3a"}, "run_id"),
    ):
        with pytest.raises(ValidationError, match=match):
            api.ResolutionResponse.model_validate(_resolution(**broken))


def test_member_methods_need_their_rule_or_probability() -> None:
    members = _load("resolution.json")["members"]
    for broken, match in (
        ({**members[1], "rule": None}, "names its D rule"),
        ({**members[1], "rule": "P1"}, "rule"),
        ({**members[2], "match_probability": None}, "has a match_probability"),
        ({**members[2], "match_probability": 1.5}, "match_probability"),
    ):
        with pytest.raises(ValidationError, match=match):
            api.ResolutionMember.model_validate(broken)


def test_possible_matches_are_never_confirmed() -> None:
    matches = _load("resolution.json")["possible_matches"]
    probabilistic, deterministic = matches[0], matches[1]
    for broken, match in (
        ({**probabilistic, "explanation": "Possible match."}, "not confirmed"),
        ({**probabilistic, "match_probability": None}, "set for probabilistic"),
        ({**deterministic, "match_probability": 0.99}, "set for probabilistic"),
        ({**deterministic, "rule": None}, "names its D rule"),
    ):
        with pytest.raises(ValidationError, match=match):
            api.PossibleMatch.model_validate(broken)
    itself = {**probabilistic["entity"], "id": "nr-syn-co-0003"}
    with pytest.raises(ValidationError, match="not a possible match of itself"):
        api.ResolutionResponse.model_validate(
            _resolution(possible_matches=[{**probabilistic, "entity": itself}])
        )


def test_possible_match_edges_have_their_own_id_form_outside_c4() -> None:
    edge = _load("subgraph.json")["edges"][0]
    psa = {**edge, "id": "syn-co-0001|psa|syn-co-0002", "type": "POSSIBLY_SAME_AS"}
    assert api.GraphEdge.model_validate(psa).id == psa["id"]
    assert api.PathRef.model_validate(_cycle_path(edge_ids=[psa["id"], "syn-payment-000102"]))
    with pytest.raises(ValidationError):
        api.GraphEdge.model_validate({**psa, "id": "syn-co-0001|same|syn-co-0002"})
    assert not re.fullmatch(EDGE_ID_PATTERN, psa["id"])  # C4 evidence keeps 1.0.0 ids


def test_path_lists_have_the_5_3_caps_in_the_schema() -> None:
    """At most 200 ownership paths and 5 shortest paths (5.3), declared before M2.12."""
    owners = api.OwnershipResponse.model_json_schema()["properties"]["paths"]
    shortest = api.PathsResponse.model_json_schema()["properties"]["paths"]
    assert (owners["maxItems"], shortest["maxItems"]) == (200, 5)
    subgraph = _load("subgraph.json")
    paths = {"from_id": "syn-acct-0007", "to_id": "syn-acct-0015", "subgraph": subgraph}
    with pytest.raises(ValidationError, match="at most 5"):
        api.PathsResponse.model_validate({**paths, "paths": [_cycle_path()] * 6})
