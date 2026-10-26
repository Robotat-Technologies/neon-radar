"""Resolution runs with the Splink models (PHASE-2.md M2.10b deliverable 10). Synthetic only:
the demo profile (data/fixtures/demo-mini and data/fixtures/er-bench) and members built here.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import duckdb
import pyarrow as pa
import pytest
import yaml
from nr_resolve_support import corpus_of, syn
from splink.internals.exceptions import EMTrainingException, SplinkException
from typer.testing import CliRunner

from neonradar_cli import er as er_cli
from neonradar_cli.main import app
from neonradar_ingest.data import layout, profiles
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_resolve import bench, calibrate, cluster, features, models, records, run, scoring
from neonradar_resolve.config import load_config

STABLE = ("canonical.csv", "candidates.jsonl", "conflicts.jsonl")
runner = CliRunner()


def _tiny_corpus(folder: Path) -> None:
    """Two people and one company: too few pairs for Splink to train either model."""
    people = [
        syn(f"syn-p-{n}", "Person", name="Testa Example", birthDate="1970-01") for n in (1, 2)
    ]
    corpus_of(folder, [*people, syn("syn-o-1", "Company", name="Test Holder Ltd")])


def _profiles_read_tiny_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every profile's `er run` reads the tiny corpus instead of its fixtures (fast)."""
    folder = tmp_path / "records"
    _tiny_corpus(folder)
    monkeypatch.setattr(profiles.Profile, "record_dirs", lambda self, project=None: [folder])


