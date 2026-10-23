"""Label files v2 (PHASE-3.md 7.2.8; `synthetic-transactions.md` 4.2).

Labels never enter records (C1 R9) or the graph. Every CSV file starts with `# synthetic: true`
and `# label_schema: 2.0.0`; the Phase 1 columns come first, in their Phase 1 order, and new columns
follow, so a reader that selects columns by name keeps working. Rows are sorted, numbers and
booleans have one spelling (`true` and `false`), and files end with a newline: the same seed gives
the same bytes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from neonradar_ingest.synth.ctx import LabelRows

LABEL_SCHEMA = "2.0.0"
SCENARIO_COLUMNS = (
    "scenario_id",
    "typology",
    "variant",
    "is_lookalike",
    "start_ts",
    "end_ts",
    "participants",
    "difficulty",
    "split",
    "n_transactions",
    "n_accounts",
    "n_entities",
    "n_relationships",
)
TRANSACTION_COLUMNS = (
    "tx_id",
    "scenario_id",
    "typology",
    "step",
    "role",
    "is_illicit",
    "variant",
    "is_lookalike",
    "is_core",
)
PARTICIPANT_COLUMNS = ("scenario_id", "object_kind", "object_id", "role", "is_core")


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def csv_text(columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    out = io.StringIO()
    out.write("# synthetic: true\n")
    out.write(f"# label_schema: {LABEL_SCHEMA}\n")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row[c]) for c in columns])
    return out.getvalue()


def files(
    labels: LabelRows, *, seed: int, record_sha256: Mapping[str, str], generator_version: str
) -> dict[str, str]:
    """File name to text for `labels/`."""
    scenarios = sorted(labels.scenarios, key=lambda r: r["scenario_id"])
    transactions = sorted(
        labels.transactions, key=lambda r: (r["scenario_id"], r["step"], r["tx_id"])
    )
    participants = sorted(
        labels.participants, key=lambda r: (r["scenario_id"], r["object_kind"], r["object_id"])
    )
    params = sorted(labels.params, key=lambda r: r["scenario_id"])
    by = Counter((r["typology"], r["variant"], r["is_lookalike"]) for r in scenarios)
    manifest = {
        "label_schema": LABEL_SCHEMA,
        "synthetic": True,
        "seed": seed,
        "records": dict(sorted(record_sha256.items())),
        "counts": [
            {"typology": t, "variant": v, "is_lookalike": look, "scenarios": n}
            for (t, v, look), n in sorted(by.items())
        ],
        "splits": sorted({r["split"] for r in scenarios}),
        "generator_version": generator_version,
    }
    return {
        "scenarios.csv": csv_text(SCENARIO_COLUMNS, scenarios),
        "transactions.csv": csv_text(TRANSACTION_COLUMNS, transactions),
        "participants.csv": csv_text(PARTICIPANT_COLUMNS, participants),
        "scenario_params.jsonl": "".join(
            json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in params
        ),
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    }


def write(directory: Path, texts: Mapping[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(texts.items()):
        (directory / name).write_text(text, encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    """Rows of a label CSV, skipping the comment lines."""
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")
    ]
    return list(csv.DictReader(lines))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
