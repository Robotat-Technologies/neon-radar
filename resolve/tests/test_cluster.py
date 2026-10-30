"""Oracle tests for the constrained clustering (PHASE-2.md 7.1)."""

from __future__ import annotations

import json
from collections.abc import Iterable

from neonradar_resolve.cluster import Config, Link, Member, dates_compatible, resolve

PARENTS = {
    "Person": "LegalEntity",
    "Organization": "LegalEntity",
    "Company": "Organization",
    "PublicBody": "Organization",
    "LegalEntity": None,
    "Address": None,
}

UK, EU, OFAC = "gb_fcdo_sanctions", "eu_fsf", "us_ofac_sdn"


def lineage(schema: str | None) -> list[str]:
    out = []
    while schema:
        out.append(schema)
        schema = PARENTS[schema]
    return out


def common_schema(schemas: Iterable[str]) -> str | None:
    """Stand-in for followthemoney.model.common_schema: the most specific schema, if one chain."""
    items = list(schemas)
    best = items[0]
    for s in items[1:]:
        if best in lineage(s):
            best = s
        elif s not in lineage(best):
            return None
    return best


CONFIG = Config(
    merge_threshold={"person": 0.99, "org": 0.995},
    candidate_threshold=0.80,
    senior_reviewers=frozenset({"@senior"}),
)


def person(
    rid,
    dataset="gb_companies_house",
    kind="registry",
    priority=1,
    flags=(),
    source=None,
    party=None,
    synthetic=False,
    dobs=(),
    names=("john smith",),
    schema="Person",
    entity_class="person",
):
    return Member(
        rid,
        dataset,
        kind,
        priority,
        schema,
        entity_class,
        synthetic,
        flag_topics=frozenset(flags),
        list_source=source,
        list_party=party,
        birth_dates=frozenset(dobs),
        name_keys=frozenset(names),
    )


def listed(rid, dataset=UK, priority=3, flags=("sanction",), party=True, **kw):
    """A sanctions list record; party=False marks a UK record not grouped by OFSI Group ID."""
    return person(
        rid,
        dataset=dataset,
        kind="list",
        priority=priority,
        flags=flags,
        source=dataset,
        party=dataset if party else None,
        **kw,
    )


def org(
    rid,
    number=None,
    lei=None,
    dataset="gb_companies_house",
    kind="registry",
    priority=1,
    flags=(),
    names=("falcon ridge trading",),
    schema="Company",
):
    return Member(
        rid,
        dataset,
        kind,
        priority,
        schema,
        "org",
        False,
        flag_topics=frozenset(flags),
        list_source=dataset if kind == "list" else None,
        list_party=dataset if kind == "list" else None,
        company_numbers=frozenset([number]) if number else frozenset(),
        leis=frozenset([lei]) if lei else frozenset(),
        name_keys=frozenset(names),
    )


def address(rid, dataset="gb_companies_house", kind="registry"):
    return Member(rid, dataset, kind, 1, "Address", "address", False)


def prob(a, b, p=0.999, strong=True, birth_or_id=True, model="person"):
    return Link(
        a, b, "probabilistic", None, p, 9.0, {"name": "exact"}, strong, birth_or_id, model=model
    )


def det(a, b, rule):
    return Link(a, b, "deterministic", rule)


def same(a, b, *reviewers):
    return Link(a, b, "human", "D7", reviewers=frozenset(reviewers or ("@labeller",)))


def canon(result):
    return {r["record_id"]: r["canonical_id"] for r in result.canonical}


def reasons(result):
    return {(c["a"], c["b"]): c["reasons"] for c in result.candidates}


def rules(result):
    return [c["rule"] for c in result.conflicts]


def run(members, det_links=(), prob_links=(), same_links=(), different=(), hints=(), config=CONFIG):
    return resolve(
        members, det_links, prob_links, same_links, different, hints, config, common_schema
    )


def test_dates_compatible():
    assert dates_compatible(frozenset({"1979-08"}), frozenset({"1979-08-23"}))
    assert dates_compatible(frozenset({"1979"}), frozenset({"1979-08"}))
    assert not dates_compatible(frozenset({"1979-08"}), frozenset({"1979-09"}))
    assert dates_compatible(frozenset({"1979-08", "1980"}), frozenset({"1980-02-01"}))
    assert dates_compatible(frozenset(), frozenset({"1980"}))


