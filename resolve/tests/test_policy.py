"""Flag topics, kinds, list sources and the merge policy P1 and P2 (PHASE-2.md 7.1.1, 7.1.4; G2-07).

The look-alike records are built here, in test code: invented names, test ids (PHASE-2.md 2.9).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from followthemoney.types import registry
from nr_resolve_support import members_of, rec, syn

from neonradar_resolve import policy, rules, schemas
from neonradar_resolve.cluster import Config, Link, Member, resolve
from neonradar_resolve.run import guard_decisions

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
        rec("uksl-gtest1", "Person", "gb_fcdo_sanctions", **sanction),
        rec("uksl-un-zzi.1", "Person", "gb_fcdo_sanctions", **sanction),
        rec("uksl-test-2", "Person", "gb_fcdo_sanctions", **sanction),
        rec("ofac-test-1", "Person", "us_ofac_sdn", **sanction),
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
    assert (members["uksl-gtest1"].list_source, members["uksl-gtest1"].list_party) == (
        "gb_fcdo_sanctions",
        "gb_fcdo_sanctions",
    )
    for ungrouped in ("uksl-un-zzi.1", "uksl-test-2"):
        assert members[ungrouped].list_source == "gb_fcdo_sanctions"
        assert members[ungrouped].list_party is None
    assert members["ofac-test-1"].list_party == "us_ofac_sdn"
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
        rec("uksl-gtest3", "Person", "gb_fcdo_sanctions", topics="sanction", **person),
    ]
    _, members = members_of(tmp_path, items)
    result = _resolve(members, prob=[_prob("gbch-off-test1", "uksl-gtest3")])
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-off-test1", "uksl-gtest3"}
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
            "gbch-co-99999901",
            "Company",
            "gb_companies_house",
            name="Example Group UK",
            registrationNumber="99999901",
            jurisdiction="gb",
        ),
        rec(
            "uksl-gtest4",
            "Organization",
            "gb_fcdo_sanctions",
            topics="sanction",
            name=listed_name,
            registrationNumber="9999-9901",
            jurisdiction="gb",
        ),
    ]
    corpus, members = members_of(tmp_path, items)
    links = rules.deterministic(corpus, members)
    assert [(x.rule, x.record_a, x.record_b) for x in links] == [
        ("D1", "gbch-co-99999901", "uksl-gtest4")
    ]
    return _resolve(members, det=links)


def test_p1_d1_with_exactly_the_same_name_merges(tmp_path: Path) -> None:
    result = _d1_pair(tmp_path, "EXAMPLE GROUP UK LIMITED")
    assert {r["canonical_id"] for r in result.canonical} == {"nr-gbch-co-99999901"}


def test_p1_d1_with_a_similar_name_is_only_a_possible_match(tmp_path: Path) -> None:
    result = _d1_pair(tmp_path, "Example Group")
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-co-99999901", "uksl-gtest4"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"


def test_p2_leak_and_registry_look_alikes_stay_apart(tmp_path: Path) -> None:
    items = [
        rec("gbch-off-test3", "Person", "gb_companies_house", name="Testa Example"),
        rec("icij-test-1", "LegalEntity", "icij_offshore_leaks", name="TESTA EXAMPLE"),
    ]
    _, members = members_of(tmp_path, items)
    assert (
        members["icij-test-1"].kind == "leak"
        and members["icij-test-1"].entity_class == "legal_entity"
    )
    result = _resolve(members, prob=[_prob("gbch-off-test3", "icij-test-1")])
    [candidate] = result.candidates
    assert candidate["reasons"] == ["leaked_cross_source"]
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-off-test3", "icij-test-1"}


def test_strict_name_check_uses_organisation_keys_for_legal_entities(tmp_path: Path) -> None:
    """A leak-style legal entity "Holder Example" shares a company number with "Example Holder
    Ltd": the person key of the first would match, the organisation keys do not (7.1.2)."""
    items = [
        rec(
            "gbch-co-99999902",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="99999902",
            jurisdiction="gb",
        ),
        rec(
            "icij-test-2",
            "LegalEntity",
            "icij_offshore_leaks",
            name="Holder Example",
            registrationNumber="9999-9902",
            jurisdiction="gb",
        ),
    ]
    corpus, members = members_of(tmp_path, items)
    assert members["icij-test-2"].name_keys == {"holder example"}
    result = _resolve(members, det=rules.deterministic(corpus, members))
    assert {r["canonical_id"] for r in result.canonical} == {"gbch-co-99999902", "icij-test-2"}
    [candidate] = result.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"


