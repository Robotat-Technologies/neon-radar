"""A resolution run as the loader reads it (C2 loader rules L8 to L14, PHASE-2.md 7.1.8, M2.11).

`ResolutionMap.load(run_dir)` reads `canonical.csv`, `candidates.jsonl` and `run.json` from a
run folder (the graph package never imports the resolver or reads `pairs.parquet`) and checks
them; a run that fails a check stops the load (`ResolutionError`, exit 1) with counts only, as
the run may hold real records. `canonical(record_id)` maps a record id to its canonical id, or
returns the id itself for a record the run does not know.
"""

import csv
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from neonradar_contracts.graph import POSSIBLY_SAME_AS_METHODS, RESOLVED_TO_METHODS

CANONICAL_HEADER = (
    "record_id", "canonical_id", "class", "cluster_size", "method", "rule",
    "match_probability", "via", "path_methods", "features",
)  # fmt: skip
# 7.1.1: the class of each resolvable FtM schema; every other schema passes through.
RESOLVABLE = {
    "Person": "person",
    "Company": "org",
    "Organization": "org",
    "PublicBody": "org",
    "LegalEntity": "legal_entity",
    "Address": "address",
}
POSSIBLE_MATCH_CLASSES = frozenset({"person", "org", "legal_entity"})  # L14
METHODS = frozenset({"identity", *RESOLVED_TO_METHODS})
CANONICAL_PREFIX = "nr-"
RUN_ID = re.compile(r"er-([0-9]{8}T[0-9]{6})-[0-9a-f]{4}\Z")


class ResolutionError(Exception):
    """A run folder the loader cannot use; the message holds counts and file names only."""

    exit_code = 1
    counts_only = True


@dataclass(frozen=True, slots=True)
class Member:
    """One row of `canonical.csv`."""

    record_id: str
    canonical_id: str
    entity_class: str
    cluster_size: int
    method: str
    rule: str | None
    match_probability: float | None
    features: str | None


def _optional(value: str) -> str | None:
    return value or None


def _probability(value: str) -> float | None:
    if not value:
        return None
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError("match_probability outside 0 to 1")
    return number


def _member(row: Mapping[str, str]) -> Member:
    member = Member(
        record_id=row["record_id"],
        canonical_id=row["canonical_id"],
        entity_class=row["class"],
        cluster_size=int(row["cluster_size"]),
        method=row["method"],
        rule=_optional(row["rule"]),
        match_probability=_probability(row["match_probability"]),
        features=_optional(row["features"]),
    )
    if not member.record_id or member.entity_class not in RESOLVABLE.values():
        raise ValueError("a row without a record id or with an unknown class")
    if member.method not in METHODS or member.cluster_size < 1:
        raise ValueError("an unknown method or a cluster size below 1")
    if member.method == "probabilistic" and member.match_probability is None:
        raise ValueError("a probabilistic member without a probability")
    return member


def _read_canonical(path: Path) -> dict[str, Member]:
    members: dict[str, Member] = {}
    bad = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        if tuple(next(reader, ())) != CANONICAL_HEADER:
            raise ResolutionError(f"{path.name}: the header is not {','.join(CANONICAL_HEADER)}")
        for cells in reader:
            try:
                member = _member(dict(zip(CANONICAL_HEADER, cells, strict=True)))
            except ValueError:
                bad += 1
                continue
            if member.record_id in members:
                bad += 1
            members[member.record_id] = member
    if bad:
        raise ResolutionError(f"{path.name}: {bad} row(s) do not read as 7.1.8 says")
    return members


def _check_clusters(members: Mapping[str, Member]) -> None:
    """Every merged record maps to an `nr-` id with one anchor and the right size; every single
    record maps to itself (identity)."""
    clusters: dict[str, list[Member]] = {}
    for member in members.values():
        clusters.setdefault(member.canonical_id, []).append(member)
    bad = 0
    for canonical_id, group in clusters.items():
        if any(m.cluster_size != len(group) for m in group):
            bad += 1
        elif len(group) == 1:
            (single,) = group
            bad += single.canonical_id != single.record_id or single.method != "identity"
        else:
            anchors = [m.record_id for m in group if m.method == "anchor"]
            anchor = canonical_id.removeprefix(CANONICAL_PREFIX)
            bad += (
                not canonical_id.startswith(CANONICAL_PREFIX)
                or anchors != [anchor]
                or any(m.method == "identity" for m in group)
            )
    if bad:
        raise ResolutionError(
            f"canonical.csv: {bad} cluster(s) break the canonical id, anchor or cluster_size rules"
        )


def _is_probability(line: Mapping[str, Any]) -> bool:
    """A probabilistic possible match carries a finite `match_probability` from 0 to 1 (C2)."""
    value = line.get("match_probability")
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    return math.isfinite(value) and 0.0 <= value <= 1.0