def test_probabilistic_merge_anchor_and_output_columns():
    r = run(
        [person("gbch-psc-b"), person("gbch-off-a")], prob_links=[prob("gbch-off-a", "gbch-psc-b")]
    )
    assert canon(r) == {"gbch-off-a": "nr-gbch-off-a", "gbch-psc-b": "nr-gbch-off-a"}
    rows = {x["record_id"]: x for x in r.canonical}
    assert rows["gbch-off-a"]["method"] == "anchor" and rows["gbch-off-a"]["via"] is None
    joined = rows["gbch-psc-b"]
    assert joined["method"] == "probabilistic" and joined["via"] == "gbch-off-a"
    assert joined["path_methods"] == "probabilistic"
    assert json.loads(str(joined["features"])) == {"name": "exact"}


def test_path_methods_cover_the_whole_path_from_the_anchor():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-x", number="00000001"),
        org("gleif-y"),
    ]
    links = [det("gbch-co-00000001", "gbch-psc-x", "D1")]
    r = run(
        members, det_links=links, prob_links=[prob("gbch-psc-x", "gleif-y", 0.999, model="org")]
    )
    rows = {x["record_id"]: x for x in r.canonical}
    assert rows["gbch-psc-x"]["path_methods"] == "deterministic"
    assert rows["gbch-psc-x"]["features"] is None
    assert rows["gleif-y"]["via"] == "gbch-psc-x"
    assert rows["gleif-y"]["path_methods"] == "deterministic+probabilistic"


def test_anchor_prefers_dataset_priority():
    members = [
        listed("uksl-g7"),
        listed("unsc-9", dataset="un_sc_sanctions", priority=4),
    ]
    r = run(members, prob_links=[prob("uksl-g7", "unsc-9")])
    assert set(canon(r).values()) == {"nr-uksl-g7"}


def test_singleton_keeps_its_id():
    r = run([person("gbch-off-a")])
    assert r.canonical[0]["canonical_id"] == "gbch-off-a"
    assert r.canonical[0]["method"] == "identity"


def test_x1_synthetic_and_real_never_merge():
    syn = person("syn-p-1", dataset="nr_synthetic", kind="synthetic", priority=10, synthetic=True)
    r = run([syn, person("gbch-off-a")], same_links=[same("syn-p-1", "gbch-off-a")])
    assert canon(r)["syn-p-1"] == "syn-p-1"
    assert rules(r) == ["X1"]


def test_x2_person_and_company_never_merge():
    r = run(
        [person("gbch-off-a"), org("gbch-co-1", names=("john smith",))],
        prob_links=[prob("gbch-off-a", "gbch-co-1")],
    )
    assert canon(r)["gbch-off-a"] == "gbch-off-a"
    assert rules(r) == ["X2"]


def test_x3_two_company_numbers_through_a_chain():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-x"),
        org("gbch-co-00000002", number="00000002"),
    ]
    links = [
        prob("gbch-co-00000001", "gbch-psc-x", 0.9999, model="org"),
        prob("gbch-psc-x", "gbch-co-00000002", 0.9998, model="org"),
    ]
    r = run(members, prob_links=links)
    assert canon(r)["gbch-psc-x"] == "nr-gbch-co-00000001"
    assert canon(r)["gbch-co-00000002"] == "gbch-co-00000002"
    assert rules(r) == ["X3"] and r.candidates == []


def test_x3_pair_below_the_merge_threshold_is_not_a_possible_match():
    members = [org("gbch-co-00000001", number="00000001"), org("gbch-psc-x", number="00000002")]
    r = run(members, prob_links=[prob("gbch-co-00000001", "gbch-psc-x", 0.95, model="org")])
    assert r.candidates == [] and rules(r) == ["X3"]


def test_x4_two_leis():
    members = [
        org("gleif-A", lei="549300AAAAAAAAAAAA00"),
        org("gleif-B", lei="549300BBBBBBBBBBBB00"),
    ]
    r = run(members, prob_links=[prob("gleif-A", "gleif-B", 0.9999, model="org")])
    assert canon(r) == {"gleif-A": "gleif-A", "gleif-B": "gleif-B"}
    assert rules(r) == ["X4"] and r.candidates == []


