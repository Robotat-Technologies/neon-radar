"""Contract tests for the wording rules (PHASE-1.md 7.1, 5.5, guardrail G5)."""

import hashlib
import unicodedata
from pathlib import Path
from typing import Any

import check_wording
import pytest
import yaml

from neonradar_contracts.wording import (
    DISCLAIMER_IDS,
    FORBIDDEN_TERMS_FILE,
    SYNTHETIC_PHRASE,
    WORDING_DIR,
    find_forbidden,
    find_forbidden_in_name,
    forbidden_patterns,
    load_disclaimer,
    parse_patterns,
    says_synthetic_scenario,
)

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
CATALOG = sorted((REPO / "detect" / "typologies").glob("*.yaml"))
# The 5.4 example templates, so the test checks something before the catalog has files.
SPEC_TEMPLATES = [
    "Funds returned to the originating account through {cycle_length} transfers "
    "within {duration_days} days",
    "Synthetic scenario: funds returned to the originating account through {cycle_length} "
    "transfers within {duration_days} days",
]
SPEC_NAMES_WITH_DETECTOR = ["Round-tripping or circular flows"]
# The "Never write" column of the 7.1 vocabulary table, copied verbatim.
NEVER_WRITE = [
    "money laundering",
    "suspicious activity",
    "laundered funds",
    "dirty money",
    "sanctioned criminal",
    "corrupt official",
    "shell company",
    "front company",
    "risk score",
    "suspicion score",
    "likelihood of laundering",
    "laundering case",
    "the launderer",
    "accomplice",
    "mule",
    "fraudster",
]
# The "Write" column of the same table: the lint must leave the allowed vocabulary usable.
WRITE = [
    "structural pattern present",
    "funds returned to the originating account",
    "transfers",
    "payments",
    "listed in opensanctions_default as sanctioned",
    "as a politically exposed person",
    "as a relative or close associate of a politically exposed person",
    "shares a registered address with 14 other companies",
    "pattern strength",
    "synthetic scenario",
    "linked to",
    "holds an account that received",
]
# SHA-256 of each file, copied verbatim from PHASE-1.md 7.1 on 21 October 2026. A change to
# these texts is a contract change (contracts/CHANGELOG.md), not an edit.
VERBATIM_SHA256 = {
    "standing-v1.txt": "86879fc9fa980eeafe7179d1eb8cd826776269db0922c7f4d86d17c0f6bb1087",
    "synthetic-demo-v1.txt": "7cd682beb2515db6c1896027b2c462854c678697adc66a7a63a7ba8e71492d13",
    "real-data-v1.txt": "9baecaabc113f4b94eed076c3583dfe5d20d24f6948a5aa3b8499fcc4defd278",
}
# forbidden-terms.txt: the Phase 1 patterns stay byte for byte at the top of the file (this is
# the SHA-256 of the whole v1 file); C3 1.1.0 appends the Phase 2 block below them.
FORBIDDEN_TERMS_V1_SHA256 = "f1baecc9b23b5c10b8740d422a9bb512a696c7a654336a9f6b9432271b9e73a5"
PHASE_2_HEADER = "# Phase 2 additions (PHASE-2.md 7.2)"
# The quoted "Never write" phrases of the PHASE-2.md 7.2 table that it does not qualify with a
# condition, copied from 7.2 rule 7.
NEVER_WRITE_PHASE_2 = [
    "identified as",
    "is really",
    "proven to be the same",
    "is the same person as",
    "matches the sanctioned person",
    "sanctions hit",
    "is the same company as",
    "holds an indirect interest of",
    "falls under the 50 Percent Rule",
    "corrupt",
    "high risk",
    "suspicious",
    "not sanctioned",
    "not a PEP",
    "no sanctions exposure",
    "cleared",
    "passed screening",
]
# The "Write" column of the PHASE-2.md 7.2 table, copied verbatim.
WRITE_PHASE_2 = [
    "Merged from 3 source records: Companies House officer, Companies House PSC, GLEIF.",
    "Joined by the same UK company number.",
    "... the same LEI.",
    "... the same Companies House person number (its first 8 characters) and similar names.",
    "... the same UN reference number.",
    "... the same address.",
    "... a reviewer's decision.",
    "... probabilistic matching (match probability 0.997).",
    "Possible match, not confirmed. Agreeing: same name, same birth month, a shared nationality "
    "or country. Differing: postcodes.",
    "Kept separate because one record is on a sanctions or PEP list and the other is not "
    "(policy P1).",
    "Kept separate because the records are listed for different reasons, for example one on a "
    "sanctions list and one as a politically exposed person (policy P1).",
    "Kept separate because one record comes from the ICIJ Offshore Leaks Database (policy P2).",
    "Possible match, not confirmed. Both records give the same UK company number, but the names "
    "differ, so they were not merged.",
    "The published bands along 2 ownership links give an indirect share of more than 12.5 and "
    "less than 37.5 percent (a NeonRadar calculation, not a figure the register records).",
    "OFAC records that A is owned or controlled by B.",
    "Has significant influence or control over a trust (or firm) whose trustees (or members) "
    "hold more than 25 and at most 50 percent of the shares, as declared to Companies House.",
    "Holds more than 25 percent of the shares as a trustee of a trust (register of overseas "
    "entities).",
    "Holds more than 50 and less than 75 percent of the voting rights, as declared to Companies "
    "House.",
    "Recorded as sanctioned on the register of overseas entities at Companies House (as "
    "declared by the overseas entity; it may be out of date).",
    "Listed in UK Parliament data as a member of the House of Commons since 2019. Members of the "
    "House of Commons are politically exposed persons while in office (MLR 2017 regulation "
    "35(14)(b)); for a domestic PEP the starting point is a lower level of risk (regulation "
    "35(3A)).",
    "No sanctions or PEP flag from the lists loaded here (UK Sanctions List; OFAC Specially "
    "Designated Nationals and Blocked Persons List; EU Financial Sanctions Files (consolidated "
    "list); UK Parliament members and ministers), which means only that these lists do not name "
    "the record. Other lists, and politically exposed persons outside them, are not loaded.",
]
# The real data notice, version 2, copied verbatim from PHASE-2.md 5.3.
REAL_DATA_V2 = (
    "This view includes records from public sources (company registers, the GLEIF index, the "
    "ICIJ Offshore Leaks Database, which is built from leaked files, official sanctions lists "
    "and, where chosen, PEP data), listed with their licences on the Data sources page. Records "
    "about real people and companies are shown as their source published them and may be out "
    "of date. Where several records appear to describe the same person or company, NeonRadar "
    "may show them as one entity; a link marked as a possible match is not confirmed. NeonRadar "
    "adds no allegations: any payment activity shown next to a real entity is synthetic "
    "background activity, and a pattern that touches a real entity is a structural observation "
    "only. Names can match the wrong person or company, so confirm identities with addresses, "
    "dates or official identifiers before drawing any conclusion. A missing sanctions or PEP "
    "flag means only that the lists loaded here do not name the record. These records can "
    "include personal data, and whoever loads them is responsible for handling it lawfully."
)