def _read_candidates(path: Path, members: Mapping[str, Member]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    unreadable = order = classes = 0
    with path.open(encoding="utf-8") as handle:
        for text in handle:
            if not text.strip():
                continue
            try:
                line = json.loads(text)
                a, b, record_a, record_b = (line[k] for k in ("a", "b", "record_a", "record_b"))
                ok = isinstance(line, dict) and line["method"] in POSSIBLY_SAME_AS_METHODS
                ok = ok and isinstance(line["reasons"], list) and isinstance(line["features"], dict)
                ok = ok and (line["method"] != "probabilistic" or _is_probability(line))
            except ValueError, KeyError, TypeError:
                unreadable += 1
                continue
            if not ok or record_a not in members or record_b not in members:
                unreadable += 1
                continue
            left, right = members[record_a], members[record_b]
            ordered = isinstance(a, str) and isinstance(b, str) and a < b
            order += not ordered or (left.canonical_id, right.canonical_id) != (a, b)
            if {left.entity_class, right.entity_class} - POSSIBLE_MATCH_CLASSES:
                classes += 1
            lines.append(line)
    if unreadable or order:
        raise ResolutionError(
            f"{path.name}: {unreadable} line(s) unreadable or naming records the run lacks,"
            f" {order} not joining two different canonical ids with a < b"
        )
    if classes:
        raise ResolutionError(
            f"{path.name}: {classes} line(s) join records that are not of class person, org or"
            " legal_entity (L14): an address never has a possible match"
        )
    return lines


@dataclass(frozen=True, slots=True)
class ResolutionMap:
    """`canonical.csv` by record id, the lines of `candidates.jsonl`, and the run's identity."""

    run_id: str
    resolver_version: str
    decided_at: str  # the run's start time, which its id encodes (4.4)
    members: Mapping[str, Member]
    candidates: tuple[Mapping[str, Any], ...]

    @classmethod
    def load(cls, run_dir: Path) -> Self:
        """Read and check a finished run folder (ResolutionError on any problem)."""
        try:
            try:
                summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            except ValueError:  # UnicodeDecodeError included
                raise ResolutionError("run.json is not a JSON object") from None
            try:
                members = _read_canonical(run_dir / "canonical.csv")
            except UnicodeDecodeError, csv.Error:
                raise ResolutionError("canonical.csv is not a UTF-8 CSV file") from None
            try:
                candidates = _read_candidates(run_dir / "candidates.jsonl", members)
            except UnicodeDecodeError:
                raise ResolutionError("candidates.jsonl is not a UTF-8 file") from None
        except FileNotFoundError as missing:
            raise ResolutionError(f"{Path(str(missing.filename)).name} is missing") from None
        if not isinstance(summary, dict):
            raise ResolutionError("run.json is not a JSON object")
        run_id, version = summary.get("run_id"), summary.get("resolver_version")
        found = RUN_ID.fullmatch(run_id) if isinstance(run_id, str) else None
        if found is None or run_id != run_dir.name or not isinstance(version, str):
            raise ResolutionError(
                "run.json: run_id must be the folder name, er-<yyyymmddThhmmss>-<4 hex>, and"
                " resolver_version a string"
            )
        _check_clusters(members)
        stamp = found[1]
        decided_at = (
            f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"
        )
        return cls(run_id, version, decided_at, members, tuple(candidates))

    def canonical(self, record_id: str) -> str:
        """The canonical id of a record of this run, else the record id itself."""
        member = self.members.get(record_id)
        return member.canonical_id if member is not None else record_id

    def clusters(self) -> dict[str, list[Member]]:
        """Merged entities only (two or more members), each with its members by record id."""
        out: dict[str, list[Member]] = {}
        for member in sorted(self.members.values(), key=lambda m: m.record_id):
            if member.cluster_size >= 2:
                out.setdefault(member.canonical_id, []).append(member)
        return out

    def check_load(self, schemas: Mapping[str, str], *, complete: bool) -> None:
        """Refuse a load that does not fit this run (counts only).

        `schemas` maps each record id of the load to its FtM schema. Every merged entity must
        have all or none of its members in the load, each record's class must be the run's,
        and a `complete` load (one that replaces what an earlier load left, L9) must hold
        exactly the resolvable records of the run.
        """
        partial = sum(
            0 < sum(m.record_id in schemas for m in group) < len(group)
            for group in self.clusters().values()
        )
        wrong_class = sum(
            1
            for rid, schema in schemas.items()
            if rid in self.members and RESOLVABLE.get(schema) != self.members[rid].entity_class
        )
        counts = Counter[str]()
        if complete:
            counts["missing"] = sum(rid not in schemas for rid in self.members)
            counts["unknown"] = sum(
                schema in RESOLVABLE and rid not in self.members for rid, schema in schemas.items()
            )
        if partial or wrong_class or counts.total():
            raise ResolutionError(
                f"the resolution run {self.run_id} does not fit these records: {partial} merged"
                f" entit(ies) with only some members in the load, {wrong_class} record(s) of"
                f" another class, {counts['missing']} record(s) of the run not in the load and"
                f" {counts['unknown']} resolvable record(s) the run does not know: run"
                " `neonradar er run` on the same records, then load again"
            )


def resolvable_ids(records: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Record id to schema name for every record with an id and a schema."""
    return {
        str(record["id"]): str(record["schema"])
        for record in records
        if isinstance(record.get("id"), str) and isinstance(record.get("schema"), str)
    }
