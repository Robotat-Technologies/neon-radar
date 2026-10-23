"""Tests for the Companies House natures table and the corporate PSC rule (PHASE-2.md M2.3b)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from neonradar_ingest.sources.companies_house.identification import (
    is_uk,
    names_agree,
    resolve_corporate,
    uk_number,
)
from neonradar_ingest.sources.companies_house.natures import (
    BANDS,
    Band,
    Nature,
    classify,
    combined_band,
    interests,
)

FIXTURE = Path(__file__).parent / "fixtures" / "natures_of_control.txt"


def all_values() -> list[str]:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def test_every_published_value_is_classified() -> None:
    values = all_values()
    assert len(values) == 86
    natures = {v: classify(v) for v in values}
    assert [v for v, n in natures.items() if n is None] == []
    by_family = Counter(
        "llp"
        if v.endswith("-limited-liability-partnership")
        else "overseas"
        if v.endswith("-registered-overseas-entity")
        else "scottish-partnership"
        if v.startswith("part-") or v.startswith("right-to-appoint-and-remove-person")
        else "company"
        for v in values
    )
    assert by_family == {"company": 24, "llp": 24, "scottish-partnership": 12, "overseas": 26}
    by_measure = Counter((n.kind, n.measure) for n in natures.values() if n is not None)
    assert by_measure == {
        ("ownership", "shares"): 5,
        ("ownership", "surplus-assets"): 6,
        ("control", "voting"): 8,
        ("control", "appointment"): 5,
        ("control", "influence"): 4,
        ("control", "nominee"): 6,
        ("control", "trust-or-firm"): 52,
    }


def test_statutory_bands() -> None:
    assert BANDS["25-to-50"] == Band(25, 50, min_exclusive=True, max_exclusive=False)
    assert BANDS["50-to-75"] == Band(50, 75, min_exclusive=True, max_exclusive=True)
    assert BANDS["75-to-100"] == Band(75, 100, min_exclusive=False, max_exclusive=False)
    assert BANDS["more-than-25"] == Band(25, 100, min_exclusive=True, max_exclusive=False)
    assert BANDS["25-to-50"].percentage == "25-50"


@pytest.mark.parametrize(
    ("value", "kind", "measure", "band", "capacity", "held"),
    [
        ("ownership-of-shares-75-to-100-percent", "ownership", "shares", "75-to-100", None, None),
        # control over a trust whose trustees hold the shares: not ownership of the shares
        (
            "ownership-of-shares-25-to-50-percent-as-trust",
            "control",
            "trust-or-firm",
            "25-to-50",
            "trust",
            "shares",
        ),
        (
            "right-to-share-surplus-assets-50-to-75-percent-as-firm-limited-liability-partnership",
            "control",
            "trust-or-firm",
            "50-to-75",
            "firm",
            "surplus-assets",
        ),
        (
            "part-right-to-share-surplus-assets-25-to-50-percent",
            "ownership",
            "surplus-assets",
            "25-to-50",
            None,
            None,
        ),
        # an overseas entity's beneficial owner who is a trustee holds the shares as trustee
        (
            "ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity",
            "ownership",
            "shares",
            "more-than-25",
            "trust",
            None,
        ),
        (
            "ownership-of-shares-more-than-25-percent-as-firm-registered-overseas-entity",
            "control",
            "trust-or-firm",
            "more-than-25",
            "firm",
            "shares",
        ),
        (
            "ownership-of-shares-more-than-25-percent-as-control-over-trust-registered-overseas-entity",
            "control",
            "trust-or-firm",
            "more-than-25",
            "control-over-trust",
            "shares",
        ),
        ("voting-rights-50-to-75-percent", "control", "voting", "50-to-75", None, None),
        (
            "voting-rights-more-than-25-percent-as-trust-registered-overseas-entity",
            "control",
            "voting",
            "more-than-25",
            "trust",
            None,
        ),
        ("right-to-appoint-and-remove-directors", "control", "appointment", None, None, None),
        (
            "right-to-appoint-and-remove-person-as-firm",
            "control",
            "trust-or-firm",
            None,
            "firm",
            "appointment",
        ),
        (
            "significant-influence-or-control-as-trust",
            "control",
            "trust-or-firm",
            None,
            "trust",
            "influence",
        ),
        (
            "registered-owner-as-nominee-another-entity-scotland-registered-overseas-entity",
            "control",
            "nominee",
            None,
            None,
            None,
        ),
    ],
)
def test_classify(
    value: str,
    kind: str,
    measure: str,
    band: str | None,
    capacity: str | None,
    held: str | None,
) -> None:
    nature = classify(value)
    assert nature is not None
    assert (nature.kind, nature.measure, nature.capacity, nature.held) == (
        kind,
        measure,
        capacity,
        held,
    )
    assert nature.band == (BANDS[band] if band else None)
    assert nature.overseas is value.endswith("-registered-overseas-entity")


def test_unknown_values() -> None:
    assert classify("ownership-of-shares-10-to-25-percent") is None
    assert classify("OWNERSHIP-OF-SHARES-25-TO-50-PERCENT") is None
    assert classify("") is None


def test_combined_band() -> None:
    low, high = BANDS["25-to-50"], BANDS["75-to-100"]
    assert combined_band([low, high]) == Band(25, 100, min_exclusive=True, max_exclusive=False)
    assert combined_band([BANDS["50-to-75"]]) == BANDS["50-to-75"]
    closed = Band(50, 75, min_exclusive=False, max_exclusive=True)
    assert combined_band([BANDS["50-to-75"], closed]).min_exclusive is False  # type: ignore[union-attr]
    assert combined_band([]) is None


def natures_of(*values: str) -> list[Nature]:
    found = [n for n in (classify(v) for v in values) if n is not None]
    assert len(found) == len(values)
    return found


def test_interests_keep_direct_and_trust_holdings_apart() -> None:
    # One PSC: shares held directly, and control over a trust that holds more shares. These are
    # two facts, so two records, never one band of (25, 75).
    found = interests(
        natures_of(
            "ownership-of-shares-25-to-50-percent",
            "ownership-of-shares-50-to-75-percent-as-trust",
            "voting-rights-25-to-50-percent",
            "right-to-appoint-and-remove-directors",
        )
    )
    assert [(i.kind, i.key, i.type_label) for i in found] == [
        ("control", "appointment", "appointment"),
        ("control", "trust-or-firm-shares-trust", "trust-or-firm"),
        ("control", "voting", "voting"),
        ("ownership", "shares", "shares"),
    ]
    bands = {i.key: i.band for i in found}
    assert bands["shares"] == BANDS["25-to-50"]
    assert bands["trust-or-firm-shares-trust"] == BANDS["50-to-75"]
    assert bands["voting"] == BANDS["25-to-50"]  # voting control keeps its band
    assert bands["appointment"] is None


def test_interests_combine_values_of_one_interest_only() -> None:
    found = interests(
        natures_of(
            "ownership-of-shares-25-to-50-percent",
            "ownership-of-shares-75-to-100-percent",
            "ownership-of-shares-25-to-50-percent-as-trust",
            "voting-rights-25-to-50-percent-as-trust",
        )
    )
    assert {i.key: i.band for i in found} == {
        "shares": Band(25, 100, min_exclusive=True, max_exclusive=False),
        "trust-or-firm-shares-trust": BANDS["25-to-50"],
        "trust-or-firm-voting-trust": BANDS["25-to-50"],
    }
    assert [i.values for i in found if i.key == "shares"] == [
        ("ownership-of-shares-25-to-50-percent", "ownership-of-shares-75-to-100-percent")
    ]


def test_overseas_entity_trustee_interests() -> None:
    found = interests(
        natures_of(
            "ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity",
            "voting-rights-more-than-25-percent-as-trust-registered-overseas-entity",
            "ownership-of-shares-more-than-25-percent-as-control-over-firm-registered-overseas-entity",
        )
    )
    assert [(i.kind, i.key, i.type_label) for i in found] == [
        ("control", "trust-or-firm-shares-control-over-firm", "trust-or-firm"),
        ("control", "voting-as-trust", "voting (as trustee)"),
        ("ownership", "shares-as-trust", "shares (as trustee)"),
    ]
    assert all(i.band == BANDS["more-than-25"] for i in found)


@pytest.mark.parametrize(
    ("identification", "address_country", "expected"),
    [
        ({"country_registered": "England", "place_registered": "Companies House"}, None, True),
        ({"country_registered": "England And Wales"}, None, True),
        ({"country_registered": "Uk"}, None, True),
        ({"country_registered": "England & Wales Companies Register"}, None, True),
        ({"country_registered": "Jersey", "place_registered": "Companies House"}, None, False),
        ({"country_registered": "United States", "place_registered": "Delaware"}, None, False),
        ({"place_registered": "Companies House Cardiff"}, None, True),
        ({"legal_authority": "United Kingdom (England And Wales)"}, None, True),
        ({"legal_authority": "Companies Act 2006"}, None, False),
        ({"legal_authority": "Companies Act 2006"}, "England", False),  # an authority decides
        ({}, "England", True),
        ({}, "New South Wales", False),
        ({}, None, False),
    ],
)
def test_is_uk(
    identification: dict[str, str | None], address_country: str | None, expected: bool
) -> None:
    assert is_uk(identification, address_country) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234567", "01234567"),
        ("01234567", "01234567"),
        ("123 456", "00123456"),
        ("SC123456", "SC123456"),
        ("sc 12345", "SC012345"),
        ("R0012345", "R0012345"),
        ("OE001234", "OE001234"),
        ("HE123456", None),
        ("SY000101", None),
        ("123456789", None),
        ("N/A", None),
        ("", None),
        (None, None),
    ],
)
def test_uk_number(raw: str | None, expected: str | None) -> None:
    assert uk_number(raw) == expected


def test_names_agree() -> None:
    assert names_agree("QUARRY LANE INSTRUMENTS LIMITED", "Quarry Lane Instruments Ltd")
    assert not names_agree("QUARRY LANE INSTRUMENTS LIMITED", "Harbour Mill Foods Ltd")


def test_resolve_corporate() -> None:
    index = {"01234567": "QUARRY LANE INSTRUMENTS LIMITED"}
    uk = {"country_registered": "England", "registration_number": "1234567"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", uk, None, index) == (
        "resolved",
        "01234567",
    )
    assert resolve_corporate("Harbour Mill Foods Ltd", uk, None, index) == (
        "name_mismatch",
        "01234567",
    )
    other = {**uk, "registration_number": "7654321"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", other, None, index) == (
        "number_not_found",
        "07654321",
    )
    assert resolve_corporate("X", {"country_registered": "England"}, None, index) == (
        "no_number",
        None,
    )
    jersey = {"country_registered": "Jersey", "registration_number": "1234567"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", jersey, None, index) == (
        "non_uk",
        None,
    )
