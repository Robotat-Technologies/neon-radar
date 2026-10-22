"""Error redaction on real profiles (PHASE-2.md M2.2 deliverable 10)."""

from typing import Any

import pytest
import typer

from neonradar_cli import redact
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import load_profile

# An obviously invented person and a record id in the Companies House officer form.
NAME, RECORD_ID = "Testa Holderson", "gbch-off-T0000001"


class CapError(Exception):
    exit_code = 4
    rule = "cap"


def test_a_real_profile_error_shows_neither_name_nor_record_id(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    data_env.approve_machine()
    with (
        pytest.raises(typer.Exit) as stopped,
        redact.guard(load_profile("uk-tiny"), "er run") as where,
    ):
        where.step, where.dataset = "match", "gb_companies_house"
        raise ValueError(f"cannot compare {NAME} ({RECORD_ID})")
    assert stopped.value.exit_code == 1
    err = capsys.readouterr().err
    assert NAME not in err and RECORD_ID not in err
    assert err.startswith("ValueError, step match, dataset gb_companies_house, err-")
    logs = list((data_env.cache / "real" / "logs").iterdir())
    assert [log.name[:7] for log in logs] == ["er-run-"]
    text = logs[0].read_text(encoding="utf-8")
    assert NAME in text and "Traceback" in text  # the full traceback stays on the machine


def test_the_exit_code_and_rule_come_from_the_exception(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        pytest.raises(typer.Exit) as stopped,
        redact.guard(load_profile("uk-tiny"), "ingest build"),
    ):
        raise CapError(f"too many records near {NAME}")
    assert stopped.value.exit_code == 4
    err = capsys.readouterr().err
    assert "CapError, step -, dataset -, rule cap, err-" in err and NAME not in err


def test_counts_only_messages_are_printed_in_full_without_a_log(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit) as stopped, redact.guard(load_profile("uk-tiny"), "data fetch"):
        raise RealDataRefused("access.real_data_profiles", "uk-tiny is not in the list")
    assert stopped.value.exit_code == 3
    assert "rule access.real_data_profiles, err-" in capsys.readouterr().err
    assert not (data_env.cache / "real").exists()


def test_a_synthetic_profile_changes_nothing(data_env: Any) -> None:
    with (
        pytest.raises(ValueError, match="Testa Holderson"),
        redact.guard(load_profile("demo"), "er run"),
    ):
        raise ValueError(f"cannot compare {NAME}")
    assert not (data_env.cache / "real").exists()


def test_own_errors_on_a_synthetic_profile_print_their_message(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit) as stopped, redact.guard(None, "data fetch"):
        raise CapError("12 records over the cap")
    assert stopped.value.exit_code == 4
    assert capsys.readouterr().err == "FAIL  12 records over the cap\n"


def test_exits_pass_through(data_env: Any) -> None:
    with pytest.raises(typer.Exit) as stopped, redact.guard(load_profile("uk-tiny"), "x"):
        raise typer.Exit(code=2)
    assert stopped.value.exit_code == 2
    assert not (data_env.cache / "real").exists()


def test_real_can_be_forced_for_commands_on_real_folders(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit), redact.guard(None, "data purge", real=True):
        raise OSError(f"cannot remove officers/{RECORD_ID}.json")
    assert RECORD_ID not in capsys.readouterr().err


def test_an_unwritable_log_never_shows_the_error(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = data_env.cache / "real"
    blocker.parent.mkdir(parents=True)
    blocker.write_text("a file where the logs folder should be\n", encoding="utf-8")
    data_env.approve_machine()
    with pytest.raises(typer.Exit) as stopped, redact.guard(load_profile("uk-tiny"), "er run"):
        raise ValueError(f"cannot compare {NAME} ({RECORD_ID})")
    assert stopped.value.exit_code == 1
    assert stopped.value.__cause__ is None and stopped.value.__suppress_context__
    err = capsys.readouterr().err
    assert NAME not in err and RECORD_ID not in err
    assert err.startswith("ValueError, step -, dataset -, err-") and "(traceback not saved)" in err


def test_attributes_print_only_when_they_are_plain_names(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    class Odd(Exception):
        exit_code = 2
        rule = NAME  # a value, not a rule id
        dataset = RECORD_ID.upper() + " x"

    data_env.approve_machine()
    with pytest.raises(typer.Exit), redact.guard(load_profile("uk-tiny"), "er run") as where:
        where.step = "match people"
        raise Odd("x")
    err = capsys.readouterr().err
    assert err.startswith("Odd, step -, dataset -, rule -, err-") and NAME not in err


def test_no_traceback_is_kept_from_the_gate_on_an_unapproved_machine(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit), redact.guard(load_profile("uk-tiny"), "data fetch") as where:
        where.step = "gate"
        raise ValueError(f"unexpected {NAME}")
    assert "(no traceback kept on an unapproved machine)" in capsys.readouterr().err
    assert not (data_env.cache / "real").exists()
