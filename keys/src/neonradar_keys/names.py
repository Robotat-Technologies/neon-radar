"""Person and organisation name keys (PHASE-2.md M2.8; research note names-addresses.md 3 to 5)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from anyascii import anyascii
from rigour.names import (
    NameTypeTag,
    SymbolCategory,
    analyze_names,
    extract_org_types,
    remove_org_prefixes,
    remove_org_types,
    remove_person_prefixes,
    tokenize_name,
)
from rigour.text import jaro_winkler, metaphone

from neonradar_keys import arabic, latin
from neonradar_keys.symbols import arabic_symbols
from neonradar_keys.text import latin_token, nfkc, scripts

_CH_NAME = re.compile(r"^\s*([^,]+?)\s*,\s*([^,]+?)\s*$")
_AR_LEGAL_FORMS = re.compile(
    r"(?<!\w)(ش\.?\s?ذ\.?\s?م\.?\s?م|ذ\.?\s?م\.?\s?م|ش\.?\s?م\.?\s?م|ش\.?\s?م\.?\s?ع(\.?\s?[مق])?"
    r"|ش\.?\s?م\.?\s?ب|ش\.?\s?م\.?\s?ل|ش\.?\s?ش\.?\s?و|ذات مسؤولي[ةه] محدود[ةه])\.?(?!\w)"
)


@dataclass(frozen=True)
class PersonKey:
    tokens: tuple[str, ...]  # normalised tokens in name order
    key: str  # sorted unique tokens joined by spaces ("" when nothing is left)
    given: tuple[str, ...]  # given-name tokens when the source says which part is which
    family: tuple[str, ...]  # family-name tokens when known
    skeletons: tuple[str, ...]  # consonant skeletons (cross-script blocking aid)
    phonetic: tuple[str, ...]  # Metaphone codes of ASCII tokens
    symbols: tuple[str, ...]  # Wikidata QIDs of name groups (rigour, plus the Arabic index)


@dataclass(frozen=True)
class OrgKey:
    key: str  # name without legal forms and leading "The", folded
    legal_forms: tuple[str, ...]  # generic legal form codes (for example "llc", "jsc", "llc_ar")


def split_ch_name(text: str) -> tuple[str, str] | None:
    """Companies House officers write "SURNAME, Forenames": returns (given, family) or None."""
    match = _CH_NAME.match(text)
    if match and match.group(1).upper() == match.group(1):
        return match.group(2), match.group(1)
    return None


def _tokens(text: str) -> list[str]:
    text = remove_person_prefixes(nfkc(text))
    raw = tokenize_name(text.casefold())
    if "Arabic" in scripts(text):
        raw = [t for t in raw if t]
        while len(raw) > 2 and arabic.ar_normalize(raw[0]) in arabic.HONORIFICS:
            raw = raw[1:]
        return arabic.arabic_rules(raw)
    folded = [latin_token(t) for t in raw]
    folded = [t for t in folded if t]
    while len(folded) > 2 and folded[0] in latin.HONORIFICS:
        folded = folded[1:]
    return [t for t in latin.latin_rules(folded) if t]


def _skeletons(tokens: Iterable[str]) -> tuple[str, ...]:
    out: set[str] = set()
    for token in tokens:
        if "Arabic" in scripts(token):
            candidates = [arabic.arabic_skeleton(token)]
        else:
            candidates = [latin.latin_skeleton(token)]
            root = latin.joined_article_root(token)
            if root:
                candidates.append(latin.latin_skeleton(root))
        out.update(c for c in candidates if len(c) >= 2)
    return tuple(sorted(out))


@lru_cache(maxsize=200_000)
def _rigour_symbols(text: str) -> frozenset[str]:
    found: set[str] = set()
    for name in analyze_names(NameTypeTag.PER, [text]):
        found.update(str(s.id) for s in name.symbols if s.category == SymbolCategory.NAME)
    return frozenset(found)


def person_key(name: str, given: str | None = None, family: str | None = None) -> PersonKey:
    """Keys for one person name. Pass given and family when the source separates them."""
    ch = split_ch_name(name)
    if ch and given is None and family is None:
        given, family = ch
        name = f"{given} {family}"
    tokens = _tokens(name)
    given_tokens = tuple(_tokens(given)) if given else ()
    family_tokens = tuple(_tokens(family)) if family else ()
    symbols = set(_rigour_symbols(name))
    if "Arabic" in scripts(name):
        symbols |= arabic_symbols(tokens)
    phonetic = tuple(sorted({metaphone(t) for t in tokens if t.isascii() and metaphone(t)}))
    return PersonKey(
        tokens=tuple(tokens),
        key=" ".join(sorted(set(tokens))),
        given=given_tokens,
        family=family_tokens,
        skeletons=_skeletons(tokens),
        phonetic=phonetic,
        symbols=tuple(sorted(symbols)),
    )


def org_key(name: str) -> OrgKey:
    text = nfkc(name).casefold()
    forms = {form for _, form in extract_org_types(text, generic=True)}
    if _AR_LEGAL_FORMS.search(text):
        forms.add("llc_ar")
    text = _AR_LEGAL_FORMS.sub(" ", text)
    text = remove_org_types(remove_org_prefixes(text), replacement=" ")
    tokens = tokenize_name(text.replace("&", " and "))
    if "Arabic" in scripts(text):
        folded = [arabic.ar_normalize(t) for t in tokens]
    else:
        folded = [latin_token(t) for t in tokens]
    return OrgKey(key=" ".join(t for t in folded if t), legal_forms=tuple(sorted(forms)))


def name_similarity(left: str, right: str) -> float:
    """Jaro-Winkler on two keys (rigour returns 0.0 for scores at or below 0.6)."""
    if not left or not right:
        return 0.0
    return float(jaro_winkler(left, right))


def latin_forms(names: Iterable[str]) -> list[str]:
    """Latin renderings of non-Latin names, for the full-text search aid (C2 names_latin)."""
    out = {anyascii(nfkc(n)).strip() for n in names if scripts(n) - {"Latin"}}
    return sorted(f for f in out if f)