# One reviewer's `same` decision and later identifier links (phase-2-reconciliation.md 2.8, G1)


def _syn_person(
    rid: str,
    kind: str = "synthetic",
    flags: tuple[str, ...] = (),
    name: str = "testa example",
    dobs: tuple[str, ...] = (),
    party: str | None = None,
) -> Member:
    return Member(
        rid, "nr_synthetic", kind, 10, "Person", "person", True, flag_topics=frozenset(flags),
        list_party=party, birth_dates=frozenset(dobs), name_keys=frozenset({name}),
    )  # fmt: skip


def _one(a: str, b: str) -> Link:
    return Link(a, b, "human", "D7", reviewers=frozenset({"@example-one"}))


def _guarded(members: list[Member], det: list[Link], same: list[Link]):  # type: ignore[no-untyped-def]
    by_id = {m.record_id: m for m in members}
    decisions = rules.Decisions(same, [], len(same))
    kept, held = guard_decisions(by_id, det, [], decisions, CONFIG)
    result = resolve(members, det, [], kept, [], [], CONFIG, schemas.common_schema)
    canon = {r["record_id"]: r["canonical_id"] for r in result.canonical}
    return canon, result.counts["decisions_awaiting_second_review"] + held


def test_one_reviewer_cannot_bring_a_flag_through_a_later_identifier_link() -> None:
    v, u, w = (
        _syn_person("syn-v"),
        _syn_person("syn-u"),
        _syn_person("syn-w", "list", ("sanction",)),
    )
    d5 = Link("syn-u", "syn-w", "deterministic", "D5")
    canon, waiting = _guarded([v, u, w], [d5], [_one("syn-u", "syn-v")])
    assert canon["syn-v"] == "syn-v" and canon["syn-u"] == canon["syn-w"] == "nr-syn-u"
    assert waiting == 1


@pytest.mark.parametrize("v_id", ["syn-a-v", "syn-z-v"])
def test_one_reviewer_decision_does_not_depend_on_id_order(v_id: str) -> None:
    v, u, w = (
        _syn_person(v_id),
        _syn_person("syn-m-u"),
        _syn_person("syn-m-w", "list", ("sanction",)),
    )
    weak = _one(*sorted((v_id, "syn-m-u")))
    both = frozenset({"@example-one", "@example-two"})
    strong = Link("syn-m-u", "syn-m-w", "human", "D7", reviewers=both)
    canon, waiting = _guarded([v, u, w], [], [weak, strong])
    assert canon[v_id] == v_id and canon["syn-m-u"] == canon["syn-m-w"] == "nr-syn-m-u"
    assert waiting == 1


def test_one_reviewer_decision_between_unflagged_clusters_applies() -> None:
    v, u = _syn_person("syn-v"), _syn_person("syn-u")
    canon, waiting = _guarded([v, u], [], [_one("syn-u", "syn-v")])
    assert canon["syn-v"] == "nr-syn-u" and waiting == 0


@pytest.mark.parametrize("blocking", ["X5", "X6"])
def test_one_reviewer_cannot_bring_a_flag_to_a_third_record(blocking: str) -> None:
    """The decision B-A makes the D3 link B-L2 break X5 (birth dates) or X6 (one list's two
    parties), so R joins {A, B} by D5 without a name check before A's link brings L's flag."""
    party = "nr_synthetic:Synthetic Authority A" if blocking == "X6" else None
    a = _syn_person("syn-z-a", dobs=("1970",) if blocking == "X5" else (), party=party)
    lst = ("list", ("sanction",))
    l1 = _syn_person("syn-z-l", *lst)
    l2 = _syn_person("syn-l2", *lst, dobs=("1980",) if blocking == "X5" else (), party=party)
    b, r = _syn_person("syn-b"), _syn_person("syn-r", name="other example")
    det = [
        Link("syn-b", "syn-l2", "deterministic", "D3"),
        Link("syn-b", "syn-r", "deterministic", "D5"),
        Link("syn-z-a", "syn-z-l", "deterministic", "D5"),
    ]
    canon, waiting = _guarded([a, b, l1, l2, r], det, [_one("syn-b", "syn-z-a")])
    assert canon["syn-r"] == "syn-r" and canon["syn-z-a"] == canon["syn-z-l"]
    assert waiting == 1


