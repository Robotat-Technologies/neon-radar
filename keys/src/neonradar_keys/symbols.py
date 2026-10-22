"""Arabic index into rigour's Wikidata name groups (built by scripts/build_ar_symbol_index.py)."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files
from itertools import pairwise

from neonradar_keys.arabic import ar_normalize


@lru_cache(maxsize=1)
def _index() -> dict[str, list[str]]:
    resource = files("neonradar_keys") / "data" / "ar_symbols.json.gz"
    with resource.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as handle:
        data: dict[str, object] = json.load(handle)
    groups = data["groups"]
    if not isinstance(groups, dict):
        raise ValueError("ar_symbols.json.gz: 'groups' must be an object")
    return groups


def arabic_symbols(tokens: Iterable[str]) -> set[str]:
    """QIDs for normalised Arabic tokens and adjacent token pairs (for compound given names)."""
    items = [ar_normalize(t) for t in tokens]
    keys = set(items) | {a + " " + b for a, b in pairwise(items)}
    index = _index()
    return {qid for key in keys for qid in index.get(key, [])}