def catalog_entries() -> list[dict[str, Any]]:
    entries = []
    for path in CATALOG:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        entries.append(data)
    return entries


def wording_texts(wording: dict[str, Any]) -> list[str]:
    """Every template of a typology file's `wording`: the Phase 1 headlines, and from Phase 3
    `detail` and each template of every entry under `variants` (PHASE-3.md 7.5.2)."""
    texts: list[str] = []
    for key, value in wording.items():
        if key == "variants":
            assert isinstance(value, dict), "wording.variants maps a variant to its templates"
            for variant in value.values():
                assert isinstance(variant, dict), variant
                texts += [str(text) for text in variant.values()]
        else:
            assert isinstance(value, str), key
            texts.append(value)
    return texts


def catalog_templates() -> list[str]:
    templates = list(SPEC_TEMPLATES)
    for entry in catalog_entries():
        templates += wording_texts(entry.get("wording") or {})
    return templates


def names_with_detector() -> list[str]:
    """Each detector typology's `name`, and from Phase 3 its `shape_name` (PHASE-3.md 7.5.2)."""
    names = list(SPEC_NAMES_WITH_DETECTOR)
    for entry in catalog_entries():
        if entry.get("detector"):
            names += [entry["name"], *([entry["shape_name"]] if entry.get("shape_name") else [])]
    return names