def test_one_reviewer_chain_stops_before_the_listed_record() -> None:
    v, u, x = _syn_person("syn-v"), _syn_person("syn-u"), _syn_person("syn-x")
    lst = _syn_person("syn-l", "list", ("sanction",))
    d5 = Link("syn-l", "syn-x", "deterministic", "D5")
    canon, waiting = _guarded(
        [v, u, x, lst], [d5], [_one("syn-u", "syn-v"), _one("syn-u", "syn-x")]
    )
    assert canon["syn-v"] == canon["syn-u"] == "nr-syn-u" and canon["syn-x"] == "nr-syn-l"
    assert waiting == 1


@pytest.mark.parametrize(
    ("listed_id", "dataset", "psc_under_the_flag"),
    [("uksl-gtest5", "gb_fcdo_sanctions", True), ("eufsf-test-5", "eu_fsf", False)],
)
def test_strict_name_check_outcome_depends_on_id_order(
    tmp_path: Path, listed_id: str, dataset: str, psc_under_the_flag: bool
) -> None:
    """A registry record with a similar name ends up under a list entry's flag when its D1 link
    sorts before the list entry's (UK, OFAC, UN, ICIJ ids sort after `gbch-`), and stays a
    possible match when the list entry's sorts first (EU ids): a property of 7.1.6's order,
    recorded in ADR-0015 for the deciders."""
    uk = {"registrationNumber": "99999903", "jurisdiction": "gb"}
    items = [
        rec("gbch-co-99999903", "Company", "gb_companies_house", name="Example Holder Ltd", **uk),
        rec("gbch-psc-test-s1", "Company", "gb_companies_house", name="Example Holdr Ltd", **uk),
        rec(listed_id, "Organization", dataset, topics="sanction", name="Example Holder Plc", **uk),
    ]
    corpus, members = members_of(tmp_path, items)
    result = _resolve(members, det=rules.deterministic(corpus, members))
    canon = {r["record_id"]: r["canonical_id"] for r in result.canonical}
    assert canon[listed_id] == "nr-gbch-co-99999903"
    assert (canon["gbch-psc-test-s1"] == "nr-gbch-co-99999903") is psc_under_the_flag
    if not psc_under_the_flag:
        [candidate] = result.candidates
        assert candidate["reasons"] == ["identifier_name_mismatch"]


# Counterexamples a random search found against the earlier guard (5 in 60,000 trials): with
# each, a record gained a flag topic it did not have without the one-reviewer decisions.
# Members: "<n> <kind> <flag or -> <SY number suffix or -> <name: a, b or c>".
FUZZ = [
    (
        "0 list - 2 a,1 synthetic - 2 b,2 list role.pep 1 b,3 list - 1 b,4 synthetic - - b,"
        "5 synthetic - - b",
        "D1 1 3,D5 1 4,D5 1 5,D5 2 4",
        "2 4,0 1,0 3",
    ),
    (
        "0 synthetic - 1 b,1 synthetic role.pep 1 c,2 synthetic - 1 c,3 synthetic - 2 b,"
        "4 synthetic sanction - b,5 synthetic role.pep - b",
        "D1 0 1,D1 2 4,D1 3 5,D5 0 2,D5 0 5",
        "4 5,1 5",
    ),
    (
        "0 list - 2 a,1 list sanction 1 b,2 list - 1 a,3 synthetic - - b,"
        "4 synthetic sanction 2 c,5 list role.pep 2 b",
        "D1 1 3,D1 3 5,D5 0 1,D5 1 5,D5 3 4",
        "1 4,4 5",
    ),
    (
        "0 synthetic - 2 a,1 synthetic - - a,2 synthetic sanction 1 a,3 synthetic - 1 c,"
        "4 leak role.pep 1 a,5 synthetic - - c",
        "D1 0 1,D1 0 5,D5 1 2,D5 2 3",
        "2 3,0 3",
    ),
    (
        "0 synthetic - - c,1 leak - - a,2 synthetic sanction - a,3 synthetic sanction 2 a,"
        "4 list sanction 1 b,5 synthetic - 2 b,6 synthetic - 1 a",
        "D1 0 6,D5 2 3,D5 2 6",
        "2 4,2 6,3 5",
    ),
]
NAMES = {"a": "testa example", "b": "testa exampel", "c": "quill marsh"}


