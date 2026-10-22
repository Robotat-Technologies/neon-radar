"""Deterministic rules D1 to D6 and human decisions D7 (PHASE-2.md 7.1.2, M2.10a deliverable 5).

Each rule gives `cluster.Link` objects with `method="deterministic"` and its rule id;
`cluster.resolve` then applies the name check, the cannot-link rules and the merge policy.
Every link has `record_a < record_b`, and the output is sorted, so runs are byte-stable.
The decisions file is written only by `neonradar er review` (M2.10c): this module only reads it.
"""

from __future__ import annotations

import itertools
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neonradar_resolve.cluster import Link, Member
from neonradar_resolve.features import address_keys, un_references
from neonradar_resolve.records import Corpus

CH_RECORD = "gbch-co-"  # D1 links each record to the Companies House record when the run has it
PERSON_NUMBER_CHARS = 8  # D3 compares the first 8 characters of nr.ch_person_number (3.3)
DECISIONS = ("same", "different")
PLACEHOLDER = "@todo"  # project.yaml handles not filled in yet (OD-22): never a reviewer


# A GitHub handle with its @: ASCII letters, digits and single inner hyphens, 39 at most.
HANDLE = re.compile(r"@[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,38}", re.ASCII)


def handle(value: object) -> str | None:
    """The handle in lower case (GitHub handles ignore case), or None when it is not one.

    Placeholders (`@TODO`) are not handles.
    """
    if not isinstance(value, str) or not value.isascii():
        return None  # before lower(): the Kelvin sign K lowers to an ASCII k
    text = value.strip().lower()
    return text if HANDLE.fullmatch(text) and text != PLACEHOLDER else None


class DecisionsError(ValueError):
    """A malformed decisions file; the message names the line, never a value."""

    exit_code = 2
    counts_only = True  # file name, line number and the rule only: safe on a real profile


Pair = tuple[str, str]  # record ids, the smaller first


def _pair(a: str, b: str) -> Pair:
    return (a, b) if a < b else (b, a)


def _pairs(groups: Mapping[str, Iterable[str]]) -> set[Pair]:
    return {pair for ids in groups.values() for pair in itertools.combinations(sorted(set(ids)), 2)}


