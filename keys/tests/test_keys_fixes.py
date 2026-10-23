"""Tests for the changes after the M2.8 reviews (RULES_VERSION 2 and 3; section 2.6 of
docs/build/phase-2-reconciliation.md). Every name and address here is invented or generic; the
spec's own cases stay in test_keys.py and still pass."""

import shutil
import subprocess
import unicodedata
import zipfile
from importlib.metadata import distribution, version
from importlib.resources import files
from pathlib import Path

import pytest

import neonradar_keys
from neonradar_keys import symbols
from neonradar_keys.addresses import address_key
from neonradar_keys.ids import has_ch_prefix, uk_company_number
from neonradar_keys.names import person_key
from neonradar_keys.postcodes import find_uk_postcode

ROOT = Path(__file__).resolve().parents[2]
LICENCE_FILES = ("ar_symbols.LICENSE.txt", "nationalities.LICENSE.txt")


def test_rules_version_was_bumped() -> None:
    assert neonradar_keys.RULES_VERSION == "3"


def test_without_the_arabic_index_a_variant_spelling_has_no_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S1: only the Arabic index gives this spelling a name group (test_keys.py asserts it does).
    assert person_key("إحمد").symbols
    monkeypatch.setattr(symbols, "_index", dict)
    assert not person_key("إحمد").symbols


@pytest.mark.parametrize(
    "raw",
    [
        "Dubai, United Arab Emirates",
        "Road Town, Tortola, British Virgin Islands",
        "Panama City, Panama",
        "New York, NY, USA",
        "Isle of Man",
        "Flat Rock, Michigan, USA",
        "Office of the Registrar, Dubai",
        # Two words were never enough (the spec's floor of three tokens stays): a bare street
        # name or flat would join unrelated records under D6.
        "High Street",
        "Example Road",
        "Flat A",
        "Unit B",
        "Flat Holm, Wales",
    ],
)
def test_place_names_alone_are_not_a_street_line(raw: str) -> None:
    # S2: "None when it has neither a postcode nor a street line".
    assert address_key(raw) is None


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("1 Example Street, Road Town, Tortola", "NOPC|1 EXAMPLE STREET ROAD TOWN TORTOLA"),
        ("Example House, Leeds", "NOPC|EXAMPLE HOUSE LEEDS"),
        ("Example Village, Example House", "NOPC|EXAMPLE VILLAGE EXAMPLE HOUSE"),
        ("Flat A, Example Court, Leeds", "NOPC|FLAT A EXAMPLE COURT LEEDS"),
        ("Office 5, Example Tower, Dubai", "NOPC|OFFICE 5 EXAMPLE TOWER DUBAI"),
    ],
)
def test_street_lines_without_a_postcode_keep_their_key(raw: str, key: str) -> None:
    assert address_key(raw) == key


WORDS_V3 = (
    "Park", "Pk", "Green", "Grn", "Towers", "Plaza", "Hall", "Quay", "Wharf", "Row", "Walk",
    "Grove", "Hill", "Mansions", "Lodge",
)  # fmt: skip
EXPANDED = {"Pk": "PARK", "Grn": "GREEN", "Blvd": "BOULEVARD"}


@pytest.mark.parametrize("word", [*WORDS_V3, "Blvd"])
def test_more_street_words_restore_keys_the_spec_gave(word: str) -> None:
    # RULES_VERSION 3: street lines without a number that version 2 dropped. Each text has three
    # tokens, so the spec gave it a key too (the rule never goes beyond the spec's floor).
    expected = EXPANDED.get(word, word.upper())
    assert address_key(f"Example {word}, Example Town") == f"NOPC|EXAMPLE {expected} EXAMPLE TOWN"


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("Calle Ejemplo, Madrid, Spain", "NOPC|CALLE EJEMPLO MADRID SPAIN"),
        ("Rue Exemple, Paris, France", "NOPC|RUE EXEMPLE PARIS FRANCE"),
        ("Beispielstraße, Berlin, Germany", "NOPC|BEISPIELSTRASSE BERLIN GERMANY"),
        ("Beispiel Strasse, Berlin, Germany", "NOPC|BEISPIEL STRASSE BERLIN GERMANY"),
        ("улица Примерная, Москва, Россия", "NOPC|ULITSA PRIMERNAYA MOSKVA ROSSIYA"),
        ("ул. Примерная, Москва, Россия", "NOPC|UL PRIMERNAYA MOSKVA ROSSIYA"),
        ("شارع المثال، دبي", "NOPC|SHR LMTHL DBY"),
    ],
)
def test_foreign_street_words_restore_keys_the_spec_gave(raw: str, key: str) -> None:
    assert address_key(raw) == key


