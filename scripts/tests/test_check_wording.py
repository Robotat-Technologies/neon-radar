from pathlib import Path

import check_wording
import pytest

TERMS = "# test terms\n\\blaunder\\w*\n\\bsuspic\\w*\n\\bshell\\s+compan\\w*\n\n"

CLEAN_TYPOLOGY = """\
slug: circular_flow
name: Round-tripping or circular flows
summary: >
  Funds leave an account and return to it. Laundering typologies list this pattern.
wording:
  # templates shown next to entities
  headline_structural: "Funds returned to the originating account through {cycle_length} transfers"
  headline_synthetic: "Synthetic scenario: funds returned to the originating account"
false_positives:
  - Refunds that look suspicious at first
"""

CLEAN_WORDING_PY = '''\
"""Wording helpers. Never write "laundered funds" or "suspicious activity" here."""


def headline(cycle_length: int) -> str:
    """Return the headline; never say launderer."""
    return f"Funds returned through {cycle_length} transfers"


STEP = "{payer} sent {amount} to {payee}"
'''


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "contracts/wording").mkdir(parents=True)
    (tmp_path / "contracts/wording/forbidden-terms.txt").write_text(TERMS, encoding="utf-8")
    (tmp_path / "detect/typologies").mkdir(parents=True)
    (tmp_path / "detect/src/neonradar_detect").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, text: str) -> None:
    (root / relative).write_text(text, encoding="utf-8")


def run(root: Path) -> int:
    return check_wording.main(["--root", str(root)])


def test_missing_terms_file_is_a_notice(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(tmp_path) == 0
    assert "notice" in capsys.readouterr().out


def test_clean_templates_pass(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "detect/typologies/circular_flow.yaml", CLEAN_TYPOLOGY)
    write(root, "detect/src/neonradar_detect/wording.py", CLEAN_WORDING_PY)
    write(root, "detect/typologies/fan_in.yaml", "slug: fan_in\nwording: null\n")
    assert run(root) == 0
    assert "2 typology files and 1 wording.py files pass 3 patterns" in capsys.readouterr().out


def test_forbidden_term_in_a_typology_template_fails(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    template = CLEAN_TYPOLOGY.replace("Synthetic scenario: funds", "Suspicious funds")
    write(root, "detect/typologies/circular_flow.yaml", template)
    assert run(root) == 1
    assert "detect/typologies/circular_flow.yaml:8: 'Suspicious'" in capsys.readouterr().out


def test_inline_wording_mapping_is_checked(root: Path) -> None:
    write(root, "detect/typologies/x.yaml", 'wording: {headline_structural: "a shell company"}\n')
    assert run(root) == 1


@pytest.mark.parametrize(
    "template", ['"Funds returned\\nLaundered funds"', '"Funds returned\\tsuspicious"']
)
def test_forbidden_term_after_a_yaml_escape_fails(
    root: Path, template: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        root, "detect/typologies/x.yaml", f"slug: x\nwording:\n  headline_structural: {template}\n"
    )
    assert run(root) == 1
    assert "detect/typologies/x.yaml:3:" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("code", "line"),
    [
        ('HEADLINE = "Funds were laundered"\n', 1),
        ('def f(name: str) -> str:\n    return f"{name} is a Launderer"\n', 2),
        ('STEPS = (\n    "first",\n    """two\nlaundering lines""",\n)\n', 4),
        ('x = {"k": "suspicion score"}\n', 1),
        ('HEADLINE = "Funds returned\\nLaundered funds"\n', 1),
        ('def f(n: int) -> str:\n    return f"{n} transfers\\tsuspicious"\n', 2),
        ('TEXT = "ok\\x20laundered"\n', 1),
    ],
)
def test_forbidden_term_in_a_wording_literal_fails(
    root: Path, code: str, line: int, capsys: pytest.CaptureFixture[str]
) -> None:
    write(root, "detect/src/neonradar_detect/wording.py", code)
    assert run(root) == 1
    assert f"detect/src/neonradar_detect/wording.py:{line}:" in capsys.readouterr().out


def test_wording_py_with_python_3_14_syntax_still_reads(root: Path) -> None:
    code = 'try:\n    pass\nexcept ValueError, TypeError:\n    TEXT = "launder"\n'
    write(root, "detect/src/neonradar_detect/wording.py", code)
    assert run(root) == 1


def test_invalid_pattern_fails(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(root, "contracts/wording/forbidden-terms.txt", "\\bok\n(unclosed\n")
    assert run(root) == 1
    assert "invalid pattern" in capsys.readouterr().out
