"""Alert headlines from a typology's wording templates (PHASE-1.md 5.4, 7.1, guardrail G5).

`render_headline` picks `headline_synthetic` for a `synthetic_scenario` alert and
`headline_structural` otherwise, fills in the metrics and refuses any result that is too long
for C4, matches a forbidden pattern (contracts/wording/forbidden-terms.txt), or says "synthetic
scenario" for an alert that is not a synthetic_scenario. Number format without a format spec:
thousands separators, at most two decimals (120000.0 gives 120,000). String metrics are codes
such as a currency; detectors never put names in metrics.

The explanation texts of an alert (M1.9b) are rendered here too, so that every entity-facing
word the detect package writes sits in this file: `payment_step` describes one payment,
`cycle_summary` a circular flow, and `check_rendered` lints the rendered texts with the source
values (entity captions, account numbers) masked out first (7.1).
scripts/check_wording.py lints the string literals of this file in CI.
"""

import math
import string
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

from neonradar_contracts.alert import HEADLINE_MAX, WordingClass
from neonradar_contracts.wording import SYNTHETIC_PHRASE, find_forbidden
from neonradar_detect.catalog import TypologyFile

MetricValue = int | float | str


class WordingError(ValueError):
    """A headline cannot be rendered within the wording rules."""


def format_metric(value: MetricValue, spec: str = "") -> str:
    """One metric as text; `spec` is the format spec of its placeholder, if any."""
    if isinstance(value, bool) or (isinstance(value, float) and not math.isfinite(value)):
        raise WordingError(f"metric value {value!r} cannot appear in a headline")
    if spec:
        try:
            return format(value, spec)
        except (TypeError, ValueError) as exc:
            raise WordingError(f"format spec {spec!r} does not fit metric value {value!r}") from exc
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return value


def render_headline(
    typology: TypologyFile, wording_class: WordingClass, metrics: Mapping[str, MetricValue]
) -> str:
    """The alert headline for `wording_class`, rendered from the typology's templates."""
    if typology.wording is None:
        raise WordingError(f"typology {typology.slug} has no wording templates")
    template = (
        typology.wording.headline_synthetic
        if wording_class == "synthetic_scenario"
        else typology.wording.headline_structural
    )
    pieces = []
    for literal, field, spec, _ in string.Formatter().parse(template):
        pieces.append(literal)
        if field is None:
            continue
        if field not in metrics:
            raise WordingError(f"metric {field!r} is missing for typology {typology.slug}")
        pieces.append(format_metric(metrics[field], spec or ""))
    headline = "".join(pieces)
    if len(headline) > HEADLINE_MAX:
        raise WordingError(f"headline has {len(headline)} characters; C4 allows {HEADLINE_MAX}")
    terms = find_forbidden(headline)
    if terms:
        raise WordingError(f"headline refused by the wording lint (7.1): {'; '.join(terms)}")
    if wording_class != "synthetic_scenario" and SYNTHETIC_PHRASE.search(headline):
        raise WordingError(f"only a synthetic_scenario headline may say so (7.1): {headline!r}")
    return headline


MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip
NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight")


def format_amount(amount: float) -> str:
    """Money in explanation texts: thousands separators; two decimals unless the amount is whole
    (120000.0 gives 120,000 and 141968.95 gives 141,968.95)."""
    if not math.isfinite(amount):
        raise WordingError(f"amount {amount!r} cannot appear in an explanation")
    return f"{amount:,.0f}" if amount == round(amount) else f"{amount:,.2f}"


def format_day(moment: datetime) -> str:
    """The UTC calendar day, `2 March 2026`, whatever the locale."""
    day = moment.astimezone(UTC)
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def format_duration(hours: float) -> str:
    """`30 hours` below two days, else days with one decimal (`6 days`, `6.3 days`)."""
    if hours < 48:
        whole = round(hours)
        return f"{whole} hour" if whole == 1 else f"{whole} hours"
    return f"{hours / 24:,.1f}".removesuffix(".0") + " days"


def payment_step(sender: str, currency: str, amount: float, receiver: str, moment: datetime) -> str:
    """One explanation step per payment: what was paid, between which accounts and when."""
    return (
        f"{sender} sent {currency} {format_amount(amount)} to {receiver} on {format_day(moment)}."
    )


def cycle_summary(
    origin: str, currency: str, sent: float, returned: float, others: int, hours: float
) -> str:
    """The summary of a circular flow: what left the origin account and what came back."""
    count = NUMBER_WORDS[others] if others < len(NUMBER_WORDS) else str(others)
    accounts = "other account" if others == 1 else "other accounts"
    return (
        f"{currency} {format_amount(sent)} left account {origin} and {currency} "
        f"{format_amount(returned)} came back to it after passing through {count} {accounts} "
        f"in {format_duration(hours)}."
    )


def check_rendered(texts: Mapping[str, str], mask: Iterable[str]) -> None:
    """The 7.1 lint on rendered alert texts (headline, summary, steps). The masked values are
    source data (entity captions, account numbers), not NeonRadar's wording, so they are
    blanked out first; any other match raises `WordingError`."""
    masked = list(mask)
    problems = [
        f"{where}: {'; '.join(terms)}"
        for where, text in texts.items()
        if (terms := find_forbidden(text, masked))
    ]
    if problems:
        raise WordingError(f"rendered text fails the wording lint (7.1): {' | '.join(problems)}")
