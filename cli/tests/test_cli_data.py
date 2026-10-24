"""`neonradar data` and `neonradar ingest build` (PHASE-2.md M2.2 deliverables 11 and 12)."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli import real_graph
from neonradar_cli.main import app
from neonradar_ingest.data import sources
from neonradar_ingest.data.sources import Builder, BuildResult

runner = CliRunner()


def reports(data_env: Any, profile: str) -> list[dict[str, Any]]:
    folder = data_env.cache / "reports" / profile
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.iterdir())]


def test_data_profiles_shows_each_gate_condition(data_env: Any) -> None:
    result = runner.invoke(app, ["data", "profiles"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[:2] == [
        "demo: synthetic data; may run on this machine: yes",
        "  datasets: nr_synthetic",
    ]
    tiny = lines[lines.index("uk-tiny: real data; may run on this machine: no") :]
    assert tiny[1:5] == [
        "  listed in access.real_data_profiles: no",
        "  access.data_protection_filed is true: no",
        "  not in CI or Codespaces: yes",
        "  NR_REAL_DATA_MACHINE=approved: no",
    ]
    assert "  not allowed: un_sc_sanctions is not in access.sanctions_lists" in tiny


def test_data_fetch_refuses_a_real_profile_by_default(data_env: Any) -> None:
    result = runner.invoke(app, ["data", "fetch", "--profile", "uk-tiny"])
    assert result.exit_code == 3
    assert "uk-tiny is not in access.real_data_profiles" in result.output


def test_data_fetch_names_the_missing_loaders(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every loader that has arrived (Companies House M2.3a, GLEIF M2.4, ICIJ M2.5 and the
    # sanctions lists from M2.6a) finds nothing here: no request, no file. The EU list's is
    # taken out, as if it had not arrived, so the command names it.
    for slug in list(sources._SOURCES):
        monkeypatch.setitem(sources._SOURCES, slug, sources.SourceSpec(slug, lambda client: []))
    monkeypatch.delitem(sources._SOURCES, "eu_fsf", raising=False)
    data_env.write_project(real_data_profiles=["uk-tiny"], data_protection_filed=True)
    data_env.approve_machine()
    result = runner.invoke(app, ["data", "fetch", "--profile", "uk-tiny"])
    assert result.exit_code == 0, result.output
    assert "eu_fsf: not available until M2.6d" in result.output
    report = reports(data_env, "uk-tiny")[0]
    assert report["datasets"]["eu_fsf"] == {"status": "not available until M2.6d"}
    for slug in ("gb_companies_house", "gleif_lei", "gb_fcdo_sanctions"):
        assert report["datasets"][slug] == {"status": "ok", "products": {}}
    assert not (data_env.cache / "real").exists()  # nothing downloaded
    assert report["project_file"] == "(outside the repository) project.yaml"
    result = runner.invoke(
        app, ["data", "fetch", "--profile", "uk-tiny", "--dataset", "icij_offshore_leaks"]
    )
    assert (result.exit_code, "not enabled in profile uk-tiny" in result.output) == (2, True)


def test_data_fetch_on_a_synthetic_profile_downloads_nothing(data_env: Any) -> None:
    result = runner.invoke(app, ["data", "fetch", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    assert "demo has no dataset to download" in result.output
    assert not (data_env.cache / "real").exists()


def test_data_status_counts(data_env: Any) -> None:
    version = data_env.cache / "real/sources/gleif_lei/golden-copy/20261018-0800"
    version.mkdir(parents=True)
    (version / "lei.zip").write_bytes(b"x" * 2_000_000)
    result = runner.invoke(app, ["data", "status", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "downloads: 1 version(s); retention 30 day(s)",
        "  gleif_lei/golden-copy/20261018-0800: 1 file(s), 0.00 GB, 0 day(s) old",
        "demo (synthetic): 0 record folder(s) with 0 file(s), 0 resolution run(s), 0 label file(s)",
        "DuckDB spill folders left behind: real 0, synthetic 0",
    ]
    report = reports(data_env, "demo")[0]
    assert report["downloads"] == {
        "gleif_lei": {
            "golden-copy": {
                "version_count": 1, "file_count": 1, "bytes": 2_000_000, "partial_files": 0,
                "versions_past_retention": 0, "oldest_days": 0,
            }
        }
    }  # fmt: skip
    assert report["profiles"] == {
        "demo": {"record_folders": 0, "record_files": 0, "resolution_runs": 0, "label_files": 0}
    }
    assert runner.invoke(app, ["data", "status"]).exit_code == 0
    assert reports(data_env, "all-profiles")[0]["profile"] == "all-profiles"


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--labels"], "add --yes"),
        (["--labels", "--logs", "--yes"], "choose one of"),
        (["--yes"], "choose one of"),
        (["--dataset", "gleif", "--yes"], "unknown dataset 'gleif'"),
    ],
)
def test_data_purge_refuses_unclear_requests(
    data_env: Any, arguments: list[str], message: str
) -> None:
    (data_env.cache / "real/labels").mkdir(parents=True)
    result = runner.invoke(app, ["data", "purge", *arguments])
    assert result.exit_code == 2 and message in result.output
    assert (data_env.cache / "real/labels").exists()


class Docker:
    """Records docker commands; containers and volumes of the real instance exist once."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        out = ""
        if command[1:3] == ["ps", "--all"]:
            out = "c0ffee\n"
        elif command[1:3] == ["volume", "ls"] and command[-1].startswith("name="):
            name = command[-1].removeprefix("name=")
            out = f"{name}\n{name}-copy\n"  # Docker's name filter also matches parts of names
        elif command[1:3] == ["volume", "ls"]:
            out = f"neonradar_{command[-1].rsplit('=', 1)[1]}\n"  # by the Compose volume label
        return subprocess.CompletedProcess(command, 0, stdout=out, stderr="")


