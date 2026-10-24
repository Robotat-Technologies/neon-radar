"""`neonradar api serve --real` is for a person at a terminal (PHASE-2.md M2.12 deliverable 4).

With standard input closed it exits 2 before it reads the project file, runs the real-data
gate, builds the app or opens any connection. Without `--real` the API connects through
`Instance.DEFAULT`. Nothing here starts a server or reaches Neo4j.
"""

from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli import api as api_cli
from neonradar_cli.main import app


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
