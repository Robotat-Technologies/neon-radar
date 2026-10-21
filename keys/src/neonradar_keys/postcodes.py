"""UK postcodes (research note names-addresses.md 7)."""

from __future__ import annotations

import re
from dataclasses import dataclass

POSTCODE_RE = re.compile(
    r"(?<![A-Z0-9])(GIR ?0AA|(?:[A-Z][0-9]{1,2}|[A-Z][A-HJ-Y][0-9]{1,2}|[A-Z][0-9][A-Z]"
    r"|[A-Z][A-HJ-Y][0-9][A-Z]) ?[0-9][ABD-HJLNP-UW-Z]{2})(?![A-Z0-9])"
)


@dataclass(frozen=True)
class PostcodeParts:
    postcode: str
    outward: str
    inward: str
    area: str
    district: str
    sector: str


def normalise_uk_postcode(text: str) -> str | None:
    """Upper case, one space before the inward code; None when the text is not a UK postcode."""
    compact = re.sub(r"\s+", "", text.upper())
    if len(compact) < 5:
        return None
    candidate = f"{compact[:-3]} {compact[-3:]}"
    return candidate if POSTCODE_RE.fullmatch(candidate) else None


def find_uk_postcode(text: str) -> tuple[str | None, str]:
    """The last UK postcode in a text, normalised, and the text without it."""
    upper = text.upper()
    matches = list(POSTCODE_RE.finditer(upper))
    if not matches:
        return None, text
    last = matches[-1]
    return normalise_uk_postcode(last.group(1)), text[: last.start()] + " " + text[last.end() :]


def postcode_parts(postcode: str) -> PostcodeParts:
    outward, inward = postcode.split(" ")
    area_match = re.match(r"[A-Z]{1,2}", outward)
    area = area_match.group(0) if area_match else outward
    return PostcodeParts(postcode, outward, inward, area, outward, f"{outward} {inward[0]}")
