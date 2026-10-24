from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_api.hardening import log_config
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
            {
                "factory": True,
                "host": "127.0.0.1",
                "port": 8000,
                "access_log": False,  # uvicorn's own access log writes query strings (M4.1)
                "log_config": log_config(),
            },
        )
    ]


def test_serve_dev_builds_the_app_with_cors(
    uvicorn_calls: list[tuple[tuple[Any, ...], dict[str, Any]]],
) -> None:
    assert runner.invoke(app, ["api", "serve", "--dev"]).exit_code == 0
    assert uvicorn_calls[0][0] == ("neonradar_api.main:create_dev_app",)


def test_only_the_api_image_binds_another_host(
    monkeypatch: pytest.MonkeyPatch, uvicorn_calls: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    monkeypatch.setenv("NR_API_IN_IMAGE", "1")
    everywhere = "0.0.0.0"  # noqa: S104
    assert runner.invoke(app, ["api", "serve", "--host", everywhere]).exit_code == 0
    assert uvicorn_calls[0][1]["host"] == everywhere
    for refused in (["--host", everywhere], ["--dev"], ["--host", "127.0.0.1"]):
        assert runner.invoke(app, ["api", "serve", "--real", *refused]).exit_code == 2
    assert len(uvicorn_calls) == 1


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
