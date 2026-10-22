"""Splink 5 models for NeonRadar entity resolution (PHASE-2.md 7.1.5).

Splink scores pairs; `cluster.py` decides merges. Feature tables come from `features.py`:
one row per resolvable record, with every empty list written as NULL (Splink's null levels
test `IS NULL`, and an empty list is not NULL in DuckDB).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import duckdb
import pyarrow as pa
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

from neonradar_resolve.feature_schema import ORG_SCHEMA, PERSON_SCHEMA, RARE_NAME_MAX

__all__ = ["ORG_SCHEMA", "PERSON_SCHEMA", "RARE_NAME_MAX", "predict", "settings", "train"]

Kind = Literal["person", "org"]


def _person_comparisons() -> list[Any]:
    # NameComparison always adds term-frequency adjustment to its exact level, so the name
    # comparison is built from levels (er-splink.md 2.3).
    name = cl.CustomComparison(
        output_column_name="name",
        comparison_description="person name",
        comparison_levels=[
            cll.NullLevel("name_key"),
            cll.ExactMatchLevel("name_key", term_frequency_adjustments=True).configure(
                label_for_charts="name key equal"
            ),
            cll.And(
                cll.JaroWinklerLevel("forename", 0.92), cll.JaroWinklerLevel("surname", 0.92)
            ).configure(label_for_charts="forename and surname similar"),
            cll.And(cll.ExactMatchLevel("surname"), cll.ExactMatchLevel("initial")).configure(
                label_for_charts="surname equal, same initial"
            ),
            cll.ArrayIntersectLevel("name_symbols", 2).configure(
                label_for_charts="two name symbols shared"
            ),
            cll.JaroWinklerLevel("name_key", 0.88).configure(label_for_charts="name key similar"),
            cll.ExactMatchLevel("surname").configure(label_for_charts="surname equal"),
            cll.ArrayIntersectLevel("skeletons", 2).configure(
                label_for_charts="two skeletons shared"
            ),
            cll.ElseLevel(),
        ],
    )
    # DateOfBirthComparison misfiles month-year strings (er-splink.md 2.3), so birth is custom.
    birth = cl.CustomComparison(
        output_column_name="birth",
        comparison_description="birth date",
        comparison_levels=[
            cll.NullLevel("birth_years"),
            cll.ArrayIntersectLevel("birth_full", 1).configure(label_for_charts="same birth date"),
            cll.ArrayIntersectLevel("birth_ym", 1).configure(label_for_charts="same birth month"),
            cll.ArrayIntersectLevel("birth_years", 1).configure(label_for_charts="same birth year"),
            cll.CustomLevel(
                "abs(birth_year_min_l - birth_year_min_r) <= 1",
                label_for_charts="birth years one apart",
            ),
            cll.ElseLevel(),
        ],
    )
    return [
        name,
        birth,
        cl.ArrayIntersectAtSizes("countries", [1]),
        cl.PostcodeComparison("postcode"),
        cl.ArrayIntersectAtSizes("linked_orgs", [2, 1]),
        cl.ArrayIntersectAtSizes("identifiers", [1]),
    ]


def _org_comparisons() -> list[Any]:
    name = cl.CustomComparison(
        output_column_name="org_name",
        comparison_description="organisation name",
        comparison_levels=[
            cll.NullLevel("name_key"),
            cll.ExactMatchLevel("name_key", term_frequency_adjustments=True).configure(
                label_for_charts="name key equal"
            ),
            cll.ArrayIntersectLevel("aliases", 1).configure(
                label_for_charts="a name or alias shared"
            ),
            cll.ExactMatchLevel("ch_same_as").configure(
                label_for_charts="same name under the Companies House rules"
            ),
            cll.JaroWinklerLevel("name_key", 0.95).configure(
                label_for_charts="name key very similar"
            ),
            cll.JaroWinklerLevel("name_key", 0.88).configure(label_for_charts="name key similar"),
            cll.ArrayIntersectLevel("name_tokens", 2).configure(
                label_for_charts="two words shared"
            ),
            cll.ElseLevel(),
        ],
    )
    incorporation = cl.CustomComparison(
        output_column_name="incorporation",
        comparison_description="incorporation year",
        comparison_levels=[
            cll.NullLevel("incorporation_year"),
            cll.ExactMatchLevel("incorporation_year").configure(label_for_charts="same year"),
            cll.CustomLevel(
                "abs(incorporation_year_l - incorporation_year_r) <= 1",
                label_for_charts="one year apart",
            ),
            cll.ElseLevel(),
        ],
    )
    return [
        name,
        cl.ExactMatch("jurisdiction"),
        cl.ArrayIntersectAtSizes("registration_numbers", [1]),
        incorporation,
        cl.PostcodeComparison("postcode"),
        cl.ArrayIntersectAtSizes("legal_forms", [1]),
    ]


def blocking_rules(kind: Kind) -> list[Any]:
    """Every rule includes `synthetic`, so synthetic and real records are never compared (X1)."""
    if kind == "person":
        return [
            block_on("surname", "birth_year_min", "synthetic"),
            block_on("forename", "birth_ym_min", "synthetic"),
            block_on("postcode", "substr(surname, 1, 1)", "synthetic"),
            block_on("linked_orgs", "synthetic", arrays_to_explode=["linked_orgs"]),
            block_on(
                "name_symbols", "birth_year_min", "synthetic", arrays_to_explode=["name_symbols"]
            ),
            block_on("name_key_rare", "synthetic"),
        ]
    return [
        block_on("name_key", "synthetic"),
        block_on("ch_same_as", "synthetic"),
        block_on("registration_numbers", "synthetic", arrays_to_explode=["registration_numbers"]),
        block_on("aliases", "synthetic", arrays_to_explode=["aliases"]),
        block_on("postcode", "name_prefix", "synthetic"),
    ]


def settings(kind: Kind) -> SettingsCreator:
    return SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="unique_id",
        comparisons=_person_comparisons() if kind == "person" else _org_comparisons(),
        blocking_rules_to_generate_predictions=blocking_rules(kind),
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=False,
        linker_uid=f"neonradar_{kind}",
    )


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 20261026
    u_max_pairs: float = 1e7
    em_max_pairs: float | None = 5e6
    prior_recall: float = 0.7


def connect(threads: int, memory_limit: str, temp_directory: str) -> duckdb.DuckDBPyConnection:
    """DuckDB settings go on the connection; DuckDBAPI has no memory or thread options."""
    return duckdb.connect(
        ":memory:",
        config={
            "threads": threads,
            "memory_limit": memory_limit,
            "temp_directory": temp_directory,
            "preserve_insertion_order": False,
        },
    )


def make_linker(
    con: duckdb.DuckDBPyConnection, kind: Kind, table: pa.Table, model: str | None = None
) -> Linker:
    db_api = DuckDBAPI(connection=con)
    sdf = db_api.register(table, dataset_display_name=f"{kind}_features")
    return Linker(sdf, model if model is not None else settings(kind), log_level=logging.WARNING)


def train(linker: Linker, kind: Kind, config: TrainingConfig) -> None:
    """Prior, u by random sampling (seeded), then two EM sessions (er-splink.md 2.4, 3.4)."""
    t = linker.training
    if kind == "person":
        t.estimate_probability_two_random_records_match(
            [block_on("name_key", "birth_ym_min")], recall=config.prior_recall
        )
        t.estimate_u_using_random_sampling(max_pairs=config.u_max_pairs, seed=config.seed)
        t.estimate_parameters_using_expectation_maximisation(
            block_on("surname", "birth_year_min"), max_pairs=config.em_max_pairs
        )
        t.estimate_parameters_using_expectation_maximisation(
            block_on("postcode"), max_pairs=config.em_max_pairs
        )
    else:
        t.estimate_probability_two_random_records_match(
            [block_on("name_key")], recall=config.prior_recall
        )
        t.estimate_u_using_random_sampling(max_pairs=config.u_max_pairs, seed=config.seed)
        t.estimate_parameters_using_expectation_maximisation(
            block_on("name_key"), max_pairs=config.em_max_pairs
        )
        t.estimate_parameters_using_expectation_maximisation(
            block_on("postcode"), max_pairs=config.em_max_pairs
        )


def level_labels(model: Mapping[str, Any]) -> dict[str, dict[int, str]]:
    """Comparison name -> {gamma value: level label}, from a saved model dict.

    Splink gives the null level -1, the most similar level the highest value and the else
    level 0 (splink/internals/comparison.py, 5.0.0).
    """
    out: dict[str, dict[int, str]] = {}
    for comparison in model["comparisons"]:
        levels = comparison["comparison_levels"]
        counter = sum(1 for level in levels if not level.get("is_null_level")) - 1
        labels: dict[int, str] = {}
        for level in levels:
            label = str(level.get("label_for_charts") or level["sql_condition"])
            if level.get("is_null_level"):
                labels[-1] = label
            else:
                labels[counter] = label
                counter -= 1
        out[comparison["output_column_name"]] = labels
    return out


# P3 (7.1.4): agreeing evidence other than the name. P6: birth years compatible or an identifier.
STRONG_EVIDENCE: dict[Kind, dict[str, frozenset[str]]] = {
    "person": {
        "birth": frozenset({"same birth date", "same birth month"}),
        "postcode": frozenset({"Exact match on full postcode"}),
        "linked_orgs": frozenset({"Array intersection size >= 2", "Array intersection size >= 1"}),
        "identifiers": frozenset({"Array intersection size >= 1"}),
    },
    "org": {
        "registration_numbers": frozenset({"Array intersection size >= 1"}),
        "incorporation": frozenset({"same year"}),
        "postcode": frozenset({"Exact match on full postcode"}),
    },
}
BIRTH_OR_ID = {
    "birth": frozenset(
        {"same birth date", "same birth month", "same birth year", "birth years one apart"}
    ),
    "identifiers": frozenset({"Array intersection size >= 1"}),
}


@dataclass(frozen=True)
class ScoredPair:
    record_a: str
    record_b: str
    probability: float
    weight: float
    features: dict[str, str]
    strong_evidence: bool
    birth_or_id_agrees: bool


def _agrees(features: Mapping[str, str], rules: Mapping[str, frozenset[str]]) -> bool:
    return any(features.get(name) in allowed for name, allowed in rules.items())


def scored_pairs(
    rows: Iterable[Mapping[str, Any]], labels: Mapping[str, Mapping[int, str]], kind: Kind
) -> list[ScoredPair]:
    """Predict output rows (as_record_list) to pairs, ordered by record ids."""
    out = []
    for row in rows:
        a, b = sorted((str(row["unique_id_l"]), str(row["unique_id_r"])))
        features = {
            name: levels[int(row[f"gamma_{name}"])] for name, levels in sorted(labels.items())
        }
        out.append(
            ScoredPair(
                a,
                b,
                round(float(row["match_probability"]), 9),
                round(float(row["match_weight"]), 6),
                features,
                _agrees(features, STRONG_EVIDENCE[kind]),
                kind == "org" or _agrees(features, BIRTH_OR_ID),
            )
        )
    return sorted(out, key=lambda p: (p.record_a, p.record_b))


def predict(linker: Linker, kind: Kind, candidate_threshold: float) -> list[ScoredPair]:
    model = linker.misc.save_model_to_json()
    labels = level_labels(model)
    result = linker.inference.predict(threshold_match_probability=candidate_threshold)
    return scored_pairs(result.as_record_list(), labels, kind)
