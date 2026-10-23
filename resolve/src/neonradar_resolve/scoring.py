"""The probabilistic half of a run (PHASE-2.md M2.10b deliverables 2 to 5, 7.1.5).

`score` reads each feature table from `features.duckdb`, counts the comparisons its blocking
rules generate (exact counts; above `max_comparisons` it stops with exit code 4 before any
training), trains the Splink model of its class and predicts at the candidate threshold.
`link` turns a scored pair into a `cluster.Link` that names the model that scored it, so
`cluster.resolve` applies that model's merge threshold. `write_pairs` and `read_pairs` keep the
pairs in `pairs.parquet`, which `er calibrate` clusters again without scoring again.

A class whose table has fewer than two records, whose blocking rules generate no comparison, or
whose model Splink cannot train on the run's data (too few pairs for the prior or an EM session)
gets no model: it scores no pair, so nothing of that class merges or becomes a possible match by
probability, and `models_skipped` counts it (an orchestrator decision under OD-10). With
`skip_untrainable=False` (real profiles) such a training error fails the run instead, and any
other error always does: a DuckDB error in Splink's SQL (an interrupt, memory, disk) is never
read as "cannot be trained".

While Splink runs, a handler of this module sits on the `splink` logger: it counts the levels
Splink could not train, and Splink's `Linker` then installs no stderr handler of its own
(`splink_logging.enable` adds one only to a logger without handlers), so nothing Splink logs is
printed outside the run's summary.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from splink import DuckDBAPI
from splink.blocking_analysis import count_comparisons_from_blocking_rules, n_largest_blocks
from splink.internals.exceptions import EMTrainingException  # no public module in Splink 5

from neonradar_resolve import cluster, models
from neonradar_resolve.config import ResolverConfig
from neonradar_resolve.models import Kind

log = logging.getLogger(__name__)
KINDS: tuple[Kind, ...] = ("person", "org")
LIBRARIES = ("splink", "duckdb", "pyarrow")
# What Splink 5.0.0 raises when the run's data cannot train a model: no pair for an EM session
# (EMTrainingException), a prior rule with no pair (math.log2 of 0) or more pairs than its
# recall allows (ValueError), an m of 0 (ZeroDivisionError). These exact classes only: the
# SplinkException that wraps every failed SQL statement, and subclasses such as pyarrow's
# ArrowInvalid, are not among them.
UNTRAINABLE = (EMTrainingException, ValueError, ZeroDivisionError)
MACHINE_ERRORS = (duckdb.Error, MemoryError, KeyboardInterrupt)
# expectation_maximisation.py (Splink 5.0.0): one warning per level and parameter it cannot train
NOT_OBSERVED = re.compile(r"Level (.*?) on comparison (\S+) not observed in dataset, "
                          r"unable to train (m|u) value")  # fmt: skip


def comparison_names(kind: Kind) -> list[str]:
    settings = models.settings(kind).get_settings("duckdb").as_dict()  # type: ignore[no-untyped-call]
    return sorted(models.level_labels(settings))


COMPARISONS = {kind: comparison_names(kind) for kind in KINDS}
PAIR_COLUMNS = (
    "record_a", "record_b", "class", "model", "probability", "weight", "strong_evidence",
    "birth_or_id_agrees", *sorted({c for names in COMPARISONS.values() for c in names}),
)  # fmt: skip


class ComparisonCapError(ValueError):
    """Blocking would generate more than `max_comparisons` pairs (7.1.5); counts only."""

    exit_code = 4
    counts_only = True


@dataclass
class Scored:
    pairs: dict[str, list[models.ScoredPair]] = field(default_factory=dict)
    trained: dict[str, dict[str, Any]] = field(default_factory=dict)  # save_model_to_json
    comparisons: dict[str, list[int]] = field(default_factory=dict)  # marginal count per rule
    untrained_levels: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)  # 1 for a class without a model
    timings: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """For `run.json`: library versions and counts only."""
        return {
            "versions": {name: version(name) for name in LIBRARIES},
            "comparisons_by_rule": {
                kind: {f"rule_{n}": c for n, c in enumerate(counts, 1)}
                for kind, counts in self.comparisons.items()
            },
            "comparisons": {kind: sum(c) for kind, c in self.comparisons.items()},
            "pairs_scored": {kind: len(p) for kind, p in self.pairs.items()},
            "untrained_levels": dict(self.untrained_levels),
            "models_skipped": dict(self.skipped),
        }


def read_features(path: Path, kind: Kind) -> pa.Table:
    """One feature table of `features.duckdb` with its schema, in record id order."""
    schema = models.PERSON_SCHEMA if kind == "person" else models.ORG_SCHEMA
    with duckdb.connect(str(path), read_only=True, config={"threads": 1}) as con:
        query = f"SELECT * FROM {kind}_features ORDER BY unique_id"  # noqa: S608 (fixed names)
        return con.sql(query).arrow().read_all().cast(schema)


def count_comparisons(con: duckdb.DuckDBPyConnection, kind: Kind, table: pa.Table) -> list[int]:
    """Each blocking rule's marginal comparison count, exact (a pair counts once)."""
    sdf = DuckDBAPI(connection=con).register(table, dataset_display_name=f"{kind}_blocking")
    found = count_comparisons_from_blocking_rules(
        sdf,
        blocking_rules=models.blocking_rules(kind),
        link_type="dedupe_only",
        record_sample_proportion=1.0,
    )
    return [int(r["marginal_comparison_count"]) for r in found]


