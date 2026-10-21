"""Alert headlines from a typology's wording templates (PHASE-1.md 5.4, 7.1, guardrail G5).

`render_headline` picks `headline_synthetic` for a `synthetic_scenario` alert and
`headline_structural` otherwise, fills in the metrics and refuses any result that is too long
for C4, matches a forbidden pattern (contracts/wording/forbidden-terms.txt), or says "synthetic
scenario" for an alert that is not a synthetic_scenario. Number format without a format spec:
thousands separators, at most two decimals (120000.0 gives 120,000). String metrics are codes
such as a currency; detectors never put names in metrics.
scripts/check_wording.py lints the string literals of this file in CI.
"""

import math
import string
from collections.abc import Mapping

from neonradar_contracts.alert import HEADLINE_MAX, WordingClass
from neonradar_contracts.wording import find_forbidden, says_synthetic_scenario
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
    if wording_class != "synthetic_scenario" and says_synthetic_scenario(headline):
        raise WordingError(f"only a synthetic_scenario headline may say so (7.1): {headline!r}")
    return headline
