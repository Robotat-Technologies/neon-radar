"""The evaluation sample (PHASE-2.md 7.3, M2.10c deliverable 2).

`frames(canonical, candidates)` builds the frames of 7.3 from a run's `canonical.csv` and
`candidates.jsonl`, sorted by record id: S1, every non-anchor person, organisation or legal
entity record whose path to its anchor includes a probabilistic link; S2, every such record whose
path holds deterministic links only, with the D rule it joined by; S3, every possible match.
Each S1 or S2 item is the record and the anchor of its cluster. Records whose path includes a
human decision are counted only (also when the path holds a probabilistic link: such a merge
is not the resolver's alone).

`draw(frames, seed, labellers)` draws simple random samples with `random.Random(seed)` (a frame
no larger than its sample is taken whole: a census), draws the overlap S4 (40 pairs from the S1
sample and 10 from the S3 sample), puts every pair into one seeded random order, so that the
strata are interleaved, shows the two records of a pair in a seeded random order, and assigns
the pairs to the labellers round-robin, each S4 pair to two different people. `write_sample`
writes `sample.jsonl` (pair id, stratum, the two record ids, the labellers) and `sample.json`
(counts only), and never replaces a sample (7.3 rule 6). Nothing here prints a record id.

`check_run` and `check_seed` are the refusals of 7.3 rule 1 on a real profile: a run that
applied decisions, and a seed other than the one in ADR-0014 once that ADR is accepted.
"""

from __future__ import annotations

import csv
import json
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SIZES = {"S1": 400, "S2": 50, "S3": 50}  # 7.3: S1 headline, S2 deterministic, S3 possible
OVERLAP = {"S1": 40, "S3": 10}  # S4: labelled a second time by a different labeller
STRATA = ("S1", "S2", "S3")
CLASSES = frozenset({"person", "org", "legal_entity"})
SAMPLE_FILE = "sample.jsonl"
SUMMARY_FILE = "sample.json"
STATUS_LINE = re.compile(r"^- \*\*Status:\*\*[ \t]*([A-Za-z-]+)", re.MULTILINE)
SEED_LINE = re.compile(r"^Evaluation sample seed:[ \t]*(.*?)[ \t]*$", re.MULTILINE)


class SampleError(ValueError):
    """A refused or unreadable sample; the message holds counts and rule numbers only."""

    exit_code = 2
    counts_only = True


@dataclass(frozen=True)
class Item:
    stratum: str  # S1 | S2 | S3
    record_a: str  # S1, S2: the record; S3: the possible match's record_a
    record_b: str  # S1, S2: the anchor of its cluster; S3: record_b
    rule: str | None = None  # S2: the D rule the record joined by


@dataclass(frozen=True)
class Frames:
    s1: list[Item]
    s2: list[Item]
    s3: list[Item]
    human: int  # non-anchor records joined through a human decision (counted, not sampled)

    def by_stratum(self) -> dict[str, list[Item]]:
        return {"S1": self.s1, "S2": self.s2, "S3": self.s3}


@dataclass(frozen=True)
class Pair:
    """One line of `sample.jsonl`."""

    pair_id: str
    stratum: str
    record_a: str
    record_b: str
    labellers: tuple[str, ...]  # two for an S4 (overlap) pair
    overlap: bool
    rule: str | None = None  # S2 only

    def line(self) -> dict[str, Any]:
        return {**asdict(self), "labellers": list(self.labellers)}


