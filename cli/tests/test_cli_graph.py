import json
import os
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from neo4j.exceptions import ClientError, ServiceUnavailable
from typer.testing import CliRunner

from neonradar_cli import graph
from neonradar_cli.main import app
from neonradar_contracts.records import RecordIssue
from neonradar_graph import instances, loader
from neonradar_graph.client import REPO_ROOT
from neonradar_graph.instances import Instance
from neonradar_graph.loader import (
    DanglingReference,
    GraphStats,
    LoadError,
    LoadRefused,
    LoadReport,
)
from neonradar_graph.mapping import MappingIssue
from neonradar_graph.migrate import MIGRATIONS_DIR, Migration, MigrationError, MigrationReport
from neonradar_graph.smoke import SmokeReport

runner = CliRunner()
MANIFEST = next((REPO_ROOT / "data" / "fixtures" / "demo-mini").glob("*.manifest.json"))


@pytest.fixture(autouse=True)
def settings_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Never read the repository's real .env in these tests."""
    for name in [key for key in os.environ if key.startswith(("NEO4J_", "NR_NEO4J_"))]:
        monkeypatch.delenv(name)
    monkeypatch.setitem(graph.Neo4jSettings.model_config, "env_file", tmp_path / "missing.env")
    for settings in (instances.RealNeo4jSettings, instances._DatabaseSetting):
        monkeypatch.setitem(settings.model_config, "env_file", tmp_path / "missing.env")


@contextmanager
def fake_driver(*args: Any) -> Iterator[object]:
    yield object()


def use_fakes(monkeypatch: pytest.MonkeyPatch, report: SmokeReport) -> None:
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)
    monkeypatch.setattr(graph, "run_smoke", lambda driver, database: report)


@pytest.mark.parametrize(
    ("report", "exit_code"),
    [
        (SmokeReport("5.26.32 community", "5.26.32", "2.13.4"), 0),
        (SmokeReport("5.26.32 community", "5.26.32", None), 1),
    ],
)
def test_smoke_prints_one_line_per_component(
    monkeypatch: pytest.MonkeyPatch, report: SmokeReport, exit_code: int
) -> None:
    use_fakes(monkeypatch, report)
    result = runner.invoke(app, ["graph", "smoke"])
    assert result.exit_code == exit_code
    assert result.output.splitlines() == report.lines()


def test_smoke_without_a_password_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(app, ["graph", "smoke"])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD is not set" in result.output


def test_smoke_when_neo4j_is_down_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, SmokeReport(None, None, None))

    def down(driver: object, timeout_s: float) -> None:
        raise ServiceUnavailable("connection refused")

    monkeypatch.setattr(graph, "wait_until_ready", down)
    result = runner.invoke(app, ["graph", "smoke", "--timeout", "1"])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  Neo4j  not reachable at bolt://localhost:7687")
    assert "test-password" not in result.output


def use_migrate(monkeypatch: pytest.MonkeyPatch, outcome: MigrationReport | Exception) -> None:
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)

    def fake_migrate(driver: object, database: str, directory: Path) -> MigrationReport:
        assert (database, directory) == ("neo4j", MIGRATIONS_DIR)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(graph, "migrate", fake_migrate)


def test_migrate_prints_each_applied_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    init = Migration("0001_init", MIGRATIONS_DIR / "0001_init.cypher", "abc", ("RETURN 1",) * 29)
    use_migrate(monkeypatch, MigrationReport(applied=[init]))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 0
    assert result.output == "applied 0001_init (29 statements)\n"


def test_migrate_again_has_nothing_to_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, MigrationReport(already_applied=["0001_init"]))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 0
    assert result.output == "nothing to apply (1 migration already applied)\n"


def test_migrate_refuses_an_edited_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, MigrationError("add a new migration; never edit an applied one"))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 1
    assert result.output == "FAIL  add a new migration; never edit an applied one\n"


def test_migrate_reports_a_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    use_migrate(monkeypatch, ClientError("Invalid input"))
    result = runner.invoke(app, ["graph", "migrate"])
    assert result.exit_code == 1
    assert result.output.startswith("FAIL  Neo4j  at bolt://localhost:7687 answered:")


def use_loader(
    monkeypatch: pytest.MonkeyPatch, outcome: LoadReport | Exception
) -> list[dict[str, Any]]:
    """Fake `loader.load`; returns the calls it received."""
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(graph, "get_driver", fake_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)

    def fake_load(
        paths: list[Path],
        resolution: Path | None,
        replace: bool,
        instance: Instance,
        *,
        strict: bool,
        timeout_s: float,
    ) -> LoadReport:
        calls.append(
            {
                "paths": paths,
                "resolution": resolution,
                "replace": replace,
                "instance": instance,
                "strict": strict,
            }
        )
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(loader, "load", fake_load)
    return calls


