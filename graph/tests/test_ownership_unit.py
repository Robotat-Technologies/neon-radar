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
