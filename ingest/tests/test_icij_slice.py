"""ICIJ slice selection and the profile block (PHASE-2.md M2.5 deliverables 2 and 6).

A small synthetic graph with a known answer: invented node ids (ten digits starting with 99, a
form no ICIJ node id has, docs/data/spikes/icij.md 5), invented names and `QQ` postcodes.
"""

import hashlib
from collections.abc import Iterable
from typing import Any

import pytest
import yaml

from neonradar_ingest.data.profiles import ProfileError, load_profile
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_ingest.sources.icij.full import usable
from neonradar_ingest.sources.icij.slice import IcijSource, Row, postcode_districts, select

A1, A2, A3 = "9910000001", "9910000002", "9910000003"
E1, E2, E3 = "9920000001", "9920000002", "9920000003"
O1, O2, O3, O4, O5 = "9930000001", "9930000002", "9930000003", "9930000004", "9930000005"
I1, X1 = "9940000001", "9950000001"


def node(node_id: str, name: str, codes: str = "", **extra: str) -> dict[str, str]:
    return {"node_id": node_id, "name": name, "country_codes": codes, **extra}


def rel(start: str, end: str, rel_type: str, link: str = "") -> dict[str, str]:
    return {"node_id_start": start, "node_id_end": end, "rel_type": rel_type, "link": link}


TABLES: dict[str, list[dict[str, str]]] = {
    "nodes-addresses.csv": [
        node(A1, "", "GBR", address="1 Synthetic Row, Testford QQ1 1AA"),
        node(A2, "", "", address="2 Example Lane, Testford QQ2 2BB"),
        node(A3, "", "", address="Unit 3, Sampleton"),
    ],
    "nodes-entities.csv": [
        node(E1, "Quarry Synthetic Holdings Ltd", "VGB"),
        node(E2, "Marsh Example Trading SA"),
        node(E3, "Lantern Sample Partners Inc", "GBR;VGB"),
    ],
    "nodes-officers.csv": [
        node(O1, "Petra Kestrane"),
        node(O2, "Ivo Braske"),
        node(O3, "Oren Quillan"),
        node(O4, "Mira Testwood"),
        node(O5, "???"),
    ],
    "nodes-intermediaries.csv": [node(I1, "Synthetic Agents Ltd")],
    "nodes-others.csv": [node(X1, "Sample Foundation")],
    "relationships.csv": [
        rel(E1, A1, "registered_address", "registered address"),
        rel(O1, A1, "registered_address", "residential address"),
        rel(X1, A1, "registered_address", "registered address"),  # others are not level 1
        rel(E2, A2, "registered_address", "registered address"),
        rel(O2, E1, "officer_of", "shareholder of"),
        rel(I1, E1, "intermediary_of", "intermediary of"),
        rel(O5, E1, "officer_of", "director of"),  # no usable name
        rel(O1, E1, "officer_of", "director of"),  # already level 1
        rel(O3, E2, "officer_of", "director of"),
        rel(O2, E3, "officer_of", "director of"),  # nothing beyond level 2 is followed
        rel(O4, E3, "officer_of", "secretary of"),
        rel(E3, E2, "same_name_as", "same name as"),  # a hint is not a link
    ],
}


def rows(member: str) -> Iterable[Row]:
    return TABLES.get(member, [])


def options(mode: str, max_nodes: int = 100, seed: int = 7) -> IcijSource:
    context = {"sources": {"gb_companies_house": {"companies": {"postcode_districts": ["QQ1"]}}}}
    block = {"enabled": True, "mode": mode, "max_nodes": max_nodes, "sample_seed": seed}
    return IcijSource.model_validate(block, context=context)


def order(seed: int, *nodes: str) -> list[str]:
    return sorted(nodes, key=lambda n: hashlib.sha256(f"{seed}|{n}".encode()).hexdigest())


def test_district_linked_takes_three_levels_from_the_postcode_districts() -> None:
    selection = select(rows, usable, options("district-linked"), frozenset({"QQ1"}))
    assert selection.levels == [{A1}, {E1, O1}, {O2, I1}]
    assert selection.kept == {A1, E1, O1, O2, I1}
    assert selection.kinds[E1] == ("entity",) and selection.kinds[A1] == ("address",)
    assert selection.skipped == {"nodes without a usable name": 1}  # O5
    assert selection.counts() == {
        "nodes_by_level": {"level_0": 1, "level_1": 2, "level_2": 2},
        "nodes_selected": 5,
        "nodes_kept": 5,
        "nodes_dropped_by_cap": 0,
    }


