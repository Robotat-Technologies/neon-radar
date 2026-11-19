import pytest
from typer.testing import CliRunner

from neonradar_cli import doctor
from neonradar_cli.doctor import Check, Status
from neonradar_cli.main import app

runner = CliRunner()


def test_version_option_prints_the_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output == "0.1.0\n"


@pytest.mark.parametrize(
    ("statuses", "exit_code"),
    [([Status.OK, Status.WARN], 0), ([Status.OK, Status.FAIL, Status.WARN], 1)],
)
def test_doctor_prints_one_line_per_check_and_exits_1_only_on_fail(
    monkeypatch: pytest.MonkeyPatch, statuses: list[Status], exit_code: int
) -> None:
    checks = [Check(f"check {n}", status, "detail") for n, status in enumerate(statuses)]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == exit_code
    assert result.output.splitlines() == [check.line() for check in checks]


def test_doctor_prints_the_port_help_once_after_the_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = [
        Check("port 7474", Status.FAIL, "in use by another program"),
        Check("port 8000", Status.WARN, "in use by another program"),
        Check("Docker memory", Status.OK, "8.0 GiB"),
    ]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    lines = [check.line() for check in checks]
    assert result.output == "\n".join([*lines, "", doctor.PORT_HELP, ""])


def test_doctor_prints_no_port_help_when_the_ports_are_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = [Check("port 7474", Status.OK, "free"), Check("Docker memory", Status.WARN, "small")]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert doctor.PORT_HELP not in result.output
