import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import spec_extract as se


def _entry(path: str, body: str, status: str = "Verbatim", fence: str = "```") -> str:
    digest = hashlib.sha256((body + "\n").encode()).hexdigest()
    return f"### `{path}`\n\n{status}. SHA-256 `{digest}`.\n\n{fence}python\n{body}\n{fence}\n"


BOOK = (
    "# Code book\n\nIntro text.\n\n## M3.2 Detection core\n\n"
    + _entry("detect/src/a.py", "A = 1")
    + "\nSome prose.\n\n"
    + _entry("detect/src/b.py", "def b():\n    return '```'", fence="````")
    + "\n## M3.3 Generator\n\n"
    + _entry("ingest/src/names.py", "class Names: ...", status="Reference")
)


def test_parse_reads_paths_status_and_exact_content() -> None:
    entries = se.parse(BOOK)
    assert [(e.milestone, e.path, e.verbatim) for e in entries] == [
        ("M3.2", "detect/src/a.py", True),
        ("M3.2", "detect/src/b.py", True),
        ("M3.3", "ingest/src/names.py", False),
    ]
    assert entries[1].content == "def b():\n    return '```'\n"


def test_a_damaged_block_is_refused() -> None:
    with pytest.raises(se.BookError, match="SHA-256"):
        se.parse(BOOK.replace("A = 1", "A = 2"))


def test_extract_writes_verbatim_files_only_and_check_finds_changes(tmp_path: Path) -> None:
    entries = se.parse(BOOK)
    written = se.extract(entries, tmp_path, None)
    assert len(written) == 2 and not (tmp_path / "ingest").exists()
    assert se.check(entries, tmp_path) == ([], [])
    (tmp_path / "detect/src/a.py").write_text("A = 3\n")
    (tmp_path / "detect/src/b.py").unlink()
    assert se.check(entries, tmp_path) == (
        ["differs: detect/src/a.py", "missing: detect/src/b.py"],
        [],
    )
    se.extract(entries, tmp_path, tmp_path / "ref")
    assert (tmp_path / "ref/ingest/src/names.py.reference").read_text() == "class Names: ...\n"


def test_recorded_deviations_pass_and_tests_never_deviate(tmp_path: Path) -> None:
    entries = se.parse(BOOK)
    se.extract(entries, tmp_path, None)
    (tmp_path / "detect/src/a.py").write_text("A = 3\n")
    digest = hashlib.sha256(b"A = 3\n").hexdigest()
    row = {"sha256": digest, "milestone": "M3.2", "reason": "import path"}
    record = tmp_path / "deviations.json"
    record.write_text(json.dumps({"detect/src/a.py": row}))
    assert se.check(entries, tmp_path, se.deviations(record)) == (
        [],
        ["deviation: detect/src/a.py (import path)"],
    )
    (tmp_path / "detect/src/a.py").write_text("A = 4\n")  # a later change is not the recorded one
    assert se.check(entries, tmp_path, se.deviations(record))[0] == ["differs: detect/src/a.py"]
    record.write_text(json.dumps({"detect/tests/test_a.py": row}))
    with pytest.raises(se.BookError, match="never deviates"):
        se.deviations(record)


def test_update_rewrites_a_block_and_its_sha(tmp_path: Path) -> None:
    entries = se.parse(BOOK)
    se.extract(entries, tmp_path, None)
    (tmp_path / "detect/src/a.py").write_text("A = 5\nB = 6\n")
    new = se.update(BOOK, entries, tmp_path, ["detect/src/a.py"])
    again = {x.path: x for x in se.parse(new)}
    assert again["detect/src/a.py"].content == "A = 5\nB = 6\n"
    assert again["detect/src/b.py"].content == "def b():\n    return '```'\n"
    assert se.check(list(again.values()), tmp_path) == ([], [])
    with pytest.raises(se.BookError, match="not in the code book"):
        se.update(BOOK, entries, tmp_path, ["detect/src/c.py"])


def test_paths_outside_the_repository_and_duplicates_are_refused(tmp_path: Path) -> None:
    bad = se.parse(BOOK.replace("detect/src/a.py", "../escape.py"))
    with pytest.raises(se.BookError, match="outside"):
        se.extract(bad, tmp_path, None)
    with pytest.raises(se.BookError, match="twice"):
        se.parse(BOOK + "\n## M3.4 More\n\n" + _entry("detect/src/a.py", "A = 1"))


def test_main_select_and_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    book = tmp_path / "book.md"
    book.write_text(BOOK)
    args = ["--milestone", "M3.2", "--book", str(book), "--root", str(tmp_path / "repo")]
    assert se.main(["extract", *args]) == 0
    assert se.main(["check", *args]) == 0
    assert "2 of 2 verbatim files match" in capsys.readouterr().out
    assert se.main(["list", "--milestone", "M9.9", "--book", str(book)]) == 2
    assert se.main(["check", "--milestone", "M9.9", "--book", str(book)]) == 2
    assert se.main(["check", "--milestone", "M3.7", "--book", str(book)]) == 0  # no code book files
    assert "M3.7 copies no file from the code book" in capsys.readouterr().out


def test_typology_files_keep_the_researchers_lines(tmp_path: Path) -> None:
    body = 'slug: x\nversion: 0.2.0\nstatus: draft\nowner: "@TODO"\napproved_by: null\ntier: core'
    entries = se.parse("## M3.5a Detectors\n\n" + _entry("detect/typologies/x.yaml", body))
    target = tmp_path / "detect/typologies/x.yaml"
    target.parent.mkdir(parents=True)
    approved = 'slug: x\nversion: 0.2.0\nstatus: approved\nowner: "@ana"\napproved_by: "@ana"\n'
    target.write_text(approved + "tier: core\n")
    se.extract(entries, tmp_path, None)
    text = target.read_text()
    assert 'owner: "@ana"' in text and "status: approved" in text and 'approved_by: "@ana"' in text
    assert se.check(entries, tmp_path) == ([], [])
    target.write_text(text.replace("tier: core", "tier: extended"))
    assert se.check(entries, tmp_path) == (["differs: detect/typologies/x.yaml"], [])
    # an approval of another definition never carries over: a new version, or the same version
    # with other content (a Phase 1 draft without a detector), keeps the owner and resets the rest
    for old in (approved.replace("0.2.0", "0.1.0") + "tier: core\n", approved + "tier: extended\n"):
        target.write_text(old)
        se.extract(entries, tmp_path, None)
        text = target.read_text()
        assert 'owner: "@ana"' in text and "status: draft" in text and "approved_by: null" in text
