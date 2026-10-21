"""The running app's OpenAPI document is the committed C3 snapshot (PHASE-1.md 5.3, 5.5)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from neonradar_api.main import create_app
from neonradar_contracts import schemas, versions
from neonradar_contracts.api import API_PREFIX

pytestmark = pytest.mark.contract

SNAPSHOT = schemas.CONTRACTS_DIR / schemas.OPENAPI_SNAPSHOT
PROBLEM_CONTENT = {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return create_app().openapi()


def test_the_app_matches_the_committed_snapshot(document: dict[str, Any]) -> None:
    assert schemas.render_json(document) == SNAPSHOT.read_text(encoding="utf-8"), (
        "contracts/openapi/v1.json is out of date: run `make contracts`"
    )


def test_the_drift_check_sees_a_changed_snapshot(tmp_path: Path, document: dict[str, Any]) -> None:
    docs = {schemas.OPENAPI_SNAPSHOT: schemas.render_json(document)}
    copy = tmp_path / schemas.OPENAPI_SNAPSHOT
    copy.parent.mkdir(parents=True)
    shutil.copy(SNAPSHOT, copy)
    assert schemas.check(tmp_path, docs) == []
    edited = json.loads(copy.read_text(encoding="utf-8"))
    edited["info"]["version"] = "9.9.9"
    copy.write_text(schemas.render_json(edited), encoding="utf-8")
    assert schemas.check(tmp_path, docs) == [
        "openapi/v1.json: differs from the models; run `make contracts`"
    ]


def test_version_title_and_openapi_level(document: dict[str, Any]) -> None:
    assert document["openapi"] == "3.1.0"
    assert document["info"]["title"] == "NeonRadar API"
    assert document["info"]["version"] == versions.API


def test_every_operation_is_under_the_v1_prefix_with_a_readable_id(
    document: dict[str, Any],
) -> None:
    ids = [op["operationId"] for path, ops in document["paths"].items() for op in ops.values()]
    assert all(path.startswith(f"{API_PREFIX}/") for path in document["paths"])
    assert len(ids) == len(set(ids)) == 12
    assert all(op_id.isidentifier() and op_id.islower() for op_id in ids)


def test_every_error_is_a_problem_and_nothing_else(document: dict[str, Any]) -> None:
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            for status, response in operation["responses"].items():
                if status != "200":
                    assert response["content"] == PROBLEM_CONTENT, (method, path, status)
    names = set(document["components"]["schemas"])
    assert not names & {"HTTPValidationError", "ValidationError"}
    assert not [name for name in names if name.endswith(("-Input", "-Output"))]


def test_every_object_schema_is_closed(document: dict[str, Any]) -> None:
    for name, schema in document["components"]["schemas"].items():
        if schema.get("type") == "object" and "properties" in schema:
            assert schema.get("additionalProperties") is False, name


LIMITS = [
    ("/search", "q", {"minLength": 2, "maxLength": 200}),
    ("/search", "limit", {"minimum": 1, "maximum": 50, "default": 20}),
    ("/entities/{entity_id}/network", "depth", {"minimum": 1, "maximum": 3, "default": 1}),
    ("/entities/{entity_id}/network", "max_nodes", {"minimum": 1, "maximum": 500, "default": 200}),
    ("/entities/{entity_id}/ownership", "max_hops", {"minimum": 1, "maximum": 8, "default": 6}),
    ("/paths", "max_hops", {"minimum": 1, "maximum": 6, "default": 4}),
    ("/alerts", "limit", {"minimum": 1, "maximum": 200, "default": 50}),
]


@pytest.mark.parametrize(("path", "name", "expected"), LIMITS)
def test_parameter_limits_are_the_ones_of_5_3(
    document: dict[str, Any], path: str, name: str, expected: dict[str, int]
) -> None:
    operation = document["paths"][f"{API_PREFIX}{path}"]["get"]
    schema = next(p["schema"] for p in operation["parameters"] if p["name"] == name)
    assert {key: schema[key] for key in expected} == expected
