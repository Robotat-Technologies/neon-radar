"""Record cards for labelling and review (PHASE-2.md 7.3 rule 2, M2.10c deliverable 3).

`load(record_dirs, ids)` streams the record folders the CLI passes twice, keeping the needed
ids only: first the records themselves and the relationship records that touch them, then the
organisations they are linked to and the addresses they reference. A card shows the dataset
title, the schema, the names in their original scripts, birth dates, nationalities and
countries, postcodes and towns, linked organisations (names and numbers), identifiers and a
source link. It never shows a match probability, a rule, a method, a stratum or anyone's label:
none of them is passed in. The flag topics and the leak status that `er review` needs to say
whether a decision waits for a second reviewer come back separately (`Facts`), never on a card.
`side_by_side` lays two cards out in two columns. Nothing here logs a value.
"""

from __future__ import annotations

import textwrap
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Any

from followthemoney import model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import iter_records
from neonradar_keys.postcodes import find_uk_postcode, normalise_uk_postcode
from neonradar_resolve import policy
from neonradar_resolve.records import RELATIONS

NAMES = ("name", "alias", "previousName")
COUNTRIES = ("nationality", "citizenship", "country", "jurisdiction")
IDENTIFIERS = (
    ("registrationNumber", "registration number"),
    ("leiCode", "LEI"),
    ("idNumber", "identity number"),
    ("passportNumber", "passport number"),
    ("taxNumber", "tax number"),
    ("vatCode", "VAT number"),
)
NR_IDENTIFIERS = (("ch_person_number", "Companies House person number"),)
ORGANISATIONS = frozenset({"Company", "Organization", "PublicBody", "LegalEntity"})
MAX_VALUES = 10  # per row; the rest is counted
ROWS = (
    "Source", "Type", "Names", "Birth dates", "Countries", "Postcodes and towns", "Organisations",
    "Identifiers", "Source link",
)  # fmt: skip


@dataclass(frozen=True)
class Card:
    """What a labeller or reviewer sees about one record (7.3 rule 2)."""

    dataset: str  # the dataset's title
    schema: str
    names: tuple[str, ...]
    birth_dates: tuple[str, ...]
    countries: tuple[str, ...]
    places: tuple[str, ...]  # "postcode, town", from the record's addresses
    organisations: tuple[str, ...]  # "name (number)" of each linked organisation
    identifiers: tuple[str, ...]  # "kind: value"
    source: str | None

    def rows(self) -> list[tuple[str, str]]:
        values = (
            [self.dataset], [self.schema], self.names, self.birth_dates, self.countries,
            self.places, self.organisations, self.identifiers, [self.source or ""],
        )  # fmt: skip
        return [(row, _join(found)) for row, found in zip(ROWS, values, strict=True)]


@dataclass(frozen=True)
class Facts:
    """What `er review` needs about a record to tell whether a merge crosses P1 or P2."""

    flag_topics: frozenset[str]
    leaked: bool


def _join(values: Sequence[str]) -> str:
    shown = list(dict.fromkeys(v for v in values if v))
    if not shown:
        return "-"
    more = len(shown) - MAX_VALUES
    return "; ".join(shown[:MAX_VALUES]) + (f"; and {more} more" if more > 0 else "")


def _values(data: Mapping[str, Any], name: str) -> list[str]:
    found = (data.get("properties") or {}).get(name) or []
    return [str(v) for v in found if isinstance(v, str | int | float) and str(v).strip()]


def _files(record_dirs: Iterable[Path]) -> list[Path]:
    return [path for folder in record_dirs for path in sorted(Path(folder).glob("*.ftm.jsonl"))]


def _place(postcode: str | None, town: str | None) -> str | None:
    found = ", ".join(x for x in (postcode, town) if x)
    return found or None


def _text_place(text: str) -> str | None:
    """The postcode and the town of an address text: the last part without digits."""
    postcode, rest = find_uk_postcode(text)
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    towns = [p for p in parts if not any(c.isdigit() for c in p)]
    return _place(postcode, towns[-1] if len(parts) > 1 and towns else None)


def _address_place(data: Mapping[str, Any]) -> str | None:
    postcode = next(
        (found for v in _values(data, "postalCode") if (found := normalise_uk_postcode(v))), None
    )
    town = next(iter(_values(data, "city")), None)
    if postcode is None and town is None:
        texts = _values(data, "full")
        return _text_place(texts[0]) if texts else None
    return _place(postcode, town)


