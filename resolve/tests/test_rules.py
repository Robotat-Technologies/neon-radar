"""Deterministic rules D1 to D6 and decisions D7 (PHASE-2.md 7.1.2), on records built here."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nr_resolve_support import members_of, rec, syn

from neonradar_resolve import rules
from neonradar_resolve.features import company_numbers

FIXTURES = Path(__file__).parent / "fixtures"
VALID_LEI, INVALID_LEI = "549300OWFMSO9NYV4H90", "549300OWFMSO9NYV4H91"


def _links(tmp_path: Path, items: list[dict[str, object]]) -> list[tuple[str | None, str, str]]:
    corpus, members = members_of(tmp_path, items)  # type: ignore[arg-type]
    return [(x.rule, x.record_a, x.record_b) for x in rules.deterministic(corpus, members)]


def _company(rid: str, number: str, **props: object) -> dict[str, object]:
    return rec(
        rid,
        "Company",
        "gb_companies_house",
        name="Example Holder Ltd",
        registrationNumber=number,
        jurisdiction="gb",
        **props,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1800000", "01800000"),
        ("SC 12345", "SC012345"),
        ("OC300001", "OC300001"),
        ("ABC", None),
        ("HE123456", None),
        ("SY000101", None),  # the synthetic prefix only for synthetic records
    ],
)
def test_d1_normalisation(tmp_path: Path, raw: str, expected: str | None) -> None:
    _, members = members_of(tmp_path, [_company("gbch-psc-test1", raw)])
    assert members["gbch-psc-test1"].company_numbers == ({expected} if expected else set())


def test_d1_synthetic_prefix_only_for_synthetic_records(tmp_path: Path) -> None:
    items = [
        syn(
            "syn-co-1",
            "Company",
            name="Example Holder Ltd",
            registrationNumber="SY000101",
            jurisdiction="gb",
        ),
        _company("gbch-psc-test2", "SY000101"),
    ]
    _, members = members_of(tmp_path, items)
    assert members["syn-co-1"].company_numbers == {"SY000101"}
    assert members["gbch-psc-test2"].company_numbers == frozenset()


def test_d1_needs_a_uk_record_and_skips_people(tmp_path: Path) -> None:
    items = [
        rec(
            "gbch-psc-test3",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="01800000",
            jurisdiction="cy",
        ),
        rec(
            "gbch-co-01800000",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="1800000",
            jurisdiction="vg",
        ),
        rec(
            "gbch-psc-test4",
            "Person",
            "gb_companies_house",
            name="Testa Example",
            registrationNumber="01800000",
            jurisdiction="gb",
        ),
    ]
    _, members = members_of(tmp_path, items)
    assert members["gbch-psc-test3"].company_numbers == frozenset()  # not a UK record
    assert members["gbch-co-01800000"].company_numbers == {"01800000"}  # always for gbch-co-
    assert members["gbch-psc-test4"].company_numbers == frozenset()


def test_d1_links_to_the_companies_house_record_when_the_run_has_it(tmp_path: Path) -> None:
    items = [
        _company("gbch-co-01800000", "01800000"),
        _company("gbch-psc-test5", "1800000"),
        _company("gbch-psc-test6", "01800000"),
    ]
    assert _links(tmp_path, items) == [
        ("D1", "gbch-co-01800000", "gbch-psc-test5"),
        ("D1", "gbch-co-01800000", "gbch-psc-test6"),
    ]


def test_d1_without_the_companies_house_record_links_every_pair(tmp_path: Path) -> None:
    items = [_company(f"gbch-psc-test{i}", "SC012345") for i in (7, 8, 9)]
    assert _links(tmp_path, items) == [
        ("D1", "gbch-psc-test7", "gbch-psc-test8"),
        ("D1", "gbch-psc-test7", "gbch-psc-test9"),
        ("D1", "gbch-psc-test8", "gbch-psc-test9"),
    ]


def test_d2_valid_check_digits_only(tmp_path: Path) -> None:
    items = [
        rec("gleif-a", "Company", "gleif_lei", name="Example Holder Ltd", leiCode=VALID_LEI),
        rec(
            "gbch-psc-test10",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            leiCode=VALID_LEI.lower(),
        ),
        rec("gleif-b", "Company", "gleif_lei", name="Example Holder Ltd", leiCode=INVALID_LEI),
        rec(
            "gbch-psc-test11",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            leiCode=INVALID_LEI,
        ),
    ]
    assert _links(tmp_path, items) == [("D2", "gbch-psc-test10", "gleif-a")]


def test_d3_uses_the_first_eight_characters_only(tmp_path: Path) -> None:
    def officer(rid: str, number: str) -> dict[str, object]:
        return rec(
            rid, "Person", "gb_companies_house", {"ch_person_number": number}, name="Testa Example"
        )

    items = [
        officer("gbch-off-a", "123456780001"),
        officer("gbch-off-b", "123456789999"),
        officer("gbch-off-c", "123456790001"),
        officer("gbch-off-d", "1234567"),
        rec(
            "gbch-co-00000001",
            "Company",
            "gb_companies_house",
            {"ch_person_number": "123456780001"},
            name="X",
        ),
    ]
    assert _links(tmp_path, items) == [("D3", "gbch-off-a", "gbch-off-b")]


def test_d4_links_listed_records_of_different_lists(tmp_path: Path) -> None:
    def listed(rid: str, dataset: str) -> dict[str, object]:
        return rec(rid, "Person", dataset, topics="sanction", name="Testa Example")

    def sanction(rid: str, dataset: str, entity: str, ref: str) -> dict[str, object]:
        return rec(rid, "Sanction", dataset, entity=entity, unscId=ref, authority="Test")

    items = [
        listed("uksl-un-zzi.1", "gb_fcdo_sanctions"),
        listed("eufsf-1", "eu_fsf"),
        listed("eufsf-2", "eu_fsf"),
        sanction("uksl-sanction-1", "gb_fcdo_sanctions", "uksl-un-zzi.1", "ZZi.1"),
        sanction("eufsf-sanction-1", "eu_fsf", "eufsf-1", "zzi.1."),
        sanction("eufsf-sanction-2", "eu_fsf", "eufsf-2", "ZZi.1"),
    ]
    assert _links(tmp_path, items) == [
        ("D4", "eufsf-1", "uksl-un-zzi.1"),
        ("D4", "eufsf-2", "uksl-un-zzi.1"),
    ]


def test_d5_same_native_id_within_one_dataset(tmp_path: Path) -> None:
    items = [
        rec("icij-1", "LegalEntity", "icij_offshore_leaks", {"source_ref": "90001"}, name="X"),
        rec("icij-2", "LegalEntity", "icij_offshore_leaks", {"source_ref": "90001"}, name="Y"),
        rec("ofac-3", "Person", "us_ofac_sdn", {"source_ref": "90001"}, name="X"),
    ]
    assert _links(tmp_path, items) == [("D5", "icij-1", "icij-2")]


def test_d6_links_addresses_only(tmp_path: Path) -> None:
    items = [
        rec("gbch-addr-1", "Address", "gb_companies_house", full="12 High St., London, n1 7gu"),
        rec(
            "icij-addr-2",
            "Address",
            "icij_offshore_leaks",
            street="12 High Street",
            city="London",
            postalCode="N1 7GU",
        ),
        rec("gbch-addr-3", "Address", "gb_companies_house", full="Moscow, Russia"),
        rec("gbch-addr-4", "Address", "gb_companies_house", full="Moscow, Russia"),
        rec(
            "gbch-off-x",
            "Person",
            "gb_companies_house",
            name="X",
            address="12 High St., London, n1 7gu",
        ),
        rec(
            "gbch-off-y",
            "Person",
            "gb_companies_house",
            name="Y",
            address="12 High St., London, n1 7gu",
        ),
    ]
    assert _links(tmp_path, items) == [("D6", "gbch-addr-1", "icij-addr-2")]


def test_d7_newest_line_decides_and_same_carries_its_reviewers() -> None:
    decisions = rules.read_decisions(FIXTURES / "decisions.jsonl")
    assert decisions.on_file == 3
    same = {(x.record_a, x.record_b): x for x in decisions.same}
    first = same[("syn-test-a1", "syn-test-a2")]
    assert (first.method, first.rule, first.reviewers) == ("human", "D7", {"@one"})
    assert same[("syn-test-b1", "syn-test-b2")].reviewers == {"@one", "@two"}
    assert decisions.different == [("syn-test-c1", "syn-test-c2")]


def test_d7_without_a_file_reads_nothing(tmp_path: Path) -> None:
    assert rules.read_decisions(None).on_file == 0
    assert rules.read_decisions(tmp_path / "missing.jsonl").on_file == 0


def test_d7_refuses_a_malformed_line_without_printing_it(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    line = {"record_a": "syn-a", "record_b": "syn-b", "decision": "maybe", "by": "@x", "at": "t"}
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    with pytest.raises(rules.DecisionsError) as caught:
        rules.read_decisions(path)
    assert str(caught.value) == "decisions.jsonl:1: not a decision line"


def test_company_numbers_ignores_people(tmp_path: Path) -> None:
    corpus, _ = members_of(
        tmp_path,
        [
            rec(
                "gbch-off-z",
                "Person",
                "gb_companies_house",
                name="Z",
                registrationNumber="01800000",
                jurisdiction="gb",
            )
        ],
    )
    assert company_numbers(corpus.records["gbch-off-z"]) == frozenset()
