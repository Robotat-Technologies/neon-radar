"""`make reset` deletes only the default instance's volumes (PHASE-2.md M2.2, 4.5).

The real-data volumes are deleted only by `neonradar data purge --graph`. `make -n` prints the
recipe without running it, so no Docker command runs here.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REAL_VOLUMES = ("neonradar_neo4j-real-data", "neonradar_neo4j-real-logs")


def recipe(*arguments: str) -> list[str]:
    result = subprocess.run(
        ["make", "--no-print-directory", "-n", "reset", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


@pytest.mark.skipif(shutil.which("make") is None, reason="needs make")
def test_reset_never_names_the_real_volumes_or_removes_declared_volumes() -> None:
    lines = recipe("CONFIRM=yes")
    docker = [line.strip() for line in lines if line.strip().startswith("docker")]
    assert docker == [
        "docker compose --profile app down",
        "docker volume rm --force neonradar_neo4j_data neonradar_neo4j_logs",
    ]
    text = "\n".join(lines)
    assert "real" not in text
    assert not any(volume in text for volume in REAL_VOLUMES)
    assert " -v" not in text and "--volumes" not in text
    assert "COMPOSE_PROJECT_NAME" in text  # another Compose project is refused first


@pytest.mark.skipif(shutil.which("make") is None, reason="needs make")
@pytest.mark.parametrize(
    ("variable", "dot_env", "code"),
    [("other", "", 1), ("", "COMPOSE_PROJECT_NAME=other\n", 1), ("neonradar", "", 0), ("", "", 0)],
)
def test_the_project_name_check_refuses_another_compose_project(
    tmp_path: Path, variable: str, dot_env: str, code: int
) -> None:
    """Only the name check runs, in a temporary folder with its own .env, never Docker."""
    text = "\n".join(recipe("CONFIRM=yes"))
    check = text[text.index('name="') : text.index("exit 1; fi", text.index('name="')) + 10]
    (tmp_path / ".env").write_text(dot_env, encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin", **({"COMPOSE_PROJECT_NAME": variable} if variable else {})}
    result = subprocess.run(
        ["sh", "-c", check.replace("\\\n", "")], cwd=tmp_path, env=env, capture_output=True,
        text=True, check=False,
    )  # fmt: skip
    assert result.returncode == code, result.stderr
