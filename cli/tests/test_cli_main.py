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