@pytest.mark.parametrize(
    "raw",
    [
        "Example Park",  # two tokens: the spec gave None too
        "Calle Ejemplo",
        "Rose Cottage, Example Village, Example County",  # a house name: the spec gave a key
        "Rue, Paris, France",  # a street word with no name after it
        "Strasse, Berlin, Germany",  # STRASSE alone starts its segment: no compound, no name
    ],
)
def test_texts_still_without_a_street_line(raw: str) -> None:
    assert address_key(raw) is None


def test_st_that_starts_a_segment_is_saint() -> None:
    key = address_key("12 Example St, St Example, QQ1 2AB")
    assert key == "QQ1 2AB|12 EXAMPLE STREET SAINT EXAMPLE"


@pytest.mark.parametrize(
    "raw",
    [
        "١٨٠٠٠٠٠",  # Arabic-Indic digits
        "０１８０００００",  # fullwidth digits
        "SC１２３４５",
        "00000000",
        "0",
        "SC000000",
    ],
)
def test_company_numbers_need_ascii_digits_and_not_only_zeros(raw: str) -> None:
    assert uk_company_number(raw) is None


def test_synthetic_all_zero_number_is_rejected_too() -> None:
    assert uk_company_number("SY000000", synthetic=True) is None
    assert uk_company_number("SY000101", synthetic=True) == "SY000101"


def test_has_ch_prefix_needs_ascii_digits() -> None:
    assert not has_ch_prefix("١٢٣٤٥٦٧٨")
    assert has_ch_prefix("01800000")
    assert not has_ch_prefix("SC١٢٣٤٥٦")  # RULES_VERSION 3: the prefix form is ASCII too
    assert has_ch_prefix("SC123456")


@pytest.mark.parametrize(
    ("text", "rest"),
    [
        ("Straße 5, QQ1 2AB, London", "Straße 5,  , London"),
        ("ﬁeld Lane, QQ1 2AB", "ﬁeld Lane,  "),
        ("Flat 3, qq1 2ab", "Flat 3,  "),
    ],
)
def test_find_uk_postcode_cuts_the_original_text(text: str, rest: str) -> None:
    # ß and ligatures grow when upper-cased; the cut must still fall around the postcode.
    assert find_uk_postcode(text) == ("QQ1 2AB", rest)


@pytest.mark.parametrize(
    "variant",
    [
        unicodedata.normalize("NFD", "Jürgen"),
        "Ｍｏｈａｍｍｅｄ",  # fullwidth
        unicodedata.normalize("NFC", "Mohammed"),
    ],
)
def test_name_symbols_do_not_depend_on_the_unicode_form(variant: str) -> None:
    plain = unicodedata.normalize("NFKC", variant)
    assert person_key(variant).symbols == person_key(plain).symbols
    assert person_key(variant).symbols


def test_licence_texts_are_package_data() -> None:
    data = files("neonradar_keys") / "data"
    mit = (data / "ar_symbols.LICENSE.txt").read_text(encoding="utf-8")
    rigour_licence = distribution("rigour").read_text("licenses/LICENSE")
    assert rigour_licence is not None and rigour_licence.strip() in mit
    assert f"v{version('rigour')}" in mit  # the tag the index was built from
    ogl = (data / "nationalities.LICENSE.txt").read_text(encoding="utf-8")
    assert (
        "Contains public sector information licensed under the Open Government Licence v3.0." in ogl
    )
    assert "Open Government Licence for public sector information" in ogl


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
def test_wheel_contains_the_data_files_and_their_licences(tmp_path: Path) -> None:
    command = ["uv", "build", "--package", "neonradar-keys", "--wheel", "--offline", "--quiet"]
    result = subprocess.run(  # noqa: S603 (fixed arguments; --offline keeps it off the network)
        [*command, "--out-dir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    (wheel,) = tmp_path.glob("neonradar_keys-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    expected = ("ar_symbols.json.gz", "nationalities.csv", *LICENCE_FILES)
    assert {f"neonradar_keys/data/{name}" for name in expected} <= names