def test_wording_variants_and_detail_are_linted() -> None:
    wording = {
        "headline_structural": "Ownership layered through {company_layers}",
        "detail": "{assessment}",
        "variants": {"loop": {"headline_structural": "Ownership loop", "headline_synthetic": "x"}},
    }
    texts = wording_texts(wording)
    assert texts == [
        "Ownership layered through {company_layers}", "{assessment}", "Ownership loop", "x",
    ]  # fmt: skip
    bad = {"variants": {"loop": {"headline_structural": "a shell company loop"}}}
    assert find_forbidden(wording_texts(bad)[0])


@pytest.mark.parametrize("template", catalog_templates())
def test_typology_wording_templates_pass_the_lint(template: str) -> None:
    assert find_forbidden(template) == []


@pytest.mark.parametrize("name", names_with_detector())
def test_matches_the_graph_pattern_of_name_passes_the_lint(name: str) -> None:
    assert find_forbidden(f"matches the graph pattern of {name}") == []


@pytest.mark.parametrize("phrase", NEVER_WRITE)
def test_every_never_write_phrase_is_forbidden(phrase: str) -> None:
    assert find_forbidden(phrase), phrase
    assert find_forbidden(phrase.upper()), "the lint is case-insensitive"


@pytest.mark.parametrize("phrase", WRITE)
def test_the_allowed_vocabulary_passes(phrase: str) -> None:
    assert find_forbidden(phrase) == []


def test_masked_source_values_are_not_linted() -> None:
    step = "NRSYN-FRAUD-TEST sent EUR 5,000 to NRSYN0000000012 on 2 March."
    assert find_forbidden(step) == ["'FRAUD' (\\bfraud\\w*)"]
    assert find_forbidden(step, mask=["NRSYN-FRAUD-TEST", "NRSYN0000000012", ""]) == []


FULLWIDTH_S = unicodedata.lookup("FULLWIDTH LATIN SMALL LETTER S")


def _fullwidth(text: str) -> str:
    return "".join(unicodedata.lookup(f"FULLWIDTH LATIN CAPITAL LETTER {c}") for c in text)


@pytest.mark.parametrize(
    "text",
    [
        unicodedata.lookup("FULLWIDTH LATIN SMALL LETTER M") + "ule account",
        unicodedata.lookup("MATHEMATICAL BOLD SMALL M") + "ule account",
        _fullwidth("FRAUD") + " pattern",
        "laun\u00addered funds",  # soft hyphen
        "mu\u200ble account",  # zero-width space
        "risk\u2060 score",  # word joiner
    ],
)
def test_compatibility_forms_cannot_hide_a_term(text: str) -> None:
    """NFKC, then no format characters: a fullwidth "m" reads as "m", a soft hyphen vanishes."""
    assert find_forbidden(text), text


def test_masks_are_normalised_like_the_text() -> None:
    caption = _fullwidth("NRSYN") + "-" + _fullwidth("FRAUD")
    step = f"{caption} sent EUR 5,000."
    assert find_forbidden(step) == ["'FRAUD' (\\bfraud\\w*)"]
    assert find_forbidden(step, mask=[caption]) == []
    assert find_forbidden(step, mask=["NRSYN-FRAUD"]) == []


def test_masking_blanks_only_whole_tokens() -> None:
    """A masked value inside a longer word is not blanked, so the word is still linted."""
    step = "NRSYN-FRAUDULENT sent EUR 5,000."
    assert find_forbidden(step, mask=["NRSYN-FRAUD"]) == ["'FRAUDULENT' (\\bfraud\\w*)"]
    assert find_forbidden(step, mask=["NRSYN-FRAUDULENT"]) == []


@pytest.mark.parametrize(
    ("text", "says_it"),
    [
        ("Synthetic scenario: funds returned", True),
        ("a SYNTHETIC  SCENARIO", True),
        ("synthetic_scenario", True),
        ("synthetic-scenario", True),
        ("synthetic activity next to a scenario", False),
        ("nonsynthetic scenario", False),
    ],
)
def test_synthetic_phrase(text: str, says_it: bool) -> None:
    assert bool(SYNTHETIC_PHRASE.search(text)) is says_it
    assert says_synthetic_scenario(text) is says_it