def test_x5_birth_dates_block_transitive_merge():
    members = [person("a", dobs=["1980-05"]), person("b"), person("c", dobs=["1981-03"])]
    r = run(members, prob_links=[prob("a", "b", 0.9999), prob("b", "c", 0.9995)])
    assert canon(r)["b"] == "nr-a" and canon(r)["c"] == "c"
    assert rules(r) == ["X5"]


def test_x5_suppresses_a_possible_match_with_a_listed_record():
    members = [person("gbch-off-a", dobs=["1975-04"]), listed("uksl-g1", dobs=["1975-03"])]
    r = run(members, prob_links=[prob("gbch-off-a", "uksl-g1", 0.9999)])
    assert r.candidates == [] and rules(r) == ["X5"]


def test_x6_two_parties_of_one_list():
    r = run([listed("uksl-g1"), listed("uksl-g2")], prob_links=[prob("uksl-g1", "uksl-g2")])
    assert canon(r)["uksl-g2"] == "uksl-g2" and rules(r) == ["X6"]


def test_x6_ungrouped_uk_designations_of_one_person_may_merge():
    members = [listed("uksl-11111", party=False), listed("uksl-g2")]
    r = run(members, prob_links=[prob("uksl-11111", "uksl-g2", 0.9999)])
    assert canon(r)["uksl-11111"] == "nr-uksl-11111"


def test_party_with_several_designations_merges_with_its_eu_entry_by_d4():
    members = [
        listed("uksl-g1", names=("ivan petrov",)),
        listed("eufsf-2", EU, 5, names=("ivan petrov",)),
    ]
    r = run(members, det_links=[det("uksl-g1", "eufsf-2", "D4")])
    assert canon(r)["eufsf-2"] == "nr-uksl-g1" and r.conflicts == []


def test_x7_cluster_cap_becomes_possible_match():
    members = [person(f"p{i:02d}") for i in range(32)]
    links = [prob("p00", f"p{i:02d}", 0.9999 - i / 100000) for i in range(1, 32)]
    r = run(members, prob_links=links)
    assert max(x["cluster_size"] for x in r.canonical) == 30
    assert any("cluster_cap" in v for v in reasons(r).values())


def test_x8_human_different_wins_over_probability():
    r = run(
        [person("a"), person("b")], prob_links=[prob("a", "b", 0.99999)], different=[("a", "b")]
    )
    assert canon(r) == {"a": "a", "b": "b"} and rules(r) == ["X8"]
    assert r.candidates == [] and r.counts["decisions_applied"] == 1


def test_different_decision_removes_possible_matches():
    members = [person("gbch-off-a"), listed("uksl-g1"), person("gbch-off-b")]
    links = [prob("gbch-off-a", "uksl-g1", 0.9999), prob("gbch-off-a", "gbch-off-b", 0.95)]
    different = [("gbch-off-a", "uksl-g1"), ("gbch-off-a", "gbch-off-b")]
    r = run(members, prob_links=links, different=different)
    assert r.candidates == [] and rules(r) == ["X8", "X8"]


def test_p1_listed_and_unlisted_only_possible_match():
    r = run(
        [person("gbch-off-a"), listed("uksl-g1")],
        prob_links=[prob("gbch-off-a", "uksl-g1", 0.99999)],
    )
    assert canon(r) == {"gbch-off-a": "gbch-off-a", "uksl-g1": "uksl-g1"}
    assert reasons(r)[("gbch-off-a", "uksl-g1")] == ["listed_unlisted"]


def test_p1_records_listed_for_different_reasons_never_merge_by_probability():
    pep = listed("ukparl-1", "gb_parliament_members", 7, flags=("role.pep",), dobs=["1970-02"])
    sanctioned = listed("ofac-5", OFAC, 6, dobs=["1970-02"])
    r = run([pep, sanctioned], prob_links=[prob("ofac-5", "ukparl-1", 0.999)])
    assert canon(r) == {"ofac-5": "ofac-5", "ukparl-1": "ukparl-1"}
    assert reasons(r)[("ofac-5", "ukparl-1")] == ["listed_differently"]


