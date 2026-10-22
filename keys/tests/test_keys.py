"""Oracle tests for neonradar_keys (PHASE-2.md M2.8). Expected values were verified on
18 October 2026 with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 and anyascii 0.3.3."""

import gzip
import json
import re
from importlib.metadata import version
from importlib.resources import files

import pytest

from neonradar_keys.addresses import address_key
from neonradar_keys.arabic import ar_normalize
from neonradar_keys.companies_house import ch_same_as_key
from neonradar_keys.countries import country_code
from neonradar_keys.ids import CH_PREFIXES, has_ch_prefix, is_valid_lei, uk_company_number
from neonradar_keys.names import latin_forms, name_similarity, org_key, person_key, split_ch_name
from neonradar_keys.postcodes import normalise_uk_postcode, postcode_parts


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("أحمد", "احمد"),
        ("إحمد", "احمد"),
        ("آمنة", "امنه"),
        ("مُحَمَّد", "محمد"),
        ("محـــمد", "محمد"),
        ("فاطمة", "فاطمه"),
        ("مصطفى", "مصطفي"),
        ("عائشة", "عايشه"),
        ("ﷲ", "الله"),
        ("٢٠٢٦", "2026"),
    ],
)
def test_ar_normalize(raw, expected):
    assert ar_normalize(raw) == expected


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("سامر بن خليل العطار", "خليل سامر عطار"),
        ("عبد الرحمن العلي", "عبدالرحمن علي"),
        ("عبدالرحمن العلي", "عبدالرحمن علي"),
        ("Abdul Rahman Al Ali", "abdrahman ali"),
        ("Abdulrahman Al-Ali", "abdrahman ali"),
        ("Abd al-Rahman al-Ali", "abdrahman ali"),
        ("Abdel Rahman El Ali", "abdrahman ali"),
        ("AL-ALI, Abdul Rahman", "abdrahman ali"),
        ("SMITH, John Michael", "john michael smith"),
        ("AL-SAYED, Omar", "omar sayed"),
        ("Mr John Smith", "john smith"),
        ("Sheikh Hamad Saleh", "hamad saleh"),
        ("الشيخ سامر العطار", "سامر عطار"),
        ("الدكتور خليل حداد", "حداد خليل"),
        ("Abdullah Haddad", "abdallah haddad"),
        ("Abd Allah Haddad", "abdallah haddad"),
        ("Abu Bakr Haddad", "abubakr haddad"),
        ("Khalil bin Samer", "khalil samer"),
        ("Александр Сергеевич Иванов", "aleksandr ivanov sergeevich"),
        ("Пётр Щербаков", "petr shcherbakov"),
        ("Jürgen Müller", "jurgen muller"),
        ("Łukasz Wiśniewski", "lukasz wisniewski"),
        ("إلهام حداد", "الهام حداد"),
    ],
)
def test_person_keys(name, key):
    assert person_key(name).key == key


def test_ch_name_split_gives_family():
    assert split_ch_name("SMITH, John Michael") == ("John Michael", "SMITH")
    assert split_ch_name("Smith, John") is None
    keys = person_key("SMITH, John Michael")
    assert keys.family == ("smith",) and keys.given == ("john", "michael")


def test_cross_script_symbols_and_skeletons():
    assert "Q5837762" in person_key("محمد").symbols
    assert "Q5837762" in person_key("Mohammed").symbols
    assert "Q5837762" in person_key("Мухаммед").symbols
    assert {"Q923", "Q1511218", "Q17501806"} <= set(person_key("Alexander").symbols)
    assert "Q17501806" in person_key("Александр").symbols
    assert person_key("إحمد خليل").symbols  # the Arabic index catches spellings the tagger misses
    assert person_key("إحمد").symbols  # only the index can satisfy this (review of #49)
    assert "bdrhmn" in person_key("Abdul Rahman").skeletons
    assert "mhmd" in person_key("Mohammed").skeletons and "mhmd" in person_key("محمد").skeletons


@pytest.mark.parametrize(
    ("name", "key", "forms"),
    [
        ("ACME TRADING LTD", "acme trading", ("llc",)),
        ("Acme Trading Limited", "acme trading", ("llc",)),
        ("ACME HOLDINGS PLC", "acme holdings", ("jsc",)),
        ("Acme Partners LLP", "acme partners", ("llp",)),
        ("ООО «Ромашка»", "romashka", ("llc",)),
        ("The Acme Company Limited", "acme company", ("llc",)),
        ("ACME & SONS (UK) LIMITED", "acme and sons uk", ("llc",)),
    ],
)
def test_org_keys(name, key, forms):
    result = org_key(name)
    assert (result.key, result.legal_forms) == (key, forms)


def test_arabic_legal_form():
    assert "llc_ar" in org_key("شركة النخيل للتجارة ذ.م.م").legal_forms


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("ACME LIMITED", "ACME"),
        ("Acme Ltd.", "ACME"),
        ("ACME UK LIMITED", "ACME"),
        ("ACME (UK) LIMITED", "ACME"),
        ("THE ACME COMPANY LIMITED", "ACME"),
        ("ACME & CO LTD", "ACME"),
        ("A.C.M.E. LIMITED", "ACME"),
        ("WWW.ACME.CO.UK LIMITED", "ACME"),
        ("ACMÉ LIMITED", "ACME"),
        ("ACME HOLDINGS LIMITED", "ACMEHOLDING"),
        ("ACME HOLDING LTD", "ACMEHOLDING"),
        ("BACK TO BASICS LIMITED", "BACK2BASIC"),
        ("BACK 2 BASICS LTD", "BACK2BASIC"),
    ],
)
def test_ch_same_as(name, key):
    assert ch_same_as_key(name) == key


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("n1 7gu", "N1 7GU"),
        ("N17GU", "N1 7GU"),
        ("ec1a1bb", "EC1A 1BB"),
        ("N1 7GC", None),
        ("QQ1 2AB", "QQ1 2AB"),
        ("ZZ1 2AB", None),
        ("hello", None),
    ],
)
def test_postcodes(raw, expected):
    assert normalise_uk_postcode(raw) == expected


