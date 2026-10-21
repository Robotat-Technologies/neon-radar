from typing import TYPE_CHECKING

import check_contract_paths
import pytest

if TYPE_CHECKING:
    from conftest import GitRepo


def branch_with(repo: "GitRepo", path: str, *, frozen: bool) -> None:
    repo.write("contracts/src/models.py", "VERSION = '1.0.0'\n")
    repo.commit("contracts")
    if frozen:
        repo.run("tag", "contracts-v1.0.0")
    repo.run("switch", "-q", "-c", "feature")
    repo.write(path, "changed\n")
    repo.commit("change")


def run(repo: "GitRepo", labels: str = "") -> int:
    return check_contract_paths.main(
        ["--root", str(repo.path), "--base", "main", "--labels", labels]
    )


@pytest.mark.parametrize(
    "path", ["graph/src/neonradar_graph/loader.py", "contracts-notes.md", "docs/contracts/x.md"]
)
def test_other_paths_pass_after_the_freeze(git_repo: "GitRepo", path: str) -> None:
    branch_with(git_repo, path, frozen=True)
    assert run(git_repo) == 0


def test_contract_change_before_the_freeze_passes(
    git_repo: "GitRepo", capsys: pytest.CaptureFixture[str]
) -> None:
    branch_with(git_repo, "contracts/src/models.py", frozen=False)
    assert run(git_repo) == 0
    assert "not frozen yet" in capsys.readouterr().out


@pytest.mark.parametrize(
    "path", ["contracts/src/models.py", "graph/schema/migrations/0002_more.cypher"]
)
def test_frozen_path_without_the_label_fails(
    git_repo: "GitRepo", path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    branch_with(git_repo, path, frozen=True)
    assert run(git_repo, '["agent", "phase-2"]') == 1
    output = capsys.readouterr().out
    assert "FAIL" in output
    assert path in output


@pytest.mark.parametrize("labels", ['["agent", "contract-change"]', "agent,contract-change"])
def test_frozen_path_with_the_label_passes(git_repo: "GitRepo", labels: str) -> None:
    branch_with(git_repo, "contracts/src/models.py", frozen=True)
    assert run(git_repo, labels) == 0


def test_moving_a_file_out_of_contracts_counts(git_repo: "GitRepo") -> None:
    git_repo.write("contracts/src/models.py", "VERSION = '1.0.0'\n")
    git_repo.commit("contracts")
    git_repo.run("tag", "contracts-v1.0.0")
    git_repo.run("switch", "-q", "-c", "feature")
    git_repo.move("contracts/src/models.py", "attic/models.py")
    git_repo.commit("move")
    assert run(git_repo) == 1
