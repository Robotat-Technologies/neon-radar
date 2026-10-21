"""The ICIJ spike: a bounded, closed slice of the archive as C1 records (M1.8c).

The slice is the first `rows` entities, every relationship that touches one of them, and the
officers, intermediaries, others and addresses those relationships name. `relationships.csv`
and the four smaller node files are streamed in full (counted, never stored); only
`nodes-entities.csv` stops after `rows`. A relationship whose other end is outside the slice
is counted and left out, so the output validates in strict mode.
"""

import csv
import io
import json
import re
import time
import zipfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path

import httpx

from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.sources.icij.archive import ArchiveInfo, Mode, open_archive
from neonradar_ingest.sources.icij.mapping import (
    DATASET,
    SKIP_HINT,
    Mapper,
    classify_link,
)

ENTITIES = "nodes-entities.csv"
RELATIONSHIPS = "relationships.csv"
OTHER_NODES = ("nodes-officers.csv", "nodes-intermediaries.csv", "nodes-others.csv",
               "nodes-addresses.csv")  # fmt: skip
GENERATED_RE = re.compile(r"GENERATED_ON_(\d{8})\.txt")


@dataclass
class FileFacts:
    header: list[str]
    rows: int = 0
    complete: bool = True
    source_ids: Counter[str] = field(default_factory=Counter)


@dataclass
class Slice:
    members: dict[str, int]
    generated_on: str | None
    files: dict[str, FileFacts]
    links: Counter[tuple[str, str]]
    mapper: Mapper


@contextmanager
def _csv(zf: zipfile.ZipFile, name: str) -> Iterator[tuple[FileFacts, Iterator[dict[str, str]]]]:
    with zf.open(name) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        facts = FileFacts(header=list(reader.fieldnames or []))

        def rows() -> Iterator[dict[str, str]]:
            for row in reader:
                facts.rows += 1
                facts.source_ids[row.get("sourceID") or ""] += 1
                yield row

        yield facts, rows()


def read_slice(zf: zipfile.ZipFile, rows: int) -> Slice:
    members = {info.filename: info.file_size for info in zf.infolist()}
    missing = [name for name in (ENTITIES, RELATIONSHIPS, *OTHER_NODES) if name not in members]
    if missing:
        raise ValueError(f"archive lacks {', '.join(missing)}; found {sorted(members)}")
    generated = next((m.group(1) for n in members if (m := GENERATED_RE.fullmatch(n))), None)
    mapper, files, links = Mapper(), {}, Counter[tuple[str, str]]()
    with _csv(zf, ENTITIES) as (facts, reader):
        seed_rows = list(islice(reader, rows))
        files[ENTITIES] = facts
        extra = next(reader, None)
        facts.complete = extra is None
        if extra is not None:  # the look-ahead row is not part of the slice
            facts.rows -= 1
            facts.source_ids[extra.get("sourceID") or ""] -= 1
    seed = {row["node_id"].strip() for row in seed_rows}
    kept: list[dict[str, str]] = []
    with _csv(zf, RELATIONSHIPS) as (facts, reader):
        files[RELATIONSHIPS] = facts
        for row in reader:
            links[(row["rel_type"], row["link"].strip().lower())] += 1
            if row["node_id_start"].strip() in seed or row["node_id_end"].strip() in seed:
                if classify_link(row["rel_type"], row["link"]) is None:
                    mapper.skip(SKIP_HINT)
                else:
                    kept.append(row)
    ends = ("node_id_start", "node_id_end")
    needed = {row[end].strip() for row in kept for end in ends} - seed
    found: dict[str, list[dict[str, str]]] = {}
    for name in OTHER_NODES:
        with _csv(zf, name) as (facts, reader):
            files[name] = facts
            found[name] = [row for row in reader if row["node_id"].strip() in needed]
    for row in seed_rows:
        mapper.add_node(ENTITIES, row)
    for name, node_rows in found.items():
        for row in node_rows:
            mapper.add_node(name, row)
    for row in kept:
        mapper.add_relationship(row)
    return Slice(members, generated, files, links, mapper)


