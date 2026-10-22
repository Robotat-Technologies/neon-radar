"""Read the C1 records of a resolution run (PHASE-2.md 7.1.1, M2.10a deliverable 1).

Streams every `*.ftm.jsonl` file of the record folders it is given (sorted), keeps the
resolvable records and, from the relationship and `Sanction` records, each record's context:
the records it is linked to and, for listed records, their sanctions. Reads ICIJ's
`*-hints.csv` side files as `(record_a, record_b, hint)` tuples. The caller resolves the
folders (the CLI with `Profile.record_dirs()`); this module never imports `neonradar_ingest`.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from followthemoney import model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import iter_records

CLASSES = {
    "Person": "person",
    "Company": "org",
    "Organization": "org",
    "PublicBody": "org",
    "LegalEntity": "legal_entity",
    "Address": "address",
}
# The relationship schemata whose ends give a record its linked organisations (7.1.5).
RELATIONS = ("Directorship", "Ownership", "Control", "Representation", "UnknownLink")
HINT_HEADER = ["record_a", "record_b", "hint"]


class RecordsError(ValueError):
    """Unreadable input; the message names a file and a line, never a value."""


@dataclass(frozen=True)
class Sanction:
    """A `Sanction` entity of a listed record: the facts rules D4, P6 and X6 read."""

    dataset: str
    authority: str | None
    authority_id: str | None
    unsc_id: str | None


@dataclass(frozen=True)
class Record:
    """One resolvable record (7.1.1), with its dataset's registry facts."""

    id: str
    schema: str
    entity_class: str  # person | org | legal_entity | address
    dataset: str
    dataset_kind: str  # registry | list | leak | synthetic (contracts/datasets.yaml)
    priority: int  # anchor_priority
    synthetic: bool  # the dataset's flag
    properties: Mapping[str, tuple[str, ...]]
    nr: Mapping[str, Any]

    def values(self, *names: str) -> list[str]:
        return [v for name in names for v in self.properties.get(name, ())]

    def first(self, name: str) -> str | None:
        values = self.properties.get(name, ())
        return values[0] if values else None


@dataclass(frozen=True)
class InputFile:
    dataset: str
    file: str
    records: int
    sha256: str


@dataclass
class Corpus:
    records: dict[str, Record] = field(default_factory=dict)
    linked: dict[str, set[str]] = field(default_factory=dict)  # record id -> linked record ids
    sanctions: dict[str, list[Sanction]] = field(default_factory=dict)
    hints: list[tuple[str, str, str]] = field(default_factory=list)
    inputs: list[InputFile] = field(default_factory=list)
    skipped: int = 0  # records that are neither resolvable nor context


def _properties(data: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    raw = data.get("properties") or {}
    return {k: tuple(str(v) for v in vs) for k, vs in raw.items() if isinstance(vs, list)}


def _link(corpus: Corpus, a: str, b: str) -> None:
    if a != b:
        corpus.linked.setdefault(a, set()).add(b)
        corpus.linked.setdefault(b, set()).add(a)


def _add(corpus: Corpus, data: dict[str, Any], where: str) -> None:
    rid, schema = data.get("id"), data.get("schema")
    datasets = data.get("datasets") or []
    if not isinstance(rid, str) or not isinstance(schema, str) or not datasets:
        raise RecordsError(f"{where}: a record without an id, a schema or a dataset")
    props = _properties(data)
    if schema in CLASSES:
        dataset = load_registry().get(str(datasets[0]))
        if dataset is None or dataset.kind is None or dataset.anchor_priority is None:
            raise RecordsError(f"{where}: dataset without kind or anchor_priority")
        if rid in corpus.records:
            raise RecordsError(f"{where}: a record id that an earlier line already used")
        corpus.records[rid] = Record(
            rid,
            schema,
            CLASSES[schema],
            dataset.slug,
            dataset.kind,
            dataset.anchor_priority,
            dataset.synthetic,
            props,
            dict(data.get("nr") or {}),
        )
    elif schema in RELATIONS:
        found = model.get(schema)
        if found is None or found.edge_source is None or found.edge_target is None:
            raise RecordsError(f"{where}: unknown relationship schema")
        for a in props.get(found.edge_source, ()):
            for b in props.get(found.edge_target, ()):
                _link(corpus, a, b)
    elif schema == "Sanction":
        sanction = Sanction(
            str(datasets[0]),
            next(iter(props.get("authority", ())), None),
            next(iter(props.get("authorityId", ())), None),
            next(iter(props.get("unscId", ())), None),
        )
        for entity in props.get("entity", ()):
            corpus.sanctions.setdefault(entity, []).append(sanction)
    else:
        corpus.skipped += 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_hints(path: Path) -> list[tuple[str, str, str]]:
    """An ICIJ hints file: header `record_a,record_b,hint`, one source hint per row."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != HINT_HEADER:
        raise RecordsError(f"{path.name}: the header is not record_a,record_b,hint")
    out = []
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != 3 or not all(row):
            raise RecordsError(f"{path.name}:{number}: a row needs three values")
        out.append((row[0], row[1], row[2]))
    return out


def read(record_dirs: Iterable[Path]) -> Corpus:
    """Every record file and hints file of the folders, in sorted order."""
    corpus = Corpus()
    for folder in record_dirs:
        folder = Path(folder)
        if not folder.is_dir():
            raise RecordsError(f"record folder {folder.name} does not exist")
        for path in sorted(folder.glob("*.ftm.jsonl")):
            count, dataset = 0, ""
            for number, data in enumerate(iter_records(path), start=1):
                _add(corpus, data, f"{path.name}:{number}")
                count += 1
                dataset = dataset or str((data.get("datasets") or [""])[0])
            corpus.inputs.append(InputFile(dataset, path.name, count, _sha256(path)))
        for path in sorted(folder.glob("*-hints.csv")):
            corpus.hints.extend(read_hints(path))
    return corpus
