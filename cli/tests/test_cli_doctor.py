import json
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
    assert doctor.check_env_file(tmp_path).detail.endswith("(copy .env.example)")
    assert doctor.check_env_file(tmp_path, password_elsewhere=True).status is Status.OK
    inside = doctor.check_env_file(tmp_path, devcontainer=True)
    assert inside.status is Status.WARN
    assert "copy .env.example" not in inside.detail
    (tmp_path / ".env").write_text("NEO4J_PASSWORD=x\n")
    assert doctor.check_env_file(tmp_path) == doctor.Check(".env", Status.OK, "present")


def test_password_without_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setattr("neonradar_graph.client.SECRETS_DIR", tmp_path / "none")
    assert not doctor.password_without_env_file()
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "neo4j_password").write_text("from-a-secret-file")
    monkeypatch.setattr("neonradar_graph.client.SECRETS_DIR", secrets)
    assert doctor.password_without_env_file()


def test_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "port_in_use", lambda port: port != 5173)
    assert doctor.check_port(7474, {7474}).detail == "used by the NeonRadar stack"
    assert doctor.check_port(5173, set()).detail == "free"
    assert doctor.check_port(7687, set()).status is Status.FAIL
    assert doctor.check_port(8000, set()).status is Status.WARN


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
    monkeypatch.setattr(doctor, "password_without_env_file", lambda: False)
    monkeypatch.setattr(doctor, "port_in_use", lambda port: False)
    names = [check.name for check in doctor.run_checks(tmp_path)]
    ports = ["port 7474", "port 7687", "port 8000", "port 5173"]
    assert names == ["Python", "uv", "Docker", "Compose", ".env", *ports, "Docker memory", "ICU"]


def test_devcontainer_turns_missing_docker_into_warnings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake(monkeypatch, {}, installed=("uv", "pkg-config"))
    monkeypatch.setattr(doctor, "port_in_use", lambda port: False)
    monkeypatch.setattr(doctor, "password_without_env_file", lambda: True)
    on_host = {check.name: check for check in doctor.run_checks(tmp_path)}
    inside = {check.name: check for check in doctor.run_checks(tmp_path, devcontainer=True)}
    for name in ("Docker", "Compose"):
        assert on_host[name].status is Status.FAIL
        assert inside[name] == doctor.Check(name, Status.WARN, doctor.NO_DOCKER_IN_DEVCONTAINER)
    assert inside["Docker memory"].status is Status.WARN
    assert inside[".env"].status is Status.OK  # the password comes from /run/secrets in there
    assert {name: check for name, check in inside.items() if name not in ("Docker", "Compose")} == {
        name: check for name, check in on_host.items() if name not in ("Docker", "Compose")
    }