@pytest.mark.parametrize(("spec", "det_spec", "same_spec"), FUZZ)
def test_one_reviewer_decisions_never_add_a_flag_or_a_leak(
    spec: str, det_spec: str, same_spec: str
) -> None:
    members = []
    for item in spec.split(","):
        n, kind, flag, number, name = item.split()
        members.append(
            Member(
                f"syn-{n}",
                "nr_synthetic",
                kind,
                10,
                "Company",
                "org",
                True,
                flag_topics=frozenset() if flag == "-" else frozenset({flag}),
                company_numbers=frozenset() if number == "-" else frozenset({f"SY00000{number}"}),
                name_keys=frozenset({NAMES[name]}),
            )
        )
    det = [
        Link(f"syn-{a}", f"syn-{b}", "deterministic", r)
        for r, a, b in map(str.split, det_spec.split(","))
    ]
    same = [_one(f"syn-{a}", f"syn-{b}") for a, b in map(str.split, same_spec.split(","))]
    by_id = {m.record_id: m for m in members}
    kept, _ = guard_decisions(by_id, det, [], rules.Decisions(same, [], len(same)), CONFIG)
    before = _flags_by_record(members, det, [], [])
    after = _flags_by_record(members, det, kept, [])
    for rid in by_id:
        assert after[rid] <= before[rid], rid  # no flag topic and no leak gained


def _flags_by_record(
    members: list[Member], det: list[Link], same: list[Link], different: list[tuple[str, str]]
) -> dict[str, set[str]]:
    """Each record's cluster's flag topics plus "leak" when the cluster holds a leaked record,
    computed from canonical.csv rows, independently of run.py."""
    result = resolve(members, det, [], same, different, [], CONFIG, schemas.common_schema)
    canon = {str(r["record_id"]): str(r["canonical_id"]) for r in result.canonical}
    marks: dict[str, set[str]] = {}
    for m in members:
        group = marks.setdefault(canon[m.record_id], set())
        group |= set(m.flag_topics) | ({"leak"} if m.kind == "leak" else set())
    return {rid: marks[cid] for rid, cid in canon.items()}


def test_one_reviewer_chain_passing_the_first_check_is_held_back() -> None:
    """Both decisions join clusters with the same flags, so both pass the first check; the
    second makes the D3 link B-L2 break X5, so R joins by D5 before L's flag arrives."""
    a = _syn_person("syn-z-a", dobs=("1970",))
    a2, b = _syn_person("syn-z-a2"), _syn_person("syn-b")
    l1 = _syn_person("syn-z-l", "list", ("sanction",))
    l2 = _syn_person("syn-l2", "list", ("sanction",), dobs=("1980",))
    r = _syn_person("syn-r", name="other example")
    det = [
        Link("syn-b", "syn-l2", "deterministic", "D3"),
        Link("syn-b", "syn-r", "deterministic", "D5"),
        Link("syn-z-a", "syn-z-l", "deterministic", "D5"),
        Link("syn-z-a2", "syn-z-l", "deterministic", "D5"),
    ]
    same = [_one("syn-z-a", "syn-z-a2"), _one("syn-b", "syn-z-a2")]
    canon, waiting = _guarded([a, a2, b, l1, l2, r], det, same)
    assert canon["syn-r"] == "syn-r" and waiting == 2


def test_one_reviewer_different_decision_can_move_a_flag_today() -> None:
    """Pins current behaviour, which the spec allows (ADR-0015 property 1, reconciliation G1):
    a `different` decision (X8) needs no second reviewer, and by keeping B from L2 it lets R
    join B by D5 before Z's flag arrives through B's other D5 link."""
    b, r = _syn_person("syn-b"), _syn_person("syn-r", name="other example")
    l2, z = (_syn_person(x, "list", ("sanction",)) for x in ("syn-l2", "syn-z"))
    det = [
        Link("syn-b", "syn-l2", "deterministic", "D3"),
        Link("syn-b", "syn-r", "deterministic", "D5"),
        Link("syn-b", "syn-z", "deterministic", "D5"),
    ]
    members = [b, r, l2, z]
    assert _flags_by_record(members, det, [], [])["syn-r"] == set()
    assert _flags_by_record(members, det, [], [("syn-b", "syn-l2")])["syn-r"] == {"sanction"}