def _organisation(data: Mapping[str, Any]) -> str:
    name = next(iter(_values(data, "name")), "-")
    numbers = _values(data, "registrationNumber") or _values(data, "leiCode")
    return f"{name} ({', '.join(numbers)})" if numbers else name


def _ends(data: Mapping[str, Any]) -> tuple[list[str], list[str]] | None:
    schema = model.get(str(data.get("schema")))
    if schema is None or schema.edge_source is None or schema.edge_target is None:
        return None
    return _values(data, schema.edge_source), _values(data, schema.edge_target)


def load(
    record_dirs: Sequence[Path], ids: Iterable[str]
) -> tuple[dict[str, Card], dict[str, Facts]]:
    """Cards and facts for `ids` (ids missing from the folders are left out)."""
    wanted = set(ids)
    records: dict[str, Mapping[str, Any]] = {}
    linked: dict[str, set[str]] = {rid: set() for rid in wanted}
    files = _files(record_dirs)
    for path in files:  # pass 1: the records and the relationships that touch them
        for raw in iter_records(path):
            rid = raw.get("id")
            if rid in wanted:
                records[str(rid)] = raw
            elif raw.get("schema") in RELATIONS and (ends := _ends(raw)) is not None:
                sources, targets = ends
                for a in sources:
                    for b in targets:
                        if a in wanted and b != a:
                            linked[a].add(b)
                        if b in wanted and a != b:
                            linked[b].add(a)
    others = {x for found in linked.values() for x in found} | {
        x for data in records.values() for x in _values(data, "addressEntity")
    }
    extra: dict[str, Mapping[str, Any]] = {}
    for path in files if others else []:  # pass 2: linked organisations and addresses
        for raw in iter_records(path):
            rid = raw.get("id")
            if rid in others and raw.get("schema") in ORGANISATIONS | {"Address"}:
                extra[str(rid)] = raw
    registry = load_registry()
    cards: dict[str, Card] = {}
    facts: dict[str, Facts] = {}
    for rid, data in sorted(records.items()):
        dataset = registry.get(str((data.get("datasets") or [""])[0]))
        places = [
            p
            for a in _values(data, "addressEntity")
            if a in extra and (p := _address_place(extra[a]))
        ] + [p for text in _values(data, "address") if (p := _text_place(text))]
        organisations = [
            _organisation(extra[x])
            for x in sorted(linked.get(rid, ()))
            if x in extra and extra[x].get("schema") in ORGANISATIONS
        ]
        nr = data.get("nr") or {}
        identifiers = [f"{label}: {v}" for prop, label in IDENTIFIERS for v in _values(data, prop)]
        identifiers += [f"{label}: {nr[key]}" for key, label in NR_IDENTIFIERS if nr.get(key)]
        source = next(iter(_values(data, "sourceUrl")), None) or (dataset.url if dataset else None)
        cards[rid] = Card(
            dataset.title if dataset else "unknown dataset",
            str(data.get("schema")),
            tuple(v for prop in NAMES for v in _values(data, prop)),
            tuple(_values(data, "birthDate")),
            tuple(v for prop in COUNTRIES for v in _values(data, prop)),
            tuple(places),
            tuple(organisations),
            tuple(identifiers),
            source,
        )
        kind = policy.record_kind(dataset.kind or "", nr) if dataset else ""
        facts[rid] = Facts(policy.flag_topics(_values(data, "topics")), policy.is_leaked(kind))
    return cards, facts


def side_by_side(left: Card, right: Card, width: int = 100) -> str:
    """Two cards in two columns, row by row, under the headings Record 1 and Record 2."""
    label = max(len(r) for r in ROWS) + 2
    column = max(20, (width - label - 3) // 2)
    lines = [f"{'':<{label}}{'Record 1':<{column}} | Record 2"]
    for (row, a), (_, b) in zip(left.rows(), right.rows(), strict=True):
        wrapped = zip_longest(textwrap.wrap(a, column) or [""], textwrap.wrap(b, column) or [""])
        for n, (x, y) in enumerate(wrapped):
            lines.append(f"{row if n == 0 else '':<{label}}{x or '':<{column}} | {y or ''}")
    return "\n".join(lines)