def _real_profile(data_env: Any) -> str:
    """A profile marked real that every gate condition allows (synthetic test records only)."""
    profile = {
        "profile": "real-er-test",
        "description": "Synthetic test records in a profile marked real.",
        "real_data": True,
        "sources": {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/er-bench"]}},
        "resolution": {"enabled": True, "config": "resolve/config/er.yaml"},
    }
    (data_env.profiles / "real-er-test.yaml").write_text(yaml.safe_dump(profile))
    data_env.allow_real("real-er-test")
    return "real-er-test"


@pytest.fixture
def one_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests use one DuckDB thread (7.1.5): bitwise identical training."""
    connect = models.connect
    monkeypatch.setattr(models, "connect", lambda _threads, memory, temp: connect(1, memory, temp))


def _latest(profile: str) -> Path:
    run_id = layout.latest_run(profile)
    assert run_id is not None
    return layout.resolution_dir(profile, run_id)


def _counting_spy(monkeypatch: pytest.MonkeyPatch, splink_log: logging.Logger) -> list[bool]:
    """Whether scoring's handler was on the `splink` logger at each comparison count: Splink's
    blocking analysis logs too, and without a handler that would reach stderr directly."""
    seen: list[bool] = []
    count = scoring.count_comparisons

    def spy(con: Any, kind: Any, table: Any) -> list[int]:
        seen.append(any(isinstance(h, scoring._Untrained) for h in splink_log.handlers))
        return count(con, kind, table)

    monkeypatch.setattr(scoring, "count_comparisons", spy)
    return seen


def test_er_run_demo_scores_pairs_and_is_byte_stable(
    data_env: Any, one_thread: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    splink_log = logging.getLogger("splink")
    monkeypatch.setattr(splink_log, "propagate", False)  # as in a CLI process: no root handler
    monkeypatch.setattr(splink_log, "handlers", [])
    counted = _counting_spy(monkeypatch, splink_log)
    dirs = []
    for _ in range(2):
        result = runner.invoke(app, ["er", "run", "--profile", "demo"])
        assert result.exit_code == 0, result.output
        assert "not observed in dataset" not in result.output  # Splink's warnings: counted only
        assert splink_log.handlers == []  # Splink added no stderr handler of its own
        dirs.append(_latest("demo"))
    assert counted and all(counted)
    first, second = dirs
    assert first != second
    names = sorted(p.name for p in first.iterdir())
    assert names == sorted(run.OUTPUTS + run.PROBABILISTIC_OUTPUTS)
    assert sorted(p.name for p in (first / "models").iterdir()) == ["org.json", "person.json"]
    for name in STABLE:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
    info = json.loads((first / "run.json").read_text(encoding="utf-8"))
    assert info["probabilistic"] is True
    assert set(info["splink"]["versions"]) == {"splink", "duckdb", "pyarrow"}
    assert info["splink"]["pairs_scored"]["person"] > 0
    # From Splink's real warnings (8 and 10 with Splink 5.0.0): a Splink version whose warning
    # text no longer matches scoring.NOT_OBSERVED gives 0 here and fails this test.
    assert all(info["splink"]["untrained_levels"][kind] > 0 for kind in ("person", "org"))
    assert info["splink"]["models_skipped"] == {"person": 0, "org": 0}
    assert info["counts"]["joined_by_method"]["probabilistic"] > 0
    links = scoring.read_pairs(first / "pairs.parquet")
    assert links == sorted(links, key=lambda x: (x.record_a, x.record_b, str(x.model)))
    assert {x.model for x in links} == {"person", "org"}
    assert all(set(x.features) == set(scoring.COMPARISONS[str(x.model)]) for x in links)
    assert not list((data_env.cache / "synthetic" / "duckdb-tmp").glob("*"))  # no spill files


def test_scored_pair_becomes_a_link_that_names_its_model() -> None:
    pair = models.ScoredPair(
        "syn-a", "syn-b", 0.993, 7.1, {"org_name": "name key equal"}, True, False
    )
    link = scoring.link(pair, "org")
    assert link == cluster.Link(
        "syn-a", "syn-b", "probabilistic", None, 0.993, 7.1, {"org_name": "name key equal"},
        True, False, model="org",
    )  # fmt: skip


def _org(rid: str) -> cluster.Member:
    return cluster.Member(
        rid, "nr_synthetic", "registry", 10, "Company", "org", True, name_keys=frozenset({"x"})
    )


@pytest.mark.parametrize(("model", "merged"), [("org", False), ("person", True)])
def test_a_pair_is_judged_by_the_threshold_of_its_model(model: str, merged: bool) -> None:
    """0.993 is above merge_threshold.person (0.99) and below merge_threshold.org (0.995)."""
    pair = models.ScoredPair("syn-a", "syn-b", 0.993, 7.1, {}, True, True)
    config = cluster.Config({"person": 0.99, "org": 0.995}, 0.80)
    result = cluster.resolve(
        [_org("syn-a"), _org("syn-b")], [], [scoring.link(pair, model)], [], [], [], config,
        lambda names: "Company",
    )  # fmt: skip
    assert (len({r["canonical_id"] for r in result.canonical}) == 1) is merged
    reasons = [c["reasons"] for c in result.candidates]
    assert reasons == ([] if merged else [["below_merge_threshold"]])


def test_pairs_parquet_round_trip(tmp_path: Path) -> None:
    members = {rid: _org(rid) for rid in ("syn-a", "syn-b", "syn-c")}
    links = [
        scoring.link(
            models.ScoredPair(a, b, p, w, dict.fromkeys(scoring.COMPARISONS[kind], label), s, i),
            kind,
        )
        for a, b, p, w, label, s, i, kind in [
            ("syn-b", "syn-c", 0.9, 3.25, "name key equal", False, True, "person"),
            ("syn-b", "syn-c", 0.97, 5.5, "same year", True, True, "org"),
            ("syn-a", "syn-b", 0.5, 0.0, "All other comparisons", True, False, "org"),
        ]
    ]
    scoring.write_pairs(tmp_path / "pairs.parquet", links, members)
    back = scoring.read_pairs(tmp_path / "pairs.parquet")
    assert back == [links[2], links[1], links[0]]  # by record ids, then model


def test_the_comparison_cap_stops_before_training(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_training(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("trained despite the comparison cap")

    monkeypatch.setattr(scoring, "count_comparisons", lambda con, kind, table: [20_000_001])
    monkeypatch.setattr(models, "train", no_training)
    result = runner.invoke(app, ["er", "run", "--profile", "demo"])
    assert result.exit_code == 4, result.output
    assert "more than max_comparisons (20000000)" in result.output
    assert "person: 20000001 comparisons, by rule [20000001]" in result.output
    assert layout.latest_run("demo") is None
    assert not list((data_env.cache / "synthetic" / "duckdb-tmp").glob("*"))


def test_the_guard_and_the_clustering_get_one_list_of_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run.py's docstring: `guard_decisions` sees the very pairs `cluster.resolve` gets."""
    scored = scoring.Scored(
        pairs={"person": [models.ScoredPair("syn-p-1", "syn-p-2", 0.999, 9.0, {}, True, True)]}
    )
    monkeypatch.setattr(scoring, "score", lambda *args, **kwargs: scored)
    seen: dict[str, Any] = {}
    guard, resolve = run.guard_decisions, cluster.resolve

    def spy_guard(members: Any, deterministic: Any, probabilistic: Any, *rest: Any) -> Any:
        seen["guard"] = probabilistic
        return guard(members, deterministic, probabilistic, *rest)

    def spy_resolve(members: Any, deterministic: Any, probabilistic: Any, *rest: Any) -> Any:
        seen.setdefault("resolve", probabilistic)
        return resolve(members, deterministic, probabilistic, *rest)

    monkeypatch.setattr(run, "guard_decisions", spy_guard)
    monkeypatch.setattr(cluster, "resolve", spy_resolve)
    folder = tmp_path / "records"
    corpus_of(folder, [syn(f"syn-p-{n}", "Person", name="Testa Example") for n in (1, 2)])
    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    result = run.run([folder], tmp_path / "run", run.RunConfig(resolver, sha, real_data=False))
    assert seen["guard"] is seen["resolve"] and len(seen["guard"]) == 1
    assert {r["canonical_id"] for r in result.result.canonical} == {"nr-syn-p-1"}
    assert not (tmp_path / "run" / "duckdb-tmp").exists()


def test_er_blocking_on_a_real_profile_prints_no_block_key(data_env: Any, one_thread: None) -> None:
    _real_profile(data_env)
    corpus = records.read([REPO_ROOT / "data" / "fixtures" / "er-bench"])
    tables = features.feature_tables(corpus, features.members(corpus))
    with duckdb.connect() as con:
        blocks = [
            r
            for k, t in zip(scoring.KINDS, tables, strict=True)
            for r in scoring.largest_blocks(con, k, t)
        ]
    values = {str(v) for rule in blocks for b in rule for k, v in b.items() if k.startswith("key_")}
    # names and postcodes (years, initials and the `synthetic` flag could match other text)
    keys = {v for v in values if len(v) >= 4 and any(c.isalpha() for c in v) and v != "True"}
    assert len(keys) >= 5
    synthetic = runner.invoke(app, ["er", "blocking", "--profile", "demo"])
    assert synthetic.exit_code == 0, synthetic.output
    assert any(k in synthetic.output for k in keys)  # synthetic: the keys are shown
    real = runner.invoke(app, ["er", "blocking", "--profile", "real-er-test"])
    assert real.exit_code == 0, real.output
    assert "person rule 1: " in real.output and "largest blocks (records): " in real.output
    assert not [k for k in keys if k in real.output]
    assert list(layout.reports_dir("real-er-test").glob("er-blocking-*.json"))


def test_er_blocking_keeps_splink_logs_off_stderr(
    data_env: Any, one_thread: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    splink_log = logging.getLogger("splink")
    monkeypatch.setattr(splink_log, "propagate", False)  # as in a CLI process: no root handler
    monkeypatch.setattr(splink_log, "handlers", [])
    counted = _counting_spy(monkeypatch, splink_log)
    result = runner.invoke(app, ["er", "blocking", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    assert counted and all(counted)
    assert splink_log.handlers == []


def test_a_caller_says_whether_it_runs_on_real_data() -> None:
    """Fail closed (OD-10): no default for real_data, and scoring.score fails on a model the
    data cannot train unless a synthetic caller asks to skip it."""
    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    with pytest.raises(TypeError, match="real_data"):
        run.RunConfig(resolver, sha)  # type: ignore[call-arg]
    assert scoring.score.__kwdefaults__["skip_untrainable"] is False
    assert "real_data" not in (er_cli._run_config.__kwdefaults__ or {})


@pytest.mark.parametrize("kind", ["person", "org"])
def test_committed_settings_match_the_models(kind: models.Kind) -> None:
    """Regenerate with: uv run python -c "from neonradar_resolve import scoring as s;
    [open(f'resolve/models/{k}.settings.json', 'w').write(s.settings_json(k)) for k in s.KINDS]"
    """
    committed = (REPO_ROOT / "resolve" / "models" / f"{kind}.settings.json").read_text()
    assert committed == scoring.settings_json(kind)
    levels = [lv for c in json.loads(committed)["comparisons"] for lv in c["comparison_levels"]]
    assert not [lv for lv in levels if {"m_probability", "u_probability"} & set(lv)]  # untrained


def _score(**classes: tuple[int, int, int, int]) -> bench.Score:
    scores = {name: bench.ClassScore(*classes.get(name, (0, 0, 0, 0))) for name in bench.CLASSES}
    return bench.Score(scores, 0, 10, 8, 0, 0, 0)


def test_gates_and_proposal() -> None:
    passing = _score(person=(100, 98, 100, 90), org=(50, 50, 60, 55))
    assert bench.gate_failures(passing) == []
    failing = bench.Score(
        {"person": bench.ClassScore(100, 96, 100, 79), "org": passing.classes["org"]},
        0, 10, 7, 1, 0, 0,
    )  # fmt: skip
    assert bench.gate_failures(failing) == [
        "person precision 0.9600 is below 0.97",
        "person recall 0.7900 is below 0.8",
        "policy-blocked recall 0.7000 is below 0.8",
        "1 hard negatives merged",
    ]
    low, high = _score(person=(100, 90, 100, 99)), _score(person=(100, 99, 100, 80))
    blocked = bench.Score(passing.classes, 0, 10, 9, 0, 0, 0)
    points = [
        calibrate.Point(0.5, low, blocked),
        calibrate.Point(0.9, high, blocked),
        calibrate.Point(0.99, high, passing),
    ]
    assert calibrate.propose(points) == {
        "merge_threshold.person": 0.9,
        "merge_threshold.org": None,
        "candidate_threshold": 0.9,
    }


def test_a_class_whose_model_cannot_be_trained_scores_nothing(tmp_path: Path) -> None:
    """Two records give Splink no pair for its EM sessions: no model, no pair, a count."""
    folder = tmp_path / "records"
    _tiny_corpus(folder)
    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    config = run.RunConfig(
        resolver.with_threads(1), sha, temp_directory=tmp_path / "spill", real_data=False
    )
    result = run.run([folder], tmp_path / "run", config)
    assert result.probabilistic is not None
    assert result.probabilistic["models_skipped"] == {"person": 1, "org": 1}
    assert result.probabilistic["pairs_scored"] == {"person": 0, "org": 0}
    assert result.counts["joined_by_method"] == {"identity": 3}
    assert not (tmp_path / "spill" / "splink").exists()


@pytest.mark.parametrize(
    ("error", "skipped"),
    [
        (EMTrainingException, True),
        (ValueError, True),
        (ZeroDivisionError, True),
        (SplinkException, False),  # what Splink wraps every failed SQL statement in
        (pa.ArrowInvalid, False),  # a ValueError subclass
    ],
)
def test_only_errors_of_the_data_skip_a_model(error: type[Exception], skipped: bool) -> None:
    assert scoring.untrainable(error("synthetic test error")) is skipped
    for cause in (duckdb.InterruptException, duckdb.OutOfMemoryException, KeyboardInterrupt):
        wrapped = error("synthetic test error")
        wrapped.__cause__ = cause("synthetic test cause")
        assert not scoring.untrainable(wrapped)


@pytest.mark.parametrize(
    ("error", "cause"),
    [
        (SplinkException, duckdb.InterruptException),
        (SplinkException, duckdb.OutOfMemoryException),
        (ValueError, duckdb.IOException),
    ],
)
def test_a_machine_error_in_training_fails_the_run(
    data_env: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: type[Exception],
    cause: type[Exception],
) -> None:
    """An interrupt, memory or disk error is not a model that cannot be trained: no skip."""
    _profiles_read_tiny_corpus(tmp_path, monkeypatch)

    def failing(*args: Any) -> None:
        raise error("synthetic test error") from cause("synthetic test cause")

    monkeypatch.setattr(models, "train", failing)
    result = runner.invoke(app, ["er", "run", "--profile", "demo"])
    assert result.exit_code == 1 and type(result.exception) is error, result.output
    assert layout.latest_run("demo") is None
    assert not list((data_env.cache / "synthetic" / "duckdb-tmp").glob("*"))


def test_on_a_real_profile_a_model_that_cannot_be_trained_fails_the_run(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """OD-10: a real run never goes on without a model. Splink prints nothing of its own: with
    no root handler (a CLI process), its Linker would add a stderr handler to `splink`."""
    profile = _real_profile(data_env)
    _profiles_read_tiny_corpus(tmp_path, monkeypatch)
    splink_log = logging.getLogger("splink")
    monkeypatch.setattr(splink_log, "propagate", False)  # pytest's root handlers out of reach
    monkeypatch.setattr(splink_log, "handlers", [])
    result = runner.invoke(app, ["er", "run", "--profile", profile])
    assert result.exit_code == 1, result.output
    assert "ValueError, step resolve, dataset -, err-" in result.output  # redacted
    assert "Deterministic matching rules" not in result.output
    assert splink_log.handlers == []  # Splink added no handler, and scoring removed its own
    assert layout.latest_run(profile) is None
    assert not list((data_env.cache / "real" / "duckdb-tmp").glob("*"))


def test_untrained_levels_are_counted_from_splink_warnings() -> None:
    """The handler's parsing and de-duplication, on the text of Splink 5.0.0's
    expectation_maximisation.py written here; the demo run test checks Splink's real output."""
    with scoring.splink_warnings() as handler:
        log = logging.getLogger("splink.internals.expectation_maximisation")
        for level, comparison, value in [("same birth date", "birth", "m"),
                                         ("same birth date", "birth", "m"),
                                         ("surname equal", "name", "u")]:  # fmt: skip
            log.warning(
                "WARNING:\n"
                f"Level {level} on comparison {comparison} not observed in dataset, "
                f"unable to train {value} value\n"
            )
    assert handler.found == {("same birth date", "birth", "m"), ("surname equal", "name", "u")}


class _Training:
    """Records the training calls `models.train` makes, without Splink."""

    def __init__(self) -> None:
        self.sessions: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def call(*args: Any, **kwargs: Any) -> None:
            if name == "estimate_parameters_using_expectation_maximisation":
                self.sessions.append(args[0].get_blocking_rule("duckdb").blocking_rule_sql)

        return call


def test_person_em_sessions_avoid_the_near_twin_block() -> None:
    """OD-26: the postcode session first, then the first linked organisation with the birth
    year; no session blocks on surname and birth year, where near twins look like matches."""
    training = _Training()
    models.train(SimpleNamespace(training=training), "person", models.TrainingConfig())  # type: ignore[arg-type]
    assert training.sessions == [
        'l."postcode" = r."postcode"',
        '(l."linked_orgs"[1] = r."linked_orgs"[1]) AND (l."birth_year_min" = r."birth_year_min")',
    ]


def test_calibration_sweep_and_document() -> None:
    """Two records of one organisation joined at 0.97: merged up to t = 0.95, apart above."""
    members = {rid: _org(rid) for rid in ("syn-a", "syn-b")}
    truth = {rid: bench.Truth("syn-e", "org", "registry", None) for rid in members}
    pair = scoring.link(models.ScoredPair("syn-a", "syn-b", 0.97, 5.0, {}, True, True), "org")
    resolver, _ = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    points = calibrate.sweep(truth, members, [], [pair], [], resolver)
    assert [p.t for p in points] == list(calibrate.SWEEP)
    recall = {p.t: p.merge.classes["org"].recall for p in points}
    assert recall[0.95] == 1.0 and recall[0.98] == 0.0
    assert calibrate.propose(points)["merge_threshold.org"] == 0.5
    text = calibrate.document(points, calibrate.propose(points), resolver, "small", 7, {})
    assert "| 0.95 | n/a | n/a | 1.0000 | 1.0000 | 0 | 0, 0 | n/a, n/a, n/a |" in text
    assert "| `candidate_threshold` | none passes | 0.8 |" in text


def test_calibration_counts_person_organisation_merges_against_a_threshold() -> None:
    """A person's LegalEntity record joined to an organisation at 0.97 merges up to t = 0.95:
    those rows show the pairs and never pass, although organisation precision is 1.0 there."""
    members = {rid: _org(rid) for rid in ("syn-a", "syn-b")}
    members["syn-c"] = cluster.Member(
        "syn-c", "nr_synthetic", "registry", 10, "LegalEntity", "legal_entity", True,
        name_keys=frozenset({"x"}),
    )  # fmt: skip
    truth = {rid: bench.Truth("syn-e", "org", "registry", None) for rid in ("syn-a", "syn-b")}
    truth["syn-c"] = bench.Truth("syn-f", "person", "registry", None)
    pairs = [
        scoring.link(models.ScoredPair("syn-a", "syn-b", 0.999, 9.0, {}, True, True), "org"),
        scoring.link(models.ScoredPair("syn-b", "syn-c", 0.97, 5.0, {}, True, True), "org"),
    ]
    resolver, _ = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    points = calibrate.sweep(truth, members, [], pairs, [], resolver)
    assert {p.t: p.merge.cross_class_pairs_merged for p in points if p.t in (0.95, 0.98)} == {
        0.95: 2,
        0.98: 0,
    }
    assert all(p.merge.classes["org"].precision == 1.0 for p in points if p.t <= 0.999)
    assert calibrate.propose(points)["merge_threshold.org"] == 0.98  # 0.5 if they were dropped
    assert "| 0.95 | n/a | n/a | 1.0000 | 1.0000 | 0 | 2, 0 |" in "\n".join(calibrate.table(points))


def test_the_candidate_sweep_raises_a_lower_merge_threshold_to_t(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The clustering drops pairs below the candidate threshold, so above a merge threshold
    the candidate rows describe that merge threshold raised to t: the sweep says so."""
    seen: list[cluster.Config] = []

    def spy(*args: Any) -> bench.Score:
        seen.append(args[-1])
        return _score()

    monkeypatch.setattr(calibrate, "_score", spy)
    resolver, _ = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    calibrate.sweep({}, {}, [], [], [], resolver)
    candidates = {c.candidate_threshold: dict(c.merge_threshold) for c in seen[1::2]}
    assert candidates[0.8] == {"person": 0.99, "org": 0.995}  # er.yaml's values
    assert candidates[0.998] == {"person": 0.998, "org": 0.998}


def test_er_calibrate_stops_when_a_record_has_no_truth(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """As `er bench`: exit 1 and nothing written. With a truth row for every record it writes
    the table to --output. Two stored pairs stand in for scoring, so Splink does not run."""
    folder, run_dir = tmp_path / "bench", tmp_path / "run"
    (folder / "labels").mkdir(parents=True)
    run_dir.mkdir()
    members = {rid: _org(rid) for rid in ("syn-a", "syn-b", "syn-c")}
    pair = scoring.link(models.ScoredPair("syn-a", "syn-b", 0.97, 5.0, {}, True, True), "org")
    scoring.write_pairs(run_dir / "pairs.parquet", [pair], members)
    result = run.RunResult("er-test", run_dir, members, cluster.Result([], [], [], {}), {})
    monkeypatch.setattr(er_cli, "_resolve_bench", lambda *args: (folder, result))
    truth = "# synthetic: true\nrecord_id,entity_id,class,style,twin_of\n"
    truth += "syn-a,syn-e,org,registry,\nsyn-b,syn-e,org,registry,\n"
    output = tmp_path / "benchmark.md"
    command = ["er", "calibrate", "--size", "small", "--output", str(output)]
    (folder / er_cli.TRUTH).write_text(truth, encoding="utf-8")
    failed = runner.invoke(app, command)
    assert failed.exit_code == 1
    assert "FAIL  left out: 1 records without truth, 0 truth records not in the run" in (
        failed.output
    )
    assert not output.exists()
    (folder / er_cli.TRUTH).write_text(truth + "syn-c,syn-f,org,registry,\n", encoding="utf-8")
    passed = runner.invoke(app, command)
    assert passed.exit_code == 0, passed.output
    assert "| `merge_threshold.org` | 0.5 | 0.995 |" in output.read_text(encoding="utf-8")
