"""Schema compatibility for cannot-link rule X2 (PHASE-2.md 7.1.3, M2.10a deliverable 2)."""

from __future__ import annotations

from collections.abc import Iterable

from followthemoney import model
from followthemoney.exc import InvalidData


def common_schema(names: Iterable[str]) -> str | None:
    """The most specific FtM schema common to every name, or None when there is none.

    Folds `followthemoney.model.common_schema` over the names (with FtM 4.11, `Person` and
    `LegalEntity` give `Person`; `Company`, `LegalEntity` and `Organization` give `Company`;
    `Person` and `Company`, and `Company` and `PublicBody`, have none).
    """
    best: str | None = None
    for name in names:
        if best is None:
            if model.get(name) is None:
                return None
            best = name
            continue
        try:
            best = model.common_schema(best, name).name
        except InvalidData:
            return None
    return best
