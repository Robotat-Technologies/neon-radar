"""Flag topics, kinds, list sources and the merge policy P1 and P2 (PHASE-2.md 7.1.1, 7.1.4; G2-07).

The look-alike records are built here, in test code: invented names, test ids (PHASE-2.md 2.9).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from followthemoney.types import registry
from nr_resolve_support import members_of, rec, syn

from neonradar_resolve import policy, rules, schemas
from neonradar_resolve.cluster import Config, Link, resolve

DESCRIPTIVE = ["corp.public", "fin", "fin.bank", "fin.fund", "gov", "gov.soe", "gov.muni"]
DESCRIPTIVE += ["pol.party", "pol.union", "rel", "mil"]
LISTED = ["sanction", "sanction.linked", "role.pep", "role.rca", "crime", "crime.fin"]
LISTED += ["debarment", "export.control", "asset.frozen", "corp.disqual", "corp.shell", "poi"]
LISTED += ["wanted", "reg.action", "mare.shadow"]
CONFIG = Config(merge_threshold={"person": 0.99, "org": 0.995}, candidate_threshold=0.80)


@pytest.mark.parametrize("topic", DESCRIPTIVE)
def test_descriptive_topics_are_not_flags(topic: str) -> None:
    assert policy.flag_topics([topic]) == frozenset()
    assert not policy.is_listed([topic])


@pytest.mark.parametrize("topic", LISTED)
def test_listed_topics_are_flags(topic: str) -> None:
    assert policy.flag_topics([topic, "fin"]) == {topic}
    assert policy.is_listed([topic])


def test_every_followthemoney_topic_is_classified() -> None:
    """Fails when FollowTheMoney adds a topic, so that a human decides whether it is a flag."""
    names = set(registry.topic.names)
    unclassified = {t for t in names if not policy.is_descriptive(t)} - policy.FLAG_TOPICS
    assert unclassified == set()
    assert names >= policy.FLAG_TOPICS
    assert not {t for t in policy.FLAG_TOPICS if policy.is_descriptive(t)}


def test_an_unknown_topic_counts_as_a_flag() -> None:
    assert policy.flag_topics(["role.new"]) == {"role.new"}


def test_record_kind() -> None:
    assert policy.record_kind("synthetic", {"synthetic_kind": "list"}) == "list"
    assert policy.record_kind("synthetic", {"synthetic_kind": "leak"}) == "leak"
    assert policy.record_kind("synthetic", {"synthetic_kind": "registry"}) == "synthetic"
    assert policy.record_kind("synthetic", None) == "synthetic"
    assert policy.record_kind("registry", {"synthetic_kind": "leak"}) == "registry"
    assert policy.record_kind("leak", {}) == "leak"
    assert policy.is_leaked("leak") and not policy.is_leaked("list")


def test_list_source_and_list_party(tmp_path: Path) -> None:
    sanction = {"topics": "sanction", "name": "Testa Example"}
    items = [
        rec("uksl-g1234", "Person", "gb_fcdo_sanctions", **sanction),
        rec("uksl-un-zzi.1", "Person", "gb_fcdo_sanctions", **sanction),
        rec("uksl-98765", "Person", "gb_fcdo_sanctions", **sanction),
        rec("ofac-555", "Person", "us_ofac_sdn", **sanction),
        rec("gbch-off-test1", "Person", "gb_companies_house", name="Testa Example"),
        syn("syn-list-1", "Person", "list", **sanction),
        rec(
            "syn-sanction-b",
            "Sanction",
            "nr_synthetic",
            {"synthetic": True},
            entity="syn-list-1",
            authority="Synthetic Authority B",
        ),
        rec(
            "syn-sanction-a",
            "Sanction",
            "nr_synthetic",
            {"synthetic": True},
            entity="syn-list-1",
            authority="Synthetic Authority A",
        ),
    ]
    _, members = members_of(tmp_path, items)
    assert (members["uksl-g1234"].list_source, members["uksl-g1234"].list_party) == (
        "gb_fcdo_sanctions",
        "gb_fcdo_sanctions",
    )
    for ungrouped in ("uksl-un-zzi.1", "uksl-98765"):
        assert members[ungrouped].list_source == "gb_fcdo_sanctions"
        assert members[ungrouped].list_party is None
    assert members["ofac-555"].list_party == "us_ofac_sdn"
    assert (
        members["gbch-off-test1"].list_source is None
        and members["gbch-off-test1"].kind == "registry"
    )
    listed = members["syn-list-1"]
    assert listed.kind == "list" and listed.flag_topics == {"sanction"}
    assert listed.list_source == listed.list_party == "nr_synthetic:Synthetic Authority A"


def _resolve(members: dict[str, object], det=(), prob=()):  # type: ignore[no-untyped-def]
    return resolve(members.values(), det, prob, [], [], [], CONFIG, schemas.common_schema)  # type: ignore[arg-type]


def _prob(a: str, b: str) -> Link:
    return Link(
        a, b, "probabilistic", None, 0.99999, 12.0, {"name": "exact"}, True, True, model="person"
    )


def test_p1_registry_and_sanctions_look_alikes_stay_apart(tmp_path: Path) -> None:
    person = {"name": "Testa Example", "birthDate": "1971-04-12"}
    items = [
        rec("gbch-off-test1", "Person", "gb_companies_house", **person),
        rec("uksl-g9001", "Person", "gb_fcdo_sanctions", topics="sanction", **person),
    ]
    _, members = members_of(tmp_path, items)
    result = _resolve(members, prob=[_prob("gbch-off-test1", "uksl-g9001")])
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-off-test1", "uksl-g9001"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["listed_unlisted"]


def test_p1_pep_and_ofac_look_alikes_stay_apart(tmp_path: Path) -> None:
    items = [
        rec(
            "ukparl-test1",
            "Person",
            "gb_parliament_members",
            topics="role.pep",
            name="Testa Example",
            birthDate="1966-03",
        ),
        rec(
            "ofac-test2",
            "Person",
            "us_ofac_sdn",
            topics="sanction",
            name="Testa Example",
            birthDate="1966-03",
        ),
    ]
    _, members = members_of(tmp_path, items)
    result = _resolve(members, prob=[_prob("ofac-test2", "ukparl-test1")])
    assert {r["canonical_id"] for r in result.canonical} == {"ofac-test2", "ukparl-test1"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["listed_differently"]


def _d1_pair(tmp_path: Path, listed_name: str):  # type: ignore[no-untyped-def]
    items = [
        rec(
            "gbch-co-00000001",
            "Company",
            "gb_companies_house",
            name="Example Group UK",
            registrationNumber="00000001",
            jurisdiction="gb",
        ),
        rec(
            "uksl-g9002",
            "Organization",
            "gb_fcdo_sanctions",
            topics="sanction",
            name=listed_name,
            registrationNumber="1",
            jurisdiction="gb",
        ),
    ]
    corpus, members = members_of(tmp_path, items)
    links = rules.deterministic(corpus, members)
    assert [(x.rule, x.record_a, x.record_b) for x in links] == [
        ("D1", "gbch-co-00000001", "uksl-g9002")
    ]
    return _resolve(members, det=links)


def test_p1_d1_with_exactly_the_same_name_merges(tmp_path: Path) -> None:
    result = _d1_pair(tmp_path, "EXAMPLE GROUP UK LIMITED")
    assert {r["canonical_id"] for r in result.canonical} == {"nr-gbch-co-00000001"}


def test_p1_d1_with_a_similar_name_is_only_a_possible_match(tmp_path: Path) -> None:
    result = _d1_pair(tmp_path, "Example Group")
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-co-00000001", "uksl-g9002"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"


def test_p2_leak_and_registry_look_alikes_stay_apart(tmp_path: Path) -> None:
    items = [
        rec("gbch-off-test3", "Person", "gb_companies_house", name="Testa Example"),
        rec("icij-90001", "LegalEntity", "icij_offshore_leaks", name="TESTA EXAMPLE"),
    ]
    _, members = members_of(tmp_path, items)
    assert (
        members["icij-90001"].kind == "leak"
        and members["icij-90001"].entity_class == "legal_entity"
    )
    result = _resolve(members, prob=[_prob("gbch-off-test3", "icij-90001")])
    [candidate] = result.candidates
    assert candidate["reasons"] == ["leaked_cross_source"]
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-off-test3", "icij-90001"}


def test_strict_name_check_uses_organisation_keys_for_legal_entities(tmp_path: Path) -> None:
    """A leak-style legal entity "Holder Example" shares a company number with "Example Holder
    Ltd": the person key of the first would match, the organisation keys do not (7.1.2)."""
    items = [
        rec(
            "gbch-co-00000002",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="00000002",
            jurisdiction="gb",
        ),
        rec(
            "icij-90002",
            "LegalEntity",
            "icij_offshore_leaks",
            name="Holder Example",
            registrationNumber="2",
            jurisdiction="gb",
        ),
    ]
    corpus, members = members_of(tmp_path, items)
    assert members["icij-90002"].name_keys == {"holder example"}
    result = _resolve(members, det=rules.deterministic(corpus, members))
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-co-00000002", "icij-90002"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"
