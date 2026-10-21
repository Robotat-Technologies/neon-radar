import json
import os
import socket
import sys
from pathlib import Path

import pytest

from neonradar_cli import doctor
from neonradar_cli.doctor import Status

GIB = 1024**3


def fake(
    monkeypatch: pytest.MonkeyPatch,
    outputs: dict[tuple[str, ...], str],
    installed: tuple[str, ...] = ("uv", "docker", "pkg-config"),
) -> None:
    """Replace command execution: `outputs` maps argument tuples to stdout; others fail."""
    monkeypatch.setattr(doctor, "run", lambda *args: outputs.get(args))
    monkeypatch.setattr(doctor.shutil, "which", lambda name: name if name in installed else None)


def test_run_returns_stdout_or_none() -> None:
    assert doctor.run(sys.executable, "-c", "print(' hi ')") == "hi"
    assert doctor.run(sys.executable, "-c", "raise SystemExit(3)") is None
    assert doctor.run("neonradar-no-such-command") is None


@pytest.mark.parametrize(
    ("output", "status"),
    [
        ("uv 0.13.4 (7456b60bc 2026-10-20)", Status.OK),
        ("uv 0.14.0", Status.WARN),
        (None, Status.FAIL),
    ],
)
def test_uv(monkeypatch: pytest.MonkeyPatch, output: str | None, status: Status) -> None:
    fake(monkeypatch, {("uv", "--version"): output} if output else {})
    assert doctor.check_uv().status is status


def test_docker_info_needs_a_reachable_server(monkeypatch: pytest.MonkeyPatch) -> None:
    command = ("docker", "info", "--format", "{{json .}}")
    fake(monkeypatch, {command: json.dumps({"ServerVersion": "29.7.2", "MemTotal": 8 * GIB})})
    assert doctor.docker_info() == {"ServerVersion": "29.7.2", "MemTotal": 8 * GIB}
    fake(monkeypatch, {command: json.dumps({"ServerErrors": ["Cannot connect"]})})
    assert doctor.docker_info() is None
    fake(monkeypatch, {command: "not json"})
    assert doctor.docker_info() is None


def test_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    fake(monkeypatch, {})
    assert doctor.check_docker({"ServerVersion": "29.7.2"}).status is Status.OK
    assert doctor.check_docker(None).detail.startswith("daemon not reachable")
    fake(monkeypatch, {}, installed=())
    assert doctor.check_docker(None).detail.startswith("not found")


@pytest.mark.parametrize(
    ("output", "status"),
    [("5.4.0", Status.OK), ("v2.29.1", Status.OK), ("1.29.2", Status.FAIL), (None, Status.FAIL)],
)
def test_compose(monkeypatch: pytest.MonkeyPatch, output: str | None, status: Status) -> None:
    fake(monkeypatch, {("docker", "compose", "version", "--short"): output} if output else {})
    assert doctor.check_compose().status is status


def test_env_file(tmp_path: Path) -> None:
    assert doctor.check_env_file(tmp_path).status is Status.WARN
    (tmp_path / ".env").write_text("NEO4J_PASSWORD=x\n")
    assert doctor.check_env_file(tmp_path).status is Status.OK


def test_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "port_in_use", lambda port: port != 5173)
    assert doctor.check_port(7474, {7474}).detail == "used by the NeonRadar stack"
    assert doctor.check_port(5173, set()).detail == "free"
    assert doctor.check_port(7687, set()).status is Status.FAIL
    assert doctor.check_port(8000, set()).status is Status.WARN
    assert doctor.check_port(8080, set()) == doctor.Check(
        "port 8080", Status.WARN, "in use by another program; the demo UI needs it"
    )


def test_stack_ports_reads_docker_ps(monkeypatch: pytest.MonkeyPatch) -> None:
    ps = ("docker", "ps", "--filter", "label=com.docker.compose.project=neonradar")
    output = "127.0.0.1:7474->7474/tcp, 127.0.0.1:7687->7687/tcp\n127.0.0.1:8000->8000/tcp"
    fake(monkeypatch, {(*ps, "--format", "{{.Ports}}"): output})
    assert doctor.stack_ports() == {7474, 7687, 8000}


def test_port_in_use_sees_a_listening_socket() -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        assert doctor.port_in_use(server.getsockname()[1])


def test_port_in_use_is_false_when_nothing_listens() -> None:
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))  # held but not listening, so nothing can accept
        assert not doctor.port_in_use(reserved.getsockname()[1])


@pytest.mark.parametrize(
    ("memory", "status"),
    [(8 * GIB, Status.OK), (4 * GIB, Status.WARN), (2 * GIB, Status.FAIL), (None, Status.WARN)],
)
def test_memory(memory: int | None, status: Status) -> None:
    info = {"ServerVersion": "29.7.2", "MemTotal": memory}
    assert doctor.check_memory(info).status is status
    assert doctor.check_memory(None).detail == "not checked; Docker is not reachable"


def test_icu(monkeypatch: pytest.MonkeyPatch) -> None:
    fake(monkeypatch, {}, installed=())
    assert doctor.check_icu().detail.startswith("pkg-config not found")
    fake(monkeypatch, {})
    assert doctor.check_icu().status is Status.WARN
    exists, version = ("pkg-config", "--exists", "icu-uc"), ("pkg-config", "--modversion", "icu-uc")
    fake(monkeypatch, {exists: "", version: "78.1"})
    assert doctor.check_icu() == doctor.Check("ICU", Status.OK, "78.1")


