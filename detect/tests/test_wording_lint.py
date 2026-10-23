"""The run-time wording lint (PHASE-3.md M3.2 deliverable 4, 7.5.2; reconciliation W1, W2)."""

import pytest

from neonradar_contracts.wording import forbidden_patterns
from neonradar_detect.wording_lint import CONDUCT, PHRASES, violations


def test_phase1_patterns_come_from_the_contract_file() -> None:
    assert violations("The funds were laundered.") == [r"\blaunder\w*"]
    assert {p.pattern for p in forbidden_patterns()} >= {r"\blaunder\w*", r"\bmules?\b"}


@pytest.mark.parametrize(
    ("text", "pattern"),
    [
        ("The account is blocked by the list.", PHRASES[0].pattern),
        ("Cash deposits show structuring.", CONDUCT[0].pattern),
        ("Payments passed through layering.", CONDUCT[1].pattern),
        ("A shell owns the company.", CONDUCT[3].pattern),
        ("The holder is the subject of a list entry.", None),
        ("The company is sanctioned.", CONDUCT[4].pattern),
    ],
)
def test_phase2_phrases_and_phase3_conduct_words(text: str, pattern: str | None) -> None:
    assert violations(text) == ([pattern] if pattern else [])


def test_neutral_words_stay_allowed() -> None:
    assert violations("Payments passed through 3 layers of structural ownership.") == []


def test_returns_patterns_never_the_matched_words() -> None:
    found = violations("Fraudulent mule accounts")
    assert found == [r"\bfraud\w*", r"\bmules?\b"]
    assert not any("Fraudulent" in p or "mule accounts" in p for p in found)


def test_captions_are_masked_as_whole_tokens_only() -> None:
    caption = "Test Mule Transport Ltd"
    assert violations(f"{caption} paid GBP 5,000.", (caption,)) == []
    # a caption inside a longer word is not masked (Phase 1's rule, stricter than substrings)
    assert violations("Shellfish Mule Ltd paid.", ("Shellfish",)) == [r"\bmules?\b"]
    # normalised first: a fullwidth letter does not hide a word
    assert violations("The company is ｓanctioned.") == [CONDUCT[4].pattern]
