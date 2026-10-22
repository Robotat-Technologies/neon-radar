"""Deterministic rules D1 to D6 and decisions D7 (PHASE-2.md 7.1.2), on records built here."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from nr_resolve_support import members_of, rec, syn

from neonradar_resolve import rules
from neonradar_resolve.features import company_numbers

FIXTURES = Path(__file__).parent / "fixtures"
VALID_LEI, INVALID_LEI = "SYN000TESTLEI0000134", "SYN000TESTLEI0000130"


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
        ("sc-999901", "SC999901"),
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
            registrationNumber="99999901",
            jurisdiction="cy",
        ),
        rec(
            "gbch-co-99999901",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="9999 9901",
            jurisdiction="vg",
        ),
        rec(
            "gbch-psc-test4",
            "Person",
            "gb_companies_house",
            name="Testa Example",
            registrationNumber="99999901",
            jurisdiction="gb",
        ),
    ]
    _, members = members_of(tmp_path, items)
    assert members["gbch-psc-test3"].company_numbers == frozenset()  # not a UK record
    assert members["gbch-co-99999901"].company_numbers == {"99999901"}  # always for gbch-co-
    assert members["gbch-psc-test4"].company_numbers == frozenset()


def test_d1_links_to_the_companies_house_record_when_the_run_has_it(tmp_path: Path) -> None:
    items = [
        _company("gbch-co-99999901", "99999901"),
        _company("gbch-psc-test5", "9999 9901"),
        _company("gbch-psc-test6", "99999901"),
    ]
    assert _links(tmp_path, items) == [
        ("D1", "gbch-co-99999901", "gbch-psc-test5"),
        ("D1", "gbch-co-99999901", "gbch-psc-test6"),
    ]


def test_d1_without_the_companies_house_record_links_every_pair(tmp_path: Path) -> None:
    items = [_company(f"gbch-psc-test{i}", "SC999901") for i in (7, 8, 9)]
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
        officer("gbch-off-a", "999999990001"),
        officer("gbch-off-b", "999999999999"),
        officer("gbch-off-c", "999999980001"),
        officer("gbch-off-d", "9999999"),
        rec(
            "gbch-co-99999901",
            "Company",
            "gb_companies_house",
            {"ch_person_number": "999999990001"},
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
        listed("eufsf-test-1", "eu_fsf"),
        listed("eufsf-test-2", "eu_fsf"),
        sanction("uksl-sanction-1", "gb_fcdo_sanctions", "uksl-un-zzi.1", "ZZi.1"),
        sanction("eufsf-sanction-1", "eu_fsf", "eufsf-test-1", "zzi.1."),
        sanction("eufsf-sanction-2", "eu_fsf", "eufsf-test-2", "ZZi.1"),
    ]
    assert _links(tmp_path, items) == [
        ("D4", "eufsf-test-1", "uksl-un-zzi.1"),
        ("D4", "eufsf-test-2", "uksl-un-zzi.1"),
    ]


def test_d5_same_native_id_within_one_dataset(tmp_path: Path) -> None:
    items = [
        rec(
            "icij-test-1",
            "LegalEntity",
            "icij_offshore_leaks",
            {"source_ref": "test-90001"},
            name="X",
        ),
        rec(
            "icij-test-2",
            "LegalEntity",
            "icij_offshore_leaks",
            {"source_ref": "test-90001"},
            name="Y",
        ),
        rec("ofac-test-3", "Person", "us_ofac_sdn", {"source_ref": "test-90001"}, name="X"),
    ]
    assert _links(tmp_path, items) == [("D5", "icij-test-1", "icij-test-2")]


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
    assert (first.method, first.rule, first.reviewers) == ("human", "D7", {"@example-one"})
    assert same[("syn-test-b1", "syn-test-b2")].reviewers == {"@example-one", "@example-two"}
    assert decisions.different == [("syn-test-c1", "syn-test-c2")]


def test_d7_without_a_file_reads_nothing(tmp_path: Path) -> None:
    assert rules.read_decisions(None).on_file == 0
    assert rules.read_decisions(tmp_path / "missing.jsonl").on_file == 0


def test_d7_refuses_a_malformed_line_without_printing_it(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    line = {
        "record_a": "syn-a",
        "record_b": "syn-b",
        "decision": "maybe",
        "by": "@example-x",
        "at": "t",
    }
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
                registrationNumber="99999901",
                jurisdiction="gb",
            )
        ],
    )
    assert company_numbers(corpus.records["gbch-off-z"]) == frozenset()


def _decision_file(tmp_path: Path, lines: list[dict[str, str]]) -> Path:
    path = tmp_path / "decisions.jsonl"
    base = {"record_a": "syn-a", "record_b": "syn-b", "note": "synthetic test line"}
    path.write_text("".join(json.dumps(base | line) + "\n" for line in lines), encoding="utf-8")
    return path


def test_d7_handles_ignore_case_and_times_compare_in_utc(tmp_path: Path) -> None:
    path = _decision_file(
        tmp_path,
        [
            {"decision": "same", "by": "@Example-One", "at": "2026-11-02T09:00:00Z"},
            {"decision": "same", "by": " @EXAMPLE-ONE ", "at": "2026-11-02T09:05:00Z"},
        ],
    )
    [link] = rules.read_decisions(path).same
    assert link.reviewers == {"@example-one"}  # one person, however the handle is written
    path = _decision_file(
        tmp_path,
        [
            {"decision": "different", "by": "@example-two", "at": "2026-11-02T10:00:00Z"},
            {
                "decision": "same",
                "by": "@example-one",
                "at": "2026-11-02T10:30:00+01:00",
            },  # 09:30 UTC
        ],
    )
    assert rules.read_decisions(path).different == [("syn-a", "syn-b")]


@pytest.mark.parametrize(
    "line",
    [
        {"decision": "same", "by": "@TODO", "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "one", "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "@one.", "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "@ one", "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "@\u043ene", "at": "2026-11-02T09:00:00Z"},  # Cyrillic o
        {"decision": "same", "by": "@one-", "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "@\u212aelvin", "at": "2026-11-02T09:00:00Z"},  # Kelvin sign
        {"decision": "same", "by": "@" + "a" * 40, "at": "2026-11-02T09:00:00Z"},
        {"decision": "same", "by": "@example-one", "at": "2026-11-02T09:00:00"},
        {"decision": "same", "by": "@example-one", "at": "yesterday"},
    ],
)
def test_d7_refuses_bad_handles_and_times_without_offset(
    tmp_path: Path, line: dict[str, str]
) -> None:
    with pytest.raises(rules.DecisionsError):
        rules.read_decisions(_decision_file(tmp_path, [line]))


def test_senior_reviewers_drop_placeholders() -> None:
    from neonradar_resolve.config import load_config

    config, _ = load_config(Path(__file__).parents[1] / "config" / "er.yaml")
    seniors = config.cluster_config(["@TODO", "@Senior", " ", "senior2"]).senior_reviewers
    assert seniors == {"@senior"}


def test_d7_on_a_real_profile_accepts_listed_reviewers_only(tmp_path: Path) -> None:
    """Fail closed: an unlisted handle stops the run (people.er_labellers, er_senior_reviewers)."""
    line = {"decision": "same", "by": "@Example-One", "at": "2026-11-02T09:00:00Z"}
    path = _decision_file(tmp_path, [line])
    [link] = rules.read_decisions(path, frozenset({"@example-one"})).same
    assert link.reviewers == {"@example-one"}
    with pytest.raises(rules.DecisionsError) as caught:
        rules.read_decisions(path, frozenset({"@example-two"}))
    assert "not in people.er_labellers" in str(caught.value)
    assert "example-one" not in str(caught.value).lower()  # the handle is not printed


def test_only_run_py_calls_the_clustering() -> None:
    """`cluster.resolve` runs only behind the decision guard in run.py (G1)."""
    root = Path(__file__).parents[2]
    files = [*root.glob("resolve/src/**/*.py"), *root.glob("cli/src/**/*.py")]
    texts = {p.name: p.read_text(encoding="utf-8") for p in files}
    assert {name for name, text in texts.items() if "cluster.resolve(" in text} == {"run.py"}
    direct = re.compile(r"from neonradar_resolve\.cluster import[^\n]*\bresolve\b")
    assert [name for name, text in texts.items() if direct.search(text)] == []


def test_d6_links_each_address_to_the_smallest_id_of_its_key(tmp_path: Path) -> None:
    def address(rid: str) -> dict[str, object]:
        return rec(rid, "Address", "gb_companies_house", full="12 High St., London, n1 7gu")

    items = [address(f"gbch-addr-{i}") for i in (3, 1, 2, 4)]
    items.append(syn("syn-addr-1", "Address", full="12 High St., London, n1 7gu"))
    assert _links(tmp_path, items) == [
        ("D6", "gbch-addr-1", "gbch-addr-2"),
        ("D6", "gbch-addr-1", "gbch-addr-3"),
        ("D6", "gbch-addr-1", "gbch-addr-4"),
    ]  # the synthetic record keeps to itself (X1)
