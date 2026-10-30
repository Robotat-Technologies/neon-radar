"""Shared helpers for the official sanctions list loaders (PHASE-2.md M2.6).

Pure functions only: no I/O, no network. The loaders build FtM entities with them.
"""

from __future__ import annotations

import calendar
import hashlib
import re
from collections.abc import Iterable

from neonradar_keys.ids import is_valid_lei, uk_company_number, un_reference

MIN_YEAR = 1800
MAX_YEAR = 2100
MAX_YEAR_SPAN = 20  # a wider birth year range gives no birth date

_PLACEHOLDER = re.compile(r"^(?:d{1,2}|m{1,2}|0{1,2})$", re.I)
_DMY = re.compile(r"^\s*(\w{1,2})\s*[/.-]\s*(\w{1,2})\s*[/.-]\s*(\d{4})\s*$")
_ISO = re.compile(r"^\s*(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:T[\d:.]+)?(?:Z|[+-]\d{2}:?\d{2})?\s*$")
_YEAR = re.compile(r"^\s*(\d{4})\s*$")
_LEI = re.compile(r"\b[A-Z0-9]{18}[0-9]{2}\b")
_UK_REGISTER = (
    r"(?:companies\s+house|united\s+kingdom|great\s+britain|england\s*(?:and|&)\s*wales"
    r"|(?<!new\s)england|scotland|northern\s+ireland|(?<![a-z])(?:uk|u\.k\.|gb)(?![a-z]))"
)
_NUMBER = r"(?<![a-z0-9])([a-z]{2}\d{6}|r0\d{6}|\d{8})(?![a-z0-9])"
# A number label: up to two words such as "company" or "registration", then "no", "number",
# "nr" or "#" ("UK Company Number", "Companies House No.", "Reg. No.", "Registered No:").
_LABEL = (
    r"(?:(?:company|companies|registration|registered|reg\.?|incorporation)\s*){0,2}"
    r"(?:no\b\.?|number|nr\b\.?|#)"
)
_GAP = r"[\s,:()-]{0,3}"  # between a register and a label: separators only, never words
_TO_NUMBER = r"[\s.:#-]{0,3}"
# "UK Company Number 01234567", "Registered in England and Wales under number 07654321"
_FORWARD = re.compile(
    _UK_REGISTER + _GAP + r"(?:(?:under|with)\s+)?" + _LABEL + _TO_NUMBER + _NUMBER, re.I
)
# "Company registration number (UK) OC301234"
_MIDDLE = re.compile(_LABEL + r"\s*\(\s*" + _UK_REGISTER + r"\s*\)" + _TO_NUMBER + _NUMBER, re.I)
# "Company number 01234567 (UK)", "Company no. 01234567, registered in England"
_BACKWARD = re.compile(
    _LABEL
    + _TO_NUMBER
    + _NUMBER
    + r"[\s,]{0,3}(?:\(\s*"
    + _UK_REGISTER
    + r"\s*\)|registered\s+in\s+(?:the\s+)?"
    + _UK_REGISTER
    + ")",
    re.I,
)
# Words that make the clause about another company ("Parent company: UK Company Number ...").
_RELATED = re.compile(
    r"\b(?:subsidiar|parent|owned\s+by|owner|shareholder|affiliate|holding\s+compan)", re.I
)
_CLAUSE_END = ";|\n"


