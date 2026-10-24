"""Is a corporate PSC or corporate officer registered at Companies House? (PHASE-2.md M2.3b)

Written for NeonRadar from the rule described in bulk-sources-loading.md 3.6; no code was
copied from another project. The registry fields are free text and "isn't guaranteed to be
correct", so a number found here is evidence for rule D1, which still needs the name check.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from neonradar_keys.ids import uk_company_number
from neonradar_keys.names import name_similarity, org_key

UK_TOKENS = frozenset(
    {
        "united kingdom",
        "uk",
        "u.k.",
        "great britain",
        "gb",
        "england",
        "wales",
        "england and wales",
        "england & wales",
        "scotland",
        "northern ireland",
        "companies house",
        "uk companies house",
        "register of companies",
        "registrar of companies",
        "uk register of companies",
    }
)
UK_STARTS = (
    "companies house",
    "united kingdom (",
    "england and wales ",
    "england & wales ",
    "uk companies house",
    "uk register of companies",
)

Outcome = Literal["resolved", "name_mismatch", "number_not_found", "no_number", "non_uk"]


def _norm(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def _uk_like(value: str) -> bool:
    return value in UK_TOKENS or value.startswith(UK_STARTS)


def is_uk(identification: Mapping[str, str | None], address_country: str | None = None) -> bool:
    """True when the registry fields say Companies House.

    An explicit `country_registered` decides on its own. Without it, `place_registered` or
    `legal_authority` decides; with none of the three, the address country does.
    """
    country = _norm(identification.get("country_registered"))
    if country:
        return _uk_like(country)
    place = _norm(identification.get("place_registered"))
    authority = _norm(identification.get("legal_authority"))
    if place or authority:
        return _uk_like(place) or _uk_like(authority)
    return _uk_like(_norm(address_country))


def uk_number(raw: str | None) -> str | None:
    """A Companies House number in its 8-character form, or None: rule D1's normalisation
    (`neonradar_keys.ids.uk_company_number`), so a prefix Companies House does not use, or a
    value such as "N/A", gives None."""
    return uk_company_number(raw)


def names_agree(a: str, b: str, threshold: float = 0.85) -> bool:
    """The loader's name check for slice expansion: equal organisation keys, or Jaro-Winkler at
    least the threshold on them (the resolver applies its own check for D1)."""
    key_a, key_b = org_key(a).key, org_key(b).key
    return bool(key_a) and (key_a == key_b or name_similarity(key_a, key_b) >= threshold)


def resolve_corporate(
    name: str,
    identification: Mapping[str, str | None],
    address_country: str | None,
    company_names: Mapping[str, str],
) -> tuple[Outcome, str | None]:
    """Outcome and normalised number for one corporate PSC or officer.

    `company_names` maps company numbers in the Free Company Data index to company names.
    """
    if not is_uk(identification, address_country):
        return "non_uk", None
    number = uk_number(identification.get("registration_number"))
    if number is None:
        return "no_number", None
    known = company_names.get(number)
    if known is None:
        return "number_not_found", number
    if not names_agree(name, known):
        return "name_mismatch", number
    return "resolved", number
