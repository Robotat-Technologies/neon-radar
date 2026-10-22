"""Identifiers used by the deterministic rules (PHASE-2.md 7.1.2)."""

from __future__ import annotations

import re

from rigour.ids import LEI

# ASCII digits only: \d would also accept Arabic-Indic and fullwidth digits (RULES_VERSION 2).
_COMPANY_NUMBER = re.compile(r"^([A-Z]{0,2})([0-9]+)$")

# Companies House company number prefixes (bulk-sources-loading.md 2.6): the official list of
# May 2012 plus the newer prefixes named by the community. "R0" is a prefix followed by six digits.
CH_PREFIXES = frozenset(
    {"AC", "FC", "GE", "GN", "GS", "IC", "IP", "LP", "NA", "NF", "NI", "NL", "NO", "NP", "NR"}
    | {"NZ", "OC", "R0", "RC", "SA", "SC", "SF", "SI", "SL", "SO", "SP", "SR", "SZ", "ZC"}
    | {"CE", "CS", "FE", "OE", "PC", "SE", "SG"}
)
# The synthetic benchmark's company number prefix (M2.9): not a Companies House prefix.
SYNTHETIC_PREFIX = "SY"


def uk_company_number(value: str | None, *, synthetic: bool = False) -> str | None:
    """Rule D1 normalisation: the 8-character Companies House form, or None.

    Upper case; spaces, dots and hyphens removed; all digits are left-padded to 8; one or two
    letters followed by digits keep the letters and pad the digits to 8 characters in all. The
    result must be all digits or start with a Companies House prefix. The synthetic prefix "SY"
    counts only when `synthetic` is true (records of a synthetic dataset). Anything else is not a
    UK company number, and so are numbers with non-ASCII digits or only zeros (a placeholder
    such as "0" would link unrelated records under D1 and separate them under X3).
    """
    if not value:
        return None
    text = re.sub(r"[\s.\-]", "", value).upper()
    match = _COMPANY_NUMBER.match(text)
    if not match:
        return None
    prefix, digits = match.groups()
    width = 8 - len(prefix)
    if len(digits) > width or not digits.strip("0"):
        return None
    number = prefix + digits.zfill(width)
    if has_ch_prefix(number) or (synthetic and number.startswith(SYNTHETIC_PREFIX)):
        return number
    return None


def has_ch_prefix(number: str) -> bool:
    """True for an all-digit (ASCII) number or one that starts with a Companies House prefix."""
    return (number.isascii() and number.isdigit()) or number[:2] in CH_PREFIXES


def is_valid_lei(value: str | None) -> bool:
    if not value:
        return False
    return bool(LEI.is_valid(value.strip().upper()))


def un_reference(value: str | None) -> str | None:
    """UN Security Council reference such as "QDi.123": upper case, no spaces or final dot."""
    if not value:
        return None
    text = re.sub(r"\s+", "", value).upper().rstrip(".")
    return text or None
