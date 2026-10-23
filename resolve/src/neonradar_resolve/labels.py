"""Label files of an evaluation sample (PHASE-2.md 7.3, M2.10c deliverables 5 and 7).

Each labeller's answers go to `labels_dir(profile, run_id)/<handle>.jsonl`, one line per answer,
appended at once (`append_label`); the newest line of a handle for a pair counts. Only a person
at a terminal writes them (`neonradar er label`); this module never chooses, fills in or infers
a label (G10). `next_pair` resumes where a labeller stopped; `adjudication_queue` gives the S4
pairs whose two labels differ, for an adjudicator who labelled neither and did not set the
thresholds (7.3 rule 4). Nothing here prints a record id, a handle or a note.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neonradar_resolve.rules import handle
from neonradar_resolve.sample import Pair

LABELS = ("same", "different", "unsure")
ANSWERS = {"s": "same", "d": "different", "u": "unsure"}
SUFFIX = ".jsonl"


class LabelsError(ValueError):
    """An unreadable label file or a refused answer; the message names a file by its place
    (never by its name, a handle) and a line."""

    exit_code = 2
    counts_only = True


@dataclass(frozen=True)
class Label:
    pair_id: str
    label: str  # same | different | unsure
    by: str
    at: datetime
    adjudication: bool
    note: str | None = None
    line: int = 0  # breaks ties between lines with the same time


def label_file(folder: Path, by: str) -> Path:
    """`<handle>.jsonl` in the run's labels folder (the @ keeps it apart from sample.jsonl)."""
    who = handle(by)
    if who is None:
        raise LabelsError("the labeller is not a GitHub handle")
    return folder / f"{who}{SUFFIX}"