@dataclass
class SpikeResult:
    info: ArchiveInfo
    mode: Mode
    requests: int | None
    bytes_received: int | None
    seconds: float
    slice: Slice
    output: Path


def write_records(mapper: Mapper, out_dir: Path, source: Source, notes: list[str]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{DATASET}-{datetime.now(UTC):%Y%m%d}-slice.ftm.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in mapper.records():
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    producer = Producer(name="neonradar_ingest.sources.icij", version=__version__)
    write_manifest(path, dataset=DATASET, producer=producer, source=source,
                   skipped=dict(sorted(mapper.skipped.items())), notes=notes)  # fmt: skip
    return path


def run_spike(
    client: httpx.Client, *, url: str, rows: int, out_dir: Path, cache_dir: Path
) -> SpikeResult:
    started = time.monotonic()
    retrieved_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    zf, info, mode, reader = open_archive(client, url, cache_dir)
    with zf:
        piece = read_slice(zf, rows)
    if reader is not None:
        reader.close()
    source = Source(urls=[info.url], retrieved_at=retrieved_at,
                    source_version=piece.generated_on or info.last_modified)  # fmt: skip
    notes = [
        f"Slice: the first {rows} rows of {ENTITIES}, every relationship that touches them and"
        " the nodes those relationships name; same_* and similar* rows are not loaded.",
        "ICIJ Offshore Leaks Database: database under ODbL 1.0, contents under CC BY-SA 3.0.",
    ]
    output = write_records(piece.mapper, out_dir, source, notes)
    return SpikeResult(
        info=info,
        mode=mode,
        requests=reader.requests if reader else None,
        bytes_received=reader.bytes_received if reader else None,
        seconds=round(time.monotonic() - started, 1),
        slice=piece,
        output=output,
    )


def summary_lines(result: SpikeResult, top: int = 30) -> list[str]:
    """What `neonradar spike icij` prints: header facts and counts, no record content."""
    info, piece = result.info, result.slice
    lines = [
        f"archive {info.url}",
        f"  Content-Length {info.size}  Last-Modified {info.last_modified}  ETag {info.etag}",
        f"  Accept-Ranges {info.accept_ranges}  Content-Type {info.content_type}",
        f"  read by {result.mode}: {result.requests} requests, {result.bytes_received} bytes,"
        f" {result.seconds} s; generated on {piece.generated_on}",
        "members: " + ", ".join(f"{n} ({s} bytes)" for n, s in sorted(piece.members.items())),
    ]
    for name, facts in piece.files.items():
        scope = "all" if facts.complete else "first"
        lines.append(f"{name}: {scope} {facts.rows} rows; columns {','.join(facts.header)}")
        sources = ", ".join(f"{s or '<empty>'} {c}" for s, c in facts.source_ids.most_common())
        lines.append(f"  sourceID: {sources}")
    by_type, by_kind = Counter[str](), Counter[str]()
    for (rel_type, link), count in piece.links.items():
        by_type[rel_type] += count
        by_kind[classify_link(rel_type, link) or "not loaded (hint)"] += count
    lines.append("rel_type: " + ", ".join(f"{t} {c}" for t, c in by_type.most_common()))
    lines.append("mapping of every row: " + ", ".join(f"{k} {c}" for k, c in by_kind.most_common()))
    lines.append(f"top {top} of {len(piece.links)} (rel_type, link) pairs, with the mapping:")
    for (rel_type, link), count in piece.links.most_common(top):
        mapped = classify_link(rel_type, link) or "not loaded (hint)"
        lines.append(f"  {count:>9}  {rel_type} | {link} -> {mapped}")
    by_schema = Counter(str(record["schema"]) for record in piece.mapper.records())
    lines.append("records: " + ", ".join(f"{s} {c}" for s, c in sorted(by_schema.items())))
    lines.append(
        "skipped: " + ", ".join(f"{k} {v}" for k, v in sorted(piece.mapper.skipped.items()))
    )
    dates, misses = piece.mapper.dates, piece.mapper.date_misses.most_common()
    lines.append(f"dates: {dates['kept']} of {dates['seen']} parsed; not parsed: {misses}")
    lines.append(f"wrote {result.output} and its manifest")
    return lines