def records_folder(tmp_path: Path, *, synthetic: bool | None = None) -> Path:
    """A folder with one (empty) record file and, when `synthetic` is given, a manifest."""
    (tmp_path / "a.ftm.jsonl").write_text("", encoding="utf-8")
    if synthetic is not None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if not synthetic:  # a look-alike of a real dataset's manifest, built here (G9)
            manifest |= {"dataset": "gb_companies_house", "synthetic": False}
            manifest["licence"] = {"id": "OGL-UK-3.0", "attribution": "Test attribution"}
        (tmp_path / "a.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def load_report(**changes: Any) -> LoadReport:
    report = LoadReport(
        strict=True,
        files=[Path("a.ftm.jsonl")],
        records=3,
        nodes_by_label=Counter({"Entity": 2, "Company": 1}),
        relationships_by_type=Counter({"OWNS": 1}),
        written=Counter(nodes_created=2, relationships_created=1),
        duration_s=0.5,
    )
    for name, value in changes.items():
        setattr(report, name, value)
    return report


DANGLING = DanglingReference("PAID", "syn-payment-1", "syn-acct-1", "syn-acct-9", False, True)


def test_load_prints_counts_and_is_strict_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report())
    result = runner.invoke(app, ["graph", "load", str(records_folder(tmp_path))])
    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "paths": [tmp_path],
            "resolution": None,
            "replace": True,
            "instance": Instance.DEFAULT,
            "strict": True,
        }
    ]
    lines = result.output.splitlines()
    assert lines[0] == "3 records from 1 file(s), strict"
    assert lines[1:7] == [
        "nodes by label:",
        "  Company: 1",
        "  Entity: 2",
        "relationships by type:",
        "  OWNS: 1",
        "created 2 nodes and 1 relationships; moved 0 relationships; labels 0 added and 0 removed",
    ]
    assert "dangling references: 0" in lines
    assert lines[-1] == "OK in 0.5 s"


def test_a_non_strict_load_reports_dangling_references_and_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report(strict=False, dangling=[DANGLING]))
    result = runner.invoke(app, ["graph", "load", "--no-strict", str(records_folder(tmp_path))])
    assert result.exit_code == 0, result.output
    assert calls[0]["strict"] is False
    assert "  DANGLING PAID syn-payment-1: no :Account node syn-acct-9" in result.output
    assert result.output.endswith("WARN in 0.5 s\n")


def test_an_empty_record_file_is_a_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_loader(monkeypatch, load_report(empty_files=[Path("empty.ftm.jsonl")]))
    result = runner.invoke(app, ["graph", "load", str(records_folder(tmp_path))])
    assert result.exit_code == 0
    assert "WARN  empty.ftm.jsonl holds no records" in result.output.splitlines()
    assert result.output.endswith("WARN in 0.5 s\n")


def test_a_strict_load_with_dangling_references_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_loader(monkeypatch, load_report(dangling=[DANGLING]))
    result = runner.invoke(app, ["graph", "load", str(records_folder(tmp_path))])
    assert result.exit_code == 1
    assert result.output.endswith(
        "FAILED (strict): 1 dangling reference(s); the rest of the load was written:"
        " fix the input and load again\n"
    )


def test_a_refused_load_lists_its_issues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    issues = [RecordIssue("R7", f"syn-payment-{n}", "amount must be above 0") for n in range(30)]
    use_loader(monkeypatch, LoadRefused(issues, [MappingIssue("syn-o-1", "two owners")]))
    result = runner.invoke(app, ["graph", "load", str(records_folder(tmp_path))])
    assert result.exit_code == 1
    lines = result.output.splitlines()
    assert lines[0] == "  R7 syn-payment-0: amount must be above 0"
    assert lines[-2:] == [
        "  ... and 6 more",
        "REFUSED (strict): 31 issue(s); nothing was written",
    ]


def test_a_load_that_cannot_start_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_loader(monkeypatch, LoadError("FORMAT a.ftm.jsonl:2: invalid JSON"))
    result = runner.invoke(app, ["graph", "load", str(records_folder(tmp_path))])
    assert (result.exit_code, result.output) == (1, "FAIL  FORMAT a.ftm.jsonl:2: invalid JSON\n")


