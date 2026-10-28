"""Time helpers for generator v1 (PHASE-3.md 7.2.1).

Activity is generated in Europe/London local time and stored in UTC, as C1 R5 requires: clock
changes come from `zoneinfo` (with the pinned `tzdata` package). Working days exclude weekends and
the England and Wales bank holidays of 2025 and 2026 from GOV.UK (`synthetic-transactions.md` 2.6),
committed here as data because nothing may be fetched at run time (G3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

LONDON = ZoneInfo("Europe/London")

BANK_HOLIDAYS = frozenset(
    date.fromisoformat(d)
    for d in (
        "2025-01-01",
        "2025-04-18",
        "2025-04-21",
        "2025-05-05",
        "2025-05-26",
        "2025-08-25",
        "2025-12-25",
        "2025-12-26",
        "2026-01-01",
        "2026-04-03",
        "2026-04-06",
        "2026-05-04",
        "2026-05-25",
        "2026-08-31",
        "2026-12-25",
        "2026-12-28",
    )
)
COVERED = (date(2025, 1, 1), date(2027, 1, 1))  # the years the holiday table covers


@dataclass(frozen=True, slots=True)
class Period:
    """The generated activity period: start <= time < end, both UTC midnights."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        for moment in (self.start, self.end):
            if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
                raise ValueError("period bounds must be UTC")
        if self.end - self.start < timedelta(days=28):
            raise ValueError("a period needs at least 28 days")
        if not (COVERED[0] <= self.start.date() and self.end.date() <= COVERED[1]):
            raise ValueError("the bank holiday table covers 2025 and 2026 only; extend it first")

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    def months(self) -> list[date]:
        """The first day of every month that starts inside the period."""
        out = []
        d = date(self.start.year, self.start.month, 1)
        if d < self.start.date():
            d = _next_month(d)
        while d < self.end.date():
            out.append(d)
            d = _next_month(d)
        return out


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def is_working_day(d: date) -> bool:
    return d.weekday() < 5 and d not in BANK_HOLIDAYS


def working_days(start: date, end: date) -> list[date]:
    """Working days in England and Wales from start (inclusive) to end (exclusive)."""
    out = []
    d = start
    while d < end:
        if is_working_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


business_days = working_days


def previous_working_day(d: date) -> date:
    while not is_working_day(d):
        d -= timedelta(days=1)
    return d


def last_working_day(month_first: date) -> date:
    return previous_working_day(_next_month(month_first) - timedelta(days=1))


last_business_day = last_working_day


def local(day: date, seconds: int) -> datetime:
    """`seconds` after local midnight in London on `day`, as a UTC time to the second."""
    naive = datetime(day.year, day.month, day.day) + timedelta(seconds=seconds)
    return naive.replace(tzinfo=LONDON).astimezone(UTC)


def at(rng: np.random.Generator, day: date, first_hour: int = 8, last_hour: int = 18) -> datetime:
    """A London local time on `day` between first_hour:00 and last_hour:00, stored as UTC."""
    return local(day, int(rng.integers(first_hour * 3600, last_hour * 3600)))


def later(
    rng: np.random.Generator, moment: datetime, min_hours: float, max_hours: float
) -> datetime:
    """A time between min_hours and max_hours after `moment`, to the second."""
    seconds = int(rng.integers(int(min_hours * 3600), int(max_hours * 3600) + 1))
    return moment + timedelta(seconds=max(1, seconds))