def test_run_checks_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake(monkeypatch, {}, installed=())
    monkeypatch.setattr(doctor, "port_in_use", lambda port: False)
    checks = doctor.run_checks(tmp_path)
    names = [check.name for check in checks]
    ports = ["port 7474", "port 7687", "port 8000", "port 8080", "port 5173"]
    phase_2 = ["disk space", "DuckDB", "real data", "DuckDB spill", "neo4j-real", "real profiles"]
    assert names == [
        "Python", "uv", "Docker", "Compose", ".env", *ports, "Docker memory", "ICU", *phase_2
    ]  # fmt: skip
    assert all(check.status is not Status.FAIL for check in checks[-len(phase_2) :])


# Phase 2 checks (PHASE-2.md M2.0): OK or WARN only, never FAIL.

DAY = 86_400
NOW = 2_000_000_000.0
ACCESS = {"real_data_days": 30, "label_days": 10, "real_data_profiles": []}


def test_disk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage = doctor.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(doctor.shutil, "disk_usage", lambda _: usage._replace(free=30 * 10**9))
    assert doctor.check_disk(tmp_path) == doctor.Check("disk space", Status.OK, "30 GB free")
    monkeypatch.setattr(doctor.shutil, "disk_usage", lambda _: usage._replace(free=24 * 10**9))
    assert doctor.check_disk(tmp_path).status is Status.WARN


def test_duckdb(monkeypatch: pytest.MonkeyPatch) -> None:
    assert doctor.check_duckdb().status is Status.OK  # a resolve dependency, so installed

    def missing(name: str) -> None:
        raise ImportError(name)

    monkeypatch.setattr(doctor.importlib, "import_module", missing)
    assert doctor.check_duckdb().status is Status.WARN


def _aged(path: Path, days: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (NOW - days * DAY, NOW - days * DAY))


def test_real_data_counts_files_and_ages_only(tmp_path: Path) -> None:
    real = tmp_path / "data" / "cache" / "real"
    assert doctor.check_real_data(tmp_path, ACCESS, NOW).detail == "none under data/cache/real/"
    _aged(real / "sources" / "a.zip", 5)
    _aged(real / "labels" / "demo" / "run" / "x.jsonl", 9)
    check = doctor.check_real_data(tmp_path, ACCESS, NOW)
    assert check.status is Status.OK
    assert check.detail.startswith("2 files under data/cache/real/, the oldest 9 days old")
    _aged(real / "labels" / "demo" / "run" / "y.jsonl", 11)  # older than label_days only
    check = doctor.check_real_data(tmp_path, ACCESS, NOW)
    assert check.status is Status.WARN
    assert "1 older than" in check.detail
    assert "y.jsonl" not in check.detail and "labels" not in check.detail
    _aged(real / "records" / "uk-tiny" / "b.jsonl", 31)
    assert "2 older than" in doctor.check_real_data(tmp_path, ACCESS, NOW).detail
    assert doctor.check_real_data(tmp_path, {}, NOW).status is Status.WARN  # no retention set


def test_spill_folders(tmp_path: Path) -> None:
    assert doctor.check_spill(tmp_path).status is Status.OK
    (tmp_path / "data" / "cache" / "real" / "duckdb-tmp" / "er-1").mkdir(parents=True)
    (tmp_path / "data" / "cache" / "synthetic" / "duckdb-tmp" / "er-2").mkdir(parents=True)
    check = doctor.check_spill(tmp_path)
    assert check.status is Status.WARN
    assert check.detail.startswith("2 leftover run folder(s)")


def test_real_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    ps = (
        "docker", "ps",
        "--filter", "label=com.docker.compose.project=neonradar",
        "--filter", "label=com.docker.compose.service=neo4j-real",
        "--format", "{{.Names}}",
    )  # fmt: skip
    info = {"ServerVersion": "29.7.2"}
    fake(monkeypatch, {ps: "neonradar-neo4j-real-1"})
    check = doctor.check_real_instance(info)
    assert check.status is Status.WARN
    assert "make down-real" in check.detail
    fake(monkeypatch, {ps: ""})
    assert doctor.check_real_instance(info).status is Status.OK
    assert doctor.check_real_instance(None).status is Status.OK


def test_real_profiles() -> None:
    assert doctor.check_real_profiles({"real_data_profiles": []}).status is Status.OK
    allowed = {"real_data_profiles": ["uk-tiny"], "data_protection_filed": False}
    check = doctor.check_real_profiles(allowed)
    assert check.status is Status.WARN
    assert "docs/data/real-data-machines.md" in check.detail
    allowed["data_protection_filed"] = True
    check = doctor.check_real_profiles(allowed)
    assert check.status is Status.OK
    assert "NR_REAL_DATA_MACHINE=approved" in check.detail


def test_read_access(tmp_path: Path) -> None:
    assert doctor.read_access(tmp_path) == {}
    project = tmp_path / "docs" / "build" / "project.yaml"
    project.parent.mkdir(parents=True)
    project.write_text("access:\n  real_data_days: 30\n", encoding="utf-8")
    assert doctor.read_access(tmp_path) == {"real_data_days": 30}
    assert isinstance(doctor.read_access(doctor.REPO_ROOT)["real_data_profiles"], list)
