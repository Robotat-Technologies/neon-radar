"""Wording for merged entities, possible matches and the absence of flags (PHASE-2.md 7.2).

The sentences are copied from 7.2 verbatim (M2.10c deliverable 4); `{...}` marks what 7.2
writes as `<...>`. They live in `graph`, not `resolve`, so the API (M2.12) can use them without
Splink, and `er review` imports them. Every possible-match text says "not confirmed", and every
string here passes the forbidden-pattern lint (`scripts/check_wording.py` scans this file).

`explain_member` and `explain_possible_match` take a mapping or an object with the fields of
`canonical.csv` and `candidates.jsonl` (or of C3's `ResolutionMember` and `PossibleMatch`):
`method`, `rule`, `match_probability`, `features` (a mapping, or the compact JSON of
`canonical.csv`), `reasons` and, for a member, `dataset` (a slug or a title).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from decimal import ROUND_DOWN, Decimal
from typing import Any, Final, Literal

from neonradar_contracts.datasets import load_registry

Counts = Literal["agrees", "differs", "missing"]

NOT_CONFIRMED: Final = "Possible match, not confirmed."

# explain_member: (method, rule) -> text (7.2)
MEMBER_TEXTS: Final[Mapping[tuple[str, str | None], str]] = {
    ("identity", None): "Built from one source record ({dataset}).",
    ("anchor", None): (
        "Anchor record: the entity takes its id and caption from this {dataset} record."
    ),
    ("deterministic", "D1"): "Joined by the same UK company number.",
    ("deterministic", "D2"): "Joined by the same LEI.",
    ("deterministic", "D3"): (
        "Joined by the same Companies House person number (its first 8 characters) and similar"
        " names."
    ),
    ("deterministic", "D4"): "Joined by the same UN reference number.",
    ("deterministic", "D5"): "Joined because {dataset} gives both records the same identifier.",
    ("deterministic", "D6"): "Joined by the same address.",
    ("probabilistic", None): "Joined by probabilistic matching (match probability {p}). {evidence}",
    ("human", "D7"): "Joined by a reviewer's decision.",
}

# explain_possible_match: reason -> sentence; `source_hint:<hint>` uses "source_hint" (7.2)
REASON_TEXTS: Final[Mapping[str, str]] = {
    "below_merge_threshold": "Probabilistic matching gave {p}, below the threshold for merging.",
    "name_only": "Only the names agree, and NeonRadar never merges on a name alone (policy P3).",
    "listed_unlisted": (
        "Kept separate because one record is on a sanctions or PEP list and the other is not"
        " (policy P1)."
    ),
    "listed_differently": (
        "Kept separate because the records are listed for different reasons, for example one on a"
        " sanctions list and one as a politically exposed person (policy P1)."
    ),
    "leaked_cross_source": (
        "Kept separate because one record comes from the ICIJ Offshore Leaks Database (policy P2)."
    ),
    "listed_needs_birth_date": (
        "Entries from two different lists are merged only when their birth years agree or they"
        " share an identifier (policy P6)."
    ),
    "cluster_cap": (
        "Kept separate because merging would have joined more than 30 records into one entity"
        " (rule X7)."
    ),
    "identifier_name_mismatch": (
        "Both records give the same {identifier}, but the names differ, so they were not merged."
    ),
    "source_hint": "The ICIJ Offshore Leaks Database marks these records as {hint}.",
}
HINT_REASON: Final = "source_hint:"

# `<identifier>` of identifier_name_mismatch, from the link's rule (7.2)
IDENTIFIER_WORDS: Final[Mapping[str, str]] = {
    "D1": "UK company number",
    "D2": "LEI",
    "D3": "Companies House person number",
    "D4": "UN reference number",
    "D5": "source identifier",
}

# ICIJ hint words (7.2); any other value reads "related (<the value with underscores as spaces>)"
HINT_WORDS: Final[Mapping[str, str]] = {
    "same_name_as": "having the same name",
    "same_id_as": "having the same identifier",
    "same_as": "the same",
    "same_company_as": "the same company",
    "same_intermediary_as": "the same intermediary",
    "probably_same_officer_as": "probably the same officer",
    "similar": "similar",
    "similar_company_as": "similar",
}
OTHER_HINT: Final = "related ({value})"

# (comparison, Splink level label) -> (what it counts as, its words), in the order of 7.2's
# table; the evidence lists words in this order. Postcodes read the same for both models.
LEVEL_WORDS: Final[Mapping[tuple[str, str], tuple[Counts, str]]] = {
    ("name", "name key equal"): ("agrees", "same name"),
    ("name", "forename and surname similar"): ("agrees", "forename and surname spelled similarly"),
    ("name", "surname equal, same initial"): ("agrees", "same surname and initial"),
    ("name", "two name symbols shared"): (
        "agrees",
        "two name parts that match across scripts or spellings",
    ),
    ("name", "name key similar"): ("agrees", "names spelled similarly"),
    ("name", "surname equal"): ("agrees", "same surname"),
    ("name", "two skeletons shared"): ("agrees", "two name parts with the same consonants"),
    ("name", "All other comparisons"): ("differs", "names"),
    ("name", "name_key is NULL"): ("missing", "name"),
    ("birth", "same birth date"): ("agrees", "same birth date"),
    ("birth", "same birth month"): ("agrees", "same birth month"),
    ("birth", "same birth year"): ("agrees", "same birth year"),
    ("birth", "birth years one apart"): ("differs", "birth years (one year apart)"),
    ("birth", "All other comparisons"): ("differs", "birth dates"),
    ("birth", "birth_years is NULL"): ("missing", "birth date"),
    ("countries", "Array intersection size >= 1"): ("agrees", "a shared nationality or country"),
    ("countries", "All other comparisons"): ("differs", "nationalities and countries"),
    ("countries", "countries is NULL"): ("missing", "nationality or country"),
    ("postcode", "Exact match on full postcode"): ("agrees", "same postcode"),
    ("postcode", "Exact match on sector"): ("agrees", "same postcode sector"),
    ("postcode", "Exact match on district"): ("agrees", "same postcode district"),
    ("postcode", "Exact match on area"): ("agrees", "same postcode area"),
    ("postcode", "All other comparisons"): ("differs", "postcodes"),
    ("postcode", "postcode is NULL"): ("missing", "postcode"),
    ("linked_orgs", "Array intersection size >= 2"): ("agrees", "two or more companies in common"),
    ("linked_orgs", "Array intersection size >= 1"): ("agrees", "a company in common"),
    ("linked_orgs", "All other comparisons"): ("differs", "linked companies (none in common)"),
    ("linked_orgs", "linked_orgs is NULL"): ("missing", "linked companies"),
    ("identifiers", "Array intersection size >= 1"): (
        "agrees",
        "a shared passport or identity number",
    ),
    ("identifiers", "All other comparisons"): ("differs", "passport and identity numbers"),
    ("identifiers", "identifiers is NULL"): ("missing", "passport or identity number"),
    ("org_name", "name key equal"): ("agrees", "same name"),
    ("org_name", "a name or alias shared"): ("agrees", "a name, alias or former name in common"),
    ("org_name", "same name under the Companies House rules"): (
        "agrees",
        "the same name under the Companies House same-name rules",
    ),
    ("org_name", "name key very similar"): ("agrees", "names spelled very similarly"),
    ("org_name", "name key similar"): ("agrees", "names spelled similarly"),
    ("org_name", "two words shared"): ("agrees", "two words of the name in common"),
    ("org_name", "All other comparisons"): ("differs", "names"),
    ("org_name", "name_key is NULL"): ("missing", "name"),
    ("jurisdiction", "Exact match on jurisdiction"): ("agrees", "same jurisdiction"),
    ("jurisdiction", "All other comparisons"): ("differs", "jurisdictions"),
    ("jurisdiction", "jurisdiction is NULL"): ("missing", "jurisdiction"),
    ("registration_numbers", "Array intersection size >= 1"): (
        "agrees",
        "a shared registration number",
    ),
    ("registration_numbers", "All other comparisons"): ("differs", "registration numbers"),
    ("registration_numbers", "registration_numbers is NULL"): ("missing", "registration number"),
    ("incorporation", "same year"): ("agrees", "same incorporation year"),
    ("incorporation", "one year apart"): ("differs", "incorporation years (one year apart)"),
    ("incorporation", "All other comparisons"): ("differs", "incorporation years"),
    ("incorporation", "incorporation_year is NULL"): ("missing", "incorporation year"),
    ("legal_forms", "Array intersection size >= 1"): ("agrees", "same legal form"),
    ("legal_forms", "All other comparisons"): ("differs", "legal forms"),
    ("legal_forms", "legal_forms is NULL"): ("missing", "legal form"),
}
COMPARISON_ORDER: Final[Mapping[str, int]] = {
    comparison: n for n, comparison in enumerate(dict.fromkeys(c for c, _ in LEVEL_WORDS))
}
EVIDENCE_PARTS: Final[tuple[tuple[Counts, str], ...]] = (
    ("agrees", "Agreeing: {words}."),
    ("differs", "Differing: {words}."),
    ("missing", "Not on both records: {words}."),
)
EVIDENCE_LINES: Final[Mapping[Counts, str]] = {
    "agrees": "Agrees: {words}",
    "differs": "Differs: {words}",
    "missing": "Not on both records: {words}",
}

ABSENCE_OF_FLAGS: Final = (
    "No sanctions or PEP flag from the lists loaded here ({lists}), which means only that these"
    " lists do not name the record. Other lists, and politically exposed persons outside them,"
    " are not loaded."
)
NO_LIST_LOADED: Final = (
    "No sanctions or PEP list is loaded here, so this view cannot show such flags."
)


def _field(item: Any, name: str) -> Any:
    return item.get(name) if isinstance(item, Mapping) else getattr(item, name, None)


def _features(value: Any) -> Mapping[str, str]:
    if not value:
        return {}
    if isinstance(value, str):  # canonical.csv keeps a member's levels as compact JSON
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise ValueError("features must be a mapping of comparison to level label")
    return {str(k): str(v) for k, v in value.items()}


def probability_text(p: float) -> str:
    """Three decimals, rounded down, so a probability never shows as 1.000 (7.2)."""
    if not 0.0 <= p <= 1.0:
        raise ValueError("a probability is between 0 and 1")
    down = Decimal(repr(float(p))).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
    return str(min(down, Decimal("0.999")))


def dataset_title(dataset: str) -> str:
    """The registry title of a dataset slug; any other text is taken as a title already."""
    found = load_registry().get(dataset)
    return found.title if found is not None else dataset


def _levels(features: Mapping[str, str]) -> list[tuple[str, Counts, str]]:
    """(comparison, counts as, words) in the order of 7.2's table; unknown levels raise."""
    out = []
    for comparison, label in features.items():
        try:
            counts, words = LEVEL_WORDS[(comparison, label)]
        except KeyError:
            raise ValueError(f"no wording for the level {label!r} of {comparison!r}") from None
        out.append((comparison, counts, words))
    return sorted(out, key=lambda level: COMPARISON_ORDER[level[0]])


