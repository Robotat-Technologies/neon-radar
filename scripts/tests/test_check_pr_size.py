from typing import TYPE_CHECKING

import check_pr_size
import hygiene_common
import pytest

if TYPE_CHECKING:
    from conftest import GitRepo

EXCLUDES = "uv.lock\ncontracts/openapi/**\n**/*.md\ndetect/typologies/*.yaml\n"


def lines(count: int) -> str:
    return "".join(f"line {i}\n" for i in range(count))


@pytest.fixture
def branch(git_repo: "GitRepo") -> "GitRepo":
    git_repo.write(".github/pr-size-exclude.txt", EXCLUDES)
    git_repo.write("big.py", lines(500))
    git_repo.commit("base")
    git_repo.run("switch", "-q", "-c", "feature")
    return git_repo


def run(repo: "GitRepo", labels: str = "") -> int:
    return check_pr_size.main(["--root", str(repo.path), "--base", "main", "--labels", labels])


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('[\n  "agent",\n  "size-exception"\n]', ["agent", "size-exception"]),
        ("agent, phase-1,,size-exception ", ["agent", "phase-1", "size-exception"]),
        ("[]", []),
        ("", []),
    ],
)
def test_parse_labels(value: str, expected: list[str]) -> None:
    assert hygiene_common.parse_labels(value) == expected


def test_parse_labels_rejects_a_json_object() -> None:
    with pytest.raises(ValueError):
        hygiene_common.parse_labels('[{"name": "agent"}]')


@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("README.md", True),
        ("docs/build/ci.md", True),
        ("uv.lock", True),
        ("contracts/openapi/v1.json", True),
        ("detect/typologies/circular_flow.yaml", True),
        ("scripts/check_pr_size.py", False),
        ("ui/uv.lock", False),
        ("detect/src/typologies.yaml", False),
    ],
)
def test_exclusion_globs(path: str, excluded: bool) -> None:
    patterns = check_pr_size.read_patterns_from_text(EXCLUDES)
    assert check_pr_size.is_excluded(path, patterns) is excluded


def test_small_change_passes(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    branch.write("new.py", lines(10))
    branch.write("docs/guide.md", lines(1000))
    branch.commit("change")
    assert run(branch) == 0
    assert "10 counted lines in 1 files" in capsys.readouterr().out


def test_large_change_fails(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    branch.write("new.py", lines(401))
    branch.commit("change")
    assert run(branch, '["agent"]') == 1
    assert "FAIL: 401 counted lines" in capsys.readouterr().out


def test_size_exception_only_warns(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    branch.write("new.py", lines(401))
    branch.commit("change")
    assert run(branch, "agent,size-exception") == 0
    assert "WARN" in capsys.readouterr().out


def test_deleted_lines_count(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    branch.write("big.py", lines(300))
    branch.commit("shrink")
    assert run(branch) == 0
    assert "200 counted lines" in capsys.readouterr().out


def test_rename_counts_under_the_new_path(
    branch: "GitRepo", capsys: pytest.CaptureFixture[str]
) -> None:
    branch.move("big.py", "docs/big.md")
    branch.commit("rename")
    assert run(branch) == 0
    assert "0 counted lines in 0 files" in capsys.readouterr().out


def test_binary_files_count_zero(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    branch.write("logo.png", b"\x89PNG\x00\x01\x02" * 100)
    branch.commit("binary")
    assert run(branch) == 0
    assert "0 counted lines in 1 files" in capsys.readouterr().out


def test_unknown_base_fails(branch: "GitRepo", capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pr_size.main(["--root", str(branch.path), "--base", "nope"]) == 1
    assert "FAIL" in capsys.readouterr().out
