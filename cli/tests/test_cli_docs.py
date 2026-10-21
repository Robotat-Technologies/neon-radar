import shutil
from pathlib import Path

from typer.testing import CliRunner

from neonradar_cli.main import app

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parents[2] / "detect/tests/fixtures/typologies/circular_flow.yaml"
)


def index(tmp_path: Path, *options: str) -> tuple[int, str]:
    args = ["docs", "typology-index", "--typologies", str(tmp_path / "typologies")]
    result = runner.invoke(app, [*args, "--output", str(tmp_path / "README.md"), *options])
    return result.exit_code, result.output


def test_writes_then_checks_the_index(tmp_path: Path) -> None:
    (tmp_path / "typologies").mkdir()
    shutil.copy(FIXTURE, tmp_path / "typologies")
    assert index(tmp_path, "--check")[0] == 1  # no index yet
    code, output = index(tmp_path)
    assert code == 0, output
    assert "| [`circular_flow`](circular-flow.md) |" in (tmp_path / "README.md").read_text()
    assert index(tmp_path, "--check") == (0, "OK  README.md matches the catalog\n")


def test_check_fails_when_the_catalog_changed(tmp_path: Path) -> None:
    (tmp_path / "typologies").mkdir()
    assert index(tmp_path)[0] == 0
    shutil.copy(FIXTURE, tmp_path / "typologies")
    code, output = index(tmp_path, "--check")
    assert code == 1
    assert "README.md is out of date: run `uv run neonradar docs typology-index`" in output


def test_invalid_typology_fails(tmp_path: Path) -> None:
    (tmp_path / "typologies").mkdir()
    (tmp_path / "typologies" / "broken.yaml").write_text("slug: [x\n", encoding="utf-8")
    code, output = index(tmp_path)
    assert code == 1
    assert output.startswith("FAIL  broken.yaml: ")
    assert not (tmp_path / "README.md").exists()


def test_committed_index_is_up_to_date() -> None:
    result = runner.invoke(app, ["docs", "typology-index", "--check"])
    assert result.exit_code == 0, result.output
