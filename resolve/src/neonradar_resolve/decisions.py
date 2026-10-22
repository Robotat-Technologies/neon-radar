"""The decisions file: human same and different decisions (PHASE-2.md 7.1.8, M2.10c deliverable 1).

`load_decisions(path, member_ids)` reads the file `er run` passes (`decisions_file(profile)`):
for each pair of records the newest line wins, and the supporters of a `same` decision are the
handles whose own newest line for that pair says `same` (`rules.read_decisions`, M2.10a). It
returns the D7 links and X8 pairs whose two records are resolvable records of this run and
counts the others as not applicable (for example a decision made on another profile).
`append_decision` is the only writer (`neonradar er review`); it refuses a `same` decision
without a note. A one-reviewer `same` decision still passes through `run.guard_decisions`
before any clustering applies it. Nothing here prints or logs a record id, a handle or a note.
"""

from __future__ import annotations

import json
import os
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neonradar_resolve.rules import DECISIONS, Decisions, DecisionsError, handle, read_decisions

__all__ = [
    "Decisions", "DecisionsError", "append_decision", "count_on_file", "load_decisions",
    "review_queue",
]  # fmt: skip


def load_decisions(
    path: Path | None, member_ids: Collection[str], reviewers: frozenset[str] | None = None
) -> Decisions:
    """The D7 links and X8 pairs about two records of `member_ids`; the rest are counted.

    `on_file` counts every pair with a decision; `not_applicable` those with a record outside
    `member_ids`. `reviewers` as in `rules.read_decisions` (a real profile's listed handles).
    """
    found = read_decisions(path, reviewers)
    same = [x for x in found.same if x.record_a in member_ids and x.record_b in member_ids]
    different = [(a, b) for a, b in found.different if a in member_ids and b in member_ids]
    outside = len(found.same) - len(same) + len(found.different) - len(different)
    return Decisions(same, different, found.on_file, outside)


def count_on_file(path: Path | None) -> int:
    """Pairs with a decision, for a run that ignores the file (`er run --no-decisions`, 7.3).

    The lines are checked as `read_decisions` checks them, but no reviewer list applies: the
    count is reported, never applied.
    """
    return read_decisions(path).on_file


def append_decision(
    path: Path,
    record_a: str,
    record_b: str,
    decision: str,
    by: str,
    note: str | None,
    *,
    at: datetime | None = None,
) -> None:
    """Append one decision line (7.1.8); `same` needs a note. The time is UTC, to the second."""
    if decision not in DECISIONS:
        raise DecisionsError("a decision is same or different")
    reviewer = handle(by)
    if reviewer is None:
        raise DecisionsError("`by` is not a GitHub handle")
    if not all(isinstance(rid, str) and rid.strip() == rid and rid for rid in (record_a, record_b)):
        raise DecisionsError("a decision needs two record ids")
    if record_a == record_b:
        raise DecisionsError("a decision needs two different records")
    text = (note or "").strip()
    if decision == "same" and not text:
        raise DecisionsError("a same decision needs a note (7.1.8)")
    when = (at or datetime.now(UTC)).astimezone(UTC)
    line = {
        "record_a": min(record_a, record_b),
        "record_b": max(record_a, record_b),
        "decision": decision,
        "by": reviewer,
        "at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": text or None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle_:
        handle_.write(json.dumps(line, ensure_ascii=False) + "\n")
        handle_.flush()
        os.fsync(handle_.fileno())


def _deciders(path: Path | None) -> dict[tuple[str, str], set[str]]:
    """Every handle with a line about each pair (the file is checked by `read_decisions`)."""
    out: dict[tuple[str, str], set[str]] = {}
    if path is None or not path.is_file():
        return out
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.strip():
                data = json.loads(line)
                a, b = data["record_a"], data["record_b"]
                if who := handle(data["by"]):
                    out.setdefault((min(a, b), max(a, b)), set()).add(who)
    return out


def review_queue(
    candidates: Iterable[Mapping[str, Any]],
    path: Path | None,
    reviewer: str,
    seniors: frozenset[str] | set[str],
    clusters: Mapping[str, Sequence[str]],
) -> list[Mapping[str, Any]]:
    """The possible matches `er review` shows: by probability, those without one last.

    `clusters` maps each canonical id of the run to its record ids. Left out, for the two
    clusters of a possible match: a newest `different` decision about any of their records
    (X8, a hard conflict never reaches review, 7.1.3); a `same` decision that two reviewers or a
    senior reviewer support (a run applies it); and any decision of this reviewer.
    """
    found = read_decisions(path)
    deciders = _deciders(path)
    canonical = {rid: cid for cid, ids in clusters.items() for rid in ids}

    def key(a: str, b: str) -> frozenset[str] | None:
        if a in canonical and b in canonical:
            return frozenset((canonical[a], canonical[b]))
        return None

    hidden = {key(a, b) for a, b in found.different}
    hidden |= {
        key(x.record_a, x.record_b)
        for x in found.same
        if len(x.reviewers) >= 2 or x.reviewers & seniors
    }
    hidden |= {key(a, b) for (a, b), who in deciders.items() if reviewer in who}
    shown = [c for c in candidates if frozenset((str(c["a"]), str(c["b"]))) not in hidden]
    return sorted(
        shown,
        key=lambda c: (
            c.get("match_probability") is None,
            -float(c.get("match_probability") or 0.0),
            str(c["record_a"]),
            str(c["record_b"]),
        ),
    )
