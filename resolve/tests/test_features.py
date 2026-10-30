"""Members and the feature tables of PHASE-2.md 7.1.5, on records built here."""

from __future__ import annotations

from pathlib import Path

import duckdb
from nr_resolve_support import members_of, rec, syn

from neonradar_resolve import features
from neonradar_resolve.feature_schema import ORG_SCHEMA, PERSON_SCHEMA, RARE_NAME_MAX

VALID_LEI = "SYN000TESTLEI0000134"


def _tables(tmp_path: Path, items: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    corpus, members = members_of(tmp_path, items)  # type: ignore[arg-type]
    person, org = features.feature_tables(corpus, members)
    rows = {r["unique_id"]: r for r in person.to_pylist()}
    orgs = {r["unique_id"]: r for r in org.to_pylist()}
    return members, rows, orgs, person, org


def test_gleif_number_counts_only_in_the_companies_house_form(tmp_path: Path) -> None:
    items = [
        rec(
            "gleif-A",
            "Company",
            "gleif_lei",
            name="Example Holder Ltd",
            registrationNumber="SC999901",
            jurisdiction="GB",
        ),
        rec(
            "gleif-B",
            "Company",
            "gleif_lei",
            name="Example Holder Ltd",
            registrationNumber="9999901",
            jurisdiction="GB",
        ),
        rec(
            "gleif-C",
            "Company",
            "gleif_lei",
            name="Example Holder Ltd",
            registrationNumber="SC999901",
            jurisdiction="IE",
        ),
    ]
    members, _, orgs, _, _ = _tables(tmp_path, items)
    assert members["gleif-A"].company_numbers == {"SC999901"}
    assert members["gleif-B"].company_numbers == frozenset()  # another registration authority
    assert members["gleif-C"].company_numbers == frozenset()
    assert orgs["gleif-B"]["registration_numbers"] == ["reg:gb:9999901"]


def test_list_source_of_a_synthetic_list_record(tmp_path: Path) -> None:
    items = [
        syn("syn-p-1", "Person", "list", name="Testa Example", topics="sanction"),
        rec(
            "syn-sanction-1",
            "Sanction",
            "nr_synthetic",
            {"synthetic": True, "synthetic_kind": "list"},
            entity="syn-p-1",
            authority="Synthetic Authority C",
        ),
    ]
    members, *_ = _tables(tmp_path, items)
    assert members["syn-p-1"].list_source == "nr_synthetic:Synthetic Authority C"
    assert members["syn-p-1"].synthetic and members["syn-p-1"].priority == 10


def test_member_fields(tmp_path: Path) -> None:
    items = [
        rec(
            "gbch-off-test1",
            "Person",
            "gb_companies_house",
            name="EXAMPLE, Testa Maria",
            alias="Testa Exampel",
            weakAlias="Tex",
            birthDate=["1971-04-12", "1971-04", "bad"],
        ),
        rec(
            "gleif-X",
            "Company",
            "gleif_lei",
            name="Example Holder Ltd",
            leiCode=[VALID_LEI.lower(), "BAD"],
        ),
    ]
    members, *_ = _tables(tmp_path, items)
    person = members["gbch-off-test1"]
    assert (person.kind, person.priority, person.entity_class, person.synthetic) == (
        "registry",
        1,
        "person",
        False,
    )
    assert person.birth_dates == {"1971-04-12", "1971-04"}
    assert person.name_keys == {"example maria testa", "exampel testa"}  # never from weakAlias
    assert members["gleif-X"].leis == {VALID_LEI}
    assert members["gleif-X"].name_keys == {"example holder"}


def test_person_columns(tmp_path: Path) -> None:
    items = [
        rec(
            "gbch-off-test2",
            "Person",
            "gb_companies_house",
            name="EXAMPLE, Testa Maria",
            alias="Testa Exampel",
            weakAlias="Tex Ample",
            birthDate=["1971-04-12", "1973"],
            nationality="British",
            country="Ireland",
            addressEntity="gbch-addr-1",
            address="1 Test Road, London, N1 7GU",
            passportNumber="sy 123 456",
            idNumber="ab12",
        ),
        rec("gbch-addr-1", "Address", "gb_companies_house", postalCode="ec1a1bb"),
        rec(
            "gbch-co-99999901",
            "Company",
            "gb_companies_house",
            name="Example Holder Ltd",
            registrationNumber="9999-9901",
            jurisdiction="gb",
        ),
        rec("gbch-psc-test9", "Company", "gb_companies_house", name="Other Holder Ltd"),
        rec(
            "gbch-directorship-1",
            "Directorship",
            "gb_companies_house",
            director="gbch-off-test2",
            organization="gbch-co-99999901",
        ),
        rec(
            "gbch-ownership-1",
            "Ownership",
            "gb_companies_house",
            owner="gbch-off-test2",
            asset="gbch-psc-test9",
        ),
    ]
    _, rows, _, _, _ = _tables(tmp_path, items)
    row = rows["gbch-off-test2"]
    assert row["name_key"] == "example maria testa"
    assert (row["forename"], row["surname"], row["initial"]) == ("testa", "example", "t")
    assert row["name_tokens"] == ["exampel", "example", "maria", "testa"]  # not "tex", not "ample"
    assert row["skeletons"] and len(row["skeletons"]) <= features.LIST_CAP
    assert row["birth_full"] == ["1971-04-12"]
    assert row["birth_ym"] == ["1971-04"]
    assert row["birth_years"] == [1971, 1973]
    assert (row["birth_year_min"], row["birth_ym_min"]) == (1971, "1971-04")
    assert row["countries"] == ["gb", "ie"]
    assert row["postcode"] == "EC1A 1BB"  # addressEntity first
    assert row["linked_orgs"] == ["gbch-psc-test9", "uk:99999901"]
    assert row["identifiers"] == ["id:AB12", "passport:SY123456"]
    assert row["synthetic"] is False and row["name_key_rare"] == row["name_key"]


def test_every_empty_list_is_null(tmp_path: Path) -> None:
    items = [
        rec("gbch-off-bare", "Person", "gb_companies_house", name="Testa"),
        rec("gbch-psc-bare", "Company", "gb_companies_house", name="Ltd"),
        rec("icij-bare", "LegalEntity", "icij_offshore_leaks"),
    ]
    _, rows, orgs, person, org = _tables(tmp_path, items)
    assert set(rows) == {"gbch-off-bare", "icij-bare"} and set(orgs) == {
        "gbch-psc-bare",
        "icij-bare",
    }
    for table, schema in ((person, PERSON_SCHEMA), (org, ORG_SCHEMA)):
        assert table.schema == schema
        for row in table.to_pylist():
            assert all(v != [] for v in row.values()), row["unique_id"]
    bare = rows["icij-bare"]
    assert bare["name_key"] is None and bare["name_tokens"] is None and bare["birth_years"] is None
    assert bare["forename"] is None and bare["initial"] is None
    assert rows["gbch-off-bare"]["forename"] is None  # the source does not say which part is which
    assert (
        orgs["gbch-psc-bare"]["name_key"] is None and orgs["gbch-psc-bare"]["name_prefix"] is None
    )


def test_org_columns(tmp_path: Path) -> None:
    items = [
        rec(
            "gbch-co-test-1",
            "Company",
            "gb_companies_house",
            name="The Example Holder Limited",
            alias="Example Holder & Sons Ltd",
            previousName="Example Trading Ltd",
            registrationNumber="SC999901",
            jurisdiction="gb-sct",
            leiCode=VALID_LEI,
            incorporationDate="2001-02-03",
            address="2 Test Road, Leeds, LS1 2AB",
        ),
    ]
    _, _, orgs, _, _ = _tables(tmp_path, items)
    row = orgs["gbch-co-test-1"]
    assert row["name_key"] == "example holder" and row["name_prefix"] == "exam"
    assert row["aliases"] == ["example holder", "example holder and sons", "example trading"]
    assert row["ch_same_as"] == "EXAMPLEHOLDER"
    assert row["name_tokens"] == ["example", "holder"]
    assert row["jurisdiction"] == "gb"
    assert row["registration_numbers"] == [f"lei:{VALID_LEI}", "uk:SC999901"]
    assert row["incorporation_year"] == 2001
    assert row["postcode"] == "LS1 2AB"
    assert row["legal_forms"] == ["llc"]


def test_name_key_rare_is_null_for_common_keys(tmp_path: Path) -> None:
    common = [
        rec(f"gbch-off-c{i}", "Person", "gb_companies_house", name="Testa Example")
        for i in range(RARE_NAME_MAX + 1)
    ]
    rare = [rec("gbch-off-r", "Person", "gb_companies_house", name="Testa Quillmarsh")]
    _, rows, _, _, _ = _tables(tmp_path, common + rare)
    assert rows["gbch-off-c0"]["name_key_rare"] is None
    assert rows["gbch-off-r"]["name_key_rare"] == "quillmarsh testa"


def test_write_features(tmp_path: Path) -> None:
    items = [
        rec("gbch-off-w", "Person", "gb_companies_house", name="Testa Example"),
        rec("gbch-psc-w", "Company", "gb_companies_house", name="Example Holder Ltd"),
    ]
    _, _, _, person, org = _tables(tmp_path / "in", items)
    path = tmp_path / features.FEATURES_FILE
    features.write_features(path, person, org, tmp_path / "spill")
    with duckdb.connect(str(path), read_only=True) as con:
        assert con.execute("SELECT count(*) FROM person_features").fetchone() == (1,)
        assert con.execute("SELECT unique_id FROM org_features").fetchall() == [("gbch-psc-w",)]
        names = [r[0] for r in con.execute("DESCRIBE person_features").fetchall()]
    assert names == PERSON_SCHEMA.names


def test_name_symbols_and_the_postcode_from_address_text(tmp_path: Path) -> None:
    items = [
        rec(
            "gbch-off-sym",
            "Person",
            "gb_companies_house",
            name="Mohammed Testa",
            address="3 Test Road, Leeds, ls12ab",
        )
    ]
    _, rows, _, _, _ = _tables(tmp_path, items)
    assert "Q5837762" in rows["gbch-off-sym"]["name_symbols"]  # the Mohammed name group
    assert rows["gbch-off-sym"]["postcode"] == "LS1 2AB"


def test_name_only_records_hold_names_and_at_most_one_country(tmp_path: Path) -> None:
    """OD-27: a record with names and one country (or a jurisdiction) is name-only; a birth
    year, a postcode, an identifier, a linked organisation, an incorporation year, a
    registration number, an LEI or a second country is evidence. A legal entity has a row in
    both tables and is name-only only when both rows are, with one country between them."""
    items = [
        syn("syn-p-1", "Person", "leak", name="Testa Example", country="GB"),
        syn("syn-p-2", "Person", "leak", name="Testa Example", birthDate="1971"),
        syn("syn-p-3", "Person", "list", name="Testa Example", passportNumber="X1"),
        syn("syn-p-4", "Person", "registry", name="Testa Example", address="1 Test Way QQ1 1QQ"),
        syn("syn-p-5", "Person", "registry", name="Testa Example"),
        syn("syn-d-1", "Directorship", "registry", director="syn-p-5", organization="syn-o-1"),
        syn("syn-p-6", "Person", "leak", name="Testa Example", nationality=["GB", "FR"]),
        syn("syn-p-7", "Person", "leak", name="Testa Example", nationality="GB", country="GB"),
        syn("syn-o-1", "Company", "list", name="Test Holder Ltd", jurisdiction="GB"),
        syn("syn-o-2", "Company", "list", name="Test Holder Ltd", incorporationDate="2001"),
        syn("syn-o-3", "Company", "list", name="Test Holder Ltd", registrationNumber="SY000001"),
        syn("syn-o-4", "Organization", "list", name="Test Holder Ltd", leiCode=VALID_LEI),
        syn("syn-l-1", "LegalEntity", "leak", name="Test Holder Ltd", country="GB"),
        syn("syn-l-2", "LegalEntity", "leak", name="Test Holder Ltd", incorporationDate="2001"),
        syn("syn-l-3", "LegalEntity", "leak", name="Test Holder Ltd", country="GB",
            jurisdiction="FR"),
    ]  # fmt: skip
    _, rows, orgs, person, org = _tables(tmp_path, items)
    assert rows["syn-p-4"]["postcode"] == "QQ1 1QQ"
    assert rows["syn-p-5"]["linked_orgs"] == ["syn-o-1"]
    assert orgs["syn-o-3"]["registration_numbers"] and orgs["syn-o-4"]["registration_numbers"]
    assert orgs["syn-o-4"]["registration_numbers"] == [f"lei:{VALID_LEI}"]
    assert orgs["syn-o-1"]["legal_forms"] and orgs["syn-o-1"]["jurisdiction"] == "gb"
    assert features.name_only(person, org) == {"syn-p-1", "syn-p-7", "syn-o-1", "syn-l-1"}


def test_every_feature_column_is_a_name_a_country_or_evidence() -> None:
    """OD-27: a column added to a feature schema counts as evidence until it is listed as a
    name or a country, so a new column can never move true pairs out of the gate unseen."""
    for schema, names, country, evidence in zip(
        (PERSON_SCHEMA, ORG_SCHEMA),
        features.NAME_COLUMNS,
        features.COUNTRY_COLUMNS,
        features.EVIDENCE_COLUMNS,
        strict=True,
    ):
        assert set(names) | {country} <= set(schema.names)
        assert sorted([*names, country, *evidence]) == sorted(schema.names)
    assert features.EVIDENCE_COLUMNS == (
        ("birth_full", "birth_ym", "birth_years", "birth_year_min", "birth_ym_min", "postcode",
         "linked_orgs", "identifiers"),
        ("registration_numbers", "incorporation_year", "postcode"),
    )  # fmt: skip