def test_p1_deterministic_with_name_check_merges():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("uksl-g7", number="00000001", dataset=UK, kind="list", priority=3, flags=("sanction",)),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "uksl-g7", "D1")])
    assert canon(r)["uksl-g7"] == "nr-gbch-co-00000001"


def test_identifier_link_across_p1_needs_an_exact_name_key():
    members = [
        org("gbch-co-00000001", number="00000001", names=("x group uk",)),
        org(
            "uksl-g7",
            number="00000001",
            dataset=UK,
            kind="list",
            priority=3,
            flags=("sanction",),
            names=("x group",),
        ),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "uksl-g7", "D1")])
    assert canon(r)["uksl-g7"] == "uksl-g7"
    [candidate] = r.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"
    assert candidate["match_probability"] is None and candidate["method"] == "deterministic"


def test_name_check_failure_keeps_records_apart():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-z", number="00000001", names=("quarry lane instruments",)),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "gbch-psc-z", "D1")])
    assert canon(r)["gbch-psc-z"] == "gbch-psc-z"
    assert reasons(r)[("gbch-co-00000001", "gbch-psc-z")] == ["identifier_name_mismatch"]


def test_d3_needs_the_name_check():
    members = [
        person("gbch-off-a", names=("john smith",)),
        person("gbch-off-b", names=("mary jones",)),
    ]
    r = run(members, det_links=[det("gbch-off-a", "gbch-off-b", "D3")])
    assert reasons(r) == {("gbch-off-a", "gbch-off-b"): ["identifier_name_mismatch"]}


def test_p2_leaked_records_stay_apart():
    leak = person(
        "icij-1",
        "icij_offshore_leaks",
        "leak",
        9,
        schema="LegalEntity",
        entity_class="legal_entity",
    )
    r = run([person("gbch-off-a"), leak], prob_links=[prob("gbch-off-a", "icij-1", 0.99999)])
    assert reasons(r)[("gbch-off-a", "icij-1")] == ["leaked_cross_source"]


def test_addresses_merge_by_d6_and_never_become_possible_matches():
    members = [address("gbch-addr-1"), address("icij-addr-2", "icij_offshore_leaks", "leak")]
    r = run(members, det_links=[det("gbch-addr-1", "icij-addr-2", "D6")])
    assert canon(r)["icij-addr-2"] == "nr-gbch-addr-1" and r.candidates == []
    many = [address(f"a{i:02d}") for i in range(32)]
    links = [det("a00", f"a{i:02d}", "D6") for i in range(1, 32)]
    r = run(many, det_links=links)
    assert max(x["cluster_size"] for x in r.canonical) == 30
    assert r.candidates == [] and set(rules(r)) == {"X7"}


def test_p3_name_only_never_merges():
    r = run([person("a"), person("b")], prob_links=[prob("a", "b", 0.99999, strong=False)])
    assert reasons(r)[("a", "b")] == ["name_only"]


def test_p5_below_merge_threshold():
    r = run(
        [person("a"), person("b"), person("c")],
        prob_links=[prob("a", "b", 0.95), prob("a", "c", 0.5)],
    )
    assert reasons(r) == {("a", "b"): ["below_merge_threshold"]}


def test_merge_threshold_follows_the_scoring_model():
    officers = [
        person(
            f"icij-{i}",
            "icij_offshore_leaks",
            "leak",
            9,
            schema="LegalEntity",
            entity_class="legal_entity",
        )
        for i in (1, 2)
    ]
    r = run(officers, prob_links=[prob("icij-1", "icij-2", 0.9999, model="person")])
    assert canon(r)["icij-2"] == "nr-icij-1"
    r = run(officers, prob_links=[prob("icij-1", "icij-2", 0.9940, model="org")])
    assert reasons(r) == {("icij-1", "icij-2"): ["below_merge_threshold"]}


def test_p6_listed_people_on_two_lists_need_birth_or_id():
    a, b = listed("uksl-g1"), listed("eufsf-2", EU, 5)
    r = run([a, b], prob_links=[prob("uksl-g1", "eufsf-2", 0.99999, birth_or_id=False)])
    assert reasons(r)[("eufsf-2", "uksl-g1")] == ["listed_needs_birth_date"]
    r2 = run([a, b], prob_links=[prob("uksl-g1", "eufsf-2", 0.99999, birth_or_id=True)])
    assert canon(r2)["eufsf-2"] == "nr-uksl-g1"


