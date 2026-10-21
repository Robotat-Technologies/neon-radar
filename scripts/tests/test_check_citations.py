from pathlib import Path

import check_citations
import pytest

BIBLIOGRAPHY = """\
version: 1
entries:
  - key: fatf_pml_2018
    title: Professional Money Laundering
    publisher: FATF
    year: 2018
    url: https://example.org/pml
    verified: 2026-10-16
  - key: ffiec_appendix_f
    title: Red flags
    publisher: FFIEC
    year: null
    url: https://example.org/f
    verified: 2026-10-21
"""

CLEAN_DOC = """\
# Money mules

A mule account can be the first layering stage [fatf_pml_2018]. Red flags are not evidence
[ffiec_appendix_f] [fatf_pml_2018].

| Term | Sources |
|---|---|
| Red flag | [ffiec_appendix_f] |

- [x] a task box, a [note], an [Upper_Case] word and a [link_text](https://example.org)
- a reference link [ref_text][ref] and an image ![alt_text](a.png)
"""

TYPOLOGY = """\
slug: circular_flow
citations: [fatf_pml_2018, ffiec_appendix_f]
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "docs/sources").mkdir(parents=True)
    (tmp_path / "docs/sources/bibliography.yaml").write_text(BIBLIOGRAPHY, encoding="utf-8")
    (tmp_path / "detect/typologies").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(root: Path, *paths: str) -> int:
    return check_citations.main(["--root", str(root), *(str(root / p) for p in paths)])


def test_known_keys_pass(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "docs/glossary.md", CLEAN_DOC)
    write(root, "README.md", "No citations here.\n")
    write(root, "detect/typologies/circular_flow.yaml", TYPOLOGY)
    assert run(root, "docs", "detect/typologies", "README.md") == 0
    out = capsys.readouterr().out
    assert "2 Markdown and 1 typology files cite 2 distinct keys" in out
    assert "(2 entries)" in out


def test_unknown_key_in_markdown_fails(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "docs/a.md", "Fine [fatf_pml_2018].\n\nNot fine [fatf_pml_2019].\n")
    assert run(root, "docs") == 1
    assert "docs/a.md:3: unknown citation key 'fatf_pml_2019'" in capsys.readouterr().out


@pytest.mark.parametrize(
    "text",
    [
        "```markdown\n[no_such_key]\n```\n",
        "~~~\n[no_such_key]\n~~~\n",
        "````\n```\n[no_such_key]\n```\n````\n",
        "1. Step:\n\n   ```yaml\n   [no_such_key]\n   ```\n",
        "Show `[no_such_key]` as code.\n",
        "Show ``a ` [no_such_key]`` as code.\n",
    ],
)
def test_code_is_not_checked(root: Path, text: str) -> None:
    write(root, "docs/a.md", text)
    assert run(root, "docs") == 0


def test_text_after_a_closed_fence_is_checked(root: Path) -> None:
    write(root, "docs/a.md", "```\ncode\n```\n\nCited [no_such_key].\n")
    assert run(root, "docs") == 1


def test_research_and_plan_are_skipped(root: Path) -> None:
    write(root, "docs/research/2026-10-16/note.md", "[no_such_key]\n")
    write(root, "docs/plan/plan.md", "[no_such_key]\n")
    assert run(root, "docs") == 0


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("slug: x\ncitations: [fatf_pml_2018, no_such_key]\n", 2),
        ("slug: x\ncitations:\n  - fatf_pml_2018\n  - no_such_key\n", 4),
    ],
)
def test_unknown_key_in_a_typology_fails(
    root: Path, text: str, line: int, capsys: pytest.CaptureFixture[str]
) -> None:
    write(root, "detect/typologies/x.yaml", text)
    assert run(root, "detect/typologies") == 1
    out = capsys.readouterr().out
    assert f"detect/typologies/x.yaml:{line}: unknown citation key 'no_such_key'" in out


def test_typology_citations_must_be_a_list(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "detect/typologies/x.yaml", "slug: x\ncitations: fatf_pml_2018\n")
    assert run(root, "detect/typologies") == 1
    assert "must be a list of keys" in capsys.readouterr().out


def test_other_yaml_files_are_ignored(root: Path) -> None:
    write(root, "docs/other.yaml", "citations: [no_such_key]\n")
    write(root, "detect/typologies/nested/x.yaml", "citations: [no_such_key]\n")
    assert run(root, "docs", "detect/typologies") == 0


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            "  - {key: fatf_pml_2018, title: t, publisher: p, year: 1, url: u, verified: v}\n" * 2,
            "duplicate key 'fatf_pml_2018'",
        ),
        (
            "  - {key: FATF-2018, title: t, publisher: p, year: 1, url: u, verified: v}\n",
            "is not a citable key",
        ),
        ("  - {key: fatf_pml_2018, title: t}\n", "lacks publisher, year, url, verified"),
        (
            "  - {key: fatf_pml_2018, title: null, publisher: p, year: null, url: u, verified:}\n",
            "has no title, verified",
        ),
    ],
)
def test_broken_bibliography_fails(
    root: Path, entries: str, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(root, "docs/sources/bibliography.yaml", f"version: 1\nentries:\n{entries}")
    assert run(root, "docs") == 1
    assert message in capsys.readouterr().out


def test_missing_bibliography_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_citations.main(["--root", str(tmp_path), str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "docs/sources/bibliography.yaml: cannot be read" in out
    assert str(tmp_path) not in out


@pytest.mark.parametrize("text", ["version: 1\nentries: []\n", "version: 1\n", "[]\n"])
def test_empty_bibliography_fails(
    root: Path, text: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(root, "docs/sources/bibliography.yaml", text)
    assert run(root, "docs") == 1
    assert "a non-empty `entries` list" in capsys.readouterr().out


def test_duplicate_citations_key_fails(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = "slug: x\ncitations: [fatf_pml_2018]\ncitations: [no_such_key]\n"
    write(root, "detect/typologies/x.yaml", text)
    assert run(root, "detect/typologies") == 1
    assert "detect/typologies/x.yaml:3: duplicate `citations` key" in capsys.readouterr().out


def test_missing_path_is_a_notice(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "docs/a.md", "Cited [fatf_pml_2018].\n")
    assert run(root, "docs", "detect/nothing-here") == 0
    assert "notice: detect/nothing-here does not exist" in capsys.readouterr().out
