"""Country and nationality codes (research note names-addresses.md 9)."""

from __future__ import annotations

import csv
import io
from functools import lru_cache
from importlib.resources import files

from rigour.territories import lookup_territory


@lru_cache(maxsize=1)
def _nationalities() -> dict[str, str]:
    resource = files("neonradar_keys") / "data" / "nationalities.csv"
    text = resource.read_text(encoding="utf-8")
    return {row["value"].casefold(): row["country"] for row in csv.DictReader(io.StringIO(text))}


@lru_cache(maxsize=50_000)
def country_code(value: str | None) -> str | None:
    """Lower-case ISO alpha-2 code for a country name, demonym or code; UK nations map to "gb".

    Exact lookups in the Companies House and FCDO lists first, then rigour without fuzzy
    matching (fuzzy matching gives confident wrong answers). Unknown values give None.
    """
    if not value or not value.strip():
        return None
    text = value.strip()
    known = _nationalities().get(text.casefold())
    if known is not None:
        return known or None
    territory = lookup_territory(text)
    if territory is None:
        return None
    code = territory.ftm_country or territory.code
    return code.split("-")[0] if code else None