def test_stats_prints_counts_by_label_and_type(monkeypatch: pytest.MonkeyPatch) -> None:
    use_loader(monkeypatch, load_report())
    counted = GraphStats(3, 1, {"Company": 1, "Entity": 2}, {"OWNS": 1})
    monkeypatch.setattr(loader, "stats", lambda driver, database: counted)
    result = runner.invoke(app, ["graph", "stats"])
    assert result.exit_code == 0
    assert result.output.splitlines() == [
        "nodes: 3",
        "  Company: 1",
        "  Entity: 2",
        "relationships: 1",
        "  OWNS: 1",
    ]


def test_wipe_refuses_without_yes_and_never_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_driver(*args: Any) -> None:
        raise AssertionError("wipe connected without --yes")

    monkeypatch.setattr(graph, "get_driver", no_driver)
    result = runner.invoke(app, ["graph", "wipe"])
    assert result.exit_code == 1
    assert result.output.startswith("REFUSED  graph wipe deletes every node except")


def test_wipe_with_yes_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    use_loader(monkeypatch, load_report())
    monkeypatch.setattr(loader, "wipe", lambda driver, database: 7)
    result = runner.invoke(app, ["graph", "wipe", "--yes"])
    assert result.exit_code == 0
    assert result.output == "deleted 7 nodes from bolt://localhost:7687 (database neo4j)\n"
    assert "test-password" not in result.output


def test_load_profile_resolution_latest_takes_the_run_er_run_finished_last(
    monkeypatch: pytest.MonkeyPatch, data_env: Any
) -> None:
    from neonradar_ingest.data import layout
    from neonradar_ingest.data.profiles import load_profile

    calls = use_loader(monkeypatch, load_report(resolution_run="er-20261023T120000-0a0b"))
    command = ["graph", "load", "--profile", "demo", "--resolution", "latest"]
    result = runner.invoke(app, command)
    assert result.exit_code == 2 and calls == []  # no finished run yet: never loads
    assert "has no finished resolution run" in result.output
    demo = load_profile("demo")
    run_dir = layout.resolution_dir(demo, "er-20261023T120000-0a0b")
    run_dir.mkdir(parents=True)
    (run_dir.parent / layout.LATEST).write_text(f"{run_dir.name}\n", encoding="utf-8")
    result = runner.invoke(app, [*command, "--no-replace"])
    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "paths": demo.record_dirs(),
            "resolution": run_dir,
            "replace": False,
            "instance": Instance.DEFAULT,
            "strict": True,
        }
    ]
    assert "resolution run er-20261023T120000-0a0b: 0 canonical entities" in result.output
    assert "possible matches not written (a node outside this load): 0" in result.output
    assert "nodes removed before the load (L9 purge): 0" in result.output


def test_load_needs_paths_or_a_profile_and_latest_needs_a_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report())
    assert runner.invoke(app, ["graph", "load"]).exit_code == 2
    folder = str(records_folder(tmp_path))
    result = runner.invoke(app, ["graph", "load", folder, "--resolution", "latest"])
    assert (result.exit_code, calls) == (2, [])
    assert "--resolution latest needs --profile NAME" in result.output


def test_a_real_profile_or_real_manifests_hit_the_gate_before_any_connection(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report())
    result = runner.invoke(app, ["graph", "load", "--profile", "uk-tiny"])
    assert (result.exit_code, calls) == (3, [])
    assert "uk-tiny is not in access.real_data_profiles" in result.output
    real = str(records_folder(tmp_path, synthetic=False))
    result = runner.invoke(app, ["graph", "load", real])
    assert (result.exit_code, calls) == (3, [])
    assert "access.real_data_profiles is empty" in result.output


def test_one_real_manifest_among_synthetic_ones_takes_the_gate(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, tmp_path: Path
) -> None:
    calls = use_loader(monkeypatch, load_report())
    (tmp_path / "real").mkdir()
    (tmp_path / "synthetic").mkdir()
    real = str(records_folder(tmp_path / "real", synthetic=False))
    synthetic = str(records_folder(tmp_path / "synthetic", synthetic=True))
    result = runner.invoke(app, ["graph", "load", synthetic, real])
    assert (result.exit_code, calls) == (3, [])
    assert "access.real_data_profiles is empty" in result.output


def test_a_synthetic_profile_never_reads_real_records_or_a_real_run(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, tmp_path: Path
) -> None:
    from neonradar_ingest.data import layout

    calls = use_loader(monkeypatch, load_report())
    real = str(records_folder(tmp_path, synthetic=False))
    result = runner.invoke(app, ["graph", "load", real, "--profile", "demo"])
    assert (result.exit_code, calls) == (2, [])
    assert "profile demo is synthetic, but 1 path(s) or manifest(s)" in result.output
    run_dir = layout.real_root() / "uk-tiny" / "resolution" / "er-20261023T120000-0a0b"
    run_dir.mkdir(parents=True)  # under the test's cache root (data_env)
    command = ["graph", "load", "--profile", "demo", "--resolution", str(run_dir)]
    result = runner.invoke(app, command)
    assert (result.exit_code, calls) == (2, [])
    assert "--resolution names a folder of real data" in result.output


