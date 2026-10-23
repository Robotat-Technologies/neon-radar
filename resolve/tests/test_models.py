"""Tests for neonradar_resolve.models (PHASE-2.md M2.10b). Invented names only."""

from __future__ import annotations

import random
from itertools import combinations
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from neonradar_keys.names import org_key, person_key
from neonradar_resolve.models import (
    ORG_SCHEMA,
    PERSON_SCHEMA,
    STRONG_EVIDENCE,
    TrainingConfig,
    connect,
    level_labels,
    make_linker,
    predict,
    settings,
    train,
)

SYLLABLES = ["ka", "lo", "mir", "dan", "vel", "tor", "sa", "ri", "bel", "zan", "fen", "or", "ul"]


def _word(rng: random.Random) -> str:
    return "".join(rng.choice(SYLLABLES) for _ in range(rng.choice([2, 3]))).capitalize()


def _typo(rng: random.Random, text: str) -> str:
    i = rng.randrange(1, len(text) - 1)
    return text[:i] + text[i + 1 :]


def person_rows(
    seed: int, entities: int = 400
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    rng = random.Random(seed)  # noqa: S311 (synthetic test data, not security)
    rows: list[dict[str, Any]] = []
    clusters: dict[int, list[str]] = {}
    for e in range(entities):
        given, family = _word(rng), _word(rng)
        year, month, day = rng.randint(1940, 2000), rng.randint(1, 12), rng.randint(1, 28)
        postcode = f"QQ{rng.randint(1, 20)} {rng.randint(1, 9)}AB"
        company = f"gbch-co-SY{rng.randint(0, 999_999):06d}"
        for r in range(rng.choice([1, 2, 2, 3])):
            g = _typo(rng, given) if r and rng.random() < 0.15 else given
            key = person_key(f"{g} {family}", given=g, family=family)
            full = f"{year:04d}-{month:02d}-{day:02d}" if r == 0 else None
            uid = f"syn-p-{e:04d}-{r}"
            clusters.setdefault(e, []).append(uid)
            rows.append(
                {
                    "unique_id": uid,
                    "synthetic": True,
                    "name_key": key.key,
                    "name_key_rare": key.key,
                    "forename": key.given[0] if key.given else None,
                    "surname": key.family[0] if key.family else None,
                    "initial": key.given[0][0] if key.given else None,
                    "name_tokens": list(key.tokens) or None,
                    "name_symbols": list(key.symbols) or None,
                    "skeletons": list(key.skeletons) or None,
                    "birth_full": [full] if full else None,
                    "birth_ym": [f"{year:04d}-{month:02d}"],
                    "birth_years": [year],
                    "birth_year_min": year,
                    "birth_ym_min": f"{year:04d}-{month:02d}",
                    "countries": ["gb"],
                    "postcode": postcode if rng.random() < 0.8 else None,
                    "linked_orgs": [company] if rng.random() < 0.7 else None,
                    "identifiers": None,
                }
            )
    truth = {tuple(sorted(p)) for ids in clusters.values() for p in combinations(ids, 2)}
    return rows, truth  # type: ignore[return-value]


def org_rows(seed: int, entities: int = 300) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    rng = random.Random(seed)  # noqa: S311 (synthetic test data, not security)
    rows: list[dict[str, Any]] = []
    clusters: dict[int, list[str]] = {}
    for e in range(entities):
        core = f"{_word(rng)} {_word(rng)}"
        number = f"SY{e:06d}"
        year = rng.randint(1990, 2025)
        home = f"QQ{rng.randint(1, 30)} {rng.randint(1, 9)}AB"
        for r, form in enumerate(rng.sample(["Limited", "Ltd", "LTD."], rng.choice([1, 2, 3]))):
            name = f"{core} {form}"
            key = org_key(name)
            uid = f"syn-o-{e:04d}-{r}"
            clusters.setdefault(e, []).append(uid)
            rows.append(
                {
                    "unique_id": uid,
                    "synthetic": True,
                    "name_key": key.key,
                    "name_key_rare": key.key,
                    "name_prefix": key.key[:4],
                    "aliases": [key.key],
                    "ch_same_as": key.key.replace(" ", "").upper(),
                    "name_tokens": key.key.split() or None,
                    "jurisdiction": "gb",
                    "registration_numbers": [number] if r == 0 or rng.random() < 0.6 else None,
                    "incorporation_year": year if rng.random() < 0.8 else None,
                    "postcode": home if rng.random() < 0.8 else f"QQ{rng.randint(1, 30)} 1AB",
                    "legal_forms": list(key.legal_forms) or None,
                }
            )
    truth = {tuple(sorted(p)) for ids in clusters.values() for p in combinations(ids, 2)}
    return rows, truth  # type: ignore[return-value]


def run(kind: str, tmp_path: Path, threads: int = 1) -> tuple[list[Any], set[tuple[str, str]]]:
    rows, truth = person_rows(7) if kind == "person" else org_rows(7)
    schema = PERSON_SCHEMA if kind == "person" else ORG_SCHEMA
    table = pa.Table.from_pylist(rows, schema=schema)
    con = connect(threads=threads, memory_limit="1GB", temp_directory=str(tmp_path / "duckdb"))
    linker = make_linker(con, kind, table)  # type: ignore[arg-type]
    train(linker, kind, TrainingConfig(u_max_pairs=2e5, em_max_pairs=None))  # type: ignore[arg-type]
    return predict(linker, kind, 0.5), truth  # type: ignore[arg-type]


def test_level_labels_follow_splink_order() -> None:
    model = settings("person").get_settings("duckdb").as_dict()
    labels = level_labels(model)
    assert labels["name"][-1] == "name_key is NULL"
    assert labels["name"][7] == "name key equal"
    assert labels["name"][0] == "All other comparisons"
    assert labels["postcode"][4] == "Exact match on full postcode"
    for kind, rules in STRONG_EVIDENCE.items():
        names = level_labels(settings(kind).get_settings("duckdb").as_dict())  # type: ignore[arg-type]
        for comparison, allowed in rules.items():
            assert allowed <= set(names[comparison].values()), (kind, comparison)


@pytest.mark.parametrize("kind", ["person", "org"])
def test_models_find_true_pairs(kind: str, tmp_path: Path) -> None:
    pairs, truth = run(kind, tmp_path)
    found = {(p.record_a, p.record_b) for p in pairs if p.probability >= 0.9}
    precision = len(found & truth) / max(len(found), 1)
    recall = len(found & truth) / len(truth)
    assert precision >= 0.95, precision
    assert recall >= 0.80, recall
    assert all(p.record_a < p.record_b for p in pairs)
    assert all(set(p.features) for p in pairs)


def test_single_thread_runs_are_identical(tmp_path: Path) -> None:
    first, _ = run("person", tmp_path / "a")
    second, _ = run("person", tmp_path / "b")
    assert first == second