def evidence(features: Mapping[str, str] | str | None) -> str:
    """ "Agreeing: ... Differing: ... Not on both records: ...", each part only with words."""
    levels = _levels(_features(features))
    parts = []
    for counts, template in EVIDENCE_PARTS:
        words = [w for _, c, w in levels if c == counts]
        if words:
            parts.append(template.format(words=", ".join(words)))
    return " ".join(parts)


def evidence_lines(features: Mapping[str, str] | str | None) -> list[str]:
    """One line per comparison: "Agrees: ...", "Differs: ..." or "Not on both records: ..."."""
    return [
        EVIDENCE_LINES[counts].format(words=words)
        for _, counts, words in _levels(_features(features))
    ]


def explain_member(member: Any) -> str:
    """The text of one member of an entity (one row of `canonical.csv`; 7.2 `explain_member`)."""
    method, rule = _field(member, "method"), _field(member, "rule") or None
    key = (str(method), None if method in ("identity", "anchor", "probabilistic") else rule)
    template = MEMBER_TEXTS.get(key)
    if template is None:
        raise ValueError(f"no member text for method {method!r} and rule {rule!r}")
    if method == "probabilistic":
        p = _field(member, "match_probability")
        if p is None:
            raise ValueError("a probabilistic member needs its match probability")
        p_text = probability_text(float(p))
        return template.format(p=p_text, evidence=evidence(_field(member, "features"))).rstrip()
    dataset = _field(member, "dataset")
    if "{dataset}" in template and not dataset:
        raise ValueError(f"the {method} text needs the member's dataset")
    return template.format(dataset=dataset_title(str(dataset)) if dataset else "")


