"""Hosts, body size, CORS, the access log and the OpenAPI media types (PHASE-4.md 7.5.3).

On an app of its own with one probe route, so the middleware is tested alone (M4.1).
"""

import json
import logging

import pytest
from apiclient import call
from fastapi import APIRouter, FastAPI, HTTPException
from neonradar_api.hardening import log_config
from neonradar_contracts.api import Problem
from phase4app import app_with
from pydantic import BaseModel

probe = APIRouter()


class Echo(BaseModel):
    text: str


@probe.get("/probe/{item_id}", responses={404: {"model": Problem}}, operation_id="probe_get")
def probe_get(item_id: str) -> dict[str, str]:
    if item_id == "missing":
        raise HTTPException(404, detail="No such item.")
    return {"ok": "yes"}


@probe.post("/probe", operation_id="probe_post")
def probe_post(body: Echo) -> dict[str, int]:
    return {"length": len(body.text)}


@probe.get("/broken/{name}", operation_id="probe_broken")
def probe_broken(name: str) -> dict[str, str]:
    raise ValueError(f"cannot read {name}")


@probe.get("/files/{rest:path}", operation_id="probe_files")
def probe_files(rest: str) -> dict[str, str]:
    return {"ok": "yes"}


@pytest.fixture
def app() -> FastAPI:
    return app_with(probe)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "[::1]", "api"])
def test_local_hosts_are_served(app: FastAPI, host: str) -> None:
    assert call(app, "GET", "/api/v1/probe/x", base=f"http://{host}:8000").status_code == 200


def test_other_hosts_are_refused(app: FastAPI) -> None:
    assert call(app, "GET", "/api/v1/probe/x", base="http://evil.example:8000").status_code == 400


def test_large_bodies_are_refused(app: FastAPI) -> None:
    big = b'{"text": "' + b"x" * (70 * 1024) + b'"}'
    headers = {"content-type": "application/json"}
    assert call(app, "POST", "/api/v1/probe", content=big, headers=headers).status_code == 413
    small = call(app, "POST", "/api/v1/probe", json={"text": "x" * 1000})
    assert small.status_code == 200


def test_cors_only_in_development() -> None:
    preflight = {"origin": "http://localhost:5173", "access-control-request-method": "POST"}
    dev = app_with(probe, dev=True)
    ok = call(dev, "OPTIONS", "/api/v1/probe", headers=preflight)
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = {**preflight, "origin": "https://evil.example"}
    assert (
        "access-control-allow-origin"
        not in call(dev, "OPTIONS", "/api/v1/probe", headers=evil).headers
    )
    plain = call(app_with(probe), "OPTIONS", "/api/v1/probe", headers=preflight)
    assert "access-control-allow-origin" not in plain.headers


def test_the_access_log_holds_route_templates_only(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="neonradar.api.access")
    call(app, "GET", "/api/v1/probe/syn-cb-co-calvane?name=Calvane")
    call(app, "GET", "/api/v1/nowhere/syn-cb-co-calvane")
    call(app, "POST", "/api/v1/probe", json={"text": "Who owns Calvane Holdings Ltd?"})
    lines = [r.getMessage() for r in caplog.records if r.name == "neonradar.api.access"]
    assert lines[0].startswith("GET /api/v1/probe/{item_id} 200 ")
    assert lines[1].startswith("GET unmatched 404 ")
    assert lines[2].startswith("POST /api/v1/probe 200 ")
    assert not any("alvane" in line or "syn-cb" in line for line in lines)


def test_errors_are_problem_details_in_the_document_and_on_the_wire(app: FastAPI) -> None:
    missing = call(app, "GET", "/api/v1/probe/missing")
    assert missing.status_code == 404
    assert missing.headers["content-type"] == "application/problem+json"
    assert missing.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "No such item.",
    }
    document = app.openapi()
    responses = document["paths"]["/api/v1/probe/{item_id}"]["get"]["responses"]
    assert set(responses["404"]["content"]) == {"application/problem+json"}
    assert set(responses["200"]["content"]) == {"application/json"}
    assert app.openapi() is document  # generated once, processed once


def test_an_unhandled_error_is_a_fixed_problem_and_logs_no_value(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        response = call(app, "GET", "/api/v1/broken/Calvane")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert "Calvane" not in response.text and "Calvane" not in caplog.text
    assert "unhandled ValueError on GET /api/v1/broken/{name}" in caplog.text


def test_path_values_that_are_not_one_segment_are_redacted(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="neonradar.api.access")
    call(app, "GET", "/api/v1/files/a/SECRET4/b")
    call(app, "GET", "/api/v1/probe/api")
    lines = [r.getMessage() for r in caplog.records if r.name == "neonradar.api.access"]
    assert [line.split()[1] for line in lines] == ["redacted", "redacted"]
    assert not any("SECRET4" in line for line in lines)


def test_every_error_response_is_documented_as_a_problem(app: FastAPI) -> None:
    document = app.openapi()
    assert "HTTPValidationError" not in json.dumps(document)
    post = document["paths"]["/api/v1/probe"]["post"]["responses"]["422"]["content"]
    assert post == {
        "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
    }


def test_the_log_config_shows_the_api_lines_and_quietens_the_driver() -> None:
    config = log_config()
    assert config["loggers"]["neonradar.api"]["level"] == "INFO"
    assert {config["loggers"][n]["level"] for n in ("neo4j", "httpx", "httpcore")} == {"WARNING"}
    assert logging.getLogger("neo4j").level == logging.WARNING  # harden() set it
