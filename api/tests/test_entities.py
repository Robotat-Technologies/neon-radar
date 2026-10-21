"""Search, entity shapes and the network queries without a database (M1.9c)."""

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from neo4j.time import DateTime

from neonradar_api import entities, shapes
from neonradar_api.main import create_app

from .conftest import ScriptedGraph

ACCOUNT = {
    "props": {
        "id": "syn-acct-0001",
        "schema": "BankAccount",
        "caption": "NRSYN0000000001",
        "account_number": "NRSYN0000000001",
        "datasets": ["nr_synthetic"],
        "countries": [],
        "names": [],
        "names_text": "",
        "topics": [],
        "referents": ["syn-acct-0001"],
        "synthetic": True,
    },
    "labels": ["Entity", "Account", "Synthetic"],
}
COMPANY = {
    "props": {
        "id": "syn-co-0001",
        "schema": "Company",
        "caption": "Marram Lea Formations Ltd",
        "names": ["Marram Lea Formations Ltd", "MLF"],
        "names_text": "Marram Lea Formations Ltd | MLF",
        "datasets": ["nr_synthetic"],
        "countries": ["gb"],
        "registration_number": "SYN00001",
        "topics": ["role.pep"],
        "not_in_c2": "dropped",
        "synthetic": True,
    },
    "labels": ["Entity", "LegalEntity", "Organization", "Company", "Synthetic", "PEP"],
}


def answers(query: str, params: dict[str, Any]) -> list[Any]:
    if query == entities.ACCOUNT:
        return [{"node": ACCOUNT}] if params["number"] == "NRSYN0000000001" else []
    if query == entities.FULLTEXT:
        return [{"total": 3, "hits": [{**COMPANY, "score": 2.5}]}]
    raise AssertionError(query)


def test_lucene_special_characters_are_escaped_and_operators_become_words() -> None:
    text = 'a+b -c && d || !(e){f}[g]^"h"~i*j?k:l\\m/n AND NOT'
    assert entities.lucene_query(text) == (
        'a\\+b \\-c \\&\\& d \\|\\| \\!\\(e\\)\\{f\\}\\[g\\]\\^\\"h\\"\\~i\\*j\\?k\\:l\\\\m\\/n'
        " and not"
    )


def test_the_matched_name_shares_most_words_with_the_query() -> None:
    names = ["Marram Lea Formations Ltd", "Lea Holdings"]
    assert entities.matched_name(names, "caption", "lea formations") == names[0]
    assert entities.matched_name(names, "caption", "holdings LEA") == names[1]
    assert entities.matched_name([], "caption", "x") == "caption"


def test_one_fixed_network_query_per_depth() -> None:
    assert sorted(entities.NETWORK) == [1, 2, 3]
    for depth, query in entities.NETWORK.items():
        assert query.count("UNWIND frontier AS h") == depth
        assert "$max_nodes" in query and "$types" in query and "$id" in query


def test_search_lists_an_exact_account_number_first_with_the_top_score() -> None:
    graph = ScriptedGraph(answers)
    with TestClient(create_app(graph)) as client:
        body = client.get("/api/v1/search", params={"q": "NRSYN0000000001"}).json()
    assert [hit["entity"]["id"] for hit in body["items"]] == ["syn-acct-0001", "syn-co-0001"]
    assert [hit["score"] for hit in body["items"]] == [2.5, 2.5]
    assert body["items"][0]["matched_name"] == "NRSYN0000000001"
    assert body["total_estimate"] == 4
    assert graph.calls[1][1]["query"] == "nrsyn0000000001"


def test_search_filters_labels_and_skips_the_index_when_it_cannot_match() -> None:
    graph = ScriptedGraph(answers)
    with TestClient(create_app(graph)) as client:
        company = client.get("/api/v1/search?q=lea+ltd&labels=Company").json()
        accounts = client.get("/api/v1/search?q=lea&labels=Account").json()
        symbols = client.get("/api/v1/search?q=**").json()
    assert company["items"][0]["matched_name"] == "Marram Lea Formations Ltd"
    assert company["items"][0]["entity"]["flags"]["pep"] is True
    assert (accounts["items"], symbols["items"]) == ([], [])
    queries = [(query, params.get("labels")) for query, params in graph.calls]
    assert queries == [
        (entities.FULLTEXT, ["Company"]),  # no account lookup when Account is not asked for
        (entities.ACCOUNT, None),  # labels=Account: the full-text index has no accounts
        (entities.ACCOUNT, None),  # "**" has no word for the index
    ]


def test_nodes_keep_only_their_c2_properties_and_times_become_utc_text() -> None:
    node = shapes.graph_node(COMPANY)
    assert node.labels == ["Entity", "LegalEntity", "Organization", "Company"]
    assert node.flags.model_dump() == {
        "synthetic": True,
        "sanctioned": False,
        "pep": True,
        "rca": False,
    }
    assert sorted(node.properties) == ["countries", "datasets", "names", "registration_number"]
    assert shapes.detail_properties(COMPANY) == {"registration_number": "SYN00001"}
    assert shapes.identifiers(COMPANY["props"]) == {"registration_number": ["SYN00001"]}
    ts = DateTime.from_native(datetime(2026, 3, 2, 9, 0, tzinfo=UTC))
    edge = shapes.graph_edge(
        {
            "props": {"id": "syn-pay-1", "ts": ts, "amount": 10.0, "topics": [], "x": 1},
            "type": "PAID",
            "source": "syn-acct-0001",
            "target": "syn-acct-0002",
        }
    )
    assert edge.properties == {"amount": 10.0, "ts": "2026-03-02T09:00:00Z"}
