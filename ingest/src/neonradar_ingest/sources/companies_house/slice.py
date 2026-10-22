"""The company slice of a profile: the `slice` step (PHASE-2.md M2.3a deliverable 5).

Seeds are always in the slice; for each postcode district, the companies with the lowest
sample hash `sha256("<sample_seed>|<number>")`, at most `max_per_district`; then the PSC
expansion (M2.3b passes it in); finally the cap `max_companies`, which removes expansion
companies first (deepest level first, then highest hash), then district companies (highest
hash first), never a seed. `slice.csv` is written in the order the officers step uses.
"""

import csv
import hashlib
import json
import sqlite3
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neonradar_ingest.sources.companies_house.build import CompaniesBlock

REASONS = ("seed", "district", "parent", "child")  # which reason a company reached twice keeps
FILE_ORDER = ("seed", "parent", "child", "district")  # the order of slice.csv (M2.3c)
HEADER = ("company_number", "reason", "level")


@dataclass(frozen=True, slots=True)
class Member:
    number: str
    reason: str
    level: int
    hash: str


def sample_hash(seed: int, number: str) -> str:
    return hashlib.sha256(f"{seed}|{number}".encode()).hexdigest()


def merge(members: Iterable[Member]) -> dict[str, Member]:
    """One member per company: the first reason in `REASONS` order, at its lowest level."""
    kept: dict[str, Member] = {}
    for member in members:
        old = kept.get(member.number)
        rank = (REASONS.index(member.reason), member.level)
        if old is None or rank < (REASONS.index(old.reason), old.level):
            kept[member.number] = member
    return kept


def cap(members: dict[str, Member], max_companies: int) -> tuple[list[Member], int]:
    """The members left after the cap, and how many it removed (never a seed)."""
    expansion = sorted((m for m in members.values() if m.reason in ("parent", "child")),
                       key=lambda m: (m.level, m.hash), reverse=True)  # fmt: skip
    districts = sorted((m for m in members.values() if m.reason == "district"),
                       key=lambda m: m.hash, reverse=True)  # fmt: skip
    excess = len(members) - max_companies
    removed = {m.number for m in (expansion + districts)[: max(excess, 0)]}
    return [m for m in members.values() if m.number not in removed], len(removed)


def file_order(members: Iterable[Member]) -> list[Member]:
    return sorted(members, key=lambda m: (FILE_ORDER.index(m.reason), m.level, m.hash, m.number))


def write(path: Path, members: Sequence[Member]) -> str:
    """Write `slice.csv` (via a temporary file) and return its SHA-256."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows((m.number, m.reason, m.level) for m in file_order(members))
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[tuple[str, str, int]]:
    """The rows of `slice.csv` in file order: (company number, reason, level)."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        if tuple(next(reader, ())) != HEADER:
            raise ValueError(f"{path.name} does not start with {','.join(HEADER)}")
        return [(number, reason, int(level)) for number, reason, level in reader]


def build_slice(
    index: Path, block: CompaniesBlock, path: Path, expansion: Iterable[Member] = ()
) -> tuple[dict[str, Any], str]:
    """The `slice` step from the `index` and the profile's `companies` block: counts, SHA-256."""
    seed = block.sample_seed
    connection = sqlite3.connect(index.absolute().as_uri() + "?mode=ro", uri=True)
    try:
        members = [Member(n, "seed", 0, sample_hash(seed, n)) for n in block.seeds]
        missing = sum(
            connection.execute("SELECT 1 FROM company WHERE number = ?", (n,)).fetchone() is None
            for n in block.seeds
        )
        district_of: dict[str, str] = {}  # each company has one district in the index
        for where in block.postcode_districts:
            rows = connection.execute("SELECT number FROM company WHERE district = ?", (where,))
            ranked = sorted((sample_hash(seed, number), number) for (number,) in rows)
            for digest, number in ranked[: block.max_per_district]:
                members.append(Member(number, "district", 0, digest))
                district_of[number] = where
    finally:
        connection.close()
    kept, removed = cap(merge([*members, *expansion]), block.max_companies)
    sha256 = write(path, kept)
    by_district = Counter(district_of[m.number] for m in kept if m.reason == "district")
    counts: dict[str, Any] = {
        "companies": len(kept),
        "seeds_missing_from_index": missing,
        "cap_removed": removed,
        "by_reason": {r: sum(m.reason == r for m in kept) for r in REASONS},
        "by_level": {str(k): v for k, v in sorted(Counter(m.level for m in kept).items())},
        "by_district": {d.lower(): by_district[d] for d in block.postcode_districts},
    }
    return counts, sha256


def write_meta(path: Path, *, version: str | None, sample_seed: int, sha256: str) -> None:
    """`slice.json` next to `slice.csv`: the snapshot the slice came from, its seed and hash."""
    meta = {"version": version, "sample_seed": sample_seed, "slice_sha256": sha256}
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def read_meta(path: Path) -> dict[str, Any]:
    meta = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return meta
