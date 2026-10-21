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
}
_CARE_OF = re.compile(r"^(C\s*/\s*O|CARE OF)\b")


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
    out: list[str] = []
    for i, word in enumerate(flat):
        if word == "ST":
            street = (i in ends or i == len(flat) - 2) and i > 0 and not flat[i - 1].isdigit()
            out.append("STREET" if street else "SAINT")
        else:
            out.append(_ABBREVIATIONS.get(word, word))
    has_street_line = any(t.isdigit() or t[:1].isdigit() for t in out) or len(out) >= 3
    if not postcode and not has_street_line:
        return None
    return (postcode or "NOPC") + "|" + " ".join(out)


def address_key_from_parts(parts: Iterable[str | None]) -> str | None:
    """Key from structured fields: premises, lines, locality, region, postcode, country."""
    return address_key(", ".join(p for p in parts if p))