def hint_words(hint: str) -> str:
    """The words for an ICIJ hint (`HINT_WORDS`), else "related (<hint with spaces>)"."""
    return HINT_WORDS.get(hint) or OTHER_HINT.format(value=hint.replace("_", " "))


def _reason(reason: str, link: Any) -> str:
    if reason.startswith(HINT_REASON):
        return REASON_TEXTS["source_hint"].format(hint=hint_words(reason[len(HINT_REASON) :]))
    template = REASON_TEXTS.get(reason)
    if template is None:
        raise ValueError(f"no text for the reason {reason!r}")
    if reason == "below_merge_threshold":
        p = _field(link, "match_probability")
        if p is None:
            raise ValueError("below_merge_threshold needs the match probability")
        return template.format(p=probability_text(float(p)))
    if reason == "identifier_name_mismatch":
        identifier = IDENTIFIER_WORDS.get(str(_field(link, "rule")))
        if identifier is None:
            raise ValueError("identifier_name_mismatch needs the link's D rule (D1 to D5)")
        return template.format(identifier=identifier)
    return template


def explain_possible_match(link: Any) -> str:
    """ "Possible match, not confirmed.", one sentence per reason in the link's order, and for
    a probabilistic match the evidence (7.2 `explain_possible_match`)."""
    reasons: Iterable[str] = _field(link, "reasons") or ()
    sentences = [NOT_CONFIRMED, *(_reason(str(r), link) for r in reasons)]
    if _field(link, "method") == "probabilistic":
        found = evidence(_field(link, "features"))
        if found:
            sentences.append(found)
    return " ".join(sentences)


def absence_of_flags(datasets: Iterable[str]) -> str:
    """The text for a node without a flag: the list datasets loaded here (slugs or titles, in
    the order given; 7.2 rule 5), or the text for when none is loaded."""
    titles = list(dict.fromkeys(dataset_title(d) for d in datasets))
    if not titles:
        return NO_LIST_LOADED
    return ABSENCE_OF_FLAGS.format(lists="; ".join(titles))