def read_canonical(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_candidates(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def frames(
    canonical: Iterable[Mapping[str, str]], candidates: Iterable[Mapping[str, Any]]
) -> Frames:
    """The frames of 7.3, each sorted by record id."""
    rows = sorted(canonical, key=lambda r: r["record_id"])
    anchors = {r["canonical_id"]: r["record_id"] for r in rows if r["method"] == "anchor"}
    s1: list[Item] = []
    s2: list[Item] = []
    human = 0
    for row in rows:
        if row["class"] not in CLASSES or row["method"] in ("identity", "anchor"):
            continue
        anchor = anchors.get(row["canonical_id"])
        methods = set(filter(None, (row.get("path_methods") or "").split("+")))
        if anchor is None or not methods:
            raise SampleError("canonical.csv: a joined record without an anchor or a path")
        if "human" in methods:
            human += 1
        elif "probabilistic" in methods:
            s1.append(Item("S1", row["record_id"], anchor))
        elif methods == {"deterministic"}:
            s2.append(Item("S2", row["record_id"], anchor, row.get("rule") or None))
        else:
            raise SampleError("canonical.csv: a path method outside 7.1.8")
    s3 = [
        Item("S3", str(c["record_a"]), str(c["record_b"]))
        for c in sorted(candidates, key=lambda c: (str(c["record_a"]), str(c["record_b"])))
    ]
    return Frames(s1, s2, s3, human)


def draw(found: Frames, seed: int, labellers: Sequence[str]) -> tuple[list[Pair], dict[str, bool]]:
    """The sample's pairs in their one seeded order, and which frames were taken whole."""
    if len(labellers) < 2 or len(set(labellers)) != len(labellers):
        raise SampleError("the sample needs at least two different labellers (S4, 7.3 rule 4)")
    rng = random.Random(seed)  # noqa: S311 (a seeded, repeatable sample: 7.3 rule 1)
    chosen: dict[str, list[Item]] = {}
    census: dict[str, bool] = {}
    for stratum, frame in found.by_stratum().items():
        census[stratum] = len(frame) <= SIZES[stratum]
        chosen[stratum] = list(frame) if census[stratum] else rng.sample(frame, SIZES[stratum])
    overlap: set[Item] = set()
    for stratum, size in OVERLAP.items():
        pool = chosen[stratum]
        overlap.update(rng.sample(pool, min(size, len(pool))))
    items = [item for stratum in STRATA for item in chosen[stratum]]
    rng.shuffle(items)  # one order for every stratum: the strata are interleaved
    pairs: list[Pair] = []
    turn = 0
    for number, item in enumerate(items, start=1):
        twice = item in overlap
        count = 2 if twice else 1
        who = tuple(labellers[(turn + k) % len(labellers)] for k in range(count))
        turn += count
        swap = rng.random() < 0.5  # which record shows first says nothing about the stratum
        a, b = (item.record_b, item.record_a) if swap else (item.record_a, item.record_b)
        pairs.append(Pair(f"pair-{number:04d}", item.stratum, a, b, who, twice, item.rule))
    return pairs, census


def check_run(run_json: Mapping[str, Any], real_data: bool) -> None:
    """7.3 rule 1: on a real profile, only a run that applied no decisions is sampled."""
    if real_data and run_json.get("decisions_used") is not False:
        raise SampleError(
            "this run did not ignore the decisions file: the evaluation sample of a real profile"
            " comes from a run made with er run --no-decisions (7.3)"
        )


def adr_seed(text: str) -> tuple[str | None, int | None]:
    """ADR-0014's status (lower case) and its evaluation sample seed (None while not set)."""
    status = STATUS_LINE.search(text)
    seed = SEED_LINE.search(text)
    value = seed.group(1) if seed else ""
    return (
        status.group(1).lower() if status else None,
        int(value) if value.isascii() and value.isdigit() else None,
    )


def check_seed(adr_text: str | None, seed: int, real_data: bool) -> int | None:
    """7.3 rule 1: once ADR-0014 is accepted, a real profile is sampled with its seed only.

    Returns the ADR's seed (None while it is not set). On a real profile an ADR that is not
    readable, that is neither proposed nor accepted, or that is accepted without a seed is
    refused too (fail closed).
    """
    status, fixed = adr_seed(adr_text) if adr_text is not None else (None, None)
    if not real_data:
        return fixed
    if status not in ("proposed", "accepted"):
        raise SampleError("ADR-0014 has no readable status (proposed or accepted)")
    if status == "accepted" and fixed is None:
        raise SampleError("ADR-0014 is accepted but sets no evaluation sample seed (7.3 rule 1)")
    if status == "accepted" and seed != fixed:
        raise SampleError("ADR-0014 sets another evaluation sample seed (7.3 rule 1)")
    return fixed


def write_sample(folder: Path, pairs: Sequence[Pair], summary: Mapping[str, Any]) -> None:
    """`sample.jsonl` and `sample.json`; an existing sample is never replaced (7.3 rule 6)."""
    target = folder / SAMPLE_FILE
    if target.exists() or (folder / SUMMARY_FILE).exists():
        raise SampleError(
            "this run already has a sample: labelling may have started, and nothing in the"
            " evaluation changes after that (7.3 rule 6)"
        )
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / SUMMARY_FILE).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair.line(), sort_keys=True) + "\n")


def read_sample(folder: Path) -> tuple[list[Pair], dict[str, Any]]:
    """The pairs of `sample.jsonl`, in their order, and `sample.json`."""
    try:
        summary = json.loads((folder / SUMMARY_FILE).read_text(encoding="utf-8"))
        lines = (folder / SAMPLE_FILE).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise SampleError("this run has no sample yet (er sample)") from None
    pairs = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            pair = Pair(
                str(data["pair_id"]),
                str(data["stratum"]),
                str(data["record_a"]),
                str(data["record_b"]),
                tuple(str(h) for h in data["labellers"]),
                bool(data["overlap"]),
                data.get("rule"),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise SampleError(f"{SAMPLE_FILE}:{number}: not a sample line") from exc
        if pair.stratum not in STRATA or len(pair.labellers) != (2 if pair.overlap else 1):
            raise SampleError(f"{SAMPLE_FILE}:{number}: not a sample line")
        pairs.append(pair)
    if len({p.pair_id for p in pairs}) != len(pairs):
        raise SampleError(f"{SAMPLE_FILE}: a pair id appears twice")
    return pairs, summary


def sample_counts(
    found: Frames,
    pairs: Sequence[Pair],
    census: Mapping[str, bool],
    **fields: Any,
) -> dict[str, Any]:
    """`sample.json` and the printed summary: counts only (no record id, no handle)."""
    drawn = {s: sum(1 for p in pairs if p.stratum == s) for s in STRATA}
    overlap = {s: sum(1 for p in pairs if p.stratum == s and p.overlap) for s in STRATA}
    return {
        **fields,
        "frames": {s.lower(): len(f) for s, f in found.by_stratum().items()},
        "sampled": {s.lower(): n for s, n in drawn.items()},
        "census": {s.lower(): bool(census[s]) for s in STRATA},
        "overlap": {s.lower(): n for s, n in overlap.items() if s in OVERLAP},
        "human_joined": found.human,
        "pairs": len(pairs),
        "labellers": len({h for p in pairs for h in p.labellers}),
    }
