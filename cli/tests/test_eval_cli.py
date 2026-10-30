"""`neonradar eval` through the CLI's test runner (PHASE-3.md M3.6 deliverable 6).

Every run goes to a temporary cache (`layout.CACHE_ROOT`). The refusals stop before a world is
generated: `evaluate.run_seed` fails the test if it is reached. The `eval check` cases replace the
CI seed's run with the baseline's own rows for the merged detectors, so they check what the
command prints and returns; the CI `eval` job runs the seed itself."""

import json
from contextlib import nullcontext
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli import eval_commands, evaluate, tty
from neonradar_cli.main import app
from neonradar_contracts.alert import Alert
from neonradar_detect import catalog, runner, runs
from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.synth import overlay, world
from neonradar_ingest.synth.namesource import default_names

cli = CliRunner()
REPO = Path(__file__).resolve().parents[2]
CI_JSON = REPO / "eval" / "baselines" / "ci.json"
SMALL = evaluate.EvalSettings(
    "synth-eval",
    world.WorldConfig(companies=60, people=90, agent_every=30, professional_every=30),
    date(2025, 1, 1),
    date(2026, 7, 1),
    illicit=1,
    lookalikes=1,
    overrides={"mass_registration_address": {"top_share": 0.0}},
)


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "cache"
    monkeypatch.setattr(layout, "CACHE_ROOT", root)
    monkeypatch.setattr(eval_commands, "FREEZE_FILE", tmp_path / "freeze.json")
    return root


@pytest.fixture
def no_seed_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        pytest.fail("a refused command generated a world")

    monkeypatch.setattr(evaluate, "run_seed", refuse)


def test_the_holdout_run_refuses_without_a_terminal_and_a_freeze(
    cache: Path, no_seed_runs: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI", "1")
    result = cli.invoke(app, ["eval", "run", "--split", "test"])  # CliRunner's stdin: no terminal
    assert result.exit_code == 2, result.output
    assert "terminal" in result.output
    assert not cache.exists()


def test_each_holdout_check_refuses_on_its_own(
    cache: Path, no_seed_runs: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(tty, "require_terminal", lambda command: None)
    monkeypatch.delenv("CODESPACES", raising=False)
    monkeypatch.setenv("CI", "true")
    steps: list[str] = []
    for env, freeze in (("CI", False), ("CODESPACES", False), (None, False), (None, True)):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("CODESPACES", raising=False)
        if env:
            monkeypatch.setenv(env, "true")
        if freeze:
            (tmp_path / "freeze.json").write_text("{}", encoding="utf-8")
        result = cli.invoke(app, ["eval", "run", "--split=test"])
        assert result.exit_code == 2, result.output
        steps.append(result.output)
    assert "CI or in Codespaces" in steps[0] and "CI or in Codespaces" in steps[1]
    assert "no eval/freeze.json" in steps[2]
    assert "comes with M3.11" in steps[3]
    memory = cli.invoke(app, ["eval", "run", "--split", "test", "--engine", "memory"])
    assert memory.exit_code == 2 and "--engine neo4j" in memory.output
    assert not cache.exists()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--split", "dev", "--seeds", "99"], "not development seeds of eval/seeds.yaml: 99"),
        (["--split", "dev", "--seeds", "1-x"], "give seeds as 1-5 or 1,3,7"),
        (["--split", "TEST"], "--split must be dev or test"),
        (["--split", "dev", "--engine", "gpu"], "--engine must be memory or neo4j"),
    ],
)
def test_only_development_seeds_run(
    cache: Path, no_seed_runs: None, args: list[str], message: str
) -> None:
    result = cli.invoke(app, ["eval", "run", *args])
    assert result.exit_code == 2, result.output
    assert message in result.output
    assert not cache.exists()


def merged_rows() -> dict[str, Any]:
    """ci.json's document with only the rows of the detectors that have merged."""
    expected = json.loads(CI_JSON.read_text(encoding="utf-8"))
    merged = runner.detectors(catalog.load())
    rows = {slug: row for slug, row in expected["typologies"].items() if slug in merged}
    return {**expected, "typologies": rows}


