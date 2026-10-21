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
    "forbidden-terms.txt": "f1baecc9b23b5c10b8740d422a9bb512a696c7a654336a9f6b9432271b9e73a5",
}


def catalog_entries() -> list[dict[str, Any]]:
    entries = []
    for path in CATALOG:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        entries.append(data)
    return entries


def catalog_templates() -> list[str]:
    templates = list(SPEC_TEMPLATES)
    for entry in catalog_entries():
        templates += list((entry.get("wording") or {}).values())
    return templates


def names_with_detector() -> list[str]:
    names = list(SPEC_NAMES_WITH_DETECTOR)
    names += [entry["name"] for entry in catalog_entries() if entry.get("detector")]
    return names


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
    ],
)
def test_compatibility_forms_cannot_hide_a_term(text: str) -> None:
    """The text is NFKC-normalised before matching, so a fullwidth or bold "m" reads as "m"."""
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


def test_synthetic_phrase_check_normalises_the_text() -> None:
    text = FULLWIDTH_S + "ynthetic scenario"
    assert not SYNTHETIC_PHRASE.search(text), "the bare pattern misses the fullwidth s"
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


def test_forbidden_terms_file() -> None:
    patterns = forbidden_patterns()
    assert len(patterns) == 23
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
