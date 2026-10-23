"""Address keys for UK addresses (research note names-addresses.md 8)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from anyascii import anyascii

from neonradar_keys.postcodes import find_uk_postcode
from neonradar_keys.text import nfkc

_COUNTRY_WORDS = [
    w.split()
    for w in (
        "UNITED KINGDOM",
        "GREAT BRITAIN",
        "NORTHERN IRELAND",
        "ENGLAND",
        "SCOTLAND",
        "WALES",
        "BRITAIN",
        "UK",
        "U K",
        "GB",
        "GBR",
    )
]
_ABBREVIATIONS = {
    "RD": "ROAD",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "LN": "LANE",
    "DR": "DRIVE",
    "CT": "COURT",
    "CRES": "CRESCENT",
    "PL": "PLACE",
    "SQ": "SQUARE",
    "GDNS": "GARDENS",
    "GRN": "GREEN",
    "CL": "CLOSE",
    "TERR": "TERRACE",
    "TER": "TERRACE",
    "PK": "PARK",
    "PDE": "PARADE",
    "HSE": "HOUSE",
    "HO": "HOUSE",
    "BLDG": "BUILDING",
    "BLDGS": "BUILDINGS",
    "CTR": "CENTRE",
    "EST": "ESTATE",
    "IND": "INDUSTRIAL",
    "APT": "FLAT",
    "APARTMENT": "FLAT",
    "FLT": "FLAT",
    "STE": "SUITE",
    "FLR": "FLOOR",
    "FIRST": "1ST",
    "SECOND": "2ND",
    "THIRD": "3RD",
    "FOURTH": "4TH",
    "FIFTH": "5TH",
    "MT": "MOUNT",
    "WY": "WAY",
    "HWY": "HIGHWAY",
    "BLVD": "BOULEVARD",  # RULES_VERSION 3
}
_CARE_OF = re.compile(r"^(C\s*/\s*O|CARE OF)\b")
# A street line (RULES_VERSION 2, words added in 3): a token that starts with a digit, or, in a
# text of three or more tokens (the spec's floor, so never a key the spec did not give), a
# thoroughfare or building word after a name in its segment ("EXAMPLE HOUSE"; "ROAD TOWN" is a
# place), a German compound ending in STRASSE, a word that comes before the street's name ("RUE
# EXEMPLE"), or a unit word before a one-letter unit ("FLAT A"; "FLAT ROCK" is a place).
_STREET_WORDS = frozenset(
    {
        "STREET", "ROAD", "AVENUE", "LANE", "DRIVE", "COURT", "CRESCENT", "PLACE", "SQUARE",
        "GARDENS", "CLOSE", "TERRACE", "PARADE", "WAY", "HIGHWAY", "MEWS", "BOULEVARD", "HOUSE",
        "BUILDING", "BUILDINGS", "CENTRE", "ESTATE", "TOWER", "CHAMBERS",
        # RULES_VERSION 3
        "PARK", "GREEN", "TOWERS", "PLAZA", "HALL", "QUAY", "WHARF", "ROW", "WALK", "GROVE",
        "HILL", "MANSIONS", "LODGE", "STRASSE",
    }
)  # fmt: skip
# Before the name (RULES_VERSION 3): calle, rue, and улица, ул. and شارع as anyascii writes them.
_PREFIX_WORDS = frozenset({"CALLE", "RUE", "ULITSA", "UL", "SHR"})
_UNIT_WORDS = frozenset({"FLAT", "SUITE", "UNIT", "FLOOR", "OFFICE", "ROOM"})


def _street_word(i: int, out: list[str], starts: set[int]) -> bool:
    """Whether token i names a street or a building (see _STREET_WORDS)."""
    word = out[i]
    followed = i + 1 < len(out) and i + 1 not in starts
    return (
        (word in _STREET_WORDS and i not in starts)
        or (word.endswith("STRASSE") and len(word) > len("STRASSE"))
        or (word in _PREFIX_WORDS and followed)
        or (word in _UNIT_WORDS and followed and len(out[i + 1]) == 1)
    )


def address_key(text: str) -> str | None:
    """ "POSTCODE|TOKENS" for an address, or None when it has neither a postcode nor a street line.

    Real loaders build the text from structured fields (premises, address lines, locality,
    postcode). A key without a UK postcode starts with "NOPC|".
    """
    upper = anyascii(nfkc(text)).upper()
    postcode, rest = find_uk_postcode(upper)
    segments = [s.strip() for s in re.split(r"[,\n;]+", rest) if s.strip()]
    segments = [s for s in segments if not _CARE_OF.match(s)]
    grouped: list[list[str]] = []
    for segment in segments:
        segment = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", segment.replace("&", " AND "))
        tokens = [t for t in re.split(r"[^A-Z0-9-]+", segment) if t and t != "-"]
        if tokens:
            grouped.append(tokens)
    flat = [t for group in grouped for t in group]
    changed = True
    while changed and flat:
        changed = False
        for words in _COUNTRY_WORDS:
            if flat[-len(words) :] == words:
                flat = flat[: -len(words)]
                changed = True
                break
    ends: set[int] = set()
    count = 0
    for group in grouped:
        count += len(group)
        ends.add(count - 1)
    starts = {0} | {end + 1 for end in ends}
    out: list[str] = []
    for i, word in enumerate(flat):
        if word == "ST":
            # SAINT when it starts a segment ("12 Main St, St Albans"; RULES_VERSION 2).
            street = (i in ends or i == len(flat) - 2) and i not in starts
            out.append("STREET" if street and not flat[i - 1].isdigit() else "SAINT")
        else:
            out.append(_ABBREVIATIONS.get(word, word))
    has_street_line = any(t[:1].isdigit() for t in out) or (
        len(out) >= 3 and any(_street_word(i, out, starts) for i in range(len(out)))
    )
    if not postcode and not has_street_line:
        return None
    return (postcode or "NOPC") + "|" + " ".join(out)


def address_key_from_parts(parts: Iterable[str | None]) -> str | None:
    """Key from structured fields: premises, lines, locality, region, postcode, country."""
    return address_key(", ".join(p for p in parts if p))