def largest_blocks(
    con: duckdb.DuckDBPyConnection, kind: Kind, table: pa.Table, n: int = 5
) -> list[list[dict[str, Any]]]:
    """Per blocking rule, the `n` largest blocks: their keys and record counts.

    Splink's `n_largest_blocks` does not explode arrays, so for a rule with
    `arrays_to_explode` (`explodes`) a block is a group of records with the same whole list.
    """
    sdf = DuckDBAPI(connection=con).register(table, dataset_display_name=f"{kind}_blocks")
    out = []
    for rule in models.blocking_rules(kind):
        rows = n_largest_blocks(sdf, blocking_rule=rule, link_type="dedupe_only", n_largest=n)
        out.append(rows.as_record_list())
    return out


def explodes(kind: Kind) -> list[bool]:
    """Per blocking rule, whether it compares the elements of a list (`arrays_to_explode`)."""
    rules = models.blocking_rules(kind)
    return [bool(r.create_blocking_rule_dict("duckdb").get("arrays_to_explode")) for r in rules]


def untrainable(exc: BaseException) -> bool:
    """Whether `exc` says the run's data cannot train the model: one of `UNTRAINABLE` exactly,
    with no DuckDB error, memory error or interrupt anywhere in its chain."""
    seen: set[int] = set()
    link: BaseException | None = exc
    while link is not None and id(link) not in seen:
        if isinstance(link, MACHINE_ERRORS):
            return False
        seen.add(id(link))
        link = link.__cause__ or link.__context__
    return type(exc) in UNTRAINABLE


