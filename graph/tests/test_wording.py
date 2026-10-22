"""The resolution texts of PHASE-2.md 7.2 (M2.10c deliverable 4)."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import check_wording
import pytest

from neonradar_contracts.wording import find_forbidden, normalize
from neonradar_graph import wording

ROOT = Path(__file__).resolve().parents[2]
# The unqualified "Never write" phrases of 7.2 rule 7, which M2.1c adds to the lint patterns;
# checked here too, so the texts pass them whether or not the patterns file has them yet.
PHASE_2_PHRASES = (
    "identified as", "is really", "proven to be the same", "is the same person as",
    "matches the sanctioned person", "sanctions hit", "is the same company as",
    "holds an indirect interest of", "falls under the 50 Percent Rule", "corrupt", "high risk",
    "suspicious", "not sanctioned", "not a PEP", "no sanctions exposure", "cleared",
    "passed screening",
)  # fmt: skip
PHASE_2_PATTERNS = [
    re.compile(r"\b" + r"\s+".join(map(re.escape, p.split())) + r"\b", re.IGNORECASE)
    for p in PHASE_2_PHRASES
]
FEATURES = {  # one level of each person comparison, as candidates.jsonl writes them
    "name": "name key equal",
    "birth": "same birth month",
    "countries": "Array intersection size >= 1",
    "postcode": "All other comparisons",
    "linked_orgs": "linked_orgs is NULL",
    "identifiers": "identifiers is NULL",
}
LISTS = ("gb_fcdo_sanctions", "us_ofac_sdn", "eu_fsf", "gb_parliament_members")


def assert_lint_clean(text: str) -> None:
    assert not find_forbidden(text), text
    assert not [p.pattern for p in PHASE_2_PATTERNS if p.search(normalize(text))], text


def rendered_members() -> list[str]:
    texts = []
    for (method, rule), _ in wording.MEMBER_TEXTS.items():
        member = {"method": method, "rule": rule, "dataset": "nr_synthetic"}
        if method == "probabilistic":
            member |= {"match_probability": 0.9973, "features": FEATURES}
        texts.append(wording.explain_member(member))
    return texts


def possible_matches() -> list[dict[str, Any]]:
    hints = [f"source_hint:{hint}" for hint in [*wording.HINT_WORDS, "officer_of_same_as"]]
    reasons = [r for r in wording.REASON_TEXTS if r != "source_hint"]
    links: list[dict[str, Any]] = [
        {"method": "probabilistic", "match_probability": 0.91, "rule": None, "reasons": [reason]}
        | {"features": FEATURES}
        for reason in reasons
        if reason != "identifier_name_mismatch"
    ]
    links += [
        {"method": "deterministic", "rule": rule, "reasons": ["identifier_name_mismatch"]}
        for rule in wording.IDENTIFIER_WORDS
    ]
    links += [{"method": "source_hint", "rule": None, "reasons": [hint]} for hint in hints]
    return links


def test_every_member_text_renders_and_passes_the_lint() -> None:
    texts = rendered_members()
    assert len(texts) == 10  # identity, anchor, D1 to D6, probabilistic, D7
    for text in texts:
        assert_lint_clean(text)
        assert "{" not in text and "<" not in text
    assert texts[0] == "Built from one source record (NeonRadar synthetic data)."


def test_member_texts_as_7_2_writes_them() -> None:
    explain = wording.explain_member
    assert explain({"method": "deterministic", "rule": "D1"}) == (
        "Joined by the same UK company number."
    )
    assert explain(SimpleNamespace(method="human", rule="D7", dataset="gleif_lei")) == (
        "Joined by a reviewer's decision."
    )
    assert explain({"method": "deterministic", "rule": "D5", "dataset": "gleif_lei"}) == (
        "Joined because GLEIF Global LEI Index gives both records the same identifier."
    )
    member = {"method": "probabilistic", "rule": "", "match_probability": "0.9979"}
    assert explain(member | {"features": None}) == (
        "Joined by probabilistic matching (match probability 0.997)."
    )
    compact = '{"birth":"same birth month","name":"name key equal"}'  # canonical.csv's form
    assert explain(member | {"features": compact}) == (
        "Joined by probabilistic matching (match probability 0.997). Agreeing: same name,"
        " same birth month."
    )


def test_every_reason_and_hint_renders_with_not_confirmed() -> None:
    links = possible_matches()
    assert len(links) == 7 + 5 + 9  # reasons, identifier rules, hints (one unknown)
    for link in links:
        text = wording.explain_possible_match(link)
        assert text.startswith("Possible match, not confirmed. ")
        assert "not confirmed" in text
        assert_lint_clean(text)
        assert "{" not in text
    unknown = wording.explain_possible_match(links[-1])
    assert unknown.endswith("marks these records as related (officer of same as).")


def test_possible_match_texts_as_7_2_writes_them() -> None:
    explain = wording.explain_possible_match
    assert explain({"method": "probabilistic", "reasons": [], "features": FEATURES}) == (
        "Possible match, not confirmed. Agreeing: same name, same birth month, a shared"
        " nationality or country. Differing: postcodes. Not on both records: linked companies,"
        " passport or identity number."
    )
    four = {k: v for k, v in FEATURES.items() if k in ("name", "birth", "countries", "postcode")}
    assert explain({"method": "probabilistic", "features": four}) == (
        "Possible match, not confirmed. Agreeing: same name, same birth month, a shared"
        " nationality or country. Differing: postcodes."
    )
    assert explain(
        {"method": "deterministic", "rule": "D1", "reasons": ["identifier_name_mismatch"]}
    ) == (
        "Possible match, not confirmed. Both records give the same UK company number, but the"
        " names differ, so they were not merged."
    )
    link = {"method": "probabilistic", "match_probability": 0.8125, "features": {}}
    assert explain(link | {"reasons": ["below_merge_threshold", "listed_unlisted"]}) == (
        "Possible match, not confirmed. Probabilistic matching gave 0.812, below the threshold"
        " for merging. Kept separate because one record is on a sanctions or PEP list and the"
        " other is not (policy P1)."
    )
    hint = {"method": "source_hint", "reasons": ["source_hint:same_name_as"]}
    assert explain(hint) == (
        "Possible match, not confirmed. The ICIJ Offshore Leaks Database marks these records as"
        " having the same name."
    )


def test_evidence_lines_follow_the_table_order() -> None:
    shuffled = dict(reversed(list(FEATURES.items())))
    assert wording.evidence_lines(shuffled) == [
        "Agrees: same name",
        "Agrees: same birth month",
        "Agrees: a shared nationality or country",
        "Differs: postcodes",
        "Not on both records: linked companies",
        "Not on both records: passport or identity number",
    ]
    org = {"org_name": "name key very similar", "incorporation": "one year apart"}
    assert wording.evidence_lines(org) == [
        "Agrees: names spelled very similarly",
        "Differs: incorporation years (one year apart)",
    ]
    assert wording.evidence(None) == "" and wording.evidence_lines({}) == []
    for text in wording.evidence_lines({c: label for c, label in wording.LEVEL_WORDS}):
        assert_lint_clean(text)


def test_every_level_has_words() -> None:
    for (comparison, label), (counts, words) in wording.LEVEL_WORDS.items():
        line = wording.evidence_lines({comparison: label})
        assert len(line) == 1 and line[0].endswith(words)
        assert counts in ("agrees", "differs", "missing")
        assert_lint_clean(words)


def test_absence_of_flags() -> None:
    assert wording.absence_of_flags(LISTS) == (
        "No sanctions or PEP flag from the lists loaded here (UK Sanctions List; OFAC Specially"
        " Designated Nationals and Blocked Persons List; EU Financial Sanctions Files"
        " (consolidated list); UK Parliament members and ministers), which means only that these"
        " lists do not name the record. Other lists, and politically exposed persons outside"
        " them, are not loaded."
    )
    assert wording.absence_of_flags([]) == (
        "No sanctions or PEP list is loaded here, so this view cannot show such flags."
    )
    assert_lint_clean(wording.absence_of_flags(LISTS))


@pytest.mark.parametrize(
    ("p", "text"),
    [(0.997, "0.997"), (0.9999999, "0.999"), (1.0, "0.999"), (0.5, "0.500"), (0.81259, "0.812")],
)
def test_probabilities_round_down_to_three_decimals(p: float, text: str) -> None:
    assert wording.probability_text(p) == text


def test_unknown_inputs_raise() -> None:
    with pytest.raises(ValueError, match="no wording for the level"):
        wording.evidence_lines({"name": "a level 7.2 does not name"})
    with pytest.raises(ValueError, match="no text for the reason"):
        wording.explain_possible_match({"reasons": ["merged_anyway"]})
    with pytest.raises(ValueError, match="no member text"):
        wording.explain_member({"method": "deterministic", "rule": "D9"})
    with pytest.raises(ValueError, match="needs the link's D rule"):
        wording.explain_possible_match({"reasons": ["identifier_name_mismatch"]})
    with pytest.raises(ValueError, match="between 0 and 1"):
        wording.probability_text(1.5)


def test_check_wording_scans_the_graph_texts(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_wording.main(["--root", str(ROOT)]) == 0
    assert (ROOT / "graph/src/neonradar_graph/wording.py").is_file()
    assert "wording.py files pass" in capsys.readouterr().out