def test_data_purge_all_real_with_graph(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    docker = Docker()
    monkeypatch.setattr(real_graph, "_run", docker)
    logs = data_env.cache / "real/logs"
    logs.mkdir(parents=True)
    (logs / "a.log").write_text("synthetic\n", encoding="utf-8")
    result = runner.invoke(app, ["data", "purge", "--all-real", "--graph", "--yes"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "purge --all-real: deleted 1 file(s), 10 bytes",
        "purge --graph: removed 1 real-data container(s) and deleted 2 volume(s); the default"
        " instance is untouched",
    ]
    project = "label=com.docker.compose.project=neonradar"
    label = "label=com.docker.compose.volume="
    assert docker.commands == [
        ["docker", "ps", "--all", "--quiet", "--filter", project,
         "--filter", "label=com.docker.compose.service=neo4j-real"],
        ["docker", "rm", "--force", "--volumes", "c0ffee"],
        ["docker", "volume", "ls", "--quiet", "--filter", project,
         "--filter", f"{label}neo4j-real-data"],
        ["docker", "volume", "ls", "--quiet", "--filter", "name=neonradar_neo4j-real-data"],
        ["docker", "volume", "ls", "--quiet", "--filter", project,
         "--filter", f"{label}neo4j-real-logs"],
        ["docker", "volume", "ls", "--quiet", "--filter", "name=neonradar_neo4j-real-logs"],
        ["docker", "volume", "rm", "neonradar_neo4j-real-data", "neonradar_neo4j-real-logs"],
    ]  # fmt: skip
    assert not (data_env.cache / "real").exists()


def test_data_purge_graph_alone_and_docker_failures(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(real_graph, "_run", lambda c: subprocess.CompletedProcess(c, 0, "", ""))
    result = runner.invoke(app, ["data", "purge", "--graph", "--yes"])
    assert result.exit_code == 0 and "removed 0 real-data container(s)" in result.output

    def unlabelled(command: list[str]) -> subprocess.CompletedProcess[str]:
        """A volume with the Compose name but no Compose labels is still found by name."""
        out = "neonradar_neo4j-real-data\n" if command[-1].startswith("name=") else ""
        return subprocess.CompletedProcess(command, 0, out, "")

    monkeypatch.setattr(real_graph, "_run", unlabelled)
    result = runner.invoke(app, ["data", "purge", "--graph", "--yes"])
    assert "removed 0 real-data container(s) and deleted 1 volume(s)" in result.output

    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "elsewhere")
    result = runner.invoke(app, ["data", "purge", "--graph", "--yes"])
    assert result.exit_code == 1 and "COMPOSE_PROJECT_NAME is set to another" in result.output
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "neonradar")
    assert runner.invoke(app, ["data", "purge", "--graph", "--yes"]).exit_code == 0

    def broken(command: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("docker")

    monkeypatch.setattr(real_graph, "_run", broken)
    result = runner.invoke(app, ["data", "purge", "--graph", "--yes"])
    assert result.exit_code == 1 and "Docker is not installed" in result.output


def test_ingest_build_demo_validates_the_fixture_and_writes_a_summary(data_env: Any) -> None:
    result = runner.invoke(app, ["ingest", "build", "--profile", "demo"])
    assert result.exit_code == 0, result.output
    report = reports(data_env, "demo")[0]
    built = report["datasets"]["nr_synthetic"]
    assert (built["status"], built["fixture_folders"], built["files"]) == ("ok", 2, 2)  # M2.9
    assert report["run_id"].startswith("build-")
    assert json.loads(result.output) == report


def test_ingest_build_runs_registered_builders_with_their_keys(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def build(profile: Any, context: Any) -> BuildResult:
        return BuildResult({"rows": 3}, {"slice_sha256": "ab" * 32}, {"lei_headers": ["LEI"]})

    builder = Builder("gleif_lei", build, steps=("slice", "load"), string_keys=("slice_sha256",),
                      list_keys=("lei_headers",))  # fmt: skip
    monkeypatch.setitem(sources._BUILDERS, "gleif_lei", builder)
    data_env.write_profile("uk-test", real_data=True, sources={"gleif_lei": {"enabled": True}})
    data_env.allow_real("uk-test")
    args = ["ingest", "build", "--profile", "uk-test", "--dataset", "gleif_lei"]
    result = runner.invoke(app, [*args, "--step", "load"])
    assert result.exit_code == 0, result.output
    built = reports(data_env, "uk-test")[0]["datasets"]["gleif_lei"]
    assert built == {"status": "ok", "rows": 3, "slice_sha256": "ab" * 32, "lei_headers": ["LEI"]}
    result = runner.invoke(app, [*args, "--step", "index"])
    assert result.exit_code == 2 and "gleif_lei has no step 'index'" in result.output
    result = runner.invoke(app, ["ingest", "build", "--profile", "uk-test", "--step", "load"])
    assert result.exit_code == 2 and "--step needs --dataset" in result.output


def test_ingest_build_gates_every_step_before_any_builder(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The officers step needs access.companies_house_key: available (checked centrally)."""
    ran: list[tuple[str, ...]] = []

    def build(profile: Any, context: Any) -> BuildResult:
        ran.append(context.steps)
        return BuildResult({"rows": 1})

    builder = Builder("gb_companies_house", build, steps=("companies", "psc", "officers"))
    monkeypatch.setitem(sources._BUILDERS, "gb_companies_house", builder)
    data_env.write_profile(
        "uk-test", real_data=True, sources={"gb_companies_house": {"enabled": True}}
    )
    data_env.allow_real("uk-test")  # access.companies_house_key stays pending
    result = runner.invoke(app, ["ingest", "build", "--profile", "uk-test"])
    assert result.exit_code == 3 and ran == []
    assert "rule access.companies_house_key" in result.output
    args = ["ingest", "build", "--profile", "uk-test", "--dataset", "gb_companies_house"]
    assert runner.invoke(app, [*args, "--step", "officers"]).exit_code == 3
    result = runner.invoke(app, [*args, "--step", "companies", "--step", "psc"])
    assert result.exit_code == 0 and ran == [("companies", "psc")]
    data_env.allow_real("uk-test", companies_house_key="available")
    assert runner.invoke(app, ["ingest", "build", "--profile", "uk-test"]).exit_code == 0
    assert ran[-1] == ()  # no --step: every step, in the builder's order


def test_ingest_build_refuses_a_real_profile_before_any_builder(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[str] = []
    builder = Builder("gb_companies_house", lambda p, c: called.append("x") or BuildResult())
    monkeypatch.setitem(sources._BUILDERS, "gb_companies_house", builder)
    result = runner.invoke(app, ["ingest", "build", "--profile", "uk-sample"])
    assert (result.exit_code, called) == (3, [])
    assert not [p for p in Path(data_env.cache).rglob("*") if p.is_file()]
