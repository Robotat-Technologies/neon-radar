"""scripts/ensure_env.sh, run on a copy in a scratch folder (never in the real checkout)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ensure_env.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")


def run_copy(tmp_path: Path, password: str) -> subprocess.CompletedProcess[str]:
    """Run a copy of the script in an empty scratch folder that is not a git repository."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "ensure_env.sh")
    env = {**os.environ, "NEO4J_PASSWORD": password, "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    return subprocess.run(  # noqa: S603 (fixed arguments, scratch folder)
        [str(BASH), str(tmp_path / "scripts" / "ensure_env.sh")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_a_password_in_the_environment_needs_no_env_file(tmp_path: Path) -> None:
    result = run_copy(tmp_path, "throwaway-test-value-1234")
    assert result.returncode == 0
    assert result.stdout == "NEO4J_PASSWORD is set in the environment; .env not needed.\n"
    assert "throwaway-test-value-1234" not in result.stdout + result.stderr
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".env").is_symlink()


def test_an_empty_password_in_the_environment_does_not_count(tmp_path: Path) -> None:
    # No .env.example in the scratch folder, so the script stops before it would write .env.
    result = run_copy(tmp_path, "")
    assert result.returncode == 1
    assert ".env.example is missing" in result.stderr
    assert not (tmp_path / ".env").exists()