def test_eval_check_names_each_changed_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(eval_commands, "ci_counts", lambda seeds, settings: merged_rows())
    copy = tmp_path / "ci.json"
    copy.write_bytes(CI_JSON.read_bytes())
    same = cli.invoke(app, ["eval", "check", "--baseline", str(copy)])
    assert same.exit_code == 0, same.output
    pending = set(json.loads(copy.read_text(encoding="utf-8"))["typologies"]) - set(
        merged_rows()["typologies"]
    )
    assert all(f"PEND  {slug}:" in same.output for slug in pending)

    slug = sorted(merged_rows()["typologies"])[0]
    changed = json.loads(copy.read_text(encoding="utf-8"))
    true = changed["typologies"][slug]["true"]
    changed["typologies"][slug]["true"] = true + 1
    copy.write_text(json.dumps(changed), encoding="utf-8")
    result = cli.invoke(app, ["eval", "check", "--baseline", str(copy)])
    assert result.exit_code == 1, result.output
    assert f"DIFF  {slug}:" in result.output
    assert f"{slug}.true: {true} != {true + 1}" in result.output


def test_the_settings_come_from_the_profile() -> None:
    settings = eval_commands.settings_from_profile(load_profile("synth-eval"))
    assert (settings.world.companies, settings.world.people) == (600, 900)
    assert (settings.start, settings.end) == (date(2025, 1, 1), date(2026, 7, 1))
    assert (settings.illicit, settings.lookalikes) == (10, 10)
    assert settings.typologies == tuple(overlay.SCENARIOS)
    assert settings.overrides == {"mass_registration_address": {"top_share": 0.0}}
    assert settings.created_at == datetime(2026, 11, 2, tzinfo=UTC)


