"""scripts/ensure_env.sh, run on a copy in a scratch folder (never in the real checkout)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ensure_env.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")


def run_copy(
    tmp_path: Path, password: str, secret: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a copy of the script in an empty scratch folder that is not a git repository."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "ensure_env.sh")
    secrets = tmp_path / "secrets"  # stands in for /run/secrets
    if secret is not None:
        secrets.mkdir()
        (secrets / "neo4j_password").write_text(secret, encoding="utf-8")
    env = {
        **os.environ,
        "NEO4J_PASSWORD": password,
        "NR_SECRETS_DIR": str(secrets),
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
    }
    return subprocess.run(
        [str(BASH), str(tmp_path / "scripts" / "ensure_env.sh")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


FROM_ENVIRONMENT = "NEO4J_PASSWORD is set in the environment; .env not needed.\n"
FROM_COMPOSE = "NEO4J_PASSWORD comes from the Compose secret neo4j_password; .env not needed.\n"


@pytest.mark.parametrize(
    ("password", "secret", "message"),
    [
        ("throwaway-test-value-1", None, FROM_ENVIRONMENT),
        ("", "throwaway-test-value-2", FROM_COMPOSE),
    ],
)
def test_a_password_in_the_environment_or_a_secret_needs_no_env_file(
    tmp_path: Path, password: str, secret: str | None, message: str
) -> None:
    result = run_copy(tmp_path, password, secret)
    assert (result.returncode, result.stdout) == (0, message)
    assert "throwaway-test-value" not in result.stdout + result.stderr
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".env").is_symlink()


@pytest.mark.parametrize("secret", [None, ""])
def test_an_empty_password_or_secret_does_not_count(tmp_path: Path, secret: str | None) -> None:
    # No .env.example in the scratch folder, so the script stops before it would write .env.
    result = run_copy(tmp_path, "", secret)
    assert result.returncode == 1
    assert ".env.example is missing" in result.stderr
    assert not (tmp_path / ".env").exists()
