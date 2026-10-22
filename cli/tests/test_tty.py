"""Human-only commands (PHASE-2.md M2.2 deliverable 13)."""

import io
import sys
from typing import Any

import pytest
import typer

from neonradar_cli import redact
from neonradar_cli.tty import TerminalRequired, require_terminal
from neonradar_ingest.data.profiles import load_profile


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_no_terminal_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("same\n"))  # piped input
    with pytest.raises(TerminalRequired, match="er label is for a person at a terminal") as stop:
        require_terminal("er label")
    assert stop.value.exit_code == 2
    monkeypatch.setattr(sys, "stdin", None)
    with pytest.raises(TerminalRequired):
        require_terminal("er review")


def test_a_terminal_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", Terminal())
    require_terminal("api serve --real")


def test_inside_the_guard_it_exits_2_with_its_message(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    for profile in ("uk-tiny", "demo"):
        with pytest.raises(typer.Exit) as stop, redact.guard(load_profile(profile), "er label"):
            require_terminal("er label")
        assert stop.value.exit_code == 2
        assert "er label is for a person at a terminal" in capsys.readouterr().err