def test_a_development_run_writes_its_folder(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(eval_commands, "load_settings", lambda name: SMALL)
    result = cli.invoke(app, ["eval", "run", "--split", "dev", "--seeds", "2"])
    assert result.exit_code == 0, result.output
    (folder,) = (cache / "synthetic" / "eval").iterdir()
    assert folder.name.startswith("eval-dev-")
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    assert (report["meta"]["split"], report["meta"]["seeds"]) == ("dev", [2])
    assert set(report["typologies"]) == set(runner.detectors(catalog.load()))
    assert json.loads((folder / "seeds.json").read_text(encoding="utf-8"))["2"]["record_sha256"]
    assert (folder / "seed-2" / "labels" / "manifest.json").is_file()
    alerts = (folder / "seed-2" / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(alerts) == sum(row["alerts"] for row in report["typologies"].values())
    for line in alerts:  # C4 alerts, with the evidence query's hash as `detect run` writes it
        alert = Alert.model_validate_json(line)
        assert alert.detector.query_sha256 == runs.EVIDENCE_SHA256
    assert "| `circular_flow` |" in result.output and (folder / "report.md").is_file()


@pytest.mark.parametrize(
    "env",
    [
        {"NEO4J_URI": "bolt://127.0.0.1:7688"},
        {"NEO4J_URI": "neo4j://localhost:7688/"},
        {"NEO4J_DATABASE": "realdata"},
        {"NEO4J_URI": "bolt://127.0.0.1:17699", "NR_NEO4J_REAL_URI": "bolt://127.0.0.1:17699"},
    ],
)
def test_the_neo4j_engine_refuses_the_real_instance(
    cache: Path, no_seed_runs: None, monkeypatch: pytest.MonkeyPatch, env: dict[str, str]
) -> None:
    """Refused from the settings alone (C2 L17): `_connected` fails the test if it is reached."""
    monkeypatch.setenv("NEO4J_PASSWORD", "unused")
    monkeypatch.delenv("NR_NEO4J_REAL_URI", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(eval_commands, "load_settings", lambda name: SMALL)
    monkeypatch.setattr(eval_commands, "_connected", lambda *a: pytest.fail("it connected"))
    result = cli.invoke(app, ["eval", "run", "--split", "dev", "--seeds", "2", "--engine", "neo4j"])
    assert result.exit_code == 3, result.output
    assert "names the real-data instance" in result.output
    assert not cache.exists()


def test_the_default_instance_passes_the_real_instance_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NR_NEO4J_REAL_URI", raising=False)
    eval_commands.refuse_real_instance("bolt://localhost:7687", "neo4j")
    eval_commands.refuse_real_instance("bolt://neo4j:7687", "neo4j")


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("a holdout seed runs only through `eval run --split test` (G11)", 2),
        ("scenario syn-sc-x may not use syn-co-y", 1),
    ],
)
def test_only_the_holdout_refusal_exits_2(
    cache: Path, monkeypatch: pytest.MonkeyPatch, message: str, code: int
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise PermissionError(message)

    monkeypatch.setattr(eval_commands, "load_settings", lambda name: SMALL)
    monkeypatch.setattr(evaluate, "run_seed", refuse)
    result = cli.invoke(app, ["eval", "run", "--split", "dev", "--seeds", "2"])
    assert result.exit_code == code, result.output
    assert message in result.output


def test_the_holdout_run_prints_no_figures(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Past the gate (patched: it refuses until M3.11), the holdout figures go to holdout_dir only.
    `run_seed` is a stand-in, so no world is generated."""
    stand_in = frozenset(range(1, 11))  # not holdout seeds: people choose those in M3.11 (G11)
    monkeypatch.setattr(eval_commands, "_holdout_gate", lambda: stand_in)
    monkeypatch.setattr(eval_commands, "load_settings", lambda name: SMALL)
    monkeypatch.setattr(eval_commands, "_source_factory", lambda engine, timeout: nullcontext())

    def run(seed: int, *args: Any, allow_holdout: bool, **kwargs: Any) -> SimpleNamespace:
        assert allow_holdout and args[3] == "test"
        (args[4] / f"seed-{seed}").mkdir()
        counts = {"records": 5, "alerts": 7}
        return SimpleNamespace(seed=seed, counts=counts, seconds={"detect": 0.1}, alerts=())

    monkeypatch.setattr(evaluate, "run_seed", run)
    monkeypatch.setattr(eval_commands, "_write_run", lambda *args: "| the holdout table |")
    result = cli.invoke(app, ["eval", "run", "--split", "test"])
    assert result.exit_code == 0, result.output
    printed, _, last = result.output.rpartition("wrote ")
    (folder,) = (cache / "holdout").iterdir()
    assert last == f"{folder}\n"
    assert "table" not in printed and "alerts" not in printed
    assert "seed 1: 5 records (detect 0.1 s)" in printed


@pytest.mark.integration
def test_the_neo4j_factory_refuses_real_nodes_and_matches_memory(
    graph_db: Any, tmp_path: Path
) -> None:
    driver, database = graph_db.driver, graph_db.database
    factory = eval_commands.neo4j_factory(driver, database)
    real = {"id": "gbch-co-T0000001", "schema": "Company", "datasets": ["gb_companies_house"]}
    with pytest.raises(eval_commands.EvalError, match="non-synthetic record"):
        factory([real])
    driver.execute_query(
        "CREATE (:Entity {id: $id, synthetic: false})", id=real["id"], database_=database
    )
    with pytest.raises(eval_commands.EvalError, match="1 non-synthetic nodes"):
        factory([])
    kept, _, _ = driver.execute_query("MATCH (n:Entity) RETURN count(n) AS n", database_=database)
    assert kept[0]["n"] == 1  # refused before the wipe
    driver.execute_query("MATCH (n:Entity) DETACH DELETE n", database_=database)

    cat = catalog.load()
    mem = evaluate.run_seed(3, SMALL, default_names(), cat, "dev", tmp_path / "m")
    neo = evaluate.run_seed(3, SMALL, default_names(), cat, "dev", tmp_path / "n", factory)
    assert mem.alert_ids  # seed 3 gives one alert, so the comparison is never of two empty runs
    assert neo.alert_ids == mem.alert_ids
    assert evaluate.baseline(neo) == evaluate.baseline(mem)