def _int(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    return int(text) if text.isdigit() else None


def partial_date(
    year: int | str | None, month: int | str | None = None, day: int | str | None = None
) -> str | None:
    """ISO date with the precision the source gives: "1970", "1970-05" or "1970-05-17".

    A missing or zero part ends the date there. An impossible month gives the year only, an
    impossible day gives the year and month. A year outside 1800 to 2100 gives None.
    """
    y, m, d = _int(year), _int(month), _int(day)
    if y is None or not MIN_YEAR <= y <= MAX_YEAR:
        return None
    if not m or not 1 <= m <= 12:
        return f"{y:04d}"
    if not d or not 1 <= d <= calendar.monthrange(y, m)[1]:
        return f"{y:04d}-{m:02d}"
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_dmy(text: str | None) -> str | None:
    """UK list dates: "17/05/1970", "dd/05/1970", "dd/mm/1970", "00/00/1970" or "1970"."""
    if not text or not text.strip():
        return None
    year_only = _YEAR.match(text)
    if year_only:
        return partial_date(year_only.group(1))
    match = _DMY.match(text)
    if not match:
        return None
    day, month, year = match.groups()
    if _PLACEHOLDER.match(month):
        return partial_date(year)
    if _PLACEHOLDER.match(day):
        return partial_date(year, month)
    if not (day.isdigit() and month.isdigit()):
        return None
    return partial_date(year, month, day)


def parse_iso(text: str | None) -> str | None:
    """ISO dates with an optional time or offset: "1970-05-17", "1970-05-17-04:00", "1970"."""
    if not text:
        return None
    match = _ISO.match(text)
    if not match:
        return None
    return partial_date(*match.groups())


def year_range(first: int | str | None, last: int | str | None) -> list[str]:
    """Birth years for a range such as the UN "BETWEEN" dates: every year of a range that spans
    at most 20 years, so rule X5 can compare each of them; nothing for a wider range, which says
    too little to compare. One known end gives that year."""
    a, b = _int(first), _int(last)
    years = sorted({y for y in (a, b) if y is not None and MIN_YEAR <= y <= MAX_YEAR})
    if len(years) == 2:
        if years[1] - years[0] > MAX_YEAR_SPAN:
            return []
        years = list(range(years[0], years[1] + 1))
    return [f"{y:04d}" for y in years]


def period_dates(
    start: tuple[int | None, int | None, int | None], end: tuple[int | None, int | None, int | None]
) -> list[str]:
    """Dates for an OFAC DatePeriod given as (year, month, day) at its start and end.

    Equal ends give that date; a whole calendar year gives the year; a whole month gives the
    year and month; anything else gives the years from year_range.
    """
    if start == end:
        value = partial_date(*start)
        return [value] if value else []
    (y1, m1, d1), (y2, m2, d2) = start, end
    if y1 is not None and y1 == y2:
        if (m1, d1, m2, d2) == (1, 1, 12, 31):
            value = partial_date(y1)
            return [value] if value else []
        if m1 is not None and m1 == m2 and d1 == 1 and d2 == calendar.monthrange(y1, m1)[1]:
            value = partial_date(y1, m1)
            return [value] if value else []
    return year_range(y1, y2)


def join_name(parts: Iterable[str | None]) -> str | None:
    """Join name parts in the given order with single spaces; None when nothing is left."""
    words = [" ".join(p.split()) for p in parts if p and p.strip()]
    return " ".join(words) or None


def split_values(text: str | None, separators: str = "|") -> list[str]:
    """Split a multi-value field on any of the separator characters, dropping empty values."""
    if not text:
        return []
    pattern = "[" + re.escape(separators) + "]"
    return [v.strip() for v in re.split(pattern, text) if v.strip()]


def extract_leis(text: str | None) -> list[str]:
    """Every 20-character token in the text that passes the ISO 17442 check digits."""
    if not text:
        return []
    found = (m.group(0) for m in _LEI.finditer(text.upper()))
    return sorted({lei for lei in found if is_valid_lei(lei)})


def uk_company_numbers(text: str | None) -> list[str]:
    """UK company numbers from free text, only where the text labels them as such.

    A candidate is exactly eight digits, or a Companies House prefix and six digits, written
    after a number label ("company number", "registration no.", "reg. no.", "no.", "#"). It
    counts when a UK register (Companies House, United Kingdom, UK, GB, England and Wales,
    Scotland, Northern Ireland) is named right before the label, in brackets between the label
    and the number, or right after the number in brackets or as "registered in ...". Only
    separators may come between the register and the label, so "registered in Cyprus" or
    "incorporated in Malta" can never sit between them. A clause (the text since the last ";",
    "|" or line break) that mentions a subsidiary, parent, owner or shareholder gives nothing:
    the number may belong to the other company. Anything else is not a UK company number.
    """
    if not text:
        return []
    numbers: set[str] = set()
    for pattern in (_FORWARD, _MIDDLE, _BACKWARD):
        for match in pattern.finditer(text):
            start = max(text.rfind(end, 0, match.start()) for end in _CLAUSE_END)
            clause = text[start + 1 : match.end()]
            if _RELATED.search(clause):
                continue
            number = uk_company_number(match.group(1))
            if number:
                numbers.add(number)
    return sorted(numbers)


def un_references(values: Iterable[str | None]) -> list[str]:
    """Normalised UN reference numbers (rule D4), deduplicated and sorted."""
    return sorted({ref for ref in (un_reference(v) for v in values) if ref})


def sanction_id(prefix: str, party_id: str, designation_key: str) -> str:
    """Id of the Sanction record for one designation of one party (PHASE-2.md 4.4)."""
    digest = hashlib.sha1(f"{party_id}|{designation_key}".encode(), usedforsecurity=False)
    return f"{prefix}-sanction-{digest.hexdigest()[:20]}"


def check_bounds(
    slug: str, counts: dict[str, int], bounds: dict[str, dict[str, list[int]]]
) -> list[str]:
    """Messages for every schema whose count is outside the range in bounds.yaml."""
    problems = []
    for schema, (low, high) in sorted(bounds.get(slug, {}).items()):
        count = counts.get(schema, 0)
        if not low <= count <= high:
            problems.append(
                f"unexpected size for {slug}: {schema} {count}, expected {low} to {high}; "
                "the format may have changed"
            )
    return problems
