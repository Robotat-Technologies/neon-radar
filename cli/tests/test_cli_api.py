from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app

runner = CliRunner()


@pytest.fixture
def uvicorn_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    import uvicorn

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    return calls


def test_serve_runs_the_app_factory_on_localhost_port_8000(
    uvicorn_calls: list[tuple[tuple[Any, ...], dict[str, Any]]],
) -> None:
    result = runner.invoke(app, ["api", "serve"])
    assert result.exit_code == 0, result.output
    assert uvicorn_calls == [
        (
            ("neonradar_api.main:create_app",),
            {"factory": True, "host": "127.0.0.1", "port": 8000},
        )
    ]


def test_serve_takes_a_port_but_never_another_host(
    uvicorn_calls: list[tuple[tuple[Any, ...], dict[str, Any]]],
) -> None:
    assert runner.invoke(app, ["api", "serve", "--port", "8123"]).exit_code == 0
    assert uvicorn_calls[0][1]["port"] == 8123
    assert uvicorn_calls[0][1]["host"] == "127.0.0.1"
    assert runner.invoke(app, ["api", "serve", "--host", "0.0.0.0"]).exit_code == 2  # noqa: S104


@pytest.mark.parametrize("port", ["0", "65536"])
def test_serve_refuses_a_port_out_of_range(
    port: str, uvicorn_calls: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    result = runner.invoke(app, ["api", "serve", "--port", port])
    assert result.exit_code == 2
    assert uvicorn_calls == []
