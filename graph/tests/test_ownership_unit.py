"""`neonradar_graph.ownership` without a database (PHASE-2.md M2.12): the query variants, the
effective share rule of `/paths`, rounding, id picking and the timeout."""

from typing import Any, cast

import pytest
from neo4j import Driver
from neo4j.exceptions import Neo4jError

from neonradar_graph import cypher, ownership


def test_one_rendered_query_per_max_hops_value_from_the_file() -> None:
    for name, hops in (
        ("ownership_up.cypher", 8),
        ("ownership_down.cypher", 8),
        ("paths.cypher", 6),
    ):
        variants = ownership._variants(name)
        assert sorted(variants) == list(range(1, hops + 1))
        for value, text in variants.items():
            assert f"{{1,{value}}}" in text and "{{" not in text
    with pytest.raises(ValueError, match="max_hops"):
        ownership._variant("paths.cypher", 7)
    with pytest.raises(ValueError, match="not a label or relationship type"):
        cypher.query("ownership_up.cypher", max_hops="9")  # only the header's values fill it


def test_rounding_is_half_up_on_the_shortest_decimal_form() -> None:
    assert ownership._rounded(9.375) == 9.375
    assert ownership._rounded(12.34565) == 12.3457
    assert ownership._rounded(0.00005) == 0.0001
    assert ownership._product([25.0, 50.0, 75.0]) == 9.375
    assert ownership._product([50.0, None]) is None


def _row(starts: list[str], **overrides: Any) -> dict[str, Any]:
    row = {
        "node_ids": ["a", "b", "c"],
        "types": ["OWNS", "OWNS"],
        "starts": starts,
        "mins": [25.0, 50.0],
        "maxes": [50.0, 75.0],
        "mins_open": [True, True],
        "maxes_open": [False, True],
    }
    return {**row, **overrides}


def test_paths_shares_need_owns_all_pointing_the_same_way() -> None:
    forward = ownership.chain_shares(_row(["a", "b"]))
    assert forward == {
        "effective_share_min": 12.5,
        "effective_share_max": 37.5,
        "effective_share_min_exclusive": True,
        "effective_share_max_exclusive": True,
    }
    assert ownership.chain_shares(_row(["b", "c"])) == forward  # both point back along the path
    empty = dict.fromkeys(forward)
    assert ownership.chain_shares(_row(["a", "c"])) == empty  # the second points the other way
    assert ownership.chain_shares(_row(["a", "b"], types=["OWNS", "CONTROLS"])) == empty
    no_max = ownership.chain_shares(_row(["a", "b"], maxes=[50.0, None]))
    assert no_max["effective_share_max"] is None and no_max["effective_share_max_exclusive"] is None
    assert no_max["effective_share_min"] == 12.5


def test_an_id_resolves_to_itself_or_to_its_one_entity() -> None:
    assert ownership.pick_entity("nr-syn-a", ["nr-syn-a"]) == "nr-syn-a"
    assert ownership.pick_entity("syn-a", ["nr-syn-a"]) == "nr-syn-a"
    with pytest.raises(ownership.UnknownId):
        ownership.pick_entity("syn-x", [])
    with pytest.raises(RuntimeError, match="more than one entity"):
        ownership.pick_entity("syn-a", ["nr-syn-a", "nr-syn-b"])


class _TimedOut:
    def execute_query(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        assert query.timeout == 5.0 and kwargs["routing_"] == "r"
        raise Neo4jError._hydrate_neo4j(
            code="Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration",
            message="timed out",
        )


def test_a_timeout_becomes_query_timeout_with_advice() -> None:
    with pytest.raises(ownership.QueryTimeout, match="smaller max_hops or fewer relationship"):
        ownership.ownership(cast(Driver, _TimedOut()), "syn-a", "up", 6, 0)


# A path through a :Sanction (SUBJECT_OF is a default /paths type): A -> S <- B.
A, S, B = "nr-syn-path-a", "syn-path-sanction", "nr-syn-path-b"
ENTITY_LABELS = ["Entity", "Company", "Synthetic"]


class _SanctionPath:
    """Answers resolve_id, paths and path_elements for the one path A -> S <- B."""

    def __init__(self) -> None:
        self.links: list[dict[str, str]] = []

    def execute_query(self, query: Any, parameters: dict[str, Any], **_: Any) -> Any:
        nodes_text, edges_text = cypher.statements("path_elements.cypher")
        if query.text == cypher.query("resolve_id.cypher"):
            rows: list[Any] = [{"id": parameters["id"]}]
        elif query.text == ownership._variant(ownership.PATHS_FILE, 2):
            assert "SUBJECT_OF" in parameters["rel_types"]  # a default type
            rows = [
                {
                    "node_ids": [A, S, B],
                    "edge_ids": ["syn-subj-a", "syn-subj-b"],
                    "types": ["SUBJECT_OF", "SUBJECT_OF"],
                    "starts": [A, B],
                    "mins": [None, None],
                    "maxes": [None, None],
                    "mins_open": [None, None],
                    "maxes_open": [None, None],
                }
            ]
        elif query.text == nodes_text:
            assert parameters["ids"] == [A, S, B]
            entity = {"schema": "Company", "caption": "Synthetic Path Company"}
            sanction = {"id": S, "schema": "Sanction", "caption": "Synthetic sanction entry"}
            rows = [
                {"node": {"props": {"id": A, **entity}, "labels": ENTITY_LABELS}},
                {"node": {"props": sanction, "labels": ["Sanction", "Synthetic"]}},
                {"node": {"props": {"id": B, **entity}, "labels": ENTITY_LABELS}},
            ]
        else:
            assert query.text == edges_text
            self.links = parameters["links"]
            rows = [
                {"edge": {"props": {"id": f"syn-subj-{end[-1]}"}, "type": "SUBJECT_OF",
                          "source": end, "target": S}}
                for end in (A, B)
            ]  # fmt: skip
        return rows, None, None


def test_a_path_through_a_sanction_keeps_the_sanction_and_its_edges() -> None:
    driver = _SanctionPath()
    found = ownership.paths(cast(Driver, driver), A, B, 2, None)
    assert [path.node_ids for path in found.paths] == [[A, S, B]]
    # Each relationship is looked up from its :Entity end, so the S -> B hop is swapped.
    assert driver.links == [
        {"a": A, "b": S, "id": "syn-subj-a", "type": "SUBJECT_OF"},
        {"a": B, "b": S, "id": "syn-subj-b", "type": "SUBJECT_OF"},
    ]
    nodes = {node.id: node.schema_ for node in found.subgraph.nodes}
    assert nodes == {A: "Company", S: "Sanction", B: "Company"}
    edges = [(edge.source, edge.type, edge.target) for edge in found.subgraph.edges]
    assert edges == [(A, "SUBJECT_OF", S), (B, "SUBJECT_OF", S)]
    assert found.paths[0].effective_share_min is None and not found.subgraph.truncated