def test_human_same_overrides_policy_with_a_second_reviewer():
    members = [person("gbch-off-a"), listed("uksl-g1")]
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@one", "@two")])
    assert canon(r)["uksl-g1"] == "nr-gbch-off-a"
    assert {x["record_id"]: x["method"] for x in r.canonical}["uksl-g1"] == "human"


def test_human_same_across_p1_waits_for_a_second_reviewer():
    members = [person("gbch-off-a"), listed("uksl-g1")]
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@one")])
    assert canon(r)["uksl-g1"] == "uksl-g1"
    assert r.counts["decisions_awaiting_second_review"] == 1
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@senior")])
    assert canon(r)["uksl-g1"] == "nr-gbch-off-a"
    r = run([person("a"), person("b")], same_links=[same("a", "b", "@one")])
    assert canon(r)["b"] == "nr-a" and r.counts["decisions_applied"] == 1


def test_decisions_about_records_outside_the_run_are_skipped():
    r = run([person("a")], same_links=[same("a", "gone")], different=[("a", "gone-too")])
    assert canon(r) == {"a": "a"} and r.counts["decisions_not_applicable"] == 2


def test_source_hints_become_possible_matches_without_probability():
    members = [
        person(
            f"icij-{i}",
            "icij_offshore_leaks",
            "leak",
            9,
            schema="LegalEntity",
            entity_class="legal_entity",
        )
        for i in (1, 2)
    ]
    hints = [("icij-1", "icij-2", "same_name_as"), ("icij-1", "icij-9", "same_name_as")]
    r = run(members, hints=hints)
    [candidate] = r.candidates
    assert candidate["method"] == "source_hint" and candidate["match_probability"] is None
    assert candidate["reasons"] == ["source_hint:same_name_as"]
    assert r.counts["hints_used"] == 1 and r.counts["hints_not_applicable"] == 1


def test_possible_match_dropped_when_a_later_merge_breaks_a_hard_rule():
    members = [person("a", dobs=["1980-05"]), person("b"), person("c", dobs=["1981-03"])]
    links = [prob("a", "b", 0.9999, strong=False), prob("b", "c", 0.995)]
    r = run(members, prob_links=links)
    assert canon(r)["c"] == "nr-b" and r.candidates == []
    assert rules(r) == ["X5"]


def test_possible_matches_inside_one_cluster_are_dropped():
    members = [person("a"), person("b")]
    r = run(members, det_links=[det("a", "b", "D5")], prob_links=[prob("a", "b", 0.9)])
    assert r.candidates == []


def test_deterministic_output():
    members = [person(f"p{i}", dobs=[f"19{60 + i % 5}-0{1 + i % 3}"]) for i in range(40)]
    links = [
        prob(f"p{i}", f"p{(i * 7) % 40}", 0.99 + (i % 9) / 1000)
        for i in range(40)
        if i != (i * 7) % 40
    ]
    hints = [(f"p{i}", f"p{i + 1}", "similar") for i in range(0, 38, 3)]
    first = run(members, prob_links=links, hints=hints)
    second = run(
        list(reversed(members)), prob_links=list(reversed(links)), hints=list(reversed(hints))
    )
    assert first == second


def test_probabilities_are_rounded_before_ordering():
    # Probabilities that differ only after the ninth decimal count as equal, so the record ids
    # decide the order and floating-point noise between runs cannot change the result.
    members = [person("gbch-off-a"), person("gbch-off-b"), person("gbch-off-c")]
    links = [
        prob("gbch-off-a", "gbch-off-c", 0.9999999994),
        prob("gbch-off-a", "gbch-off-b", 0.9999999991),
    ]
    capped = Config(merge_threshold={"person": 0.99}, candidate_threshold=0.80, cluster_cap=2)
    r = run(members, prob_links=links, config=capped)
    assert canon(r)["gbch-off-b"] == "nr-gbch-off-a"
    assert canon(r)["gbch-off-c"] == "gbch-off-c"
    assert [c["match_probability"] for c in r.candidates] == [0.999999999]
