"""Tests for neonradar_ingest.sources.lists.common (PHASE-2.md M2.6a). Synthetic values only."""

from __future__ import annotations

import pytest

from neonradar_ingest.sources.lists.common import (
    check_bounds,
    extract_leis,
    join_name,
    parse_dmy,
    parse_iso,
    partial_date,
    period_dates,
    sanction_id,
    split_values,
    uk_company_numbers,
    un_references,
    year_range,
)

# A synthetic LEI with valid ISO 17442 check digits (prefix SYN0, as in M2.9).
SYN_LEI = "SYN0000000000000AB65"


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((1970, 5, 17), "1970-05-17"),
        (("1970", "05", "17"), "1970-05-17"),
        ((1970, 5, None), "1970-05"),
        ((1970, 0, 0), "1970"),
        ((1970, None, 17), "1970"),
        ((1970, 13, 1), "1970"),
        ((1970, 2, 30), "1970-02"),
        ((2024, 2, 29), "2024-02-29"),
        ((2023, 2, 29), "2023-02"),
        ((1799, 1, 1), None),
        ((None, 1, 1), None),
        (("19x0", 1, 1), None),
    ],
)
def test_partial_date(args: tuple[object, ...], expected: str | None) -> None:
    assert partial_date(*args) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("17/05/1970", "1970-05-17"),
        ("7/5/1970", "1970-05-07"),
        ("dd/05/1970", "1970-05"),
        ("DD/MM/1970", "1970"),
        ("dd/mm/1970", "1970"),
        ("00/00/1970", "1970"),
        ("00/05/1970", "1970-05"),
        ("1970", "1970"),
        ("31/02/1970", "1970-02"),
        ("05/17/1970", "1970"),  # never month first: 17 is not a month
        ("", None),
        ("circa 1970", None),
        (None, None),
    ],
)
def test_parse_dmy(text: str | None, expected: str | None) -> None:
    assert parse_dmy(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1970-05-17", "1970-05-17"),
        ("1970-05-17-04:00", "1970-05-17"),
        ("1970-05-17+02:00", "1970-05-17"),
        ("2026-10-15T10:20:30.123Z", "2026-10-15"),
        ("1970-05", "1970-05"),
        ("1970", "1970"),
        ("17/05/1970", None),
        ("", None),
    ],
)
def test_parse_iso(text: str, expected: str | None) -> None:
    assert parse_iso(text) == expected


def test_year_range() -> None:
    assert year_range(1960, 1962) == ["1960", "1961", "1962"]
    assert year_range("1960", "1965") == ["1960", "1961", "1962", "1963", "1964", "1965"]
    assert year_range(1950, 1960) == [str(y) for y in range(1950, 1961)]  # X5 sees 1955 too
    assert len(year_range(1950, 1970)) == 21  # a span of 20 years: every year
    assert year_range(1950, 1971) == []  # wider: no birth date at all
    assert year_range(1962, 1960) == ["1960", "1961", "1962"]
    assert year_range(1960, None) == ["1960"]
    assert year_range(None, None) == []


def test_period_dates() -> None:
    assert period_dates((1970, 5, 17), (1970, 5, 17)) == ["1970-05-17"]
    assert period_dates((1970, 1, 1), (1970, 12, 31)) == ["1970"]
    assert period_dates((1970, 2, 1), (1970, 2, 28)) == ["1970-02"]
    assert period_dates((1972, 2, 1), (1972, 2, 29)) == ["1972-02"]
    assert period_dates((1970, 1, 1), (1971, 12, 31)) == ["1970", "1971"]
    assert period_dates((1970, 3, 1), (1970, 6, 30)) == ["1970"]
    assert period_dates((1940, 1, 1), (1975, 12, 31)) == []
    assert period_dates((None, None, None), (None, None, None)) == []


def test_join_and_split() -> None:
    assert join_name(["Petra", None, "  ", "Anne  Marie", "MARLOWE"]) == "Petra Anne Marie MARLOWE"
    assert join_name([None, ""]) is None
    assert split_values("Asset freeze|Travel ban| |") == ["Asset freeze", "Travel ban"]
    assert split_values("a; b|c", ";|") == ["a", "b", "c"]
    assert split_values(None) == []


