"""Resolution runs with the Splink models (PHASE-2.md M2.10b deliverable 10). Synthetic only:
the demo profile (data/fixtures/demo-mini and data/fixtures/er-bench) and members built here.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import duckdb
import pytest
import yaml
from nr_resolve_support import corpus_of, syn
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import layout
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_resolve import bench, calibrate, cluster, features, models, records, run, scoring
from neonradar_resolve.config import load_config

STABLE = ("canonical.csv", "candidates.jsonl", "conflicts.jsonl")
runner = CliRunner()


@pytest.fixture
def one_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests use one DuckDB thread (7.1.5): bitwise identical training."""
    connect = models.connect
    monkeypatch.setattr(models, "connect", lambda _threads, memory, temp: connect(1, memory, temp))


def _latest(profile: str) -> Path:
    run_id = layout.latest_run(profile)
    assert run_id is not None
    return layout.resolution_dir(profile, run_id)


def test_er_run_demo_scores_pairs_and_is_byte_stable(data_env: Any, one_thread: None) -> None:
    dirs = []
    for _ in range(2):
        result = runner.invoke(app, ["er", "run", "--profile", "demo"])
        assert result.exit_code == 0, result.output
        dirs.append(_latest("demo"))
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
    monkeypatch.setattr(scoring, "score", lambda *args: scored)
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
    result = run.run([folder], tmp_path / "run", run.RunConfig(resolver, sha))
    assert seen["guard"] is seen["resolve"] and len(seen["guard"]) == 1
    assert {r["canonical_id"] for r in result.result.canonical} == {"nr-syn-p-1"}
    assert not (tmp_path / "run" / "duckdb-tmp").exists()


def test_er_blocking_on_a_real_profile_prints_no_block_key(data_env: Any, one_thread: None) -> None:
    profile = {
        "profile": "real-er-test",
        "description": "Synthetic test records in a profile marked real.",
        "real_data": True,
        "sources": {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/er-bench"]}},
        "resolution": {"enabled": True, "config": "resolve/config/er.yaml"},
    }
    (data_env.profiles / "real-er-test.yaml").write_text(yaml.safe_dump(profile))
    data_env.allow_real("real-er-test")
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
    people = [
        syn(f"syn-p-{n}", "Person", name="Testa Example", birthDate="1970-01") for n in (1, 2)
    ]
    corpus_of(folder, [*people, syn("syn-o-1", "Company", name="Test Holder Ltd")])
    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    config = run.RunConfig(resolver.with_threads(1), sha, temp_directory=tmp_path / "spill")
    result = run.run([folder], tmp_path / "run", config)
    assert result.probabilistic is not None
    assert result.probabilistic["models_skipped"] == {"person": 1, "org": 1}
    assert result.probabilistic["pairs_scored"] == {"person": 0, "org": 0}
    assert result.counts["joined_by_method"] == {"identity": 3}
    assert not (tmp_path / "spill" / "splink").exists()


def test_untrained_levels_are_counted_from_splink_warnings() -> None:
    """The text of splink/internals/expectation_maximisation.py (5.0.0); a Splink bump that
    changes it makes this test fail instead of reporting 0 untrained levels."""
    with scoring._untrained() as handler:
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
    assert "| 0.95 | n/a | n/a | 1.0000 | 1.0000 | 0 |" in text
    assert "| `candidate_threshold` | none passes | 0.8 |" in text