class _Untrained(logging.Handler):
    """Collects the (level, comparison, parameter) Splink reports it could not train; while it
    is on the `splink` logger, Splink installs no stderr handler of its own."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.found: set[tuple[str, ...]] = set()

    def emit(self, record: logging.LogRecord) -> None:
        self.found.update(m.groups() for m in NOT_OBSERVED.finditer(record.getMessage()))


@contextmanager
def _untrained() -> Iterator[_Untrained]:
    handler, logger = _Untrained(), logging.getLogger("splink")
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


def score(
    features_path: Path,
    config: ResolverConfig,
    temp_directory: Path,
    *,
    skip_untrainable: bool = True,
) -> Scored:
    """Train both models on this run's own data and score pairs at the candidate threshold.

    `skip_untrainable=False` (real profiles): a model the data cannot train fails the run.
    """
    out = Scored(skipped=dict.fromkeys(KINDS, 0))
    tables = {kind: read_features(features_path, kind) for kind in KINDS}
    con = models.connect(config.duckdb.threads, config.duckdb.memory_limit, str(temp_directory))
    try:
        for kind, table in tables.items():
            out.comparisons[kind] = count_comparisons(con, kind, table) if len(table) > 1 else []
        over = {k: sum(c) for k, c in out.comparisons.items() if sum(c) > config.max_comparisons}
        if over:
            counts = "; ".join(
                f"{k}: {sum(c)} comparisons, by rule {c}" for k, c in out.comparisons.items()
            )
            raise ComparisonCapError(
                f"blocking would generate more than max_comparisons"
                f" ({config.max_comparisons}) for {', '.join(sorted(over))} ({counts})"
            )
        training = models.TrainingConfig(
            seed=config.seed,
            u_max_pairs=config.training.u_max_pairs,
            em_max_pairs=config.training.em_max_pairs,
            prior_recall=config.training.prior_recall,
        )
        for kind, table in tables.items():
            out.pairs[kind] = []
            if not sum(out.comparisons[kind]):
                out.skipped[kind] = 1
                continue
            start = time.perf_counter()
            with _untrained() as handler:  # before make_linker: see the module docstring
                linker = models.make_linker(con, kind, table)
                try:
                    models.train(linker, kind, training)
                except UNTRAINABLE as exc:
                    if not skip_untrainable or not untrainable(exc):
                        raise
                    # the class names only: a message can quote SQL or numbers of the data
                    log.warning("the %s model could not be trained (%s)", kind, type(exc).__name__)
                    out.skipped[kind] = 1
                    continue
                out.untrained_levels[kind] = len(handler.found)
                out.timings[f"train_{kind}"] = round(time.perf_counter() - start, 3)
                start = time.perf_counter()
                out.pairs[kind] = models.predict(linker, kind, config.candidate_threshold)
                out.trained[kind] = linker.misc.save_model_to_json()
                out.timings[f"predict_{kind}"] = round(time.perf_counter() - start, 3)
    finally:
        con.close()
    return out


def link(pair: models.ScoredPair, kind: str) -> cluster.Link:
    """A scored pair as a probabilistic link that names its model (7.1.6)."""
    return cluster.Link(
        pair.record_a,
        pair.record_b,
        "probabilistic",
        None,
        pair.probability,
        pair.weight,
        pair.features,
        pair.strong_evidence,
        pair.birth_or_id_agrees,
        model=kind,
    )


def links(scored: Scored) -> list[cluster.Link]:
    return [link(p, kind) for kind, pairs in scored.pairs.items() for p in pairs]


def write_pairs(
    path: Path, scored: Iterable[cluster.Link], members: Mapping[str, cluster.Member]
) -> None:
    """`pairs.parquet`: one row per scored pair and model, sorted by record ids (7.1.8)."""
    rows = []
    for x in sorted(scored, key=lambda x: (x.record_a, x.record_b, str(x.model))):
        classes = sorted({members[x.record_a].entity_class, members[x.record_b].entity_class})
        rows.append(
            {
                **dict.fromkeys(PAIR_COLUMNS),
                "record_a": x.record_a,
                "record_b": x.record_b,
                "class": "+".join(classes),
                "model": x.model,
                "probability": x.probability,
                "weight": x.weight,
                "strong_evidence": x.strong_evidence,
                "birth_or_id_agrees": x.birth_or_id_agrees,
                **x.features,
            }
        )
    schema = pa.schema(
        [(name, pa.float64() if name in ("probability", "weight") else pa.string())
         for name in PAIR_COLUMNS[:6]]
        + [("strong_evidence", pa.bool_()), ("birth_or_id_agrees", pa.bool_())]
        + [(name, pa.string()) for name in PAIR_COLUMNS[8:]]
    )  # fmt: skip
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)


def read_pairs(path: Path) -> list[cluster.Link]:
    """The links of `pairs.parquet`, as `score` gave them to the clustering."""
    out = []
    for row in pq.read_table(path).to_pylist():
        kind = row["model"]
        out.append(
            cluster.Link(
                row["record_a"],
                row["record_b"],
                "probabilistic",
                None,
                row["probability"],
                row["weight"],
                {name: row[name] for name in COMPARISONS[kind]},
                row["strong_evidence"],
                row["birth_or_id_agrees"],
                model=kind,
            )
        )
    return out


def write_models(folder: Path, scored: Scored) -> None:
    """`models/<kind>.json`: the trained parameters of this run (never committed)."""
    folder.mkdir()
    for kind, model in scored.trained.items():
        text = json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        (folder / f"{kind}.json").write_text(text, encoding="utf-8")


def settings_json(kind: Kind) -> str:
    """`resolve/models/<kind>.settings.json`: the committed settings, no trained parameters."""
    settings = models.settings(kind).get_settings("duckdb").as_dict()  # type: ignore[no-untyped-call]
    return json.dumps(settings, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
