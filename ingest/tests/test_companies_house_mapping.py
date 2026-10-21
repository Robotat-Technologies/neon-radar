"""Companies House to C1 mapping (M1.8a step 5) against synthetic response bodies."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from neonradar_contracts.records import validate_batch, validate_record
from neonradar_ingest.sources.companies_house.mapping import (
    Mapper,
    classify_nature,
    normalise_company_number,
    share_band,
)

FIXTURES = Path(__file__).parent / "fixtures" / "companies_house"
NUMBER = "SYN00001"
COMPANY = "gbch-co-SYN00001"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def mapped() -> Mapper:
    mapper = Mapper()
    assert mapper.add_company(load("company-SYN00001.json")) == COMPANY
    for page in ("officers-SYN00001-1.json", "officers-SYN00001-2.json"):
        for item in load(page)["items"]:
            mapper.add_officer(item, COMPANY, NUMBER)
    for item in load("psc-SYN00001.json")["items"]:
        mapper.add_psc(item, COMPANY, NUMBER)
    return mapper


def psc(kind: str, natures: list[str], native: str = "SYNpsc-x") -> dict[str, Any]:
    return {
        "kind": kind,
        "name": "Synthetic Name",
        "natures_of_control": natures,
        "links": {"self": f"/company/{NUMBER}/persons-with-significant-control/x/{native}"},
    }


def officer(role: str, name: str = "ULVARAZI, Nadim", **extra: Any) -> dict[str, Any]:
    links = {"self": "/company/SYN00001/appointments/SYNapp9", "officer": {
        "appointments": "/officers/SYNoff-9/appointments"}}  # fmt: skip
    return {"name": name, "officer_role": role, "links": links, **extra}


def test_fixture_maps_to_the_expected_records() -> None:
    assert mapped().records() == load("records-SYN00001.expected.json")


def test_mapped_records_pass_the_c1_validator_in_strict_mode() -> None:
    records = mapped().records()
    issues = [issue for record in records for issue in validate_record(record)]
    assert issues + validate_batch(records, strict=True) == []


def test_counts_for_the_spike_report() -> None:
    stats = mapped().stats
    assert (stats.appointments, stats.corporate_appointments, stats.natural_appointments) == (
        5,
        1,
        4,
    )
    assert stats.surname_first_names == 4
    assert stats.skipped == {"psc:super-secure-person-with-significant-control": 1}
    assert stats.natures == {"ownership": 2, "control:voting": 1, "control:appointment": 1,
                             "control:influence": 2}  # fmt: skip
    assert stats.dropped == {"Person.nationality": 1}  # "Not Specified"
    assert stats.identity_verification["officers.identity_verification_details"] == 2
    assert stats.identity_verification["psc.appointment_verification_start_on"] == 2


def test_identity_verification_details_are_never_mapped() -> None:
    text = json.dumps(mapped().records())
    assert "verification" not in text
    assert "2025-11-20" not in text  # an appointment_verification_start_on value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("617987", "00617987"), (" sc045551 ", "SC045551"), ("01800000", "01800000"),
     ("oe 000002", "OE000002")],
)  # fmt: skip
def test_company_numbers_are_normalised(raw: str, expected: str) -> None:
    assert normalise_company_number(raw) == expected


@pytest.mark.parametrize(
    ("nature", "kind", "band"),
    [
        ("ownership-of-shares-25-to-50-percent", ("ownership", None), (25.0, 50.0)),
        ("ownership-of-shares-75-to-100-percent-as-firm", ("ownership", None), (75.0, 100.0)),
        ("right-to-share-surplus-assets-50-to-75-percent-limited-liability-partnership",
         ("ownership", None), (50.0, 75.0)),
        ("part-right-to-share-surplus-assets-25-to-50-percent-as-trust", ("ownership", None),
         (25.0, 50.0)),
        ("ownership-of-shares-more-than-25-percent-registered-overseas-entity",
         ("ownership", None), (25.0, 100.0)),
        ("voting-rights-25-to-50-percent-limited-liability-partnership", ("control", "voting"),
         (25.0, 50.0)),
        ("right-to-appoint-and-remove-person-as-firm", ("control", "appointment"), None),
        ("right-to-appoint-and-remove-members-limited-liability-partnership",
         ("control", "appointment"), None),
        ("significant-influence-or-control-as-trust", ("control", "influence"), None),
        ("registered-owner-as-nominee-person-england-wales-registered-overseas-entity",
         ("unmapped", None), None),
    ],
)  # fmt: skip
def test_natures_of_control_are_classified(
    nature: str, kind: tuple[str, str | None], band: tuple[float, float] | None
) -> None:
    assert classify_nature(nature) == kind
    assert share_band(nature) == band


@pytest.mark.parametrize(
    "kind",
    ["legal-person-person-with-significant-control", "legal-person-with-significant-control"],
)
def test_both_spellings_of_the_legal_person_kind_map_to_a_legal_entity(kind: str) -> None:
    mapper = Mapper()
    mapper.add_psc(psc(kind, ["significant-influence-or-control"]), COMPANY, NUMBER)
    schemata = {record["schema"] for record in mapper.records()}
    assert schemata == {"LegalEntity", "Control"}


def test_unknown_kinds_and_unmapped_natures_are_skipped_and_counted() -> None:
    mapper = Mapper()
    statement = psc("persons-with-significant-control-statement", [], "SYNpsc-1")
    mapper.add_psc(statement, COMPANY, NUMBER)
    nominee = "registered-owner-as-nominee-person-scotland-registered-overseas-entity"
    mapper.add_psc(psc("individual-beneficial-owner", [nominee], "SYNpsc-2"), COMPANY, NUMBER)
    mapper.add_psc({"kind": "individual-person-with-significant-control"}, COMPANY, NUMBER)
    assert mapper.stats.skipped == {
        "psc:persons-with-significant-control-statement": 1,
        f"nature:{nominee}": 1,
        "psc-without-id": 1,
    }
    assert [record["schema"] for record in mapper.records()] == ["Person"]


def test_officer_ids_use_make_id_and_keep_the_raw_id() -> None:
    mapper = Mapper()
    item = officer("director")
    item["links"]["officer"]["appointments"] = "/officers/Ab_c-D/appointments"
    mapper.add_officer(item, COMPANY, NUMBER)
    person = next(r for r in mapper.records() if r["schema"] == "Person")
    assert person["id"] == "gbch-off-Ab.c-D"
    assert person["nr"]["source_ref"] == "Ab_c-D"


def test_officers_without_an_officer_link_are_skipped() -> None:
    mapper = Mapper()
    mapper.add_officer({"name": "ULVARAZI, Nadim", "officer_role": "director"}, COMPANY, NUMBER)
    assert mapper.records() == []
    assert mapper.stats.skipped == {"officer-without-id-or-role": 1}


def test_corporate_officers_without_a_company_identification_are_legal_entities() -> None:
    mapper = Mapper()
    ident = {"identification_type": "other-corporate-body-or-firm", "legal_form": "Partnership"}
    mapper.add_officer(officer("corporate-director", "SYN FIRM", identification=ident),
                       COMPANY, NUMBER)  # fmt: skip
    entity = next(r for r in mapper.records() if r["schema"] != "Directorship")
    assert entity["schema"] == "LegalEntity"
    assert entity["properties"]["legalForm"] == ["Partnership"]


def test_names_unescape_html_entities_and_count_the_name_format() -> None:
    mapper = Mapper()
    mapper.add_officer(officer("director", "Nadim Ulvarazi"), COMPANY, NUMBER)
    mapper.add_officer(officer("nominee-secretary", "O&#39;ULVARAZI, Nadim"), COMPANY, NUMBER)
    names = [r["properties"]["name"] for r in mapper.records() if r["schema"] == "Person"]
    assert names == [["Nadim Ulvarazi", "O'ULVARAZI, Nadim"]]  # one officer id, two names
    assert mapper.stats.surname_first_names == 1
    nominee = {
        r["properties"]["role"][0]: r["nr"]["is_nominee"]
        for r in mapper.records()
        if r["schema"] == "Directorship"
    }
    assert nominee == {"director": False, "nominee-secretary": True}


def test_a_jurisdiction_outside_the_uk_is_counted_not_mapped() -> None:
    mapper = Mapper()
    mapper.add_company(
        {"company_number": "SYN00009", "company_name": "SYN", "jurisdiction": "noneu"}
    )
    (company,) = mapper.records()
    assert "jurisdiction" not in company["properties"]
    assert mapper.stats.unmapped_fields == {"company.jurisdiction=noneu": 1}


def test_care_of_is_left_out_of_the_address() -> None:
    assert load("company-SYN00001.json")["registered_office_address"]["care_of"]
    assert "CARE OF" not in json.dumps(mapped().records())


def test_overlapping_pages_count_and_map_each_appointment_and_psc_once() -> None:
    mapper = mapped()
    before = (copy.deepcopy(mapper.stats), mapper.records())
    for item in load("officers-SYN00001-2.json")["items"]:  # page 2 again
        mapper.add_officer(item, COMPANY, NUMBER)
    for item in load("psc-SYN00001.json")["items"]:
        mapper.add_psc(item, COMPANY, NUMBER)
    assert (mapper.stats, mapper.records()) == before


def test_the_number_asked_for_stands_in_for_a_missing_company_number() -> None:
    assert Mapper().add_company({"company_name": "SYN"}, "syn00009") == "gbch-co-SYN00009"
    with pytest.raises(ValueError, match="no company_number"):
        Mapper().add_company({"company_name": "SYN"})
