"""`neonradar api serve --real` is for a person at a terminal (PHASE-2.md M2.12 deliverable 4).

With standard input closed it exits 2 before it reads the project file, runs the real-data
gate, builds the app or opens any connection. Past the checks it serves without an access log,
and the real-data app logs only route templates and error classes (G9) and allows no other
origin. Without `--real` the API connects through `Instance.DEFAULT`. Nothing here starts a
server or reaches Neo4j.
"""

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from neonradar_api.files import RepoFiles
from neonradar_api.main import UI_DEV_ORIGIN, create_app
from neonradar_api.problems import Contained
from neonradar_cli import api as api_cli
from neonradar_cli.main import app

from .conftest import REPO_ROOT, TEST_HOSTS, ScriptedGraph

# A look-alike of what a real request carries; it must reach no log line.
RECORD_ID = "gbch-co-T0000001"
RECORD_NAME = "Test Holder Ltd"


def _forbidden(name: str) -> Any:
    def fail(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"{name} ran before the terminal check")

    return fail


def test_closed_stdin_exits_2_before_any_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    from neonradar_api import graph, main
    from neonradar_cli import data
    from neonradar_ingest.data import gate

    monkeypatch.setattr(uvicorn, "run", _forbidden("uvicorn.run"))
    monkeypatch.setattr(main, "create_app", _forbidden("create_app"))
    monkeypatch.setattr(graph, "get_driver", _forbidden("get_driver"))
    monkeypatch.setattr(data, "project_or_exit", _forbidden("project_or_exit"))
    monkeypatch.setattr(gate, "check_real_instance", _forbidden("the real-data gate"))
    result = CliRunner().invoke(app, ["api", "serve", "--real"], input=None)
    assert result.exit_code == 2, result.output
    assert "is for a person at a terminal" in result.output
    assert "Serving real data" not in result.output


def test_without_real_the_api_uses_the_default_instance() -> None:
    from neonradar_api.graph import GraphConnection
    from neonradar_graph.instances import Instance

    assert GraphConnection()._settings == Instance.DEFAULT.settings  # `api serve`'s factory app
    assert api_cli.HOST == "127.0.0.1"


def test_past_the_checks_it_serves_8001_without_an_access_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uvicorn

    from neonradar_api import main
    from neonradar_cli import data, tty
    from neonradar_ingest.data import gate

    built: list[dict[str, Any]] = []
    served: list[tuple[Any, dict[str, Any]]] = []
    real_app: Any = object()

    def build(graph: Any, **options: Any) -> Any:
        built.append(options)
        return real_app

    monkeypatch.setattr(tty, "require_terminal", lambda command: None)
    monkeypatch.setattr(data, "project_or_exit", lambda: object())
    monkeypatch.setattr(gate, "check_real_instance", lambda project: None)
    monkeypatch.setattr(main, "create_app", build)
    monkeypatch.setattr(uvicorn, "run", lambda target, **kw: served.append((target, kw)))
    saved = {name: logging.getLogger(name).level for name in ("neo4j", "httpx", "httpcore")}
    for name in saved:  # as if a logging setup had lowered them
        logging.getLogger(name).setLevel(logging.DEBUG)
    try:
        result = CliRunner().invoke(app, ["api", "serve", "--real"])
        levels = {logging.getLogger(name).level for name in saved}
    finally:
        for name, level in saved.items():
            logging.getLogger(name).setLevel(level)
    assert result.exit_code == 0, result.output
    # The driver's debug log prints query parameters: held at WARNING explicitly.
    assert levels == {logging.WARNING}
    assert callable(built[0]["report"])  # the redacted app: no CORS, no tracebacks in logs
    (target, options), *_ = served
    assert isinstance(target, Contained) and target.app is real_app
    assert options == {
        "host": "127.0.0.1",
        "port": 8001,
        "access_log": False,
        "log_level": "warning",
    }


def test_port_is_refused_with_real(monkeypatch: pytest.MonkeyPatch) -> None:
    from neonradar_cli import tty

    monkeypatch.setattr(tty, "require_terminal", _forbidden("require_terminal"))
    result = CliRunner().invoke(app, ["api", "serve", "--real", "--port", "8000"])
    assert result.exit_code == 2
    assert "--real always serves port 8001" in result.output


def _failing(query: str, params: dict[str, Any]) -> list[Any]:
    raise ValueError(f"{RECORD_NAME} {RECORD_ID}")


def test_the_real_app_logs_the_route_and_class_only(caplog: pytest.LogCaptureFixture) -> None:
    reported: list[Exception] = []
    real = create_app(
        ScriptedGraph(_failing), RepoFiles(REPO_ROOT), TEST_HOSTS, report=reported.append
    )
    with (
        caplog.at_level(logging.DEBUG, logger="neonradar_api"),
        TestClient(Contained(real)) as client,  # raises if the error reached the server
    ):
        answer = client.get(f"/api/v1/entities/{RECORD_ID}")
        preflight = client.options(
            "/api/v1/meta",
            headers={"origin": UI_DEV_ORIGIN, "access-control-request-method": "GET"},
        )
    assert answer.status_code == 500
    assert RECORD_NAME not in answer.text  # `instance` is the path, for the person who asked
    assert [type(error) for error in reported] == [ValueError]
    lines = [(record.getMessage(), record.exc_info) for record in caplog.records]
    assert lines == [("unhandled ValueError on GET /api/v1/entities/{entity_id}", None)]
    assert "access-control-allow-origin" not in preflight.headers


def test_the_default_app_logs_the_route_template(caplog: pytest.LogCaptureFixture) -> None:
    default = create_app(ScriptedGraph(_failing), RepoFiles(REPO_ROOT), TEST_HOSTS)
    with (
        caplog.at_level(logging.DEBUG, logger="neonradar_api"),
        TestClient(default, raise_server_exceptions=False) as client,
    ):
        assert client.get(f"/api/v1/entities/{RECORD_ID}").status_code == 500
    (record,) = caplog.records
    assert record.getMessage() == "unhandled error on GET /api/v1/entities/{entity_id}"
