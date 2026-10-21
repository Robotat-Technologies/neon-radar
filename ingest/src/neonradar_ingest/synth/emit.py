"""Write a synthetic load: C1 records, their manifest and the label files (PHASE-1.md M1.8e).

Records are FollowTheMoney `ValueEntity` lines plus the `nr` extension (contracts/C1-record.md),
sorted by schema and id, UTF-8 with `\\n` line ends, so the same input gives the same bytes.
Ground-truth labels go to `labels/transactions.csv` and `labels/scenarios.csv` (R9); payments
missing from `transactions.csv` are background.
"""

import csv
import json
import unicodedata
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

from followthemoney import ValueEntity, model

from neonradar_contracts.records import (
    SYNTHETIC_DATASET,
    Manifest,
    Producer,
    manifest_path,
    write_manifest,
)
from neonradar_ingest.synth import GENERATOR, GENERATOR_VERSION

SCHEMA_ORDER = (
    "Company", "Organization", "Person", "Address", "Ownership", "Directorship",
    "Representation", "BankAccount", "Payment",
)  # fmt: skip
CSV_MARKER = "# synthetic: true\n"
TRANSACTION_COLUMNS = ("tx_id", "scenario_id", "typology", "step", "role", "is_illicit")
SCENARIO_COLUMNS = (
    "scenario_id", "typology", "variant", "is_lookalike", "start_ts", "end_ts", "participants",
)  # fmt: skip


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


@dataclass(slots=True)
class Rec:
    """One synthetic record before serialisation."""

    id: str
    schema: str
    kind: Literal["registry", "activity"]
    props: dict[str, list[str]]
    nr: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        entity = ValueEntity(model[self.schema], {"id": self.id, "datasets": [SYNTHETIC_DATASET]})
        for prop, values in self.props.items():
            entity.add(prop, [nfc(value) for value in values], cleaned=True)
        nr = {"v": "1.0", "synthetic": True, "synthetic_kind": self.kind, **self.nr}
        return {**entity.to_dict(), "nr": nr}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def ordered(records: list[Rec]) -> list[Rec]:
    """Records sorted by schema (SCHEMA_ORDER), then id: the order every load is written in."""
    order = {schema: index for index, schema in enumerate(SCHEMA_ORDER)}
    return sorted(records, key=lambda rec: (order[rec.schema], rec.id))


@dataclass(frozen=True, slots=True)
class Scenario:
    """Ground truth for one planted scenario or benign look-alike (never written to records)."""

    scenario_id: str
    typology: str
    variant: str
    is_lookalike: bool
    is_illicit: bool
    steps: tuple[tuple[str, str, str], ...]  # (payment id, role, timestamp) in order
    participants: tuple[tuple[str, str], ...]  # (role, record id)


def _write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(CSV_MARKER)
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def write_labels(folder: Path, scenarios: list[Scenario]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    tx_rows: list[tuple[str, ...]] = []
    scenario_rows: list[tuple[str, ...]] = []
    for sc in scenarios:
        illicit = str(sc.is_illicit).lower()
        for step, (tx_id, role, _) in enumerate(sc.steps, start=1):
            tx_rows.append((tx_id, sc.scenario_id, sc.typology, str(step), role, illicit))
        participants = ";".join(f"{role}:{rid}" for role, rid in sc.participants)
        scenario_rows.append(
            (sc.scenario_id, sc.typology, sc.variant, str(sc.is_lookalike).lower(),
             sc.steps[0][2], sc.steps[-1][2], participants)
        )  # fmt: skip
    _write_csv(folder / "transactions.csv", TRANSACTION_COLUMNS, tx_rows)
    _write_csv(folder / "scenarios.csv", SCENARIO_COLUMNS, scenario_rows)


def write_load(
    out: Path,
    stem: str,
    records: list[Rec],
    scenarios: list[Scenario],
    *,
    seed: int,
    notes: list[str],
    created_at: str | None = None,
) -> Path:
    """Write `<stem>.ftm.jsonl`, its manifest and `labels/`; return the record file's path."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stem}.ftm.jsonl"
    _write_text(path, "".join(rec.to_json() + "\n" for rec in ordered(records)))
    write_labels(out / "labels", scenarios)
    producer = Producer(name=GENERATOR, version=GENERATOR_VERSION, git_sha=None)
    write_manifest(
        path, dataset=SYNTHETIC_DATASET, producer=producer, seed=seed, notes=notes,
        created_at=created_at,
    )  # fmt: skip
    # write_manifest records FollowTheMoney only; the names and streams also depend on these.
    manifest_file = manifest_path(path)
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    for package in ("faker", "numpy"):
        data["dependencies"][package] = version(package)
    data["dependencies"] = dict(sorted(data["dependencies"].items()))
    manifest = Manifest.model_validate(data)
    text = json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
    _write_text(manifest_file, text + "\n")
    return path
