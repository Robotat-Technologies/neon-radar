"""The name an alert is shown under (PHASE-4.md 5.3; PHASE-3.md R9).

An alert about a real organisation is shown under its typology's neutral shape name ("cash
deposits just below a threshold"), never under a name that sounds like conduct; an alert on
synthetic data keeps the typology's name, which teaches the subject. `AlertSummary.display_name`
and the UI's alert queue use this.
"""

from __future__ import annotations

from collections.abc import Mapping

from neonradar_detect.catalog import Typology


def shape_name(typologies: Mapping[str, Typology], slug: str) -> str | None:
    typology = typologies.get(slug)
    return typology.shape_name if typology is not None and typology.shape_name else None


def display_name(typologies: Mapping[str, Typology], slug: str, involves_real: bool) -> str:
    typology = typologies.get(slug)
    shape = shape_name(typologies, slug)
    if involves_real:
        return shape or "a structural pattern"
    return typology.name if typology is not None else slug