@pytest.mark.parametrize(
    "text",
    [FULLWIDTH_S + "ynthetic scenario", "Synthetic\u2060 scenario", "Synthe\u00adtic scenario"],
)
def test_synthetic_phrase_check_normalises_the_text(text: str) -> None:
    assert not SYNTHETIC_PHRASE.search(text), "the bare pattern misses it"
    assert says_synthetic_scenario(text)


@pytest.mark.parametrize(
    ("name", "passes"),
    [
        ("origin_holder", True),
        ("circular_flow", True),
        ("mule_account", False),
        ("shell_company", False),
    ],
)
def test_identifiers_are_linted_with_underscores_as_spaces(name: str, passes: bool) -> None:
    assert (find_forbidden_in_name(name) == []) is passes


@pytest.mark.parametrize("disclaimer_id", DISCLAIMER_IDS)
def test_disclaimer_files_exist_and_are_one_paragraph(disclaimer_id: Any) -> None:
    text = load_disclaimer(disclaimer_id)
    assert text.strip() == text
    assert text
    assert "\n" not in text
    assert (WORDING_DIR / f"{disclaimer_id}.txt").read_text(encoding="utf-8") == text + "\n"


def test_unknown_disclaimer_id() -> None:
    with pytest.raises(ValueError, match="unknown disclaimer id"):
        load_disclaimer("standing-v2")  # type: ignore[arg-type]


@pytest.mark.parametrize(("name", "digest"), sorted(VERBATIM_SHA256.items()))
def test_wording_files_are_unchanged_from_the_spec(name: str, digest: str) -> None:
    assert hashlib.sha256((WORDING_DIR / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("phrase", NEVER_WRITE_PHASE_2)
def test_every_unqualified_phase_2_never_write_phrase_is_forbidden(phrase: str) -> None:
    assert find_forbidden(phrase), phrase
    assert find_forbidden(phrase.upper()), "the lint is case-insensitive"
    assert find_forbidden(f"The record {phrase.replace(' ', chr(10))} here."), "any whitespace"


@pytest.mark.parametrize("text", WRITE_PHASE_2)
def test_every_phase_2_write_text_passes(text: str) -> None:
    assert find_forbidden(text) == []


def test_the_phase_2_patterns_are_one_per_phrase_with_word_boundaries() -> None:
    text = FORBIDDEN_TERMS_FILE.read_text(encoding="utf-8")
    block = text.split(PHASE_2_HEADER + "\n", 1)[1]
    expected = ["\\b" + "\\s+".join(phrase.split()) + "\\b" for phrase in NEVER_WRITE_PHASE_2]
    assert block.splitlines() == expected


def test_real_data_v2_is_the_phase_2_notice_and_v1_stays() -> None:
    assert load_disclaimer("real-data-v2") == REAL_DATA_V2
    assert (WORDING_DIR / "real-data-v1.txt").exists()
    assert load_disclaimer("real-data-v1") != REAL_DATA_V2


def test_forbidden_terms_file() -> None:
    patterns = forbidden_patterns()
    assert len(patterns) == 23 + len(NEVER_WRITE_PHASE_2)
    raw = FORBIDDEN_TERMS_FILE.read_bytes()
    v1 = raw[: raw.index(b"\n" + PHASE_2_HEADER.encode())]
    assert hashlib.sha256(v1).hexdigest() == FORBIDDEN_TERMS_V1_SHA256
    lines = FORBIDDEN_TERMS_FILE.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# NeonRadar wording lint v1")
    # scripts/check_wording.py (standard library, CI) reads the file the same way.
    assert [p.pattern for p in check_wording.load_patterns(FORBIDDEN_TERMS_FILE)] == [
        p.pattern for p in patterns
    ]


def test_parse_patterns_skips_comments_and_blank_lines() -> None:
    patterns = parse_patterns("# comment\n\n  \\bfoo\\b  \n#\\bbar\n")
    assert [p.pattern for p in patterns] == ["\\bfoo\\b"]
    assert patterns[0].search("FOO")