def test_postcode_parts():
    parts = postcode_parts("N1 7GU")
    assert (parts.area, parts.district, parts.sector) == ("N", "N1", "N1 7")


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("Flat 3, 12 High St., London, n1 7gu", "N1 7GU|FLAT 3 12 HIGH STREET LONDON"),
        (
            "FLAT 3, 12 HIGH STREET, LONDON, N1 7GU, UNITED KINGDOM",
            "N1 7GU|FLAT 3 12 HIGH STREET LONDON",
        ),
        (
            "Ste 4, Example Hse, 1-3 Example Rd., London N1 7GU",
            "N1 7GU|SUITE 4 EXAMPLE HOUSE 1-3 EXAMPLE ROAD LONDON",
        ),
        ("12 St Johns Road, London, N1 7GU", "N1 7GU|12 SAINT JOHNS ROAD LONDON"),
        (
            "c/o Example Accountants LLP, 2 Market Sq, Reading, RG1 2AA",
            "RG1 2AA|2 MARKET SQUARE READING",
        ),
        ("1st Floor 5 Church Ln Leeds LS12AB", "LS1 2AB|1ST FLOOR 5 CHURCH LANE LEEDS"),
        ("Moscow, Russia", None),
    ],
)
def test_address_keys(raw, key):
    assert address_key(raw) == key


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("British", "gb"),
        ("Welsh", "gb"),
        ("Scottish", "gb"),
        ("Irish", "ie"),
        ("Emirati", "ae"),
        ("Saudi Arabian", "sa"),
        ("Mauritian", "mu"),
        ("Congolese (Congo)", "cg"),
        ("Chadian", "td"),
        ("Stateless", None),
        ("United Kingdom", "gb"),
        ("England", "gb"),
        ("GBR", "gb"),
        ("VGB", "vg"),
        ("", None),
        ("Atlantis", None),
    ],
)
def test_country_codes(value, code):
    assert country_code(value) == code


@pytest.mark.parametrize(
    ("raw", "number"),
    [
        ("1800000", "01800000"),
        ("01800000", "01800000"),
        ("SC 12345", "SC012345"),
        ("OC300001", "OC300001"),
        ("sc-012345", "SC012345"),
        ("R0000123", "R0000123"),
        ("ABC", None),
        ("123456789", None),
        ("HE123456", None),  # a Cypriot number: HE is not a Companies House prefix
        ("GB123456", None),
        ("N1234567", None),
        ("SY000101", None),  # the synthetic prefix counts only for synthetic records
        (None, None),
    ],
)
def test_uk_company_number(raw, number):
    assert uk_company_number(raw) == number


def test_synthetic_company_numbers() -> None:
    assert uk_company_number("SY000101", synthetic=True) == "SY000101"
    assert uk_company_number("sy 101", synthetic=True) == "SY000101"
    assert uk_company_number("SC 12345", synthetic=True) == "SC012345"
    assert uk_company_number("HE123456", synthetic=True) is None


def test_lei():
    assert is_valid_lei("549300OWFMSO9NYV4H90")
    assert not is_valid_lei("549300OWFMSO9NYV4H91")
    assert not is_valid_lei(None)


def test_similarity_and_latin_forms():
    # The spec's company words were retired under OD-12 (contracts/CHANGELOG.md); the C1 example's
    # replacement name is used instead.
    assert name_similarity("quillon marsh trading", "quillon marsh trade") > 0.95
    assert name_similarity("rana", "nora") == 0.0
    # The spec's example person name is on the synthetic-name denylist (OD-12): a surname from
    # the synthetic word list (words.py) instead.
    assert latin_forms(["Haddad", "Хаддад"]) == ["Khaddad"]


def test_companies_house_prefixes() -> None:
    assert len(CH_PREFIXES) == 36  # 29 official and 7 newer prefixes (bulk-sources-loading.md 2.6)
    assert {"SC", "NI", "OC", "OE", "R0"} <= CH_PREFIXES
    assert "SY" not in CH_PREFIXES  # the synthetic benchmark prefix (M2.9)
    assert "NC" not in CH_PREFIXES  # in neither list of the research note
    assert has_ch_prefix("01234567")
    assert has_ch_prefix("SC123456")
    assert has_ch_prefix("R0012345")
    assert not has_ch_prefix("HE123456")


def test_symbol_index_matches_installed_rigour() -> None:
    # ar_symbols.json.gz is built from rigour's name data at the tag of the pinned version. A
    # lock update that moves rigour must rebuild it (scripts/build_ar_symbol_index.py).
    resource = files("neonradar_keys") / "data" / "ar_symbols.json.gz"
    with resource.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as handle:
        source = json.load(handle)["source"]
    match = re.search(r"/rigour/v([^/]+)/", source)
    assert match is not None
    assert match.group(1) == version("rigour")