def test_a_real_load_prints_counts_only(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, tmp_path: Path
) -> None:
    data_env.allow_real("uk-tiny")
    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")
    dangling = DanglingReference("OWNS", "gbch-o-T1", "gbch-p-T1", "gbch-co-T0000001", True, False)
    calls = use_loader(monkeypatch, load_report(strict=False, dangling=[dangling]))
    real = str(records_folder(tmp_path, synthetic=False))
    result = runner.invoke(app, ["graph", "load", "--no-strict", real])
    assert result.exit_code == 0, result.output
    assert calls[0]["instance"] is Instance.REAL
    assert "gbch-" not in result.output and "test-real-password" not in result.output
    printed = json.loads(result.output)
    assert printed["dangling_references"] == 1 and printed["instance_real"] is True
    assert printed["nodes_by_label"] == {"company": 1, "entity": 2}


def test_verify_prints_one_line_per_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    from neonradar_graph import verify

    use_loader(monkeypatch, load_report())
    counts = {f"I{n}": 0 for n in range(1, 15)}
    monkeypatch.setattr(verify, "verify", lambda driver, database: counts)
    result = runner.invoke(app, ["graph", "verify"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[:2] == ["I1: 0", "I2: 0"] and lines[13] == "I14: 0"
    assert lines[-1] == "OK  0 violation(s) of 14 invariants"
    counts["I13"] = 2
    result = runner.invoke(app, ["graph", "verify"])
    assert (result.exit_code, result.output.splitlines()[-1]) == (
        1,
        "FAIL  2 violation(s) of 14 invariants",
    )


@pytest.mark.parametrize(
    "command",
    [
        ["graph", "migrate", "--real"],
        ["graph", "verify", "--real"],
        ["graph", "stats", "--real"],
        ["graph", "wipe", "--real", "--yes"],
    ],
)
def test_real_instance_commands_refuse_while_no_real_profile_is_listed(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, command: list[str]
) -> None:
    def no_driver(*args: Any) -> None:
        raise AssertionError("connected before the real-data gate")

    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")
    monkeypatch.setattr(graph, "get_driver", no_driver)
    result = runner.invoke(app, command)
    assert result.exit_code == 3, result.output
    assert "access.real_data_profiles is empty" in result.output


def test_real_stats_use_the_real_instance_and_print_counts(
    monkeypatch: pytest.MonkeyPatch, data_env: Any
) -> None:
    data_env.allow_real("uk-tiny")
    seen: list[Any] = []

    @contextmanager
    def real_driver(settings: Any) -> Iterator[object]:
        seen.append((settings.uri, settings.database))
        yield object()

    monkeypatch.setattr(graph, "get_driver", real_driver)
    monkeypatch.setattr(graph, "wait_until_ready", lambda driver, timeout_s: None)
    counted = GraphStats(3, 1, {"Company": 1, "Entity": 2}, {"OWNS": 1})
    monkeypatch.setattr(loader, "stats", lambda driver, database: counted)
    result = runner.invoke(app, ["graph", "stats", "--real"])
    assert result.exit_code == 1  # no NEO4J_REAL_PASSWORD
    assert result.output == (
        "FAIL  NEO4J_REAL_PASSWORD is not set: set it on a machine listed in"
        " docs/data/real-data-machines.md\n"
    )
    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")
    result = runner.invoke(app, ["graph", "stats", "--real"])
    assert result.exit_code == 0, result.output
    assert seen == [(instances.REAL_URI, instances.REAL_DATABASE)]
    assert result.output.splitlines()[0] == "nodes: 3"


# graph load --overlay (C2 L18, PHASE-3.md M3.4) ----------------------------------------------


def overlay_folder(folder: Path, profile: str, records: list[dict[str, Any]] | None = None) -> Path:
    folder.mkdir(parents=True)
    (folder / "overlay.json").write_text(json.dumps({"profile": profile}), encoding="utf-8")
    lines = "".join(json.dumps(item) + "\n" for item in records or [])
    (folder / "o.ftm.jsonl").write_text(lines, encoding="utf-8")
    return folder


def use_overlay(monkeypatch: pytest.MonkeyPatch, outcome: LoadReport) -> list[dict[str, Any]]:
    """Fake `overlay.load_overlay`; returns the calls it received."""
    from neonradar_graph import overlay

    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("NEO4J_REAL_PASSWORD", "test-real-password")

    def fake(folder: Path, profile: str, instance: Instance, allowed: Any = (), **_: Any) -> Any:
        calls.append({"profile": profile, "instance": instance, "allowed": list(allowed)})
        return outcome

    monkeypatch.setattr(overlay, "load_overlay", fake)
    return calls


@pytest.mark.parametrize("protected", ["real", "REAL", "spikes", "Holdout", "heldout"])
def test_an_overlay_in_a_protected_folder_is_refused_before_it_is_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, protected: str
) -> None:
    calls = use_overlay(monkeypatch, load_report())
    folder = overlay_folder(tmp_path / "data" / "cache" / protected / "overlay" / "x", "demo")
    result = runner.invoke(app, ["graph", "load", "--overlay", str(folder)])
    assert (result.exit_code, calls) == (3, [])
    assert "protected data/cache folder" in result.output


def test_a_synthetic_overlay_loads_into_the_default_instance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = use_overlay(monkeypatch, load_report(overlay_records=3, overlay_removed=2))
    folder = str(overlay_folder(tmp_path / "ov", "synth-demo"))
    result = runner.invoke(app, ["graph", "load", "--overlay", folder])
    assert result.exit_code == 0, result.output
    assert calls == [{"profile": "synth-demo", "instance": Instance.DEFAULT, "allowed": []}]
    assert "overlay ov: 3 records; previous overlay nodes removed: 2" in result.output
    real = str(overlay_folder(tmp_path / "real", "uk-tiny"))  # a real profile's overlay.json
    for args, code in [
        (["--overlay", "latest"], 2),
        (["--overlay", folder, folder], 2),
        (["--overlay", folder, "--no-strict"], 2),
        (["--overlay", real], 3),
    ]:
        assert runner.invoke(app, ["graph", "load", *args]).exit_code == code, args
    assert len(calls) == 1


def test_a_real_profile_s_overlay_passes_the_gate_and_the_overlay_list_first(
    monkeypatch: pytest.MonkeyPatch, data_env: Any, tmp_path: Path
) -> None:
    calls = use_overlay(monkeypatch, load_report(overlay_records=3))
    args = ["graph", "load", "--profile", "uk-tiny", "--overlay", "latest"]
    result = runner.invoke(app, args)
    assert (result.exit_code, calls) == (3, [])
    assert "uk-tiny is not in access.real_data_profiles" in result.output
    data_env.allow_real("uk-tiny")
    result = runner.invoke(app, args)
    assert (result.exit_code, calls) == (3, [])
    assert "uk-tiny is not in access.real_overlay_profiles" in result.output
    data_env.allow_real("uk-tiny", real_overlay_profiles=["uk-tiny"])
    latest = data_env.cache / "real" / "overlay" / "uk-tiny"  # a tmp tree (data_env)
    latest.mkdir(parents=True)
    (latest / "LATEST").write_text("ov-20261023T120000-0a0b\n", encoding="utf-8")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert calls == [{"profile": "uk-tiny", "instance": Instance.REAL, "allowed": ["uk-tiny"]}]
    printed = json.loads(result.output)
    assert (printed["overlay_records"], printed["instance_real"]) == (3, True)
    result = runner.invoke(
        app, ["graph", "load", "--profile", "uk-tiny", "--overlay", str(tmp_path)]
    )
    assert (result.exit_code, len(calls)) == (3, 1)


def test_a_doctored_overlay_stops_with_exit_2_before_connecting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The data steward's review question (M3.4): a Directorship naming a base company."""
    from neonradar_graph import overlay

    def no_driver(*args: Any) -> Any:
        raise AssertionError("connected before the bridge check")

    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(overlay, "get_driver", no_driver)
    nr = {"v": "1.0", "synthetic": True}
    rows = [
        {"id": "syn-ov-co-1", "schema": "Company", "datasets": ["nr_synthetic"],
         "properties": {"name": ["Synthetic Example Ltd"]}, "nr": nr},
        {"id": "syn-ov-dir-1", "schema": "Directorship", "datasets": ["nr_synthetic"],
         "properties": {"director": ["syn-ov-co-1"], "organization": ["syn-co-0000000001"]},
         "nr": nr},
    ]  # fmt: skip
    folder = overlay_folder(tmp_path / "ov", "synth-demo", rows)
    result = runner.invoke(app, ["graph", "load", "--overlay", str(folder)])
    assert result.exit_code == 2, result.output
    assert "the bridge check failed" in result.output and "syn-co-" not in result.output