def test_the_cap_keeps_whole_levels_then_the_smallest_hashes() -> None:
    capped = select(rows, usable, options("district-linked", max_nodes=4), frozenset({"QQ1"}))
    assert capped.kept == {A1, E1, O1, order(7, O2, I1)[0]}
    assert capped.counts()["nodes_dropped_by_cap"] == 1
    other_seed = select(rows, usable, options("district-linked", 4, 8), frozenset({"QQ1"}))
    assert other_seed.kept == {A1, E1, O1, order(8, O2, I1)[0]}
    tight = select(rows, usable, options("district-linked", max_nodes=2), frozenset({"QQ1"}))
    assert tight.kept == {A1, order(7, E1, O1)[0]}  # level 2 is dropped whole
    assert tight.counts()["nodes_dropped_by_cap"] == 3
    assert set(tight.kinds) == tight.kept


def test_gb_linked_takes_gbr_nodes_and_their_direct_neighbours() -> None:
    selection = select(rows, usable, options("gb-linked"), frozenset())
    assert selection.levels == [{A1, E3}, {E1, O1, X1, O2, O4}]  # E2 only through a hint
    capped = select(rows, usable, options("gb-linked", max_nodes=3), frozenset())
    assert capped.kept == {A1, E3, order(7, E1, O1, X1, O2, O4)[0]}


def test_full_takes_every_usable_node_and_ignores_the_cap() -> None:
    selection = select(rows, usable, options("full", max_nodes=1), frozenset())
    assert len(selection.kept) == 12 and O5 not in selection.kept
    assert selection.counts()["nodes_dropped_by_cap"] == 0


def committed_companies_house_block() -> dict[str, Any]:
    text = (REPO_ROOT / "ingest" / "profiles" / "uk-sample.yaml").read_text(encoding="utf-8")
    profile = yaml.safe_load(text)
    block: dict[str, Any] = profile["sources"]["gb_companies_house"]
    return block


def test_the_block_model_needs_postcode_districts_and_refuses_unknown_keys(data_env: Any) -> None:
    sample = load_profile("uk-sample").options("icij_offshore_leaks")
    assert (sample.mode, sample.max_nodes, sample.sample_seed) == (
        "district-linked",
        50000,
        20261026,
    )
    assert load_profile("uk-tiny").options("icij_offshore_leaks").enabled is False
    with_districts = committed_companies_house_block()
    without = {
        **with_districts,
        "companies": {**with_districts["companies"], "postcode_districts": []},
    }
    cases = {
        "icij-a": ({"enabled": True, "mode": "district-linked"}, without, "postcode_districts"),
        "icij-b": ({"enabled": True, "mode": "district-linked"}, None, "postcode_districts"),
        "icij-c": ({"enabled": True, "radius": 3}, with_districts, "radius"),
        "icij-d": ({"enabled": True, "mode": "nearby"}, with_districts, "mode"),
    }
    for name, (block, companies_house, message) in cases.items():
        sources = {"icij_offshore_leaks": block}
        if companies_house is not None:
            sources["gb_companies_house"] = companies_house
        data_env.write_profile(name, real_data=True, sources=sources)
        with pytest.raises(ProfileError, match=message):
            load_profile(name)
    gb = {"icij_offshore_leaks": {"enabled": True, "mode": "gb-linked", "max_nodes": 10}}
    data_env.write_profile("icij-e", real_data=True, sources=gb)
    assert load_profile("icij-e").options("icij_offshore_leaks").mode == "gb-linked"


def test_postcode_districts_reads_dicts_and_profile_blocks(data_env: Any) -> None:
    assert postcode_districts(load_profile("uk-sample").sources) >= {"EC2A", "M1"}
    assert postcode_districts(
        {"gb_companies_house": {"companies": {"postcode_districts": [" qq1 "]}}}
    ) == {"QQ1"}
    assert postcode_districts({}) == frozenset()