def test_extract_leis() -> None:
    assert extract_leis(f"LEI: {SYN_LEI}; INN 7700000000") == [SYN_LEI]
    assert extract_leis(SYN_LEI.lower()) == [SYN_LEI]
    assert extract_leis("SYN0000000000000AB66") == []  # wrong check digits
    assert extract_leis(None) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("UK Company Number 01234567", ["01234567"]),
        ("Companies House number: SC123456", ["SC123456"]),
        ("Registered in England and Wales under number 07654321", ["07654321"]),
        ("Registered in England and Wales with company number 07654321", ["07654321"]),
        ("England and Wales Company Registration Number: 07654321", ["07654321"]),
        ("Registered in Scotland, No. SC123456", ["SC123456"]),
        ("UK Reg. No. 01234567", ["01234567"]),
        ("Company number 01234567 (UK)", ["01234567"]),
        ("Company number 01234567 (United Kingdom)", ["01234567"]),
        ("Company No: 01234567 (England and Wales)", ["01234567"]),
        ("Company no. 01234567, registered in England", ["01234567"]),
        ("United Kingdom, Company Number NI612345", ["NI612345"]),
        ("Company registration number (UK) OC301234", ["OC301234"]),
        ("Registration number (UK): 01234567", ["01234567"]),
        ("UK company number R0012345", ["R0012345"]),
        ("Company Number 12345678 (Cyprus), UK Company Number 87654321", ["87654321"]),
        ("Company Number 12345678 (Cyprus); UK Company Number 87654321", ["87654321"]),
        ("Company Number 12345678 (Cyprus)", []),
        ("UK-based, registered in Cyprus as number 12345678", []),
        ("Subsidiary of a UK group, incorporated in Malta, company 12345678", []),
        ("Parent company: UK Company Number 01234567", []),
        ("Owned by a UK company, company number 01234567 (UK)", []),
        ("UK company 01234567", []),  # no number label
        ("Registered in England and Wales; Tax number 01234567", []),
        ("Registered in England and Wales, number of employees 01234567", []),
        ("UK VAT number 12345678", []),
        ("Registration Number HE123456", []),
        ("UK Company Number HE123456", []),  # HE is not a Companies House prefix
        ("UK Company Number SY000101", []),  # SY is the synthetic prefix, not Companies House
        ("OGRN 1027700000000; INN 7700000000; KPP 770001001", []),
        ("Ukraine, EDRPOU 12345678", []),
        ("GBP 12345678", []),
        ("New England office 12345678", []),
        ("UK office; Tax ID 12345678", []),
        ("UK Company Number 1234567", []),  # seven digits are not taken from free text
        ("UK Company Number 123456789", []),
        ("UK Company Number 01234567 and 07654321", ["01234567"]),
        ("", []),
        (None, []),
    ],
)
def test_uk_company_numbers(text: str | None, expected: list[str]) -> None:
    assert uk_company_numbers(text) == expected


def test_un_references_and_ids() -> None:
    assert un_references(["QDi.123", " qdi.123. ", None, "KPe.001"]) == ["KPE.001", "QDI.123"]
    first = sanction_id("uksl", "uksl-g101", "SYN0001")
    assert first == sanction_id("uksl", "uksl-g101", "SYN0001")
    assert first != sanction_id("uksl", "uksl-g101", "SYN0002")
    assert first.startswith("uksl-sanction-")
    assert len(first) == len("uksl-sanction-") + 20


def test_check_bounds() -> None:
    bounds = {"eu_fsf": {"Person": [3400, 8000], "Organization": [970, 2300]}}
    assert check_bounds("eu_fsf", {"Person": 4398, "Organization": 1728}, bounds) == []
    problems = check_bounds("eu_fsf", {"Person": 12}, bounds)
    assert problems == [
        "unexpected size for eu_fsf: Organization 0, expected 970 to 2300; "
        "the format may have changed",
        "unexpected size for eu_fsf: Person 12, expected 3400 to 8000; the format may have changed",
    ]
    assert check_bounds("us_ofac_sdn", {"Person": 1}, bounds) == []
