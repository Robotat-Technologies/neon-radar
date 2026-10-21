"""The protection script requires exactly the CI job ids and never changes settings in tests.

The script runs only with --dry-run or under CLAUDECODE=1, where it must refuse; a fake `gh`
first on PATH records any call, and the tests assert that none happened.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "setup_repo_protection.sh"
WORKFLOWS = [ROOT / ".github/workflows/ci.yml", ROOT / ".github/workflows/pr-hygiene.yml"]


def job_ids(workflow: Path) -> list[str]:
    """Job ids: the two-space keys under the top-level `jobs:` key."""
    jobs, inside = [], False
    for line in workflow.read_text(encoding="utf-8").splitlines():
        if line and not line[0].isspace():
            inside = line.startswith("jobs:")
        elif inside and (match := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)):
            jobs.append(match.group(1))
    return jobs


def required_checks() -> list[str]:
    match = re.search(r"^REQUIRED_CHECKS=\(([^)]*)\)", SCRIPT.read_text(encoding="utf-8"), re.M)
    assert match
    return match.group(1).split()


def test_required_checks_are_the_job_ids() -> None:
    ids = [job for workflow in WORKFLOWS for job in job_ids(workflow)]
    assert sorted(ids) == sorted(required_checks()) == ["hygiene", "integration", "python", "ui"]


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_jobs_have_no_name(workflow: Path) -> None:
    """A job `name:` would replace the job id as the check name (PHASE-1.md 3.2)."""
    text = workflow.read_text(encoding="utf-8")
    jobs_section = text[text.index("\njobs:") :]
    assert not re.search(r"^    name:", jobs_section, re.M)


@pytest.fixture
def fake_gh(tmp_path: Path) -> tuple[dict[str, str], Path]:
    calls = tmp_path / "gh-calls.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{calls}"\nexit 1\n', encoding="utf-8")
    gh.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env.pop("CLAUDECODE", None)
    return env, calls


def run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, check=False
    )


def protection_body(output: str) -> dict[str, object]:
    start = output.index("/protection")
    body = output[output.index("{", start) : output.index("\n}\n", start) + 2]
    parsed = json.loads(body)
    assert isinstance(parsed, dict)
    return parsed


def test_dry_run_prints_the_spec_settings(fake_gh: tuple[dict[str, str], Path]) -> None:
    env, calls = fake_gh
    result = run(["--dry-run", "--repo", "owner/name"], env)
    assert result.returncode == 0, result.stderr
    assert not calls.exists()
    body = protection_body(result.stdout)
    assert body["required_status_checks"] == {
        "strict": False,
        "checks": [{"context": check} for check in ["python", "integration", "ui", "hygiene"]],
    }
    assert body["required_pull_request_reviews"] == {
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "required_approving_review_count": 1,
    }
    assert body["enforce_admins"] is True
    assert body["required_linear_history"] is False
    assert body["allow_force_pushes"] is False
    assert body["allow_deletions"] is False
    for path in [
        "PUT repos/owner/name/private-vulnerability-reporting",
        "PATCH repos/owner/name ",
        "PATCH repos/owner/name/code-scanning/default-setup",
        "PUT repos/owner/name/vulnerability-alerts",
        "PUT repos/owner/name/automated-security-fixes",
    ]:
        assert f"WOULD SEND: {path}" in result.stdout


def test_single_operator_options(fake_gh: tuple[dict[str, str], Path]) -> None:
    env, calls = fake_gh
    args = ["--dry-run", "--repo=owner/name", "--approvals", "0", "--no-code-owner-review"]
    result = run(args, env)
    assert result.returncode == 0, result.stderr
    assert not calls.exists()
    reviews = protection_body(result.stdout)["required_pull_request_reviews"]
    assert reviews == {
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "required_approving_review_count": 0,
    }


def test_refuses_inside_claude_code(fake_gh: tuple[dict[str, str], Path]) -> None:
    env, calls = fake_gh
    result = run(["--repo", "owner/name"], {**env, "CLAUDECODE": "1"})
    assert result.returncode == 2
    assert "Refusing to run inside Claude Code" in result.stderr
    assert not calls.exists()


@pytest.mark.parametrize(
    "args",
    [["--approvals", "7"], ["--approvals", "x"], ["--repo", "not-a-repo"], ["--repo"], ["-x"]],
)
def test_bad_options_fail_before_any_call(
    fake_gh: tuple[dict[str, str], Path], args: list[str]
) -> None:
    env, calls = fake_gh
    result = run(["--dry-run", *args], env)
    assert result.returncode == 2
    assert not calls.exists()