def _group(items: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for key, rid in items:
        groups.setdefault(key, []).append(rid)
    return groups


def d1(members: Mapping[str, Member]) -> set[Pair]:
    """D1: organisations and legal entities with the same UK company number."""
    groups = _group(
        (n, m.record_id)
        for m in members.values()
        if m.entity_class in ("org", "legal_entity")
        for n in m.company_numbers
    )
    pairs: set[Pair] = set()
    for number, ids in groups.items():
        hub = f"{CH_RECORD}{number}"
        if hub in ids:
            pairs.update(_pair(hub, rid) for rid in ids if rid != hub)
        else:
            pairs.update(_pairs({number: ids}))
    return pairs


def d2(members: Mapping[str, Member]) -> set[Pair]:
    """D2: records with the same valid LEI."""
    return _pairs(_group((x, m.record_id) for m in members.values() for x in m.leis))


def d3(corpus: Corpus, members: Mapping[str, Member]) -> set[Pair]:
    """D3: person records with the same first 8 characters of `nr.ch_person_number`."""
    items = []
    for rid, m in members.items():
        number = corpus.records[rid].nr.get("ch_person_number")
        if m.entity_class == "person" and isinstance(number, str):
            number = number.strip().upper()
            if len(number) >= PERSON_NUMBER_CHARS:
                items.append((number[:PERSON_NUMBER_CHARS], rid))
    return _pairs(_group(items))


def d4(corpus: Corpus, members: Mapping[str, Member]) -> set[Pair]:
    """D4: listed records from different lists with the same UN reference number."""
    groups = _group(
        (ref, rid)
        for rid, m in members.items()
        if m.flag_topics and m.list_source
        for ref in un_references(corpus, corpus.records[rid])
    )
    return {(a, b) for a, b in _pairs(groups) if members[a].list_source != members[b].list_source}


def d5(corpus: Corpus) -> set[Pair]:
    """D5: two records of one dataset with the same native id in `nr.source_ref`."""
    items = []
    for rid, record in corpus.records.items():
        ref = record.nr.get("source_ref")
        if isinstance(ref, str) and ref:
            items.append((f"{record.dataset}|{ref}", rid))
    return _pairs(_group(items))


def d6(corpus: Corpus) -> set[Pair]:
    """D6: Address records with the same address key (a full postcode or a street line).

    Each record links to the smallest record id of its key (synthetic and real records apart,
    X1), so a key shared by n records gives n - 1 links, not n(n - 1)/2.
    """
    groups = _group(
        (f"{corpus.records[rid].synthetic}|{key}", rid) for rid, key in address_keys(corpus).items()
    )
    pairs: set[Pair] = set()
    for ids in groups.values():
        hub = min(ids)
        pairs.update(_pair(hub, rid) for rid in ids if rid != hub)
    return pairs


def deterministic(corpus: Corpus, members: Mapping[str, Member]) -> list[Link]:
    """The links of D1 to D6, sorted by rule and record ids."""
    found = {
        "D1": d1(members),
        "D2": d2(members),
        "D3": d3(corpus, members),
        "D4": d4(corpus, members),
        "D5": d5(corpus),
        "D6": d6(corpus),
    }
    return [
        Link(a, b, "deterministic", rule) for rule, pairs in found.items() for a, b in sorted(pairs)
    ]


@dataclass(frozen=True)
class Decisions:
    same: list[Link]  # D7 links, each with the handles whose newest line says same
    different: list[tuple[str, str]]  # X8 pairs
    on_file: int  # pairs with at least one decision


def read_decisions(path: Path | None, reviewers: frozenset[str] | None = None) -> Decisions:
    """For each pair the newest line decides (by `at` in UTC, then by line order).

    A `same` link carries `reviewers`: the handles whose own newest line for the pair says
    `same` (7.1.8). A missing file means no decisions. Every `by` must be a GitHub handle;
    with `reviewers` (a real profile: people.er_labellers and people.er_senior_reviewers) it
    must also be one of them, so an unlisted name fails the run instead of counting.
    """
    if path is None or not path.is_file():
        return Decisions([], [], 0)
    Stamp = tuple[datetime, int, str]
    newest: dict[tuple[str, str], Stamp] = {}
    by_handle: dict[tuple[str, str], dict[str, Stamp]] = {}
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            where = f"{path.name}:{number}"
            try:
                data = json.loads(line)
                a, b, decision = data["record_a"], data["record_b"], data["decision"]
                by, at = handle(data["by"]), datetime.fromisoformat(data["at"])
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise DecisionsError(f"{where}: not a decision line") from exc
            strings = all(isinstance(v, str) and v for v in (a, b))
            if not strings or decision not in DECISIONS or a == b:
                raise DecisionsError(f"{where}: not a decision line")
            if by is None:
                raise DecisionsError(f"{where}: `by` is not a GitHub handle")
            if reviewers is not None and by not in reviewers:
                raise DecisionsError(
                    f"{where}: the reviewer is not in people.er_labellers or"
                    " people.er_senior_reviewers"
                )
            if at.tzinfo is None:
                raise DecisionsError(f"{where}: the time has no offset")
            pair = (min(a, b), max(a, b))
            stamp = (at.astimezone(UTC), number, decision)
            if pair not in newest or stamp > newest[pair]:
                newest[pair] = stamp
            own = by_handle.setdefault(pair, {})
            if by not in own or stamp > own[by]:
                own[by] = stamp
    same, different = [], []
    for pair in sorted(newest):
        if newest[pair][2] == "same":
            reviewers = frozenset(h for h, s in by_handle[pair].items() if s[2] == "same")
            same.append(Link(pair[0], pair[1], "human", "D7", reviewers=reviewers))
        else:
            different.append(pair)
    return Decisions(same, different, len(newest))
