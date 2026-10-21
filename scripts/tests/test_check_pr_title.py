import check_pr_title
import pytest


@pytest.mark.parametrize(
    "title",
    [
        "ci(ci): add the CI workflows [M1.6]",
        "feat: add a loader",
        "fix(api)!: drop a field",
        "docs(m1-10a): add the glossary",
        "build(deps): bump ruff from 0.17.1 to 0.17.2",
        "build(deps-dev): bump the python-minor-patch group with 3 updates",
        "chore(repo): tidy",
    ],
)
def test_conventional_titles_pass(title: str) -> None:
    assert check_pr_title.main([title]) == 0


@pytest.mark.parametrize(
    "title",
    [
        "Add CI",
        "Bump ruff from 0.17.1 to 0.17.2",
        "feature(ci): add CI",
        "Feat(ci): add CI",
        "ci(CI): add CI",
        "ci(c_i): add CI",
        "ci(): add CI",
        "ci (ci): add CI",
        "ci(ci):add CI",
        "ci(ci): ",
        "ci(ci): add CI\nsecond line",
    ],
)
def test_other_titles_fail(title: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pr_title.main([title]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_help_exits_0() -> None:
    with pytest.raises(SystemExit) as exc:
        check_pr_title.main(["--help"])
    assert exc.value.code == 0
