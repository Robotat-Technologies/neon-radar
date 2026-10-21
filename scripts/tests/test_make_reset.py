"""`make reset` deletes only the default instance's volumes (PHASE-2.md M2.2, 4.5).

The real-data volume is deleted only by `neonradar data purge --graph`. `make -n` prints the
recipe without running it, so no Docker command runs here.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


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
def test_reset_never_names_the_real_volume_or_removes_declared_volumes() -> None:
    lines = recipe("CONFIRM=yes")
    docker = [line.strip() for line in lines if line.strip().startswith("docker")]
    assert docker == [
        "docker compose --profile app down",
        "docker volume rm --force neonradar_neo4j_data neonradar_neo4j_logs",
    ]
    text = "\n".join(lines)
    assert "real" not in text
    assert " -v" not in text and "--volumes" not in text