def append_label(
    folder: Path,
    pair_id: str,
    label: str,
    by: str,
    note: str | None = None,
    *,
    adjudication: bool = False,
    at: datetime | None = None,
) -> None:
    """Append one answer to the labeller's file at once (`er label` calls it per answer)."""
    if label not in LABELS:
        raise LabelsError("a label is same, different or unsure")
    path = label_file(folder, by)
    line = {
        "pair_id": pair_id,
        "label": label,
        "by": path.name.removesuffix(SUFFIX),
        "at": (at or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adjudication": adjudication,
        "note": (note or "").strip() or None,
    }
    folder.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle_:
        handle_.write(json.dumps(line, ensure_ascii=False) + "\n")
        handle_.flush()
        os.fsync(handle_.fileno())


def read_labels(folder: Path) -> list[Label]:
    """Every line of every `@<handle>.jsonl` file; a line's `by` must match its file. An error
    names a file by its place in sorted order, never by its name (which is a handle)."""
    found: list[Label] = []
    paths = sorted(folder.glob(f"@*{SUFFIX}"))
    for place, path in enumerate(paths, start=1):
        owner = path.name.removesuffix(SUFFIX)
        with path.open(encoding="utf-8") as lines:
            for number, text in enumerate(lines, start=1):
                if not text.strip():
                    continue
                where = f"label file {place} of {len(paths)}, line {number}"
                try:
                    data = json.loads(text)
                    at = datetime.fromisoformat(data["at"])
                    label = Label(
                        str(data["pair_id"]),
                        data["label"],
                        str(data["by"]),
                        at,
                        data["adjudication"] is True,
                        data.get("note"),
                        number,
                    )
                except (ValueError, KeyError, TypeError) as exc:
                    raise LabelsError(f"{where}: not a label line") from exc
                if label.label not in LABELS or at.tzinfo is None:
                    raise LabelsError(f"{where}: not a label line")
                if handle(label.by) != owner:
                    raise LabelsError(f"{where}: the line's labeller is not the file's")
                found.append(label)
    return found


def newest(labels: Iterable[Label], *, adjudication: bool) -> dict[tuple[str, str], Label]:
    """The newest label of each (handle, pair id), of one kind (answers or adjudications)."""
    out: dict[tuple[str, str], Label] = {}
    for label in labels:
        if label.adjudication != adjudication:
            continue
        key = (label.by, label.pair_id)
        current = out.get(key)
        if current is None or (label.at, label.line) >= (current.at, current.line):
            out[key] = label
    return out


def answers(pair: Pair, labels: Iterable[Label]) -> list[Label]:
    """The newest answer of each labeller assigned to the pair, in assignment order."""
    found = newest(labels, adjudication=False)
    return [found[(h, pair.pair_id)] for h in pair.labellers if (h, pair.pair_id) in found]


def next_pair(pairs: Sequence[Pair], labels: Iterable[Label], by: str) -> tuple[int, Pair] | None:
    """The first pair assigned to `by` that `by` has not answered (its place counts from 1)."""
    done = {pid for (who, pid) in newest(labels, adjudication=False) if who == by}
    mine = [p for p in pairs if by in p.labellers]
    for number, pair in enumerate(mine, start=1):
        if pair.pair_id not in done:
            return number, pair
    return None


def disagreements(pairs: Sequence[Pair], labels: Sequence[Label]) -> list[Pair]:
    """S4 pairs whose two labellers both answered, differently."""
    out = []
    for pair in pairs:
        given = answers(pair, labels)
        if pair.overlap and len(given) == 2 and given[0].label != given[1].label:
            out.append(pair)
    return out


def answered_by(pair: Pair, labels: Iterable[Label]) -> set[str]:
    """The pair's labellers and anyone else with an answer (not an adjudication) for it."""
    return set(pair.labellers) | {
        x.by for x in labels if not x.adjudication and x.pair_id == pair.pair_id
    }


def eligible_adjudicator(
    pair: Pair, by: str, barred: Iterable[str], labels: Iterable[Label] = ()
) -> bool:
    """Neither assigned the pair nor one who labelled it, and not a person who set the
    thresholds (7.3 rule 4)."""
    return by not in set(barred) and by not in answered_by(pair, labels)


def check_adjudicator(by: str, barred: Iterable[str], allowed: Iterable[str] | None) -> None:
    """`er label --adjudicate`: refuse the people who set the thresholds (the tech lead and the
    graph mentor, ADR-0014) and, when `allowed` is given (a real profile: the project lead and
    people.er_labellers), anyone not in it (7.3 rule 4)."""
    if by in set(barred):
        raise LabelsError(
            "the tech lead and the graph mentor set the thresholds (ADR-0014), so they do not"
            " adjudicate (7.3 rule 4)"
        )
    if allowed is not None and by not in set(allowed):
        raise LabelsError("an adjudicator is the project lead or in people.er_labellers")


def adjudicated(
    pair: Pair,
    labels: Iterable[Label],
    barred: Iterable[str],
    allowed: Iterable[str] | None = None,
) -> Label | None:
    """The newest adjudication of the pair by an eligible person (in `allowed`, when given)."""
    labels = list(labels)
    permitted = None if allowed is None else set(allowed)
    found = [
        x
        for (who, pid), x in newest(labels, adjudication=True).items()
        if pid == pair.pair_id
        and eligible_adjudicator(pair, who, barred, labels)
        and (permitted is None or who in permitted)
    ]
    return max(found, key=lambda x: (x.at, x.line), default=None)


def adjudication_queue(
    pairs: Sequence[Pair],
    labels: Sequence[Label],
    by: str,
    barred: Iterable[str],
    allowed: Iterable[str] | None = None,
) -> tuple[list[Pair], int]:
    """Disagreements `by` may adjudicate and that nobody has, and how many `by` may not."""
    barred = set(barred)
    allowed = None if allowed is None else set(allowed)
    queue, refused = [], 0
    for pair in disagreements(pairs, labels):
        if adjudicated(pair, labels, barred, allowed) is not None:
            continue
        if eligible_adjudicator(pair, by, barred, labels):
            queue.append(pair)
        else:
            refused += 1
    return queue, refused
