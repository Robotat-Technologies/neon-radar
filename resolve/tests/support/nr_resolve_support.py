"""Records built in test code (PHASE-2.md 2.9): written to a temporary C1 file and read back."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neonradar_resolve import features, records


def rec(
    rid: str, schema: str, dataset: str, nr: dict[str, Any] | None = None, **props: Any
) -> dict[str, Any]:
    """One C1 record; each property value may be a string or a list of strings."""
    properties = {k: v if isinstance(v, list) else [v] for k, v in props.items()}
    return {
        "id": rid,
        "schema": schema,
        "properties": properties,
        "referents": [],
        "datasets": [dataset],
        "nr": {"v": "1.1", **(nr or {})},
    }


def syn(
    rid: str, schema: str, kind: str = "registry", nr: dict[str, Any] | None = None, **props: Any
) -> dict[str, Any]:
    return rec(
        rid,
        schema,
        "nr_synthetic",
        {"synthetic": True, "synthetic_kind": kind, **(nr or {})},
        **props,
    )


def corpus_of(folder: Path, items: list[dict[str, Any]]) -> records.Corpus:
    folder.mkdir(parents=True, exist_ok=True)
    lines = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items)
    (folder / "test.ftm.jsonl").write_text(lines, encoding="utf-8")
    return records.read([folder])


def members_of(folder: Path, items: list[dict[str, Any]]) -> tuple[records.Corpus, dict[str, Any]]:
    corpus = corpus_of(folder, items)
    return corpus, features.members(corpus)
