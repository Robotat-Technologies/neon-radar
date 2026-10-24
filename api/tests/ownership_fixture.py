"""The ownership fixture of PHASE-2.md M2.12 and its expected table (the oracle), for
`test_ownership.py` and `test_paths.py`: the API on the shared Neo4j with the fixture loaded."""

import json
import re
from collections.abc import Iterator
from typing import Any, Final

from fastapi.testclient import TestClient

from neonradar_api.files import RepoFiles
from neonradar_api.main import create_app
from neonradar_contracts.api import PathRef
from neonradar_graph.loader import load_files, wipe
from neonradar_graph.migrate import migrate

from .conftest import REPO_ROOT, SessionGraph

P: Final = "/api/v1"
FIXTURE: Final = REPO_ROOT / "graph" / "tests" / "fixtures" / "ownership"
EXPECTED: Final[dict[str, Any]] = json.loads((FIXTURE / "expected.json").read_text("utf-8"))
PREFIX: Final[str] = EXPECTED["prefix"]
INTERVAL: Final = re.compile(r"([\[(])([0-9.]+), ([0-9.]+)([\])])")
SHARES: Final = (
    "effective_share_min",
    "effective_share_max",
    "effective_share_min_exclusive",
    "effective_share_max_exclusive",
)


def interval(text: str | None) -> dict[str, Any]:
    """The four PathRef share fields of a table interval such as `(9.375, 37.5)`."""
    if text is None:
        return dict.fromkeys(SHARES)
    found = INTERVAL.fullmatch(text)
    assert found, text
    return dict(
        zip(
            SHARES,
            (float(found[2]), float(found[3]), found[1] == "(", found[4] == ")"),
            strict=True,
        )
    )


def table_row(path: PathRef) -> tuple[list[str], dict[str, Any]]:
    """A returned path as the table writes it: node ids without the prefix, and its shares."""
    nodes = [node_id.removeprefix(PREFIX) for node_id in path.node_ids]
    return nodes, {name: getattr(path, name) for name in SHARES}


def serve(target: Any) -> Iterator[TestClient]:
    """Wipe the shared Neo4j, load the fixture and serve the API on it."""
    wipe(target.driver, target.database)
    migrate(target.driver, target.database)
    report = load_files(target.driver, [FIXTURE], database=target.database)
    assert not report.failed
    app = create_app(SessionGraph(target), RepoFiles(REPO_ROOT))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client
