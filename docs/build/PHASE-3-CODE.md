# NeonRadar build spec, Phase 3: the code book

| | |
|---|---|
| File | `docs/build/PHASE-3-CODE.md` |
| Companion of | `docs/build/PHASE-3.md` (the spec: read it first; this file holds code only) |
| Version | 1.0, 19 October 2026 |
| Holds | 141 verbatim files and 7 reference files, 18,242 lines, in 13 milestone sections |

This file holds every file that `PHASE-3.md` gives verbatim, so that the spec stays readable and no file is ever retyped. Each milestone section lists the files that milestone copies. Each entry is the file's repository path, a status line and the file's exact content in one fenced block.

- **Verbatim**: copy exactly, with `scripts/spec_extract.py extract`, and prove the copy with `check` (PHASE-3.md 2.10). A mechanical deviation (an import path the reconciliation names) is recorded in `docs/build/phase-3-deviations.json`, which `check` reads; tests, the CI baseline and the freeze file never deviate.
- **Reference**: shows the behaviour of an adapter that meets Phase 1 or Phase 2 code. The milestone writes the adapter itself, keeping the interface the verbatim code uses; `extract --reference DIR` writes these files to `DIR` to read, never into the repository.
- **Typology files** (`detect/typologies/*.yaml`) are verbatim except their `owner:`, `status:` and `approved_by:` lines, which belong to the typology researchers: `extract` keeps the repository's lines when the rest of the file is unchanged (otherwise it keeps only the owner line, so a changed definition starts again as a draft) and `check` ignores them.

Every status line ends with the SHA-256 of the block's content (the lines between the fences, each followed by a newline). `spec_extract` refuses a code book whose blocks do not match their hashes. An accepted change to a verbatim file after its milestone (a parameter the typology researchers set before the freeze, a fix found in review) reaches this file through `spec_extract update --path <file>`, which rewrites the block and its SHA-256 line, in the same pull request as the change (PHASE-3.md 2.10).

```bash
uv run python scripts/spec_extract.py list --milestone M3.2
uv run python scripts/spec_extract.py extract --milestone M3.2 --reference /tmp/m3-2-reference
uv run python scripts/spec_extract.py check --milestone M3.2
```

Tested together on 19 October 2026 with Python 3.14.6 (PHASE-3.md 3.4). The prototype stood in for Phase 1 and Phase 2 code with a stub of `compute_alert_id` and with the reference adapters below (the catalog, the wording lint, the name modules, the test fixtures), which is why the seams of PHASE-3.md 2.10 are reference files here. It had no copy of Phase 1's C4 `Alert` model: alerts were checked for C4's field shapes by a script (3.4), and M3.2 validates them against the model itself.

---

## M3.0 Phase 3 handover and agent kit update

The code book script and its tests, and the two agent rule files. In M3.0 the script cannot copy itself: take its two blocks out by hand once, then run `check`. 4 verbatim files (PHASE-3.md M3.0).

### `scripts/spec_extract.py`

Verbatim. Python, 321 lines. SHA-256 `18e1acc3312e966360ad4d927efe0390cb4c97e46af80c21b8e120d1b656165e`.

```python
"""Copy verbatim files out of the Phase 3 code book, or check them (PHASE-3.md 2.10, M3.0).

The code book (`docs/build/PHASE-3-CODE.md`) holds one section per milestone (`## M3.x ...`) and,
inside it, one entry per file: a heading with the repository path in backticks, a status line
("Verbatim." or "Reference.") that ends with the file's SHA-256 in backticks, and one fenced block
with the file's exact content. Verbatim files are copied as they are; reference files show the
behaviour an adapter must have and are never copied (`--reference DIR` writes them elsewhere to
read).

    uv run python scripts/spec_extract.py list [--milestone M3.2]
    uv run python scripts/spec_extract.py extract --milestone M3.2 [--root .] [--reference DIR]
    uv run python scripts/spec_extract.py check --milestone M3.2 [--root .]
    uv run python scripts/spec_extract.py update --path detect/typologies/structuring.yaml

`check` exits 1 when a verbatim file in the repository differs from the code book (or is
missing), so a pull request shows exactly which copied files it changed. A mechanical deviation
(PHASE-3.md 2.2 step 6b) passes when `docs/build/phase-3-deviations.json` records it: the path,
the SHA-256 of the repository's file, the milestone and the reason. Test files, the CI baseline,
the freeze file and the copilot's benchmark (PHASE-4.md 2.10) never deviate. Phase 4 passes
`--book docs/build/PHASE-4-CODE.md --deviations docs/build/phase-4-deviations.json` (or
`make spec-check M=M4.x`). `update` writes the repository's current file into its code
book block and recomputes the block's SHA-256: the way an accepted change to a verbatim file
reaches the code book (2.10), in the same pull request as the change. Every command first checks
each block against its stated SHA-256 and stops on a mismatch: the code book is damaged.

Typology files (`detect/typologies/*.yaml`) are verbatim except their `owner:`, `status:` and
`approved_by:` lines, which belong to the typology researchers (G4): `extract` keeps the
repository's lines when the rest of the file is the same as the code book's, and otherwise keeps
only the owner line, so that a changed definition (a new version, or new parameters, wording or
detector under the same version) starts again as `status: draft` with `approved_by: null`: an
approval of one definition never carries over to another. `check` ignores the three lines.

A milestone without a section in the code book has no verbatim files: `check --milestone` names
it and exits 0 when it is one of `NO_CODE`, and exits 2 for an unknown milestone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BOOK = Path("docs/build/PHASE-3-CODE.md")
DEFAULT_DEVIATIONS = Path("docs/build/phase-3-deviations.json")
NEVER_DEVIATE = (
    "eval/baselines/",
    "eval/freeze.json",
    # the copilot's benchmark (PHASE-4.md 2.10, M4.0): a change is a benchmark-change
    "copilot/bench/",
    "data/fixtures/copilot-bench/",
    "docs/benchmark-questions.md",
)
MILESTONE = re.compile(r"^## (M\d+\.\d+[a-z]?)\b")
ENTRY = re.compile(r"^### `([^`]+)`\s*$")
STATUS = re.compile(r"^(Verbatim|Reference)\.(?:.*)SHA-256 `([0-9a-f]{64})`\.?\s*$")
FENCE = re.compile(r"^(`{3,})([\w+-]*)\s*$")
PRESERVED = ("owner:", "status:", "approved_by:")
# Phase 3 milestones that copy no file from the code book (M3.4-1 and M3.4-2 use M3.4)
NO_CODE = ("M3.7", "M3.8", "M3.9", "M3.11", "M3.12", "M3.13")


@dataclass(frozen=True, slots=True)
class Entry:
    milestone: str
    path: str
    verbatim: bool
    sha256: str
    content: str
    line: int  # the line of the entry heading
    body_start: int = 0  # the first line of the block's content (0-based)
    body_end: int = 0  # the line of the closing fence (0-based)
    status_line: int = 0  # 0-based


class BookError(ValueError):
    pass


def parse(text: str) -> list[Entry]:
    entries: list[Entry] = []
    lines = text.split("\n")
    milestone = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        m = MILESTONE.match(line)
        if m:
            milestone = m.group(1)
            i += 1
            continue
        e = ENTRY.match(line)
        if not e:
            i += 1
            continue
        if not milestone:
            raise BookError(f"line {i + 1}: file entry outside a milestone section")
        path, start = e.group(1), i + 1
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        s = STATUS.match(lines[i]) if i < len(lines) else None
        if not s:
            raise BookError(f"line {start}: {path} has no status line with a SHA-256")
        status_line = i
        i += 1
        while i < len(lines) and not FENCE.match(lines[i]):
            if ENTRY.match(lines[i]) or MILESTONE.match(lines[i]):
                raise BookError(f"line {start}: {path} has no code block")
            i += 1
        if i >= len(lines):
            raise BookError(f"line {start}: {path} has no code block")
        fence = FENCE.match(lines[i])
        ticks = fence.group(1) if fence else "```"
        i += 1
        body_start = i
        body: list[str] = []
        while i < len(lines) and lines[i] != ticks:
            body.append(lines[i])
            i += 1
        if i >= len(lines):
            raise BookError(f"line {start}: the code block of {path} is not closed")
        body_end = i
        i += 1
        content = "\n".join(body) + "\n"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != s.group(2):
            raise BookError(f"line {start}: {path} does not match its SHA-256 (damaged code book)")
        entries.append(
            Entry(
                milestone,
                path,
                s.group(1) == "Verbatim",
                digest,
                content,
                start,
                body_start,
                body_end,
                status_line,
            )
        )
    paths = [x.path for x in entries]
    duplicates = sorted({p for p in paths if paths.count(p) > 1})
    if duplicates:
        raise BookError(f"files listed twice: {duplicates}")
    return entries


def select(entries: list[Entry], milestone: str | None) -> list[Entry]:
    if milestone is None:
        return entries
    chosen = [x for x in entries if x.milestone == milestone]
    if not chosen:
        raise BookError(f"no files for {milestone}")
    return chosen


def _safe(root: Path, path: str) -> Path:
    target = (root / path).resolve()
    if root.resolve() not in target.parents:
        raise BookError(f"{path} points outside the repository")
    return target


def preserves(path: str) -> bool:
    return path.startswith("detect/typologies/") and path.endswith(".yaml")


def merged(book: str, current: str) -> str:
    """`book` with the repository's own owner, status and approved_by lines; when anything else
    differs, only the owner line is kept, so the changed definition starts as a draft."""
    keep = {
        line.split(":", 1)[0]: line for line in current.split("\n") if line.startswith(PRESERVED)
    }
    if _masked(book) != _masked(current):
        keep = {k: v for k, v in keep.items() if k == "owner"}
    return "\n".join(
        keep.get(line.split(":", 1)[0], line) if line.startswith(PRESERVED) else line
        for line in book.split("\n")
    )


def _masked(text: str) -> str:
    return "\n".join(
        line.split(":", 1)[0] if line.startswith(PRESERVED) else line for line in text.split("\n")
    )


def extract(entries: list[Entry], root: Path, reference: Path | None) -> list[str]:
    written = []
    for x in entries:
        content = x.content
        if x.verbatim:
            target = _safe(root, x.path)
            if preserves(x.path) and target.exists():
                content = merged(content, target.read_text(encoding="utf-8"))
        elif reference is not None:
            target = reference / (x.path + ".reference")
        else:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(str(target))
    return written


def never_deviates(path: str) -> bool:
    return "/tests/" in f"/{path}" or path.startswith(NEVER_DEVIATE)


def deviations(path: Path) -> dict[str, dict[str, str]]:
    """The recorded mechanical deviations: path to `sha256`, `milestone` and `reason`."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, row in data.items():
        if never_deviates(name):
            raise BookError(f"{name} never deviates: change the code book instead (update)")
        if not row.get("reason") or not re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")):
            raise BookError(f"deviation {name} needs a reason and the file's SHA-256")
    return dict(data)


def check(
    entries: list[Entry], root: Path, recorded: dict[str, dict[str, str]] | None = None
) -> tuple[list[str], list[str]]:
    """(problems, accepted deviations)."""
    problems, accepted = [], []
    for x in entries:
        if not x.verbatim:
            continue
        target = _safe(root, x.path)
        if not target.exists():
            problems.append(f"missing: {x.path}")
            continue
        data = target.read_bytes()
        if preserves(x.path):
            same = _masked(data.decode("utf-8")) == _masked(x.content)
        else:
            same = data == x.content.encode("utf-8")
        if same:
            continue
        row = (recorded or {}).get(x.path)
        if row and row["sha256"] == hashlib.sha256(data).hexdigest():
            accepted.append(f"deviation: {x.path} ({row['reason']})")
        else:
            problems.append(f"differs: {x.path}")
    return problems, accepted


def update(text: str, entries: list[Entry], root: Path, paths: list[str]) -> str:
    """The code book with the blocks of `paths` replaced by the repository's files."""
    lines = text.split("\n")
    by_path = {x.path: x for x in entries}
    for path in sorted(paths, key=lambda p: -by_path[p].line if p in by_path else 0):
        x = by_path.get(path)
        if x is None:
            raise BookError(f"{path} is not in the code book")
        content = _safe(root, path).read_text(encoding="utf-8")
        if not content.endswith("\n") or lines[x.body_end] in content.split("\n"):
            raise BookError(f"{path} cannot go into its block as it is (fence or final newline)")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        lines[x.status_line] = re.sub(r"`[0-9a-f]{64}`", f"`{digest}`", lines[x.status_line])
        lines[x.body_start : x.body_end] = content[:-1].split("\n")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy or check the code book's verbatim files.")
    parser.add_argument("command", choices=["list", "extract", "check", "update"])
    parser.add_argument("--milestone")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--deviations", type=Path, default=DEFAULT_DEVIATIONS)
    parser.add_argument("--path", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        text = args.book.read_text(encoding="utf-8")
        if args.command == "update":
            if not args.path:
                raise BookError("update needs at least one --path")
            new = update(text, parse(text), args.root, args.path)
            parse(new)  # the new blocks must match their new SHA-256 lines
            args.book.write_text(new, encoding="utf-8", newline="\n")
            for path in args.path:
                print("updated", path)
            return 0
        if args.command == "check" and args.milestone in NO_CODE:
            print(f"{args.milestone} copies no file from the code book: 0 of 0 verbatim files")
            return 0
        entries = select(parse(text), args.milestone)
        if args.command == "list":
            for x in entries:
                kind = "verbatim " if x.verbatim else "reference"
                print(f"{x.milestone:7} {kind} {x.sha256[:12]} {x.path}")
            return 0
        if args.command == "extract":
            for path in extract(entries, args.root, args.reference):
                print("wrote", path)
            return 0
        problems, accepted = check(entries, args.root, deviations(args.root / args.deviations))
        for p in [*accepted, *problems]:
            print(p)
        verbatim = sum(1 for x in entries if x.verbatim)
        matching = verbatim - len(problems) - len(accepted)
        print(
            f"{matching} of {verbatim} verbatim files match the code book, "
            f"{len(accepted)} recorded deviations"
        )
        return 1 if problems else 0
    except BookError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

### `scripts/tests/test_spec_extract.py`

Verbatim. Python, 129 lines. SHA-256 `b37533f08a80179156501c0f19553abe2e0cdf6760e1a7c6304a4bc2881794d5`.

```python
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
```

### `.claude/rules/detect.md`

Verbatim. Markdown, 35 lines. SHA-256 `afc3e284d095544b6405bf160ebee3095764e6dd883159e0acc0f009535a3be4`.

```markdown
---
paths:
  - "detect/**"
  - "eval/**"
  - "cli/src/neonradar_cli/evaluate.py"
---

# Detection rules (PHASE-3.md 2.1, 2.10, 7.1, 7.5, 7.6)

- Verbatim files come from `docs/build/PHASE-3-CODE.md` with `scripts/spec_extract.py`; never
  retype one, and never edit a verbatim test, `eval/baselines/ci.json` or `eval/freeze.json`
  to make a check pass. A failing verbatim test is a stop-and-ask case. A mechanical deviation
  goes into `docs/build/phase-3-deviations.json`; an accepted change goes into the code book
  with `spec_extract update` in the same pull request (2.10).
- Detectors see the graph only through the `Source` protocol (`source.py`). Every Cypher
  statement lives in `detect/src/neonradar_detect/queries/<method>.cypher`, is bounded,
  parameterised, ordered by C2 ids before any `LIMIT`, and passes `make cypher-lint`.
- A change to a query file or to `neo4jsource.py` needs the same change in `memsource.py`
  (the oracle), and `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration"`.
- R-REAL (G12) is applied by the runner on every instance: never emit a payment-based alert
  that involves a non-synthetic entity, or any alert that names a non-synthetic person (a
  `:LegalEntity` that is not an `:Organization`) as a subject or in its evidence.
- Registry relationships count only while current: no end date, or one after the end of the
  window (`LinkRow.current`).
- Alert text describes the shape and its numbers; it never names the conduct a typology is
  named after. `wording.render` lints every text it renders and raises on a match (7.5.2).
- GDS: `stream` only, concurrency 4, projections dropped in `finally`; no `graphdatascience`.
- Evaluation: the agent never runs `neonradar eval run --split test`, never chooses holdout
  seeds and never opens a holdout world (G11). Development figures are called development
  figures.
- A detector change that moves a count in `eval/baselines/ci.json` is an accepted change, not
  a fix to make a check pass: it needs a typology researcher's approval, updates the file and
  its code book block (`spec_extract update`) in the same pull request, for the typologies the
  milestone names only, and explains each change; after the freeze it also needs
  `freeze-change` (M3.11).
```

### `.claude/rules/synth.md`

Verbatim. Markdown, 26 lines. SHA-256 `d30bd8bd974d69227de808503b36893f1b272180fdc0f20aa527977f321dc72c`.

```markdown
---
paths:
  - "ingest/src/neonradar_ingest/synth/**"
  - "ingest/profiles/synth-*.yaml"
---

# Generator rules (PHASE-3.md 2.1, 7.2)

- Scenarios and look-alikes work only through `ScenarioCtx`, which refuses any id the scenario
  did not create: no scenario ever touches a base entity (G1).
- The only record that may name a base entity is the account holding of an eligible base
  organisation, plus the payer or beneficiary field of a payment on that account (I15, I16).
  People from a base never get an account or a payment.
- Every random draw comes from a named stream (`streams.stream(seed, *keys)`); names draw from
  their own streams, so a different name source changes names only. Never iterate a set into
  an output; sort.
- Same seed, same base, same code: same bytes. `test_synth_v1.py` checks it; never relax it.
- Labels never enter records or the graph (C1 R9): no record names a scenario, a typology, a
  role or a look-alike, not even in an id.
- People on synthetic lists, PEP personas and their relatives and associates get invented
  surnames (`NameSource.invented_person`); never put a realistic full name on a synthetic list.
- A holdout seed (split `test`) is generated only by `neonradar eval run --split test`, which a
  human runs; never generate one, and never read `data/cache/holdout/` (G11).
- The generator never imports `neonradar_detect`, and the detectors never import the
  generator (PHASE-3.md 4.1).
- Payments are kept as their C1 lines (`Ctx.payments`); read one with `Ctx.record(id)`.
```

## M3.1 C2 1.2.0: overlays, bridge invariants and detection runs

The three invariants of C2 1.2.0 (5.2). 1 verbatim file (PHASE-3.md M3.1).

### `graph/src/neonradar_graph/queries/verify_overlay.cypher`

Verbatim. Cypher, 25 lines. SHA-256 `996d1af7b70391131875d593ee6b79844ddfa126c2d84a52f961b165cd845ee0`.

```cypher
// I15: the only relationship between a synthetic and a non-synthetic node is HOLDS_ACCOUNT from a
// non-synthetic organisation to a synthetic account (C2 1.2.0; support nodes have no synthetic
// property, so FLAGS, PRODUCED and RESOLVED_TO never count)
MATCH (a)-[r]->(b)
WHERE a.synthetic <> b.synthetic
  AND NOT (type(r) = 'HOLDS_ACCOUNT' AND a.synthetic = false AND a:Organization AND b:Account)
RETURN count(r) AS violations;
// I16: no payment joins two accounts that are both held by non-synthetic entities
MATCH (h1:LegalEntity)-[:HOLDS_ACCOUNT]->(:Account)-[p:PAID]-(:Account)<-[:HOLDS_ACCOUNT]-(h2:LegalEntity)
WHERE NOT h1:Synthetic AND NOT h2:Synthetic
RETURN count(DISTINCT p) AS violations;
// I17: no alert names a non-synthetic person (a :LegalEntity that is not an :Organization) as a
// subject or among its evidence nodes, and no alert that involves a non-synthetic entity has a
// payment among its evidence relationships (R-REAL, G12; :Alert.evidence_node_ids and
// :Alert.evidence_edge_ids, C2 1.2.0)
MATCH (a:Alert)
WHERE EXISTS { (a)-[:FLAGS]->(p:LegalEntity) WHERE NOT p:Organization AND p.synthetic = false }
   OR EXISTS {
        MATCH (p:Entity)
        WHERE p.id IN coalesce(a.evidence_node_ids, [])
          AND p:LegalEntity AND NOT p:Organization AND p.synthetic = false
      }
   OR (a.involves_real_entities = true
       AND EXISTS { MATCH ()-[x:PAID]->() WHERE x.id IN coalesce(a.evidence_edge_ids, []) })
RETURN count(a) AS violations;
```

## M3.2 Detection core and `circular_flow` 0.2.0

The detection core, the 33 query files, the `circular_flow` detector, its typology file and the tests; five reference files for the adapters M3.2 writes. 52 verbatim files and 5 reference files (PHASE-3.md M3.2).

### `detect/src/neonradar_detect/model.py`

Verbatim. Python, 90 lines. SHA-256 `a0a45035ec935f10f3f02b770ab8f252fd9ecc62e69c4dae87eb0ad0dbf5945e`.

```python
"""What a detector returns before it becomes a C4 alert (PHASE-3.md 7.1.1).

A `Finding` holds ids, metrics and the order of the explanation steps, never text: the alert builder
renders the text from the typology's templates (`wording.py`), so every sentence passes the
wording lint in one place.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Subject:
    entity_id: str
    role: str


@dataclass(frozen=True, slots=True)
class Finding:
    typology: str
    variant: str
    anchor: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    subjects: tuple[Subject, ...]
    metrics: Mapping[str, Any]
    pattern_strength: float
    steps: tuple[tuple[str, ...], ...]
    window: tuple[datetime, datetime] | None = None
    activity: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if list(self.node_ids) != sorted(set(self.node_ids)):
            raise ValueError("node_ids must be sorted and unique")
        if list(self.edge_ids) != sorted(set(self.edge_ids)):
            raise ValueError("edge_ids must be sorted and unique")
        if not 0.0 <= self.pattern_strength <= 1.0:
            raise ValueError("pattern_strength must lie in [0, 1]")
        edges = set(self.edge_ids)
        if any(e not in edges for step in self.steps for e in step):
            raise ValueError("every step edge must be an evidence edge")
        if self.anchor not in set(self.node_ids):
            raise ValueError("the anchor must be an evidence node")
        if not self.subjects:
            raise ValueError("a finding needs at least one subject")


@dataclass(frozen=True, slots=True)
class NodeInfo:
    """What the alert builder and the policy need to know about one node."""

    id: str
    labels: frozenset[str]
    caption: str
    synthetic: bool
    datasets: tuple[str, ...]
    holders: tuple[str, ...] = ()


def clip01(value: float) -> float:
    """Clip to [0, 1] and round to 4 decimals, the form every pattern strength takes."""
    return round(min(1.0, max(0.0, value)), 4)


@dataclass(frozen=True, slots=True)
class EdgeInfo:
    """What the alert builder and the policy need to know about one evidence relationship."""

    id: str
    type: str
    source: str
    target: str
    synthetic: bool
    amount: float | None = None
    currency: str = ""
    ts: datetime | None = None
    channel: str = ""
    share_min: float | None = None
    share_max: float | None = None
    share_min_exclusive: bool = False
    share_max_exclusive: bool = False
    role: str = ""
    control_type: str = ""
    start_date: str = ""
    end_date: str = ""
```

### `detect/src/neonradar_detect/rows.py`

Verbatim. Python, 206 lines. SHA-256 `b4c2c1814889c6e1ba6bd96754b862d9099bf6317bc4751266d3cbb5620367cc`.

```python
"""Typed rows that candidate steps return (PHASE-3.md 7.1.2).

Each `Source` method (source.py) returns these, sorted as documented, whether it ran a query file
on Neo4j (`neo4jsource.py`) or the reference code on a `MemGraph` (`memsource.py`). The parity
test compares the two implementations row for row, so every field is a plain value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, order=True)
class Pay:
    """One PAID relationship seen from an account: `counterparty` is the other account."""

    ts: datetime
    edge_id: str
    counterparty: str
    amount: float
    currency: str
    channel: str


@dataclass(frozen=True, slots=True)
class Hop:
    edge_id: str
    source: str
    target: str
    ts: datetime
    amount: float
    currency: str
    source_holders: tuple[str, ...]
    target_holders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccountFlows:
    """An account with its payments in a period, for the flow typologies."""

    account: str
    holders: tuple[str, ...]
    inflows: tuple[Pay, ...]
    outflows: tuple[Pay, ...]


@dataclass(frozen=True, slots=True)
class CounterpartyInfo:
    account: str
    opening_date: str
    holder_labels: tuple[str, ...]
    holders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccountHistory:
    """Every payment of one account up to the end of the period, for dormancy."""

    account: str
    opening_date: str
    holders: tuple[str, ...]
    payments: tuple[tuple[Pay, str], ...]  # (payment, "in" or "out"), in time order


@dataclass(frozen=True, slots=True)
class LinkRow:
    """A registry relationship: type, id, ends and the C2 properties a detector reads."""

    rel_type: str
    rel_id: str
    source: str
    target: str
    share_min: float | None = None
    share_max: float | None = None
    share_min_exclusive: bool = False
    share_max_exclusive: bool = False
    is_nominee: bool = False
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    control_type: str = ""

    def current(self, as_of: str) -> bool:
        """Whether the relationship still holds on `as_of` (an ISO date): no end date, or one
        after it. Partial dates compare as text, so "2026" counts as ended by "2026-07-01"."""
        return not (self.end_date and self.end_date <= as_of)


@dataclass(frozen=True, slots=True)
class EntityRow:
    id: str
    labels: tuple[str, ...]
    schema: str
    jurisdiction: str
    incorporation_date: str
    synthetic: bool
    accounts_category: str = ""
    sector: str = ""
    status: str = ""
    dissolution_date: str = ""
    datasets: tuple[str, ...] = ()
    psc_statements: tuple[str, ...] = ()
    full: str = ""  # addresses only
    postal_code: str = ""  # addresses only
    city: str = ""  # addresses only
    countries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, order=True)
class Deposit:
    """A cash deposit into one of a holder's accounts; `branch` is the paying cash ledger."""

    ts: datetime
    edge_id: str
    account: str
    branch: str
    amount: float
    currency: str


@dataclass(frozen=True, slots=True)
class HolderDeposits:
    holder: str
    deposits: tuple[Deposit, ...]


@dataclass(frozen=True, slots=True, order=True)
class PaidEdge:
    ts: datetime
    edge_id: str
    source: str
    target: str
    amount: float
    currency: str
    channel: str


@dataclass(frozen=True, slots=True)
class Component:
    """A weakly connected component of a projected payment graph: accounts and their PAID edges."""

    accounts: tuple[str, ...]
    edges: tuple[PaidEdge, ...]


@dataclass(frozen=True, slots=True)
class OwnershipPath:
    """OWNS relationships in order from the first node to the last: nodes[i] owns nodes[i + 1]."""

    nodes: tuple[str, ...]
    links: tuple[LinkRow, ...]


@dataclass(frozen=True, slots=True)
class AddressCluster:
    address: str
    full: str
    postal_code: str
    members: tuple[tuple[str, str], ...]  # (organisation id, HAS_ADDRESS relationship id), by id


@dataclass(frozen=True, slots=True)
class SanctionRow:
    """A :Sanction node an entity is SUBJECT_OF (C2; `provisions` is new in C2 1.2.0)."""

    id: str
    datasets: tuple[str, ...]
    authority: str
    program: str
    provisions: tuple[str, ...]
    start_date: str
    end_date: str


@dataclass(frozen=True, slots=True)
class ListedRow:
    """A :Sanctioned entity with its own datasets and its designations, by sanction id."""

    entity: str
    labels: tuple[str, ...]
    datasets: tuple[str, ...]
    sanctions: tuple[SanctionRow, ...]


@dataclass(frozen=True, slots=True)
class Hub:
    """A node with many relationships of one type (REPRESENTS or DIRECTOR_OF) to organisations."""

    hub: str
    links: tuple[LinkRow, ...]  # by relationship id


@dataclass(frozen=True, slots=True)
class CashProfile:
    """One company's cash deposits in a currency: the window and the period before it, in pence."""

    holder: str
    sector: str
    postal_code: str  # of the registered address ("" when none)
    city: str
    accounts: tuple[str, ...]
    window_pence: int
    window_deposits: int
    prior_pence: int
    prior_deposits: int
```

### `detect/src/neonradar_detect/source.py`

Verbatim. Python, 165 lines. SHA-256 `ca65f9b8aec4ad328009c2ba800e13fc40705e67da0b3a5b5d2f07c7f83efe04`.

```python
"""The candidate steps every detector may use (PHASE-3.md 7.1.2).

A detector never talks to Neo4j directly. It calls methods of a `Source`: `Neo4jSource` runs the
query file of the same name in `queries/`, `MemSource` runs the reference code on a `MemGraph`.
Both return the typed rows of `rows.py` in the documented order, so detector logic is plain
Python that unit tests run without a database, and the parity test proves the two sources agree.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from neonradar_detect.expand import FrontierItem
from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.rows import (
    AccountFlows,
    AccountHistory,
    AddressCluster,
    CashProfile,
    Component,
    CounterpartyInfo,
    EntityRow,
    HolderDeposits,
    Hop,
    Hub,
    LinkRow,
    ListedRow,
    OwnershipPath,
    Pay,
)


@dataclass(frozen=True, slots=True)
class Window:
    """The detection period: payments with start <= ts < end."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("window bounds must be timezone-aware (UTC)")
        if not self.start < self.end:
            raise ValueError("window start must be before its end")


@dataclass(slots=True)
class DetectorOutput:
    findings: list[Finding]
    stats: dict[str, int] = field(default_factory=dict)


class Source(Protocol):
    def paid_time_range(self) -> tuple[datetime, datetime] | None: ...

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]: ...

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]: ...

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]: ...

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]: ...

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]: ...

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]: ...

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]: ...

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]: ...

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]: ...

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]: ...

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]: ...

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]: ...

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]: ...

    def quiet_account_histories(
        self,
        min_gap_days: int,
        max_quiet_payments: int,
        max_quiet_amount: float,
        history_start: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[AccountHistory]: ...

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]: ...

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]: ...

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]: ...

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]: ...

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]: ...

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]: ...

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]: ...

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]: ...

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]: ...

    def registered_count_quantile(self, q: float, active_only: bool) -> int: ...

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]: ...

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]: ...

    def listed_entities(self) -> list[ListedRow]: ...

    def flagged_ids(self, flag: str) -> list[str]: ...
```

### `detect/src/neonradar_detect/expand.py`

Verbatim. Python, 137 lines. SHA-256 `daa672651b49203d4e2d13f6ffa6cd961b60c0853a5ef367738e290f35397eb3`.

```python
"""Time-respecting path expansion over PAID, one hop at a time (PHASE-3.md 7.1.3).

Path typologies (`circular_flow`, `layering_chain`) never ask Neo4j for every path of length 2 to
6 at once: on a payment graph each account pays many others, and a quantified path pattern whose
conditions sit in a later WHERE clause enumerates every path before it filters (3.2). Instead the
detector keeps a frontier of partial paths and asks the source for the next hop of all of them in
one call (`Source.paid_hop`, query `paid_hop.cypher`), with the time, amount and currency
conditions inside the hop query. The order of every result is fixed, so the paths found do not
depend on the source.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from neonradar_detect.rows import Hop


@dataclass(frozen=True, slots=True)
class FrontierItem:
    """One partial path waiting for its next hop; `paid_hop` receives these as maps."""

    key: int
    account: str
    after: datetime
    until: datetime
    min_amount: float
    max_amount: float
    currency: str
    visited: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Path:
    hops: tuple[Hop, ...]

    @property
    def accounts(self) -> tuple[str, ...]:
        return (self.hops[0].source, *(h.target for h in self.hops))

    @property
    def first(self) -> Hop:
        return self.hops[0]

    @property
    def last(self) -> Hop:
        return self.hops[-1]


@dataclass(frozen=True, slots=True)
class ExpansionStats:
    partial_paths: int
    truncated: int


HopFn = Callable[[Sequence[FrontierItem]], dict[int, list[Hop]]]


def expand(
    starts: Sequence[Hop],
    hop: HopFn,
    *,
    extend: Callable[[Path, int], FrontierItem | None],
    keep: Callable[[Path, Hop], bool],
    accept: Callable[[Path], bool],
    max_hops: int,
    max_branching: int,
    max_frontier: int,
    chunk: int = 10_000,
) -> tuple[list[Path], ExpansionStats]:
    """Every path that `extend`, `keep` and `accept` allow, breadth first from each start hop.

    `extend(path, key)` gives the frontier item for the next hop of `path`, or None to stop it;
    `keep(path, hop)` filters the hops the source returned (conditions a query cannot express,
    such as holder overlaps); `accept(path)` says whether a path is a result. Starts are expanded
    `chunk` at a time (in time order), so the frontier stays bounded however many starts there
    are. Per partial path at most `max_branching` next hops are kept (earliest first, then by edge
    id), and per level of a chunk at most `max_frontier` partial paths (in path order); whatever
    is cut is counted in `truncated`, which the run summary reports.
    """
    ordered = sorted(starts, key=lambda h: (h.ts, h.edge_id))
    results: list[Path] = []
    partial = truncated = 0
    for i in range(0, len(ordered), chunk):
        found, stats = _expand_chunk(
            ordered[i : i + chunk], hop, extend, keep, accept, max_hops, max_branching, max_frontier
        )
        results.extend(found)
        partial += stats.partial_paths
        truncated += stats.truncated
    return results, ExpansionStats(partial, truncated)


def _expand_chunk(
    starts: Sequence[Hop],
    hop: HopFn,
    extend: Callable[[Path, int], FrontierItem | None],
    keep: Callable[[Path, Hop], bool],
    accept: Callable[[Path], bool],
    max_hops: int,
    max_branching: int,
    max_frontier: int,
) -> tuple[list[Path], ExpansionStats]:
    level = [Path((s,)) for s in starts]
    results = [p for p in level if accept(p)]
    partial = len(level)
    truncated = 0
    for _ in range(1, max_hops):
        if not level:
            break
        if len(level) > max_frontier:
            truncated += len(level) - max_frontier
            level = level[:max_frontier]
        frontier: list[FrontierItem] = []
        by_key: dict[int, Path] = {}
        for key, path in enumerate(level):
            item = extend(path, key)
            if item is not None:
                frontier.append(item)
                by_key[key] = path
        nexts = hop(frontier) if frontier else {}
        level = []
        for key in sorted(nexts):
            path = by_key[key]
            hops = [h for h in nexts[key] if keep(path, h)]
            if len(hops) > max_branching:
                truncated += len(hops) - max_branching
                hops = hops[:max_branching]
            for h in hops:
                grown = Path((*path.hops, h))
                if accept(grown):
                    results.append(grown)
                level.append(grown)
        partial += len(level)
    return results, ExpansionStats(partial, truncated)
```

### `detect/src/neonradar_detect/memgraph.py`

Verbatim. Python, 139 lines. SHA-256 `7a55ff935b11110e6480067027746c2f6e5a025815db735e004a6a6457997beb`.

```python
"""In-memory property graph with the C2 labels, types and properties (PHASE-3.md 7.1.2).

Every detector has a reference candidate step that runs on this graph. Unit tests use it, so they
need no database, and the parity test (M3.2) compares it with the Cypher candidate step on the same
records loaded into Neo4j. Nodes and relationships carry exactly the C2 properties, and every
listing is in id order, so results never depend on insertion order.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    labels: frozenset[str]
    props: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    @property
    def synthetic(self) -> bool:
        return bool(self.props.get("synthetic", False))


@dataclass(frozen=True, slots=True)
class Rel:
    id: str
    type: str
    source: str
    target: str
    props: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    @property
    def synthetic(self) -> bool:
        return bool(self.props.get("synthetic", False))


class MemGraph:
    """Nodes by id, relationships by id, adjacency by (node, type)."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._rels: dict[str, Rel] = {}
        self._out: dict[tuple[str, str], list[Rel]] = defaultdict(list)
        self._in: dict[tuple[str, str], list[Rel]] = defaultdict(list)
        self._by_label: dict[str, list[str]] = defaultdict(list)
        self._by_type: dict[str, list[str]] = defaultdict(list)
        self._dirty = False

    def add_node(self, node_id: str, labels: Iterable[str], props: Mapping[str, Any]) -> None:
        if node_id in self._nodes:
            raise ValueError(f"duplicate node id {node_id}")
        node = Node(node_id, frozenset(labels), dict(props, id=node_id))
        self._nodes[node_id] = node
        for label in node.labels:
            self._by_label[label].append(node_id)
        self._dirty = True

    def add_rel(
        self, rel_id: str, rel_type: str, source: str, target: str, props: Mapping[str, Any]
    ) -> None:
        if rel_id in self._rels:
            raise ValueError(f"duplicate relationship id {rel_id}")
        if source not in self._nodes or target not in self._nodes:
            raise KeyError(f"relationship {rel_id} has an end that is not a node")
        rel = Rel(rel_id, rel_type, source, target, dict(props, id=rel_id))
        self._rels[rel_id] = rel
        self._out[(source, rel_type)].append(rel)
        self._in[(target, rel_type)].append(rel)
        self._by_type[rel_type].append(rel_id)
        self._dirty = True

    def _sort(self) -> None:
        if not self._dirty:
            return
        for ids in self._by_label.values():
            ids.sort()
        for ids in self._by_type.values():
            ids.sort()
        for rels in self._out.values():
            rels.sort(key=lambda r: r.id)
        for rels in self._in.values():
            rels.sort(key=lambda r: r.id)
        self._dirty = False

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def rel(self, rel_id: str) -> Rel:
        return self._rels[rel_id]

    def nodes(self, label: str | None = None) -> list[Node]:
        self._sort()
        if label is None:
            return [self._nodes[i] for i in sorted(self._nodes)]
        return [self._nodes[i] for i in self._by_label.get(label, [])]

    def rels(self, rel_type: str) -> list[Rel]:
        self._sort()
        return [self._rels[i] for i in self._by_type.get(rel_type, [])]

    def out_rels(self, node_id: str, *types: str) -> list[Rel]:
        self._sort()
        found = [r for t in types for r in self._out.get((node_id, t), [])]
        return sorted(found, key=lambda r: r.id) if len(types) > 1 else found

    def in_rels(self, node_id: str, *types: str) -> list[Rel]:
        self._sort()
        found = [r for t in types for r in self._in.get((node_id, t), [])]
        return sorted(found, key=lambda r: r.id) if len(types) > 1 else found

    def holders(self, account_id: str) -> list[Node]:
        """The sources of HOLDS_ACCOUNT into an account, in id order."""
        return sorted(
            (self._nodes[r.source] for r in self.in_rels(account_id, "HOLDS_ACCOUNT")),
            key=lambda n: n.id,
        )

    def accounts(self, holder_id: str) -> list[Node]:
        """The accounts a legal entity holds, in id order."""
        return sorted(
            (self._nodes[r.target] for r in self.out_rels(holder_id, "HOLDS_ACCOUNT")),
            key=lambda n: n.id,
        )

    def counts(self) -> dict[str, int]:
        return {"nodes": len(self._nodes), "relationships": len(self._rels)}
```

### `detect/src/neonradar_detect/memsource.py`

Verbatim. Python, 795 lines. SHA-256 `91d5466577a08f0b8e708a896f7aabcce8b7eb4e20c7dcfa2cec54c4b05d3fdc`.

```python
"""Reference candidate steps on a MemGraph (PHASE-3.md 7.1.2).

`MemSource` implements every method of `Source` in plain Python. It is the oracle: each method
returns what its query file in `queries/` must return on the same graph, in the same order. The
detector tests run on both sources and the world parity test compares them on a generated world
(PHASE-3.md 7.1.5).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

from neonradar_detect.expand import FrontierItem
from neonradar_detect.memgraph import MemGraph, Rel
from neonradar_detect.model import EdgeInfo, NodeInfo
from neonradar_detect.rows import (
    AccountFlows,
    AccountHistory,
    AddressCluster,
    CashProfile,
    Component,
    CounterpartyInfo,
    Deposit,
    EntityRow,
    HolderDeposits,
    Hop,
    Hub,
    LinkRow,
    ListedRow,
    OwnershipPath,
    PaidEdge,
    Pay,
    SanctionRow,
)

INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})
REGISTRY_TYPES = ("OWNS", "CONTROLS", "DIRECTOR_OF", "REPRESENTS", "FAMILY_OF", "ASSOCIATE_OF")


def _pay(rel: Rel, counterparty: str) -> Pay:
    return Pay(
        rel.props["ts"],
        rel.id,
        counterparty,
        float(rel.props["amount"]),
        rel.props["currency"],
        rel.props.get("channel") or "",
    )


def _current(rel: Rel, as_of: str) -> bool:
    end = rel.props.get("end_date") or ""
    return not (end and end <= as_of)


def _link(rel: Rel) -> LinkRow:
    p = rel.props
    return LinkRow(
        rel.type,
        rel.id,
        rel.source,
        rel.target,
        p.get("share_pct_min"),
        p.get("share_pct_max"),
        bool(p.get("share_min_exclusive", False)),
        bool(p.get("share_max_exclusive", False)),
        bool(p.get("is_nominee", False)),
        p.get("role") or p.get("relationship") or "",
        p.get("start_date") or "",
        p.get("end_date") or "",
        p.get("control_type") or "",
    )


class MemSource:
    def __init__(self, graph: MemGraph) -> None:
        self.graph = graph

    # helpers ---------------------------------------------------------------------------------

    def _ledger(self, account: str) -> bool:
        """A bank's cash ledger (C1 `account_kind` cash_ledger): the counterparty of cash deposits
        and withdrawals, never a candidate account and never a hop of a path."""
        return bool(self.graph.node(account).get("account_kind") == "cash_ledger")

    def _holders(self, account: str) -> tuple[str, ...]:
        return tuple(n.id for n in self.graph.holders(account))

    def _entity_row(self, node_id: str) -> EntityRow:
        n = self.graph.node(node_id)
        return EntityRow(
            n.id,
            tuple(sorted(n.labels)),
            n.get("schema", ""),
            n.get("jurisdiction") or "",
            n.get("incorporation_date") or "",
            n.synthetic,
            n.get("accounts_category") or "",
            n.get("sector") or "",
            n.get("status") or "",
            n.get("dissolution_date") or "",
            tuple(n.get("datasets", ())),
            tuple(n.get("psc_statements", ())),
            n.get("full") or "",
            n.get("postal_code") or "",
            n.get("city") or "",
            tuple(n.get("countries", ())),
        )

    # common ----------------------------------------------------------------------------------

    def paid_time_range(self) -> tuple[datetime, datetime] | None:
        times = [r.props["ts"] for r in self.graph.rels("PAID")]
        return (min(times), max(times)) if times else None

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]:
        """Evidence nodes and the holders of evidence accounts, with what the policy needs."""
        out: dict[str, NodeInfo] = {}
        wanted = sorted(set(ids))
        for node_id in wanted:
            n = self.graph.node(node_id)
            holders = self._holders(node_id) if "Account" in n.labels else ()
            out[node_id] = NodeInfo(
                n.id,
                n.labels,
                n.get("caption", n.id),
                n.synthetic,
                tuple(n.get("datasets", ())),
                holders,
            )
            for h in holders:
                if h not in out:
                    hn = self.graph.node(h)
                    out[h] = NodeInfo(
                        hn.id,
                        hn.labels,
                        hn.get("caption", hn.id),
                        hn.synthetic,
                        tuple(hn.get("datasets", ())),
                        (),
                    )
        return out

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]:
        """The evidence relationships with their ends and the properties the wording uses."""
        out = {}
        for rel_id in sorted(set(ids)):
            r = self.graph.rel(rel_id)
            q = r.props
            out[rel_id] = EdgeInfo(
                r.id,
                r.type,
                r.source,
                r.target,
                r.synthetic,
                float(q["amount"]) if q.get("amount") is not None else None,
                q.get("currency") or "",
                q.get("ts"),
                q.get("channel") or "",
                q.get("share_pct_min"),
                q.get("share_pct_max"),
                bool(q.get("share_min_exclusive", False)),
                bool(q.get("share_max_exclusive", False)),
                q.get("role") or q.get("relationship") or "",
                q.get("control_type") or "",
                q.get("start_date") or "",
                q.get("end_date") or "",
            )
        return out

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]:
        hops = []
        for rel in self.graph.rels("PAID"):
            ts = rel.props["ts"]
            if self._ledger(rel.source) or self._ledger(rel.target):
                continue
            if float(rel.props["amount"]) >= min_amount and start <= ts < end:
                hops.append(
                    Hop(
                        rel.id,
                        rel.source,
                        rel.target,
                        ts,
                        float(rel.props["amount"]),
                        rel.props["currency"],
                        self._holders(rel.source),
                        self._holders(rel.target),
                    )
                )
        hops.sort(key=lambda h: (h.ts, h.edge_id))
        return hops[:limit]

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]:
        found: dict[int, list[Hop]] = {}
        for item in frontier:
            hops = []
            for rel in self.graph.out_rels(item.account, "PAID"):
                ts = rel.props["ts"]
                amount = float(rel.props["amount"])
                if not (item.after < ts <= item.until):
                    continue
                if not (item.min_amount <= amount <= item.max_amount):
                    continue
                if (
                    rel.props["currency"] != item.currency
                    or rel.target in item.visited
                    or self._ledger(rel.target)
                ):
                    continue
                hops.append(
                    Hop(
                        rel.id,
                        rel.source,
                        rel.target,
                        ts,
                        amount,
                        rel.props["currency"],
                        (),
                        self._holders(rel.target),
                    )
                )
            hops.sort(key=lambda h: (h.ts, h.edge_id))
            if hops:
                found[item.key] = hops
        return found

    # flow typologies -------------------------------------------------------------------------

    def _flows(self, account: str, start: datetime, end: datetime) -> AccountFlows:
        ins = sorted(
            _pay(r, r.source)
            for r in self.graph.in_rels(account, "PAID")
            if start <= r.props["ts"] < end
        )
        outs = sorted(
            _pay(r, r.target)
            for r in self.graph.out_rels(account, "PAID")
            if start <= r.props["ts"] < end
        )
        return AccountFlows(account, self._holders(account), tuple(ins), tuple(outs))

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        """Accounts other than cash ledgers with at least `min_inbound_counterparties` distinct
        paying accounts in one bucket of `bucket_hours` (buckets counted from `start`; payments of
        `channel` only, when given), with every payment in and out in [start, end), by account id.
        A window of `bucket_hours` with 2k payers puts k of them in one bucket, so a detector asks
        for half its threshold and loses nothing."""
        out = []
        width = bucket_hours * 3600
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            buckets: dict[int, set[str]] = defaultdict(set)
            for r in self.graph.in_rels(acct.id, "PAID"):
                ts = r.props["ts"]
                if start <= ts < end and (channel is None or r.props.get("channel") == channel):
                    buckets[int((ts - start).total_seconds() // width)].add(r.source)
            if any(len(v) >= min_inbound_counterparties for v in buckets.values()):
                out.append(self._flows(acct.id, start, end))
        return out[:limit]

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        """As `flows_by_inbound`, counting distinct payees."""
        out = []
        width = bucket_hours * 3600
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            buckets: dict[int, set[str]] = defaultdict(set)
            for r in self.graph.out_rels(acct.id, "PAID"):
                ts = r.props["ts"]
                if start <= ts < end:
                    buckets[int((ts - start).total_seconds() // width)].add(r.target)
            if any(len(v) >= min_outbound_counterparties for v in buckets.values()):
                out.append(self._flows(acct.id, start, end))
        return out[:limit]

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]:
        out = {}
        for a in sorted(set(accounts)):
            n = self.graph.node(a)
            holders = self.graph.holders(a)
            labels = sorted({lab for h in holders for lab in h.labels})
            out[a] = CounterpartyInfo(
                a, n.get("opening_date") or "", tuple(labels), tuple(h.id for h in holders)
            )
        return out

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]:
        """For each (payer account, payee account), the times of every PAID between them, sorted;
        pairs with no payment are left out."""
        out = {}
        for a, b in sorted(set(pairs)):
            times = sorted(r.props["ts"] for r in self.graph.out_rels(a, "PAID") if r.target == b)
            if times:
                out[(a, b)] = tuple(times)
        return out

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        out = {}
        for a in sorted(set(accounts)):
            pays = sorted(
                _pay(r, r.target)
                for r in self.graph.out_rels(a, "PAID")
                if start <= r.props["ts"] < end
            )
            if pays:
                out[a] = pays
        return out

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        """Each account's incoming payments in [start, end), in order of (ts, id)."""
        out: dict[str, list[Pay]] = {}
        for a in sorted(set(accounts)):
            pays = [
                _pay(r, r.source)
                for r in self.graph.in_rels(a, "PAID")
                if start <= r.props["ts"] < end
            ]
            if pays:
                out[a] = sorted(pays)
        return out

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]:
        """(edge id, payer account, payee account) for PAID between two of `accounts` in the
        period, by edge id."""
        wanted = set(accounts)
        rows = []
        for a in sorted(wanted):
            for r in self.graph.out_rels(a, "PAID"):
                if r.target in wanted and start <= r.props["ts"] < end:
                    rows.append((r.id, r.source, r.target))
        return sorted(rows)

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]:
        """Number of PAID relationships into or out of each account in the period."""
        out = {}
        for a in sorted(set(accounts)):
            n = sum(1 for r in self.graph.in_rels(a, "PAID") if start <= r.props["ts"] < end)
            n += sum(1 for r in self.graph.out_rels(a, "PAID") if start <= r.props["ts"] < end)
            out[a] = n
        return out

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]:
        """Holders whose accounts received at least `min_in_band` cash deposits of band_low to
        threshold (both included: the detector applies each currency's edge) in the period, with
        every cash deposit of the period into any of their accounts, in time order. By holder id."""
        out = []
        for holder in self.graph.nodes("LegalEntity"):
            deposits = []
            for acct in self.graph.accounts(holder.id):
                for r in self.graph.in_rels(acct.id, "PAID"):
                    if r.props.get("channel") == "cash_deposit" and start <= r.props["ts"] < end:
                        deposits.append(
                            Deposit(
                                r.props["ts"],
                                r.id,
                                acct.id,
                                r.source,
                                float(r.props["amount"]),
                                r.props["currency"],
                            )
                        )
            if sum(1 for d in deposits if band_low <= d.amount <= threshold) >= min_in_band:
                out.append(HolderDeposits(holder.id, tuple(sorted(deposits))))
        return out[:limit]

    def quiet_account_histories(
        self,
        min_gap_days: int,
        max_quiet_payments: int,
        max_quiet_amount: float,
        history_start: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[AccountHistory]:
        """Accounts with a quiet period that ends with a payment in [start, end): at least
        `min_gap_days` from a payment, or from the opening date when that is on or after
        `history_start` (the date of the first payment in the data, so the account's whole life is
        loaded), to that payment, with at most `max_quiet_payments` payments between them totalling
        at most `max_quiet_amount`. Each with every payment of the account before `end`, in order
        of (ts, id); accounts by id."""
        out = []
        gap = timedelta(days=min_gap_days)
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            pays: list[tuple[Pay, str]] = []
            for r in self.graph.in_rels(acct.id, "PAID"):
                if r.props["ts"] < end:
                    pays.append((_pay(r, r.source), "in"))
            for r in self.graph.out_rels(acct.id, "PAID"):
                if r.props["ts"] < end:
                    pays.append((_pay(r, r.target), "out"))
            if not pays:
                continue
            pays.sort(key=lambda x: (x[0].ts, x[0].edge_id))
            ts = [x.ts for x, _ in pays]
            amt = [x.amount for x, _ in pays]
            opening = acct.get("opening_date") or ""
            opened = None
            if len(opening) == 10 and opening >= history_start:
                opened = datetime.fromisoformat(opening).replace(tzinfo=ts[0].tzinfo)
            found = False
            for j in range(len(pays)):
                if not start <= ts[j] < end:
                    continue
                for m in range(max_quiet_payments + 1):
                    k = j - m - 1
                    if k < 0:
                        break
                    if ts[j] - ts[k] >= gap and sum(amt[k + 1 : j]) <= max_quiet_amount:
                        found = True
                        break
                if (
                    not found
                    and opened is not None
                    and j <= max_quiet_payments
                    and sum(amt[:j]) <= max_quiet_amount
                    and ts[j] - opened >= gap
                ):
                    found = True
                if found:
                    break
            if found:
                out.append(AccountHistory(acct.id, opening, self._holders(acct.id), tuple(pays)))
        return out[:limit]

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]:
        """Accounts held by a company whose accounts category is DORMANT, or that was incorporated
        on or after `incorporated_since`, with at least `min_payments` payments in the period
        (those payments only, in time order)."""
        out = []
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            holders = self.graph.holders(acct.id)
            if not any(
                "Company" in h.labels
                and (
                    (h.get("accounts_category") or "").upper() == "DORMANT"
                    or (
                        len(h.get("incorporation_date") or "") == 10
                        and h.get("incorporation_date") >= incorporated_since
                    )
                )
                for h in holders
            ):
                continue
            pays: list[tuple[Pay, str]] = []
            for r in self.graph.in_rels(acct.id, "PAID"):
                if start <= r.props["ts"] < end:
                    pays.append((_pay(r, r.source), "in"))
            for r in self.graph.out_rels(acct.id, "PAID"):
                if start <= r.props["ts"] < end:
                    pays.append((_pay(r, r.target), "out"))
            if len(pays) >= min_payments:
                pays.sort(key=lambda x: (x[0].ts, x[0].edge_id))
                out.append(
                    AccountHistory(
                        acct.id,
                        acct.get("opening_date") or "",
                        tuple(h.id for h in holders),
                        tuple(pays),
                    )
                )
        return out[:limit]

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]:
        """Weakly connected components of the PAID relationships in [start, end) whose two accounts
        were both opened at most `new_days` before the payment (accounts with a full ISO opening
        date, cash ledgers excluded); components of at least `min_size` accounts, each with its
        accounts sorted, ordered by their smallest account id. The reference for GDS WCC on the
        same projection (queries/recent_account_components.cypher)."""
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def new_at(account_id: str, ts: datetime) -> bool:
            opened = self.graph.node(account_id).get("opening_date") or ""
            if len(opened) != 10 or self._ledger(account_id):
                return False
            return 0 <= (ts.date() - datetime.fromisoformat(opened).date()).days <= new_days

        edges = []
        for r in self.graph.rels("PAID"):
            ts = r.props["ts"]
            if start <= ts < end and new_at(r.source, ts) and new_at(r.target, ts):
                edges.append(r)
                for x in (r.source, r.target):
                    parent.setdefault(x, x)
                a, b = find(r.source), find(r.target)
                if a != b:
                    parent[max(a, b)] = min(a, b)
        groups: dict[str, list[str]] = defaultdict(list)
        for x in parent:
            groups[find(x)].append(x)
        out = []
        for members in groups.values():
            if len(members) < min_size:
                continue
            member_set = set(members)
            comp_edges = sorted(
                PaidEdge(
                    r.props["ts"],
                    r.id,
                    r.source,
                    r.target,
                    float(r.props["amount"]),
                    r.props["currency"],
                    r.props.get("channel") or "",
                )
                for r in edges
                if r.source in member_set
            )
            out.append(Component(tuple(sorted(members)), tuple(comp_edges)))
        return sorted(out, key=lambda c: c.accounts[0])

    # registry --------------------------------------------------------------------------------

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]:
        return {i: self._entity_row(i) for i in sorted(set(ids))}

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        """Registry relationships of `types` that end at each id, by relationship id."""
        out: dict[str, list[LinkRow]] = defaultdict(list)
        for i in sorted(set(ids)):
            for r in self.graph.in_rels(i, *types):
                out[i].append(_link(r))
            out[i].sort(key=lambda link: link.rel_id)
        return dict(out)

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        out: dict[str, list[LinkRow]] = defaultdict(list)
        for i in sorted(set(ids)):
            for r in self.graph.out_rels(i, *types):
                out[i].append(_link(r))
            out[i].sort(key=lambda link: link.rel_id)
        return dict(out)

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]:
        """Number of DIRECTOR_OF relationships each id starts that still hold on `as_of`."""
        return {
            p: sum(1 for r in self.graph.out_rels(p, "DIRECTOR_OF") if _current(r, as_of))
            for p in sorted(set(people))
        }

    def _owns(self, node_id: str, as_of: str, into: bool = False) -> list[Rel]:
        rels = self.graph.in_rels(node_id, "OWNS") if into else self.graph.out_rels(node_id, "OWNS")
        return [r for r in rels if _current(r, as_of)]

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        """Maximal paths of 1 to `max_hops` OWNS relationships that still hold on `as_of`, from a
        top (a node no such OWNS points to) to a leaf Company (one that owns no Organization
        through one), never repeating a node. Ordered by the node ids along the path."""
        out: list[OwnershipPath] = []
        g = self.graph

        def owns_org(n: str) -> list[Rel]:
            return [r for r in self._owns(n, as_of) if "Organization" in g.node(r.target).labels]

        tops = [
            n.id
            for n in g.nodes("LegalEntity")
            if not self._owns(n.id, as_of, into=True) and owns_org(n.id)
        ]

        def walk(path: list[str], links: list[Rel]) -> None:
            last = path[-1]
            nexts = [r for r in owns_org(last) if r.target not in path]
            if links and "Company" in g.node(last).labels and not owns_org(last):
                out.append(OwnershipPath(tuple(path), tuple(_link(r) for r in links)))
            if len(links) >= max_hops:
                return
            for r in nexts:
                walk([*path, r.target], [*links, r])

        for top in tops:
            walk([top], [])
        out.sort(key=lambda x: x.nodes)
        return out[:limit]

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        """Simple cycles of 2 to `max_hops` OWNS relationships that still hold on `as_of`, each
        once, starting at its smallest node id; nodes[0] == nodes[-1]."""
        out: list[OwnershipPath] = []
        g = self.graph

        def walk(origin: str, path: list[str], links: list[Rel]) -> None:
            for r in self._owns(path[-1], as_of):
                if r.target == origin and len(links) + 1 >= 2:
                    out.append(OwnershipPath((*path, origin), tuple(_link(x) for x in [*links, r])))
                elif r.target > origin and r.target not in path and len(links) + 1 < max_hops:
                    walk(origin, [*path, r.target], [*links, r])

        for start in g.nodes("LegalEntity"):
            walk(start.id, [start.id], [])
        out.sort(key=lambda x: x.nodes)
        return out[:limit]

    def _active(self, node_id: str) -> bool:
        n = self.graph.node(node_id)
        return not n.get("dissolution_date") and (n.get("status") or "").casefold() not in INACTIVE

    def _registered(self, address: str, active_only: bool) -> list[tuple[str, str]]:
        return sorted(
            (r.source, r.id)
            for r in self.graph.in_rels(address, "HAS_ADDRESS")
            if r.props.get("role") == "registered"
            and "Organization" in self.graph.node(r.source).labels
            and (not active_only or self._active(r.source))
        )

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]:
        """Addresses with at least `min_members` organisations whose HAS_ADDRESS role is
        registered (with `active_only`, organisations without a dissolution date whose status is
        not an inactive one), ordered by address id."""
        out = []
        for addr in self.graph.nodes("Address"):
            members = self._registered(addr.id, active_only)
            if len(members) >= min_members:
                out.append(
                    AddressCluster(
                        addr.id,
                        addr.get("full") or "",
                        addr.get("postal_code") or "",
                        tuple(members),
                    )
                )
        return out[:limit]

    def registered_count_quantile(self, q: float, active_only: bool) -> int:
        """The nearest-rank `q` quantile of the number of registered organisations per address,
        over addresses with at least one: the value at position max(1, ceil(q * n)) in ascending
        order; 0 when no address has one."""
        counts = sorted(
            c
            for c in (len(self._registered(a.id, active_only)) for a in self.graph.nodes("Address"))
            if c > 0
        )
        if not counts:
            return 0
        return counts[max(1, math.ceil(q * len(counts))) - 1]

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]:
        """Nodes with relationships of `rel_type` (REPRESENTS or DIRECTOR_OF) to at least
        `min_members` distinct organisations, by node id, each with those relationships by id."""
        if rel_type not in ("REPRESENTS", "DIRECTOR_OF"):
            raise ValueError(f"not a hub relationship: {rel_type}")
        by_source: dict[str, list[Rel]] = defaultdict(list)
        for r in self.graph.rels(rel_type):
            if "Organization" in self.graph.node(r.target).labels:
                by_source[r.source].append(r)
        out = []
        for source in sorted(by_source):
            rels = by_source[source]
            if len({r.target for r in rels}) >= min_members:
                out.append(
                    Hub(source, tuple(sorted((_link(r) for r in rels), key=lambda x: x.rel_id)))
                )
        return out[:limit]

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]:
        """Companies whose accounts received cash deposits in `currency` in [prior_start, end):
        sums in pence (each amount rounded to pence first) and counts for [start, end) and for
        [prior_start, start), the sector, and the postcode and city of the registered address (the
        smallest postcode when there are several). By holder id."""
        out = []
        for c in self.graph.nodes("Company"):
            accounts = set()
            win = win_n = prior = prior_n = 0
            for h in self.graph.out_rels(c.id, "HOLDS_ACCOUNT"):
                for r in self.graph.in_rels(h.target, "PAID"):
                    ts = r.props["ts"]
                    if r.props.get("channel") != "cash_deposit" or r.props["currency"] != currency:
                        continue
                    if not prior_start <= ts < end:
                        continue
                    accounts.add(h.target)
                    pence = round(float(r.props["amount"]) * 100)
                    if ts >= start:
                        win += pence
                        win_n += 1
                    else:
                        prior += pence
                        prior_n += 1
            if not accounts:
                continue
            addresses = sorted(
                (
                    self.graph.node(r.target).get("postal_code") or "",
                    self.graph.node(r.target).get("city") or "",
                )
                for r in self.graph.out_rels(c.id, "HAS_ADDRESS")
                if r.props.get("role") == "registered"
            )
            postal, city = addresses[0] if addresses else ("", "")
            out.append(
                CashProfile(
                    c.id,
                    c.get("sector") or "",
                    postal,
                    city,
                    tuple(sorted(accounts)),
                    win,
                    win_n,
                    prior,
                    prior_n,
                )
            )
        return out[:limit]

    def listed_entities(self) -> list[ListedRow]:
        """Every :Sanctioned entity with its labels, datasets and the :Sanction nodes it is
        SUBJECT_OF (by sanction id), ordered by entity id."""
        out = []
        for e in self.graph.nodes("Sanctioned"):
            sanctions = []
            for r in self.graph.out_rels(e.id, "SUBJECT_OF"):
                s = self.graph.node(r.target)
                sanctions.append(
                    SanctionRow(
                        s.id,
                        tuple(s.get("datasets", ())),
                        s.get("authority") or "",
                        s.get("program") or "",
                        tuple(s.get("provisions", ())),
                        s.get("start_date") or "",
                        s.get("end_date") or "",
                    )
                )
            sanctions.sort(key=lambda x: x.id)
            out.append(
                ListedRow(
                    e.id, tuple(sorted(e.labels)), tuple(e.get("datasets", ())), tuple(sanctions)
                )
            )
        return out

    def flagged_ids(self, flag: str) -> list[str]:
        """Ids of the :Entity nodes with one flag label (Sanctioned, PEP or RCA), sorted."""
        if flag not in ("Sanctioned", "PEP", "RCA"):
            raise ValueError(f"not a flag label: {flag}")
        return [n.id for n in self.graph.nodes(flag)]
```

### `detect/src/neonradar_detect/neo4jsource.py`

Verbatim. Python, 608 lines. SHA-256 `fdbe168e3384b3723146f95dd9a8f30c6325d14ea238972be20c39fea1744431`.

```python
"""The production `Source`: one query file per method, run on Neo4j (PHASE-3.md 7.1.2).

Every query is read from `queries/<name>.cypher` and sent with `session.run(neo4j.Query(text,
timeout=...), parameters)`: an auto-commit query, so a memory-limit `TransientError` is reported
rather than retried in a loop (`detection-cypher-gds.md` 2.9). Times go in as UTC ISO strings and
are parsed in the query with `datetime($x)`; DATETIME values come back as `neo4j.time.DateTime` and
are turned into aware `datetime` objects here. The four templated queries take a value from a
fixed list for one of three placeholders (`{{max_hops}}`, `{{flag}}`, `{{rel_type}}`), checked
before substitution, so no caller text ever reaches a query. Results are converted into the
rows of `rows.py` in the order the query files document; the parity tests check them against
`MemSource` (PHASE-3.md 7.1.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from importlib import resources
from typing import Any

import neo4j
import neo4j.time

from neonradar_detect.expand import FrontierItem
from neonradar_detect.model import EdgeInfo, NodeInfo
from neonradar_detect.rows import (
    AccountFlows,
    AccountHistory,
    AddressCluster,
    CashProfile,
    Component,
    CounterpartyInfo,
    Deposit,
    EntityRow,
    HolderDeposits,
    Hop,
    Hub,
    LinkRow,
    ListedRow,
    OwnershipPath,
    PaidEdge,
    Pay,
    SanctionRow,
)

REGISTRY_TYPES = frozenset(
    {
        "OWNS",
        "CONTROLS",
        "CONSOLIDATES",
        "DIRECTOR_OF",
        "REPRESENTS",
        "FAMILY_OF",
        "ASSOCIATE_OF",
        "HAS_ADDRESS",
        "HOLDS_ACCOUNT",
        "HOLDS_POSITION",
    }
)
TEMPLATE_VALUES = {
    "max_hops": {str(n) for n in range(1, 9)},
    "flag": {"Sanctioned", "PEP", "RCA"},
    "rel_type": {"REPRESENTS", "DIRECTOR_OF"},
}


def iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("times must be timezone-aware")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def native(value: neo4j.time.DateTime) -> datetime:
    moment: datetime = value.to_native()
    return moment.astimezone(UTC)


def query_text(name: str, **template: str) -> str:
    text = (
        resources.files("neonradar_detect.queries")
        .joinpath(f"{name}.cypher")
        .read_text(encoding="utf-8")
    )
    for key, value in template.items():
        if value not in TEMPLATE_VALUES[key]:
            raise ValueError(f"{key} may not be {value!r}")
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError(f"unfilled placeholder in {name}")
    return text


def _pay(row: dict[str, Any]) -> Pay:
    return Pay(
        native(row["ts"]),
        row["edge_id"],
        row["counterparty"],
        float(row["amount"]),
        row["currency"],
        row["channel"],
    )


def _link(row: dict[str, Any]) -> LinkRow:
    return LinkRow(
        row["rel_type"],
        row["rel_id"],
        row["source"],
        row["target"],
        row["share_min"],
        row["share_max"],
        bool(row["share_min_exclusive"]),
        bool(row["share_max_exclusive"]),
        bool(row["is_nominee"]),
        row["role"],
        row["start_date"],
        row["end_date"],
        row["control_type"],
    )


class Neo4jSource:
    def __init__(self, driver: neo4j.Driver, database: str, timeout_s: float = 600.0) -> None:
        self.driver = driver
        self.database = database
        self.timeout_s = timeout_s

    def _run(self, name: str, parameters: dict[str, Any], **template: str) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                neo4j.Query(query_text(name, **template), timeout=self.timeout_s), parameters
            )
            return [record.data() for record in result]

    # common ----------------------------------------------------------------------------------

    def paid_time_range(self) -> tuple[datetime, datetime] | None:
        [row] = self._run("paid_time_range", {})
        return (native(row["first"]), native(row["last"])) if row["first"] is not None else None

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]:
        out: dict[str, NodeInfo] = {}
        for row in self._run("node_info", {"ids": sorted(set(ids))}):
            holders = tuple(h["id"] for h in row["holders"])
            out[row["id"]] = NodeInfo(
                row["id"],
                frozenset(row["labels"]),
                row["caption"],
                bool(row["synthetic"]),
                tuple(row["datasets"]),
                holders,
            )
            for h in row["holders"]:
                out.setdefault(
                    h["id"],
                    NodeInfo(
                        h["id"],
                        frozenset(h["labels"]),
                        h["caption"],
                        bool(h["synthetic"]),
                        tuple(h["datasets"]),
                        (),
                    ),
                )
        return out

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]:
        out = {}
        for r in self._run("edge_info", {"ids": sorted(set(ids))}):
            out[r["id"]] = EdgeInfo(
                r["id"],
                r["type"],
                r["source"],
                r["target"],
                bool(r["synthetic"]),
                float(r["amount"]) if r["amount"] is not None else None,
                r["currency"],
                native(r["ts"]) if r["ts"] is not None else None,
                r["channel"],
                r["share_min"],
                r["share_max"],
                bool(r["share_min_exclusive"]),
                bool(r["share_max_exclusive"]),
                r["role"],
                r["control_type"],
                r["start_date"],
                r["end_date"],
            )
        return out

    # paths -----------------------------------------------------------------------------------

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]:
        rows = self._run(
            "paid_starts",
            {"min_amount": min_amount, "start": iso(start), "end": iso(end), "limit": limit},
        )
        return [
            Hop(
                r["edge_id"],
                r["source"],
                r["target"],
                native(r["ts"]),
                float(r["amount"]),
                r["currency"],
                tuple(r["source_holders"]),
                tuple(r["target_holders"]),
            )
            for r in rows
        ]

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]:
        items = [
            {
                "key": f.key,
                "account": f.account,
                "after": iso(f.after),
                "until": iso(f.until),
                "min_amount": f.min_amount,
                "max_amount": f.max_amount,
                "currency": f.currency,
                "visited": list(f.visited),
            }
            for f in frontier
        ]
        found: dict[int, list[Hop]] = {}
        for i in range(0, len(items), 5000):
            for r in self._run("paid_hop", {"frontier": items[i : i + 5000]}):
                found.setdefault(r["key"], []).append(
                    Hop(
                        r["edge_id"],
                        r["source"],
                        r["target"],
                        native(r["ts"]),
                        float(r["amount"]),
                        r["currency"],
                        (),
                        tuple(r["target_holders"]),
                    )
                )
        return found

    # flows -----------------------------------------------------------------------------------

    def _flows(self, name: str, params: dict[str, Any]) -> list[AccountFlows]:
        return [
            AccountFlows(
                r["account"],
                tuple(r["holders"]),
                tuple(_pay(x) for x in r["inflows"]),
                tuple(_pay(x) for x in r["outflows"]),
            )
            for r in self._run(name, params)
        ]

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        return self._flows(
            "flows_by_inbound",
            {
                "min_counterparties": min_inbound_counterparties,
                "start": iso(start),
                "end": iso(end),
                "channel": channel,
                "bucket_hours": bucket_hours,
                "limit": limit,
            },
        )

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        return self._flows(
            "flows_by_outbound",
            {
                "min_counterparties": min_outbound_counterparties,
                "start": iso(start),
                "end": iso(end),
                "bucket_hours": bucket_hours,
                "limit": limit,
            },
        )

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]:
        return {
            r["account"]: CounterpartyInfo(
                r["account"], r["opening_date"], tuple(r["holder_labels"]), tuple(r["holders"])
            )
            for r in self._run("counterparty_info", {"ids": sorted(set(accounts))})
        }

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]:
        wanted = sorted(set(pairs))
        out: dict[tuple[str, str], tuple[datetime, ...]] = {}
        for i in range(0, len(wanted), 20000):
            for r in self._run("paid_times", {"pairs": [list(p) for p in wanted[i : i + 20000]]}):
                out[(r["payer"], r["payee"])] = tuple(native(t) for t in r["times"])
        return out

    def _payments(
        self, name: str, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        out: dict[str, list[Pay]] = {}
        for r in self._run(
            name, {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        ):
            out.setdefault(r["account"], []).append(_pay(r))
        return out

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        return self._payments("payments_from", accounts, start, end)

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        return self._payments("payments_into", accounts, start, end)

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]:
        rows = self._run(
            "payments_among", {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        )
        return [(r["edge_id"], r["payer"], r["payee"]) for r in rows]

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]:
        rows = self._run(
            "activity_counts", {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        )
        return {r["account"]: int(r["payments"]) for r in rows}

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]:
        rows = self._run(
            "holder_cash_deposits",
            {
                "band_low": band_low,
                "threshold": threshold,
                "min_in_band": min_in_band,
                "start": iso(start),
                "end": iso(end),
                "limit": limit,
            },
        )
        return [
            HolderDeposits(
                r["holder"],
                tuple(
                    Deposit(
                        native(d["ts"]),
                        d["edge_id"],
                        d["account"],
                        d["branch"],
                        float(d["amount"]),
                        d["currency"],
                    )
                    for d in r["deposits"]
                ),
            )
            for r in rows
        ]

    def _histories(self, name: str, params: dict[str, Any]) -> list[AccountHistory]:
        out = []
        for r in self._run(name, params):
            pays = tuple((_pay(x), x["direction"]) for x in r["pays"])
            out.append(AccountHistory(r["account"], r["opening_date"], tuple(r["holders"]), pays))
        return out

    def quiet_account_histories(
        self,
        min_gap_days: int,
        max_quiet_payments: int,
        max_quiet_amount: float,
        history_start: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[AccountHistory]:
        return self._histories(
            "quiet_account_histories",
            {
                "min_gap_days": min_gap_days,
                "max_quiet_payments": max_quiet_payments,
                "max_quiet_amount": max_quiet_amount,
                "history_start": history_start,
                "start": iso(start),
                "end": iso(end),
                "limit": limit,
            },
        )

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]:
        return self._histories(
            "company_account_histories",
            {
                "incorporated_since": incorporated_since,
                "start": iso(start),
                "end": iso(end),
                "min_payments": min_payments,
                "limit": limit,
            },
        )

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]:
        params = {"new_days": new_days, "start": iso(start), "end": iso(end)}
        edges = [
            PaidEdge(
                native(r["ts"]),
                r["edge_id"],
                r["source"],
                r["target"],
                float(r["amount"]),
                r["currency"],
                r["channel"],
            )
            for r in self._run("recent_account_edges", params)
        ]
        if not edges:
            return []
        graph = f"nr-ring-{uuid.uuid4().hex}"
        try:
            self._run("recent_account_components_project", {**params, "graph_name": graph})
            rows = self._run("recent_account_components_wcc", {"graph_name": graph})
        finally:
            self._run("recent_account_components_drop", {"graph_name": graph})
        groups: dict[int, list[str]] = {}
        for r in rows:
            groups.setdefault(r["component_id"], []).append(r["account_id"])
        out = []
        for members in groups.values():
            if len(members) < min_size:
                continue
            member_set = set(members)
            out.append(
                Component(
                    tuple(sorted(members)),
                    tuple(sorted(e for e in edges if e.source in member_set)),
                )
            )
        return sorted(out, key=lambda c: c.accounts[0])

    # registry --------------------------------------------------------------------------------

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]:
        out = {}
        for r in self._run("entities", {"ids": sorted(set(ids))}):
            out[r["id"]] = EntityRow(
                r["id"],
                tuple(sorted(r["labels"])),
                r["schema"],
                r["jurisdiction"],
                r["incorporation_date"],
                bool(r["synthetic"]),
                r["accounts_category"],
                r["sector"],
                r["status"],
                r["dissolution_date"],
                tuple(r["datasets"]),
                tuple(r["psc_statements"]),
                r["full"],
                r["postal_code"],
                r["city"],
                tuple(r["countries"]),
            )
        return out

    def _links(
        self, name: str, ids: Iterable[str], types: Sequence[str]
    ) -> dict[str, list[LinkRow]]:
        bad = set(types) - REGISTRY_TYPES
        if bad:
            raise ValueError(f"not registry relationship types: {sorted(bad)}")
        out: dict[str, list[LinkRow]] = {}
        for r in self._run(name, {"ids": sorted(set(ids)), "types": sorted(set(types))}):
            out.setdefault(r["key"], []).append(_link(r))
        return out

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        return self._links("links_into", ids, types)

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        return self._links("links_from", ids, types)

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]:
        return {
            r["id"]: int(r["appointments"])
            for r in self._run("appointment_counts", {"ids": sorted(set(people)), "as_of": as_of})
        }

    def _paths(self, name: str, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        rows = self._run(name, {"limit": limit, "as_of": as_of}, max_hops=str(max_hops))
        return [
            OwnershipPath(tuple(r["node_ids"]), tuple(_link(x) for x in r["links"])) for r in rows
        ]

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        return self._paths("ownership_paths", max_hops, limit, as_of)

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        return self._paths("ownership_cycles", max_hops, limit, as_of)

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]:
        rows = self._run(
            "registered_clusters",
            {"min_members": min_members, "active_only": active_only, "limit": limit},
        )
        return [
            AddressCluster(
                r["address"], r["full"], r["postal_code"], tuple((m[0], m[1]) for m in r["members"])
            )
            for r in rows
        ]

    def registered_count_quantile(self, q: float, active_only: bool) -> int:
        [row] = self._run("registered_count_quantile", {"q": q, "active_only": active_only})
        return int(row["value"])

    def listed_entities(self) -> list[ListedRow]:
        return [
            ListedRow(
                r["entity"],
                tuple(sorted(r["labels"])),
                tuple(r["datasets"]),
                tuple(
                    SanctionRow(
                        s["id"],
                        tuple(s["datasets"]),
                        s["authority"],
                        s["program"],
                        tuple(s["provisions"]),
                        s["start_date"],
                        s["end_date"],
                    )
                    for s in r["sanctions"]
                ),
            )
            for r in self._run("listed_entities", {})
        ]

    def flagged_ids(self, flag: str) -> list[str]:
        return [r["id"] for r in self._run("flagged_ids", {}, flag=flag)]

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]:
        rows = self._run("hubs", {"min_members": min_members, "limit": limit}, rel_type=rel_type)
        return [Hub(r["hub"], tuple(_link(x) for x in r["links"])) for r in rows]

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]:
        rows = self._run(
            "cash_profiles",
            {
                "prior_start": iso(prior_start),
                "start": iso(start),
                "end": iso(end),
                "currency": currency,
                "limit": limit,
            },
        )
        return [
            CashProfile(
                r["holder"],
                r["sector"],
                r["postal_code"],
                r["city"],
                tuple(r["accounts"]),
                int(r["window_pence"]),
                int(r["window_deposits"]),
                int(r["prior_pence"]),
                int(r["prior_deposits"]),
            )
            for r in rows
        ]
```

### `detect/src/neonradar_detect/policy.py`

Verbatim. Python, 102 lines. SHA-256 `79888f101952bd017f4052370687f91e4969d9d5aacbd52e911813ffb292c47a`.

```python
"""Data flags (C4) and the real-data detection rule R-REAL (PHASE-3.md 2.1, G12; 7.1.4).

`data_flags` implements the C4 definitions exactly: a node is involved when it is an evidence node,
a subject, or a holder of an evidence account. `decide` applies R-REAL on every instance, in this
order, and the first rule that applies gives the reason:

(a) a finding that rests on payments (the detector says so, or a PAID relationship is in its
    evidence) and involves a non-synthetic node is withheld, because every payment in NeonRadar
    is synthetic and says nothing about a real entity;
(b) a finding whose subjects include a non-synthetic person is withheld;
(c) a finding whose other involved nodes include a non-synthetic person is withheld, so that no
    alert names a real person anywhere (data protection by design, `typology-detection-
    definitions.md` 16.5);
(d) with `registry_on_real=False` (`access.real_registry_alerts: false`, the stricter option of
    PHASE-3.md 1.2), every other finding that involves a non-synthetic node is withheld too.

A person is a `:LegalEntity` that is not an `:Organization`: a `:Person`, or a legal entity whose
kind the source does not state (ICIJ officers and intermediaries), which may be a person.
Withheld findings are counted in the run summary by reason and typology, never stored or shown.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from neonradar_detect.model import EdgeInfo, Finding, NodeInfo


class Decision(StrEnum):
    EMIT = "emit"
    ACTIVITY_ON_REAL = "activity_on_real"
    REAL_PERSON_SUBJECT = "real_person_subject"
    REAL_PERSON_EVIDENCE = "real_person_evidence"
    REGISTRY_ON_REAL = "registry_on_real"


@dataclass(frozen=True, slots=True)
class DataFlags:
    involves_real_entities: bool
    synthetic_activity: bool
    datasets: tuple[str, ...]

    @property
    def wording_class(self) -> str:
        return "structural_pattern" if self.involves_real_entities else "synthetic_scenario"


def involved_ids(finding: Finding, nodes: Mapping[str, NodeInfo]) -> list[str]:
    """Evidence nodes, subjects and the holders of evidence accounts, sorted."""
    ids = set(finding.node_ids) | {s.entity_id for s in finding.subjects}
    for node_id in finding.node_ids:
        info = nodes[node_id]
        if "Account" in info.labels:
            ids.update(info.holders)
    return sorted(ids)


def may_be_person(info: NodeInfo) -> bool:
    """A `:Person`, or a `:LegalEntity` of unstated kind: anything legal that is not an
    organisation."""
    return "LegalEntity" in info.labels and "Organization" not in info.labels


def rests_on_payments(finding: Finding, edges: Mapping[str, EdgeInfo]) -> bool:
    return finding.activity or any(edges[e].type == "PAID" for e in finding.edge_ids)


def data_flags(
    finding: Finding, nodes: Mapping[str, NodeInfo], edges: Mapping[str, EdgeInfo]
) -> DataFlags:
    involved = involved_ids(finding, nodes)
    missing = [i for i in involved if i not in nodes]
    if missing:
        raise KeyError(f"no node information for {len(missing)} involved ids")
    involves_real = any(not nodes[i].synthetic for i in involved)
    synthetic_activity = all(edges[e].synthetic for e in finding.edge_ids)
    datasets = sorted({d for i in involved for d in nodes[i].datasets})
    return DataFlags(involves_real, synthetic_activity, tuple(datasets))


def decide(
    finding: Finding,
    flags: DataFlags,
    nodes: Mapping[str, NodeInfo],
    edges: Mapping[str, EdgeInfo],
    *,
    registry_on_real: bool = True,
) -> Decision:
    if flags.involves_real_entities and rests_on_payments(finding, edges):
        return Decision.ACTIVITY_ON_REAL
    subjects = {s.entity_id for s in finding.subjects}
    if any(not nodes[s].synthetic and may_be_person(nodes[s]) for s in sorted(subjects)):
        return Decision.REAL_PERSON_SUBJECT
    for node_id in involved_ids(finding, nodes):
        info = nodes[node_id]
        if node_id not in subjects and not info.synthetic and may_be_person(info):
            return Decision.REAL_PERSON_EVIDENCE
    if flags.involves_real_entities and not registry_on_real:
        return Decision.REGISTRY_ON_REAL
    return Decision.EMIT
```

### `detect/src/neonradar_detect/alerts.py`

Verbatim. Python, 129 lines. SHA-256 `1da750065ff1684d6bdfe13a86934638a50a9965884e0b9cf90d020eeb271caa`.

```python
"""Findings to C4 1.0.0 alerts (PHASE-3.md 7.5.1).

The builder adds what a detector does not know: the alert id (C4's `compute_alert_id`, M1.7c), the
priority, the rendered text, the data flags, the notes a data source asks for and the evidence
query. Every alert's evidence query is
the generic `queries/evidence.cypher`, which re-selects the evidence nodes and relationships by id,
so `neonradar detect verify-alert` can check an alert against the graph.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from neonradar_contracts.alert import compute_alert_id

from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.policy import DataFlags
from neonradar_detect.wording import Rendered

EVIDENCE_QUERY = (
    (Path(__file__).parent / "queries" / "evidence.cypher").read_text(encoding="utf-8")
    if (Path(__file__).parent / "queries" / "evidence.cypher").exists()
    else "// queries/evidence.cypher"
)


# Notes a data source asks for wherever its records are shown (PHASE-1.md 5.1: "Show ICIJ's
# disclaimer with the data"; the wording is ICIJ's FAQ, `icij_faq`). Each passes the wording lint.
DATASET_NOTES = {
    "icij_offshore_leaks": (
        "Records from the ICIJ Offshore Leaks Database: ICIJ says there are legitimate uses for "
        "offshore companies and trusts, and recommends caution before drawing any conclusions, "
        "as many people and entities have the same or similar names."
    ),
}


def default_priority(strength: float) -> str:
    return "high" if strength >= 0.75 else ("medium" if strength >= 0.5 else "low")


def build(
    finding: Finding,
    rendered: Rendered,
    flags: DataFlags,
    nodes: Mapping[str, NodeInfo],
    *,
    detector_module: str,
    detector_version: str,
    typology_version: str,
    query_sha256: str,
    run_id: str,
    created_at: datetime,
    doc_path: str,
    citations: Sequence[str],
    false_positives: Sequence[str],
    priority_rule: Callable[[Finding], str | None] | None = None,
) -> dict[str, Any]:
    priority = (priority_rule(finding) if priority_rule else None) or default_priority(
        finding.pattern_strength
    )
    evidence: dict[str, Any] = {
        "node_ids": list(finding.node_ids),
        "edge_ids": list(finding.edge_ids),
        "query": {
            "cypher": EVIDENCE_QUERY,
            "parameters": {"node_ids": list(finding.node_ids), "edge_ids": list(finding.edge_ids)},
        },
    }
    if finding.window is not None:
        evidence["window"] = {"start": _utc(finding.window[0]), "end": _utc(finding.window[1])}
    return {
        "alert_id": compute_alert_id(
            finding.typology, detector_version, finding.node_ids, finding.edge_ids
        ),
        "contract_version": "1.0.0",
        "typology": finding.typology,
        "typology_version": typology_version,
        "detector": {
            "name": detector_module,
            "version": detector_version,
            "query_sha256": query_sha256,
        },
        "run_id": run_id,
        "created_at": _utc(created_at),
        "priority": priority,
        "pattern_strength": finding.pattern_strength,
        "headline": rendered.headline,
        "wording_class": flags.wording_class,
        "subjects": [
            {"entity_id": s.entity_id, "role": s.role, "caption": nodes[s.entity_id].caption}
            for s in finding.subjects
        ],
        "evidence": evidence,
        "metrics": dict(finding.metrics),
        "explanation": {
            "summary": rendered.summary,
            "steps": [
                {"order": i, "text": text, "edge_ids": list(edges)}
                for i, (text, edges) in enumerate(rendered.steps, 1)
            ],
            "typology_reference": {
                "slug": finding.typology,
                "doc_path": doc_path,
                "citations": list(citations),
            },
            "false_positive_notes": [
                *false_positives,
                *(DATASET_NOTES[d] for d in flags.datasets if d in DATASET_NOTES),
            ],
        },
        "data_flags": {
            "involves_real_entities": flags.involves_real_entities,
            "synthetic_activity": flags.synthetic_activity,
            "datasets": list(flags.datasets),
        },
        "disclaimer_id": "standing-v1",
    }


def _utc(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def edge_ends(edges: Mapping[str, EdgeInfo]) -> set[str]:
    return {x for e in edges.values() for x in (e.source, e.target)}
```

### `detect/src/neonradar_detect/wording.py`

Verbatim. Python, 231 lines. SHA-256 `24e7797ec3f34667aa2a790f76a7e638a9faf1ab1e9aa3c77c9c67784ff5a1f2`.

```python
"""Entity-facing text for alerts: headlines, summaries and steps (PHASE-3.md 7.5.2).

Headlines come from the typology file's templates (PHASE-1.md 5.4): `wording.headline_structural`
or `wording.headline_synthetic`, or the pair under `wording.variants.<variant>` when the finding's
variant has one. A placeholder is `{metric}` or `{metric|filter}`: `money` (the finding's
`currency` and the amount), `pct` (a ratio as a whole percent) and `n:<singular>[:<plural>]` (a
count with its noun). Headlines describe the shape and its numbers, never the conduct a typology is
named after (`typology-detection-definitions.md` 16.1), and the summary names the typology's
neutral `shape_name`, after the optional `wording.detail` template (the sentences a detector's
metrics need, such as the result of each sanctions test). Steps are rendered from the evidence
relationships. `render` lints every text it renders (`wording_lint.violations`, with the captions
of every node it names masked out) and raises `WordingError` on a match, so no run can emit text
that names conduct (G5); the error names the typology, the part and the patterns, never the text.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neonradar_detect.catalog import Typology
from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.wording_lint import violations

MAX_HEADLINE = 140
MAX_STEP = 280
PLACEHOLDER = re.compile(r"\{(\w+)(?:\|([a-z]+)(?::([^:}]+))?(?::([^:}]+))?)?\}")


class WordingError(ValueError):
    """Rendered alert text matched the wording lint."""


@dataclass(frozen=True, slots=True)
class Rendered:
    headline: str
    summary: str
    steps: tuple[tuple[str, tuple[str, ...]], ...]  # (text, edge ids)


def money(currency: str, amount: float) -> str:
    text = f"{amount:,.2f}"
    return f"{currency} {text[:-3] if text.endswith('.00') else text}"


def day(moment: datetime | str) -> str:
    d = datetime.fromisoformat(moment) if isinstance(moment, str) else moment
    return f"{d.day} {d.strftime('%B')} {d.year}"


def counted(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def render_template(template: str, metrics: Mapping[str, Any]) -> str:
    def one(m: re.Match[str]) -> str:
        name, kind, a, b = m.groups()
        value = metrics[name]
        if kind is None:
            return _value(value)
        if kind == "money":
            return money(str(metrics["currency"]), float(value))
        if kind == "pct":
            return f"{round(100 * float(value))} percent"
        if kind == "n":
            return counted(int(value), a, b)
        raise ValueError(f"unknown filter {kind}")

    return PLACEHOLDER.sub(one, template)


def placeholders(template: str) -> set[str]:
    return {m.group(1) for m in PLACEHOLDER.finditer(template)}


def templates(typology: Typology, variant: str) -> Mapping[str, str]:
    return typology.wording.get("variants", {}).get(variant) or typology.wording


def _cap(text: str, limit: int) -> str:
    """`text`, or its words up to `limit - 1` characters and an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut and not text[limit - 1].isspace():
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:") + "…"


def band(e: EdgeInfo) -> str:
    low, high = e.share_min, e.share_max
    if low is None and high is None:
        return "an unrecorded share"
    if low is not None and high is not None and low == high:
        return f"{low:g} percent"
    if high is None or (high >= 100 and not e.share_max_exclusive):
        return (
            f"{low:g} percent or more"
            if not e.share_min_exclusive
            else f"more than {low:g} percent"
        )
    lower = f"more than {low:g}" if e.share_min_exclusive else f"at least {low:g}"
    upper = f"less than {high:g}" if e.share_max_exclusive else f"at most {high:g}"
    return f"{lower} and {upper} percent"


def dates(e: EdgeInfo) -> str:
    """The " from <start>" and " to <end>" parts for the full dates a relationship records."""
    since = f" from {day(e.start_date)}" if len(e.start_date) == 10 else ""
    until = f" to {day(e.end_date)}" if len(e.end_date) == 10 else ""
    return since + until


def edge_sentence(e: EdgeInfo, name: Callable[[str], str]) -> str:
    s, t = name(e.source), name(e.target)
    if e.type == "PAID" and e.ts is not None:
        if e.channel == "cash_deposit":
            return f"{money(e.currency, e.amount or 0)} in cash was paid into {t} on {day(e.ts)}."
        return f"{s} paid {money(e.currency, e.amount or 0)} to {t} on {day(e.ts)}."
    if e.type == "OWNS":
        return f"{s} is recorded as holding {band(e)} of {t}{dates(e)}."
    if e.type == "CONTROLS":
        what = {
            "appointment": "the right to appoint or remove a majority of the board of",
            "voting": f"{band(e)} of the voting rights in",
        }.get(e.control_type, "significant influence or control over")
        return f"{s} is recorded with {what} {t}{dates(e)}."
    if e.type == "CONSOLIDATES":
        return f"{s} is recorded as consolidating {t} in its accounts."
    if e.type == "DIRECTOR_OF":
        return f"{s} is recorded as a director of {t}{dates(e)}."
    if e.type == "REPRESENTS":
        return f"{s} is recorded as an agent of {t}."
    if e.type == "HAS_ADDRESS":
        return f"{s} is registered at {t}."
    if e.type == "FAMILY_OF":
        return f"{s} and {t} are recorded as family ({e.role or 'relationship not given'})."
    if e.type == "ASSOCIATE_OF":
        return f"{s} and {t} are recorded as associates ({e.role or 'relationship not given'})."
    if e.type == "HOLDS_ACCOUNT":
        return f"{s} holds account {t}."
    return f"{s} is linked to {t}."


def group_sentence(group: Sequence[EdgeInfo], name: Callable[[str], str]) -> str:
    """One step: a single relationship in full, or a group summarised."""
    if len(group) == 1:
        return _cap(edge_sentence(group[0], name), MAX_STEP)
    if all(e.type == "PAID" for e in group):
        currencies = sorted({e.currency for e in group})
        total = sum(e.amount or 0 for e in group)
        first = min(e.ts for e in group if e.ts)
        last = max(e.ts for e in group if e.ts)
        sources = sorted({e.source for e in group})
        targets = sorted({e.target for e in group})
        amount = (
            money(currencies[0], total) if len(currencies) == 1 else "amounts in several currencies"
        )
        when = (
            f"on {day(first)}"
            if first.date() == last.date()
            else f"between {day(first)} and {day(last)}"
        )
        if all(e.channel == "cash_deposit" for e in group):
            into = name(targets[0]) if len(targets) == 1 else counted(len(targets), "account")
            text = f"{counted(len(group), 'cash deposit')} of {amount} in total into {into} {when}."
        elif len(targets) == 1:
            payers, n = counted(len(sources), "account"), counted(len(group), "payment")
            text = f"{payers} paid {amount} in {n} to {name(targets[0])} {when}."
        elif len(sources) == 1:
            n, payees = counted(len(group), "payment"), counted(len(targets), "account")
            text = f"{name(sources[0])} paid {amount} in {n} to {payees} {when}."
        else:
            accounts = counted(len(set(sources) | set(targets)), "account")
            text = f"{counted(len(group), 'payment')} of {amount} in total among {accounts} {when}."
        return _cap(text, MAX_STEP)
    joined = " ".join(edge_sentence(e, name) for e in group)
    if len(joined) <= MAX_STEP:
        return joined
    head = edge_sentence(group[0], name)
    return _cap(
        f"{head} And {counted(len(group) - 1, 'more recorded relationship')} of the same kind.",
        MAX_STEP,
    )


def render(
    finding: Finding,
    typology: Typology,
    wording_class: str,
    nodes: Mapping[str, NodeInfo],
    edges: Mapping[str, EdgeInfo],
) -> Rendered:
    def name(node_id: str) -> str:
        info = nodes.get(node_id)
        return info.caption if info is not None else node_id

    pair = templates(typology, finding.variant)
    key = "headline_synthetic" if wording_class == "synthetic_scenario" else "headline_structural"
    headline = _cap(render_template(pair[key], finding.metrics), MAX_HEADLINE)
    plain = _cap(render_template(pair["headline_structural"], finding.metrics), MAX_HEADLINE)
    detail_template = pair.get("detail") or typology.wording.get("detail") or ""
    detail = f"{render_template(detail_template, finding.metrics)} " if detail_template else ""
    summary = (
        f"{plain}. {detail}This matches the graph pattern of {typology.shape_name}. The records "
        "show the shape only; the notes below list ordinary activity that looks the same."
    )
    steps = tuple(
        (group_sentence([edges[e] for e in group], name), tuple(group)) for group in finding.steps
    )
    captions = tuple(
        sorted({info.caption for info in nodes.values()} | set(nodes), key=len, reverse=True)
    )
    parts = [("headline", headline), ("summary", summary)]
    parts += [(f"step {i}", text) for i, (text, _) in enumerate(steps, 1)]
    for part, text in parts:
        found = violations(text, captions)
        if found:
            raise WordingError(f"{typology.slug}: the {part} matches {found}")
    return Rendered(headline, summary, steps)
```

### `detect/src/neonradar_detect/runner.py`

Verbatim. Python, 161 lines. SHA-256 `853bb97ca1799510b617b3fe9c97aba5df4f6d89db9e8facf9144457a560fc18`.

```python
"""Run the detectors of a profile, apply R-REAL and build the alerts (PHASE-3.md 7.5.3).

`run_detection` is the one path every caller uses: `neonradar detect run`, `make load`, the
evaluation harness and the tests. It never writes; the CLI writes `alerts.jsonl` and
`summary.json` and loads them (C2 1.2.0, L19). Withheld findings are counted by typology and
reason and never kept. The detectors are the modules the catalog names, run in ORDER. Rendering
lints every text (`wording.render` raises `WordingError`), so a run never emits text that names
conduct.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from types import ModuleType
from typing import Any

from neonradar_detect import alerts, policy, wording
from neonradar_detect.catalog import Typology
from neonradar_detect.source import Source, Window

# PHASE-1.md 7.2 order; a typology runs when its catalog file names a detector (PHASE-1.md 5.4)
ORDER = (
    "structuring",
    "rapid_pass_through",
    "layering_chain",
    "circular_flow",
    "fan_in_collection",
    "fan_out_distribution",
    "dormant_reactivation",
    "shell_chain",
    "mass_registration_address",
    "sanctions_exposure",
    "formation_agent_cluster",
    "recycled_directors",
    "pep_exposure",
    "cash_commingling",
    "trade_based_ml",
)


def detectors(catalog: Mapping[str, Typology]) -> dict[str, ModuleType]:
    """Slug to detector module, in ORDER, for every catalog typology that names a detector."""
    out: dict[str, ModuleType] = {}
    for slug in ORDER:
        typology = catalog.get(slug)
        if typology is None or not typology.detector:
            continue
        module = importlib.import_module(typology.detector)
        if slug != module.SLUG:
            raise ValueError(f"{typology.detector} declares {module.SLUG}, not {slug}")
        out[slug] = module
    unknown = sorted(set(catalog) - set(ORDER))
    if unknown:
        raise ValueError(f"typologies outside ORDER: {unknown}")
    return out


@dataclass(slots=True)
class RunResult:
    alerts: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)


def params_sha256(params: Mapping[str, Any]) -> str:
    """SHA-256 of the parameters actually used, as canonical JSON (sorted keys, no spaces)."""
    body = {
        slug: (asdict(p) if hasattr(p, "__dataclass_fields__") else dict(p))
        for slug, p in sorted(params.items())
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_detection(
    source: Source,
    params: Mapping[str, Any],
    window: Window,
    catalog: Mapping[str, Typology],
    *,
    run_id: str,
    created_at: datetime,
    query_sha256: Mapping[str, str] | None = None,
    real_registry_alerts: bool = True,
) -> RunResult:
    """Run every typology in `params` (slug to its Params) in catalog order.
    `real_registry_alerts` is `access.real_registry_alerts` (G12, rule (c) in `policy`)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_typology: dict[str, dict[str, Any]] = {}
    for slug, module in detectors(catalog).items():
        if slug not in params:
            continue
        result = module.run(source, params[slug], window)
        withheld = {d.value: 0 for d in policy.Decision if d is not policy.Decision.EMIT}
        emitted = duplicates = 0
        for finding in result.findings:
            edges = source.edge_info(finding.edge_ids)
            ends = alerts.edge_ends(edges)
            nodes = source.node_info(
                set(finding.node_ids) | {s.entity_id for s in finding.subjects} | ends
            )
            flags = policy.data_flags(finding, nodes, edges)
            decision = policy.decide(
                finding, flags, nodes, edges, registry_on_real=real_registry_alerts
            )
            if decision is not policy.Decision.EMIT:
                withheld[decision.value] += 1
                continue
            typology = catalog[slug]
            alert = alerts.build(
                finding,
                wording.render(finding, typology, flags.wording_class, nodes, edges),
                flags,
                nodes,
                detector_module=module.__name__,
                detector_version=module.VERSION,
                typology_version=typology.version,
                query_sha256=(query_sha256 or {}).get(slug, ""),
                run_id=run_id,
                created_at=created_at,
                doc_path=typology.doc,
                citations=typology.citations,
                false_positives=typology.false_positives,
                priority_rule=getattr(module, "priority", None),
            )
            if alert["alert_id"] in seen:
                duplicates += 1
                continue
            seen.add(alert["alert_id"])
            out.append(alert)
            emitted += 1
        per_typology[slug] = {
            "findings": len(result.findings),
            "alerts": emitted,
            "duplicates": duplicates,
            "withheld": withheld,
            "stats": dict(result.stats),
        }
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda a: (order[a["priority"]], -a["pattern_strength"], a["alert_id"]))
    summary = {
        "run_id": run_id,
        "window": {
            "start": window.start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": window.end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "params_sha256": params_sha256(params),
        "typologies": per_typology,
        "alerts": len(out),
        "withheld": {
            reason: sum(c["withheld"][reason] for c in per_typology.values())
            for reason in (d.value for d in policy.Decision if d is not policy.Decision.EMIT)
        },
    }
    return RunResult(out, summary)
```

### `detect/src/neonradar_detect/graphrows.py`

Verbatim. Python, 256 lines. SHA-256 `2d840172319aae557b38941e7154dd63141cf87a052e1f73739dd433ab4fbfc1`.

```python
"""C1 records to a MemGraph with the C2 1.2.0 labels, types and properties (PHASE-3.md 7.1.2).

The oracle's own reading of C2 (PHASE-1.md 5.2 and the 1.1.0 and 1.2.0 changes), limited to the
labels, types and properties the detectors read (the table in 7.1.2). It does not call the
graph package's mapping, so that the oracle is an independent implementation: the loader's
mapping and this one are compared by every detector test in Neo4j mode, which loads the same
records with the project's loader, and by the world parity test (7.1.5). `test_graphrows.py` pins
the result. Records are taken as they are, one node per record: the oracle does no entity
resolution, so it is for synthetic data, where resolution is off.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from neonradar_detect.memgraph import MemGraph

LABELS = {
    "Person": ["Entity", "LegalEntity", "Person"],
    "Company": ["Entity", "LegalEntity", "Organization", "Company"],
    "Organization": ["Entity", "LegalEntity", "Organization"],
    "LegalEntity": ["Entity", "LegalEntity"],
    "Address": ["Entity", "Address"],
    "BankAccount": ["Entity", "Account"],
    "Position": ["Entity", "Position"],
}
FLAGS = {"sanction": "Sanctioned", "role.pep": "PEP", "role.rca": "RCA"}


def _one(props: dict[str, list[str]], key: str) -> str | None:
    vals = props.get(key) or []
    return vals[0] if vals else None


def from_records(records: list[dict[str, Any]]) -> MemGraph:
    g = MemGraph()
    by_id = {r["id"]: r for r in records}
    for r in sorted(records, key=lambda r: r["id"]):
        schema = r["schema"]
        if schema not in LABELS and schema != "Sanction":
            continue
        p = r["properties"]
        nr = r.get("nr") or {}
        synthetic = bool(nr.get("synthetic", False))
        topics = sorted(p.get("topics", []))
        if schema == "Sanction":
            g.add_node(
                r["id"],
                ["Sanction"],
                {
                    k: v
                    for k, v in {
                        "authority": _one(p, "authority"),
                        "program": _one(p, "program"),
                        "provisions": p.get("provisions") or None,
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                        "listing_date": _one(p, "listingDate"),
                        "datasets": r["datasets"],
                        "synthetic": synthetic,
                        "caption": _one(p, "authority") or r["id"],
                    }.items()
                    if v is not None
                },
            )
            continue
        labels = list(LABELS[schema])
        labels += [FLAGS[t] for t in topics if t in FLAGS]
        if synthetic:
            labels.append("Synthetic")
        names = p.get("name", []) or p.get("full", [])
        props: dict[str, Any] = {
            "schema": schema,
            "caption": (names[0] if names else (_one(p, "accountNumber") or r["id"])),
            "names": names,
            "topics": topics,
            "datasets": r["datasets"],
            "synthetic": synthetic,
            "referents": [r["id"]],
        }
        if schema == "BankAccount":
            props.update(
                account_number=_one(p, "accountNumber"),
                bank_name=_one(p, "bankName"),
                currency=_one(p, "currency"),
                opening_date=_one(p, "openingDate"),
                account_kind=nr.get("account_kind"),
            )
            props["caption"] = props["account_number"]
        if schema in ("Company", "Organization", "LegalEntity"):
            props.update(
                jurisdiction=_one(p, "jurisdiction"),
                registration_number=_one(p, "registrationNumber"),
                incorporation_date=_one(p, "incorporationDate"),
                dissolution_date=_one(p, "dissolutionDate"),
                status=_one(p, "status"),
                sector=_one(p, "sector"),
                accounts_category=nr.get("accounts_category"),
                psc_statements=nr.get("psc_statements"),
            )
        if schema == "Person":
            props.update(birth_date=_one(p, "birthDate"), nationalities=p.get("nationality", []))
        if schema == "Address":
            props.update(
                full=_one(p, "full"),
                country=_one(p, "country"),
                postal_code=_one(p, "postalCode"),
                city=_one(p, "city"),
            )
        if schema == "Position":
            props.update(country=_one(p, "country"))
        props["countries"] = sorted(
            set(p.get("country", []) + p.get("jurisdiction", []) + p.get("nationality", []))
        )
        g.add_node(r["id"], labels, {k: v for k, v in props.items() if v is not None})
    for r in sorted(records, key=lambda r: r["id"]):
        p = r["properties"]
        nr = r.get("nr") or {}
        base = {"datasets": r["datasets"], "synthetic": bool(nr.get("synthetic", False))}
        s = r["schema"]
        if s in ("Company", "Organization", "Person", "LegalEntity"):
            roles = nr.get("address_roles", {})
            for addr in p.get("addressEntity", []):
                g.add_rel(
                    f"{r['id']}|addr|{addr}",
                    "HAS_ADDRESS",
                    r["id"],
                    addr,
                    {**base, "role": roles.get(addr, "unknown")},
                )
        elif s == "Sanction":
            entity = _one(p, "entity") or ""
            g.add_rel(f"{entity}|sanction|{r['id']}", "SUBJECT_OF", entity, r["id"], base)
        elif s == "Payment":
            amount = float(_one(p, "amount") or 0)
            moment = datetime.strptime(_one(p, "date") or "", "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=UTC
            )
            g.add_rel(
                r["id"],
                "PAID",
                _one(p, "payerAccount") or "",
                _one(p, "beneficiaryAccount") or "",
                {
                    **base,
                    "amount": amount,
                    "currency": _one(p, "currency"),
                    "ts": moment,
                    "channel": nr.get("channel"),
                    "purpose": _one(p, "purpose"),
                },
            )
        elif s == "Ownership":
            owner, asset = _one(p, "owner") or "", _one(p, "asset") or ""
            if by_id.get(asset, {}).get("schema") == "BankAccount":
                g.add_rel(r["id"], "HOLDS_ACCOUNT", owner, asset, {**base, "role": _one(p, "role")})
            elif nr.get("consolidation"):
                g.add_rel(
                    r["id"],
                    "CONSOLIDATES",
                    owner,
                    asset,
                    {
                        **base,
                        "level": nr["consolidation"],
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                    },
                )
            else:
                g.add_rel(
                    r["id"],
                    "OWNS",
                    owner,
                    asset,
                    {
                        **base,
                        "share_pct_min": nr.get("share_pct_min"),
                        "share_pct_max": nr.get("share_pct_max"),
                        "share_min_exclusive": bool(nr.get("share_pct_min_exclusive", False)),
                        "share_max_exclusive": bool(nr.get("share_pct_max_exclusive", False)),
                        "is_nominee": bool(nr.get("is_nominee", False)),
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                    },
                )
        elif s == "Control":
            g.add_rel(
                r["id"],
                "CONTROLS",
                _one(p, "controller") or "",
                _one(p, "controlled") or "",
                {
                    **base,
                    "control_type": _one(p, "controlType"),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                    "share_pct_min": nr.get("share_pct_min"),
                    "share_pct_max": nr.get("share_pct_max"),
                    "share_min_exclusive": bool(nr.get("share_pct_min_exclusive", False)),
                    "share_max_exclusive": bool(nr.get("share_pct_max_exclusive", False)),
                },
            )
        elif s == "Directorship":
            g.add_rel(
                r["id"],
                "DIRECTOR_OF",
                _one(p, "director") or "",
                _one(p, "organization") or "",
                {
                    **base,
                    "role": _one(p, "role"),
                    "is_nominee": bool(nr.get("is_nominee", False)),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                },
            )
        elif s == "Representation":
            g.add_rel(
                r["id"],
                "REPRESENTS",
                _one(p, "agent") or "",
                _one(p, "client") or "",
                {**base, "role": _one(p, "role")},
            )
        elif s == "Family":
            g.add_rel(
                r["id"],
                "FAMILY_OF",
                _one(p, "person") or "",
                _one(p, "relative") or "",
                {**base, "relationship": _one(p, "relationship")},
            )
        elif s == "Occupancy":
            g.add_rel(
                r["id"],
                "HOLDS_POSITION",
                _one(p, "holder") or "",
                _one(p, "post") or "",
                {
                    **base,
                    "status": _one(p, "status"),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                },
            )
        elif s == "Associate":
            g.add_rel(
                r["id"],
                "ASSOCIATE_OF",
                _one(p, "person") or "",
                _one(p, "associate") or "",
                {**base, "relationship": _one(p, "relationship")},
            )
    return g
```

### `detect/src/neonradar_detect/catalog.py`

Reference. Python, 83 lines. SHA-256 `92161e4f86a2e76bd473ef23f2059a53259a7da80bf88608296b1f70cebf9235`.

M3.2 extends Phase 1's `TypologyFile` and `load_catalog()` and keeps this interface: `Typology`, `load()` and `params_for(typology, module, overrides)`.

```python
"""The typology catalog, `detect/typologies/<slug>.yaml` (PHASE-1.md 5.4; PHASE-3.md 7.5.2).

Phase 3 adds two fields to the Phase 1 shape: `shape_name`, the neutral name entity-facing text
uses ("matches the graph pattern of <shape name>"), and `wording.variants`, headline templates for
a detector variant. The repository's `TypologyFile` model (M1.7c) gains both; this module is the
prototype's reader. `params_for` builds a detector's `Params` from the file's defaults and a
profile's overrides, refusing unknown names and values outside a parameter's bounds.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

CATALOG_DIR = Path(__file__).resolve().parents[2] / "typologies"


@dataclass(frozen=True, slots=True)
class Typology:
    slug: str
    name: str
    shape_name: str
    tier: str
    version: str
    doc: str
    citations: tuple[str, ...]
    parameters: Mapping[str, Mapping[str, Any]]
    metrics: tuple[str, ...]
    wording: Mapping[str, Any]
    false_positives: tuple[str, ...]
    detector: str


def load(directory: Path = CATALOG_DIR) -> dict[str, Typology]:
    out = {}
    for path in sorted(directory.glob("*.yaml")):
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[d["slug"]] = Typology(
            d["slug"],
            d["name"],
            d.get("shape_name") or "",
            d["tier"],
            d["version"],
            d["doc"],
            tuple(d["citations"]),
            d.get("parameters") or {},
            tuple(d.get("metrics") or ()),
            d.get("wording") or {},
            tuple(d.get("false_positives") or ()),
            d.get("detector") or "",
        )
    return out


def params_for(
    typology: Typology, module: ModuleType, overrides: Mapping[str, Any] | None = None
) -> Any:
    """The detector's Params: catalog defaults, then the profile's overrides, each within bounds."""
    values: dict[str, Any] = {}
    fields = {f.name: f for f in dataclasses.fields(module.Params)}
    for name, spec in typology.parameters.items():
        if name not in fields:
            raise KeyError(f"{typology.slug}: catalog parameter {name} is not a detector parameter")
        values[name] = spec["default"]
    for name, value in (overrides or {}).items():
        bounds = typology.parameters.get(name)
        if bounds is None:
            raise KeyError(f"{typology.slug}: unknown parameter {name}")
        if "min" in bounds and not bounds["min"] <= value <= bounds["max"]:
            raise ValueError(
                f"{typology.slug}: {name}={value} outside [{bounds['min']}, {bounds['max']}]"
            )
        values[name] = value
    for name, value in values.items():
        if isinstance(value, list):
            values[name] = tuple(value)
    return module.Params(**values)
```

### `detect/src/neonradar_detect/wording_lint.py`

Reference. Python, 64 lines. SHA-256 `d46045b12f9cdbf5554fe549cac1a1ff2e9d7717757db3dc7e8fc95c421dd2c3`.

M3.2 keeps `violations(text, masked)` and calls Phase 1's lint over `contracts/wording/forbidden-terms.txt` instead of the `PATTERNS` below, adding `PHRASES` (Phase 2) and `CONDUCT` (Phase 3) as they are.

```python
"""The wording lint for alert text (PHASE-3.md 7.5.2): Phase 1's patterns, Phase 2's never-write
phrases and Phase 3's conduct words.

REFERENCE IMPLEMENTATION. In the repository `violations` calls Phase 1's lint function on
`contracts/wording/forbidden-terms.txt` (the reconciliation names it) and adds `PHRASES` and
`CONDUCT` below; this copy holds Phase 1's patterns too, so the prototype tests run on their own.
"""

from __future__ import annotations

import re

PATTERNS = [
    r"\blaunder\w*",
    r"\blaundromat\w*",
    r"\bcriminal\w*",
    r"\bcrimes?\b",
    r"\bguilty\b",
    r"\bfraud\w*",
    r"\bsuspic\w*",
    r"\bsuspect\w*",
    r"\billicit\w*",
    r"\billegal\w*",
    r"\bdirty\s+money\b",
    r"\bcorrupt\w*",
    r"\bbrib\w*",
    r"\bterroris\w*",
    r"\bmules?\b",
    r"\bshell\s+compan\w*",
    r"\bfront\s+compan\w*",
    r"\bconceal\w*",
    r"\bevad\w*",
    r"\bevasion\b",
    r"\brisk[\s-]+scor\w*",
    r"\baccomplice\w*",
    r"\bwrongdo\w*",
]
FORBIDDEN = [re.compile(p, re.IGNORECASE) for p in PATTERNS]
# Phase 2 never-write phrases for ownership results (PHASE-2.md 7.2 rule 6)
PHRASES = [
    re.compile(p, re.IGNORECASE)
    for p in (r"\bis blocked\b", r"50 percent rule", r"no sanctions exposure")
]
# Phase 3: words that name the conduct a typology is named after, or a status the records cannot
# give (G5; `typology-detection-definitions.md` 16.1). "structural" and "layers" stay allowed.
CONDUCT = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bstructuring\b",
        r"\blayering\b",
        r"\bsmurf\w*",
        r"\bshell\b",
        r"\bis sanctioned\b",
        r"\bare sanctioned\b",
    )
]


def violations(text: str, masked: tuple[str, ...] = ()) -> list[str]:
    """Patterns `text` matches once the given captions are masked out."""
    for caption in sorted(masked, key=len, reverse=True):
        if caption:
            text = text.replace(caption, "<entity>")
    return [p.pattern for p in [*FORBIDDEN, *PHRASES, *CONDUCT] if p.search(text)]
```

### `detect/src/neonradar_detect/detectors/circular_flow.py`

Verbatim. Python, 159 lines. SHA-256 `9e1cd56923de75a373e3a2bb37701be9046525fa85ec992bee22a4fdc035ea03`.

```python
"""circular_flow 0.2.0: funds that return to the originating account, or to another account of
the same holder (PHASE-1.md 7.2 entry 4; PHASE-3.md 7.3.4).

Starts are payments of at least `min_amount`. From each start the expansion follows later
payments in the same currency, each between `min_return_ratio` and `1 + max_hop_gain` times the
first amount, within `max_window_days` of the first payment, through accounts not visited yet. A
cycle closes at the first account that is the origin (variant `same_account`) or, with
`same_holder`, another account of one of the origin's holders (variant `same_holder`), and is a
finding when it has `min_hops` to `max_hops` payments and returns at least `min_return_ratio` of
the first amount. A cycle back to the very account it left needs `min_hops_same_account` payments:
a payment straight back is the shape of a refund, a loan repaid or a cash pool sweep, and on the
development worlds a two-payment minimum added 130 alerts and no true one (50 on look-alikes, 50
on other typologies' scenarios, 30 on background activity; PHASE-3.md 7.6.5). A return to another
account of the same holder still counts from two payments. Time order makes each
cycle start at its earliest payment, so it is found once.

pattern_strength = 0.5 * return ratio + 0.3 * (1 - duration / window)
+ 0.2 * min(1, (hops - 1) / 4), clipped to [0, 1]: a heuristic for ordering the queue (PHASE-1.md
M1.9b), not a risk score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from neonradar_detect.expand import FrontierItem, Path, expand
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Hop
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "circular_flow"
VERSION = "0.2.0"
QUERIES = ("paid_hop.cypher", "paid_starts.cypher")
RETURN_POINT = {
    "same_account": "the originating account",
    "same_holder": "another account of the same holder",
}


@dataclass(frozen=True, slots=True)
class Params:
    min_hops: int = 2
    min_hops_same_account: int = 3
    max_hops: int = 6
    max_window_days: int = 14
    min_return_ratio: float = 0.8
    min_amount: float = 1000.0
    max_hop_gain: float = 0.05
    same_holder: bool = True
    max_starts: int = 1_000_000
    max_branching: int = 20
    max_frontier: int = 50_000


def _closes(path: Path, p: Params) -> str | None:
    """The variant if the last hop returns to the origin's side, else None."""
    origin = path.first.source
    target = path.last.target
    if target == origin:
        return "same_account"
    if p.same_holder and set(path.last.target_holders) & set(path.first.source_holders):
        return "same_holder"
    return None


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    if (
        not 2 <= p.min_hops <= p.max_hops <= 8
        or not p.min_hops <= p.min_hops_same_account <= p.max_hops
    ):
        raise ValueError("need 2 <= min_hops <= min_hops_same_account <= max_hops <= 8")
    span = timedelta(days=p.max_window_days)
    starts = source.paid_starts(p.min_amount, window.start, window.end, p.max_starts)

    def extend(path: Path, key: int) -> FrontierItem | None:
        if len(path.hops) >= p.max_hops or _closes(path, p) is not None:
            return None
        first = path.first
        return FrontierItem(
            key=key,
            account=path.last.target,
            after=path.last.ts,
            until=first.ts + span,
            min_amount=p.min_return_ratio * first.amount,
            max_amount=(1 + p.max_hop_gain) * first.amount,
            currency=first.currency,
            visited=tuple(sorted(set(path.accounts[1:]))),
        )

    def keep(path: Path, hop: Hop) -> bool:
        return True

    def accept(path: Path) -> bool:
        variant = _closes(path, p)
        if variant is None or len(path.hops) < p.min_hops:
            return False
        return variant != "same_account" or len(path.hops) >= p.min_hops_same_account

    cycles, stats = expand(
        starts,
        source.paid_hop,
        extend=extend,
        keep=keep,
        accept=accept,
        max_hops=p.max_hops,
        max_branching=p.max_branching,
        max_frontier=p.max_frontier,
    )
    findings = [f for f in (_finding(c, p) for c in cycles) if f is not None]
    return DetectorOutput(
        findings,
        {"starts": len(starts), "partial_paths": stats.partial_paths, "truncated": stats.truncated},
    )


def _finding(cycle: Path, p: Params) -> Finding | None:
    variant = _closes(cycle, p)
    first, last = cycle.first, cycle.last
    ratio = last.amount / first.amount
    if variant is None or ratio < p.min_return_ratio:
        return None
    hours = (last.ts - first.ts).total_seconds() / 3600
    window_hours = p.max_window_days * 24
    if hours > window_hours:
        return None
    hops = len(cycle.hops)
    strength = clip01(
        0.5 * min(1.0, ratio) + 0.3 * (1 - hours / window_hours) + 0.2 * min(1.0, (hops - 1) / 4)
    )
    origin = first.source
    subjects = [Subject(origin, "origin")]
    subjects += [Subject(h, "origin_holder") for h in sorted(first.source_holders)]
    if variant == "same_holder":
        subjects.append(Subject(last.target, "return_account"))
    metrics = {
        "cycle_length": hops,
        "sent_amount": round(first.amount, 2),
        "returned_amount": round(last.amount, 2),
        "currency": first.currency,
        "duration_hours": round(hours, 1),
        "duration_days": max(1, math.ceil(hours / 24)),
        "return_ratio": round(ratio, 4),
        "return_point": RETURN_POINT[variant],
    }
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=origin,
        node_ids=tuple(sorted(set(cycle.accounts))),
        edge_ids=tuple(sorted(h.edge_id for h in cycle.hops)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple((h.edge_id,) for h in cycle.hops),
        window=(first.ts, last.ts),
        activity=True,
    )
```

### `detect/src/neonradar_detect/queries/activity_counts.cypher`

Verbatim. Cypher, 7 lines. SHA-256 `52a059a2e30ff808d235dfd80118599c89b434eeaedef7dfa51f07291d4924c0`.

```cypher
// activity_counts: number of PAID relationships into or out of each account in [$start, $end).
// Parameters: $ids, $start, $end. One row per account, by id (0 when there is none).
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})
RETURN a.id AS account,
       COUNT { MATCH (a)-[r:PAID]-() WHERE r.ts >= datetime($start) AND r.ts < datetime($end) } AS payments
ORDER BY account
```

### `detect/src/neonradar_detect/queries/appointment_counts.cypher`

Verbatim. Cypher, 7 lines. SHA-256 `9d731c20b54f278bbf16f6f05998810c6a0a3072cf0ce4a0ecda1c74fbb46918`.

```cypher
// appointment_counts: number of DIRECTOR_OF relationships each of $ids starts that still hold on $as_of (no
// end_date, or one after it). Parameters: $ids, $as_of (an ISO date). One row per id, by id.
UNWIND $ids AS person_id
MATCH (p:Entity {id: person_id})
RETURN p.id AS id,
       COUNT { (p)-[d:DIRECTOR_OF]->() WHERE coalesce(d.end_date, '') = '' OR d.end_date > $as_of } AS appointments
ORDER BY id
```

### `detect/src/neonradar_detect/queries/cash_profiles.cypher`

Verbatim. Cypher, 24 lines. SHA-256 `97e8eded4423ebb2e192f539eb76557e87a0e968d117477044e5d1b7fcb1f331`.

```cypher
// cash_profiles: companies whose accounts received cash deposits in $currency in [$prior_start, $end): sums in
// pence (each amount rounded to pence first, so sums are exact) and counts for [$start, $end) and for
// [$prior_start, $start), the sector, and the postcode and city of the registered address (the smallest
// postcode when there are several). By holder id. Parameters: $prior_start, $start, $end, $currency, $limit.
MATCH (c:Company)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(:Account)
WHERE r.channel = 'cash_deposit' AND r.currency = $currency
  AND r.ts >= datetime($prior_start) AND r.ts < datetime($end)
WITH c, a, r, toInteger(round(r.amount * 100)) AS pence, r.ts >= datetime($start) AS recent
WITH c, collect(DISTINCT a.id) AS accounts,
     sum(CASE WHEN recent THEN pence ELSE 0 END) AS window_pence, sum(CASE WHEN recent THEN 1 ELSE 0 END) AS window_deposits,
     sum(CASE WHEN recent THEN 0 ELSE pence END) AS prior_pence, sum(CASE WHEN recent THEN 0 ELSE 1 END) AS prior_deposits
ORDER BY c.id
LIMIT $limit
OPTIONAL CALL (c) {
  MATCH (c)-[h:HAS_ADDRESS]->(addr:Address)
  WHERE h.role = 'registered'
  RETURN coalesce(addr.postal_code, '') AS postal_code, coalesce(addr.city, '') AS city
  ORDER BY postal_code, city
  LIMIT 1
}
RETURN c.id AS holder, coalesce(c.sector, '') AS sector, coalesce(postal_code, '') AS postal_code,
       coalesce(city, '') AS city, apoc.coll.sort(accounts) AS accounts,
       window_pence, window_deposits, prior_pence, prior_deposits
ORDER BY holder
```

### `detect/src/neonradar_detect/queries/company_account_histories.cypher`

Verbatim. Cypher, 21 lines. SHA-256 `df68a8a6c3e8092c2673f6477cf9df4f9cec06f3285c5ff73db77edf6069a6d5`.

```cypher
// company_account_histories: customer accounts held by a company filed as dormant, or incorporated on or after
// $incorporated_since, with at least $min_payments payments in [$start, $end) (those payments only, in order of
// (ts, id)). Parameters: $incorporated_since, $start, $end, $min_payments, $limit.
MATCH (c:Company)-[:HOLDS_ACCOUNT]->(a:Account)
WHERE coalesce(a.account_kind, 'customer') <> 'cash_ledger'
  AND (toUpper(coalesce(c.accounts_category, '')) = 'DORMANT'
       OR (size(coalesce(c.incorporation_date, '')) = 10 AND c.incorporation_date >= $incorporated_since))
WITH DISTINCT a
CALL (a) {
  MATCH (a)-[r:PAID]-(x:Account)
  WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  WITH r, x, startNode(r) = a AS out
  ORDER BY r.ts, r.id
  RETURN collect({edge_id: r.id, counterparty: x.id, ts: r.ts, amount: r.amount, currency: r.currency,
                  channel: coalesce(r.channel, ''), direction: CASE WHEN out THEN 'out' ELSE 'in' END}) AS pays
}
WITH a, pays WHERE size(pays) >= $min_payments
WITH a, pays ORDER BY a.id LIMIT $limit
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders, pays
ORDER BY account
```

### `detect/src/neonradar_detect/queries/counterparty_info.cypher`

Verbatim. Cypher, 8 lines. SHA-256 `b7e5ced9d7f025f4dcec1b3ddf74c36dd42b2c67bd810f87f28abc7b629460ff`.

```cypher
// counterparty_info: each account's opening date, its holders (sorted) and the labels they carry.
// Parameters: $ids. By account id.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) UNWIND labels(h) AS label RETURN DISTINCT label ORDER BY label } AS holder_labels,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders
ORDER BY account
```

### `detect/src/neonradar_detect/queries/edge_info.cypher`

Verbatim. Cypher, 34 lines. SHA-256 `ad3115e4a2f5a220c5b4ebf9fdd26c3a05c5713350b66c0dbd1ea039ffc45d6f`.

```cypher
// edge_info: the evidence relationships with their ends and the properties the wording uses.
// Parameters: $ids. Relationship ids are unique per type (C2), so each type is sought by its own index.
UNWIND $ids AS rid
CALL (rid) {
    MATCH (s)-[r:PAID {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:OWNS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:CONTROLS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:CONSOLIDATES {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:DIRECTOR_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HOLDS_ACCOUNT {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HAS_ADDRESS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:REPRESENTS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:FAMILY_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:ASSOCIATE_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HOLDS_POSITION {id: rid}]->(t) RETURN r, s, t
}
RETURN r.id AS id, type(r) AS type, s.id AS source, t.id AS target, r.synthetic AS synthetic,
       r.amount AS amount, coalesce(r.currency, '') AS currency, r.ts AS ts, coalesce(r.channel, '') AS channel,
       r.share_pct_min AS share_min, r.share_pct_max AS share_max,
       coalesce(r.share_min_exclusive, false) AS share_min_exclusive,
       coalesce(r.share_max_exclusive, false) AS share_max_exclusive,
       coalesce(r.role, r.relationship, '') AS role, coalesce(r.control_type, '') AS control_type,
       coalesce(r.start_date, '') AS start_date, coalesce(r.end_date, '') AS end_date
ORDER BY id
```

### `detect/src/neonradar_detect/queries/entities.cypher`

Verbatim. Cypher, 11 lines. SHA-256 `7d5af74ba1e500d54da76e4fce83dcfb74e6c29f7a664b87614c53955dff0d82`.

```cypher
// entities: what detectors read about entities. Parameters: $ids. By id.
UNWIND $ids AS entity_id
MATCH (n:Entity {id: entity_id})
RETURN n.id AS id, labels(n) AS labels, coalesce(n.schema, '') AS schema, coalesce(n.jurisdiction, '') AS jurisdiction,
       coalesce(n.incorporation_date, '') AS incorporation_date, n.synthetic AS synthetic,
       coalesce(n.accounts_category, '') AS accounts_category, coalesce(n.sector, '') AS sector,
       coalesce(n.status, '') AS status, coalesce(n.dissolution_date, '') AS dissolution_date,
       coalesce(n.datasets, []) AS datasets, coalesce(n.psc_statements, []) AS psc_statements,
       coalesce(n.full, '') AS full, coalesce(n.postal_code, '') AS postal_code, coalesce(n.city, '') AS city,
       coalesce(n.countries, []) AS countries
ORDER BY id
```

### `detect/src/neonradar_detect/queries/evidence.cypher`

Verbatim. Cypher, 33 lines. SHA-256 `fc0cca04bbea1be69ed2f01eeee36cbc19cc0cb99721eeb1da110dd44166c01c`.

```cypher
// evidence: the nodes and relationships of one alert, re-selected by id (C4 evidence.query).
// Parameters: $node_ids, $edge_ids. `neonradar detect verify-alert` checks that both lists come back whole.
MATCH (n:Entity)
WHERE n.id IN $node_ids
WITH collect(n) AS nodes
CALL () {
  UNWIND $edge_ids AS rid
  CALL (rid) {
      MATCH (s)-[r:PAID {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:OWNS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:CONTROLS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:CONSOLIDATES {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:DIRECTOR_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HOLDS_ACCOUNT {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HAS_ADDRESS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:REPRESENTS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:FAMILY_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:ASSOCIATE_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HOLDS_POSITION {id: rid}]->(t) RETURN r
  }
  RETURN collect(r) AS rels
}
RETURN [n IN nodes | n.id] AS node_ids, [r IN rels | r.id] AS edge_ids, nodes, rels
```

### `detect/src/neonradar_detect/queries/flagged_ids.cypher`

Verbatim. Cypher, 5 lines. SHA-256 `b6e2a6f804d36821dcadb43ce398921415670df2a052524b832217fe1b039282`.

```cypher
// flagged_ids: ids of the :Entity nodes with one flag label, sorted. {{flag}} comes from a fixed list.
// lint-values: flag=Sanctioned,PEP,RCA
MATCH (n:Entity:{{flag}})
RETURN n.id AS id
ORDER BY id
```

### `detect/src/neonradar_detect/queries/flows_by_inbound.cypher`

Verbatim. Cypher, 20 lines. SHA-256 `0dc7217c58faf6658f93870df343223edacb5490c2635b2e82333dcf78eeff58`.

```cypher
// flows_by_inbound: customer accounts with at least $min_counterparties distinct payers in one bucket of
// $bucket_hours counted from $start (payments of $channel only, when it is not null), with every payment
// in and out in [$start, $end). Parameters: $min_counterparties, $start, $end, $channel, $bucket_hours, $limit.
MATCH (p:Account)-[r:PAID]->(a:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end) AND ($channel IS NULL OR r.channel = $channel)
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger'
WITH a, duration.inSeconds(datetime($start), r.ts).seconds / ($bucket_hours * 3600) AS bucket, count(DISTINCT p) AS payers
WHERE payers >= $min_counterparties
WITH DISTINCT a
ORDER BY a.id
LIMIT $limit
RETURN a.id AS account,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders,
       COLLECT { MATCH (x:Account)-[r:PAID]->(a) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS inflows,
       COLLECT { MATCH (a)-[r:PAID]->(x:Account) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS outflows
ORDER BY account
```

### `detect/src/neonradar_detect/queries/flows_by_outbound.cypher`

Verbatim. Cypher, 20 lines. SHA-256 `ef5319939bb1ba4bca3423bf2ce6d96e5db2e89ee480b063501bed148a3c514d`.

```cypher
// flows_by_outbound: customer accounts with at least $min_counterparties distinct payees in one bucket of
// $bucket_hours counted from $start, with every payment in and out in [$start, $end).
// Parameters: $min_counterparties, $start, $end, $bucket_hours, $limit.
MATCH (a:Account)-[r:PAID]->(p:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger'
WITH a, duration.inSeconds(datetime($start), r.ts).seconds / ($bucket_hours * 3600) AS bucket, count(DISTINCT p) AS payees
WHERE payees >= $min_counterparties
WITH DISTINCT a
ORDER BY a.id
LIMIT $limit
RETURN a.id AS account,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders,
       COLLECT { MATCH (x:Account)-[r:PAID]->(a) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS inflows,
       COLLECT { MATCH (a)-[r:PAID]->(x:Account) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS outflows
ORDER BY account
```

### `detect/src/neonradar_detect/queries/holder_cash_deposits.cypher`

Verbatim. Cypher, 15 lines. SHA-256 `d0d65dc4ca6ef202174deb5060a82a2daec40307decbaf3d83a2438c3c5adf22`.

```cypher
// holder_cash_deposits: holders whose accounts received at least $min_in_band cash deposits of $band_low to
// $threshold (both included) in [$start, $end), with every cash deposit of the period into any of their
// accounts, in order of (ts, id). Parameters: $band_low, $threshold, $min_in_band, $start, $end, $limit.
MATCH (h:LegalEntity)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(:Account)
WHERE r.channel = 'cash_deposit' AND r.ts >= datetime($start) AND r.ts < datetime($end)
  AND r.amount >= $band_low AND r.amount <= $threshold
WITH h, count(DISTINCT r) AS in_band
WHERE in_band >= $min_in_band
WITH h ORDER BY h.id LIMIT $limit
RETURN h.id AS holder,
       COLLECT { MATCH (h)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(b:Account)
                 WHERE r.channel = 'cash_deposit' AND r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN {ts: r.ts, edge_id: r.id, account: a.id, branch: b.id, amount: r.amount, currency: r.currency}
                 ORDER BY r.ts, r.id } AS deposits
ORDER BY holder
```

### `detect/src/neonradar_detect/queries/hubs.cypher`

Verbatim. Cypher, 15 lines. SHA-256 `2f618dd6c074a080bf10de6cd2e0229c52f47b119ca0e284ccaad7e8d961a13e`.

```cypher
// hubs: nodes with {{rel_type}} relationships to at least $min_members distinct organisations, by node id,
// each with those relationships by id. {{rel_type}} comes from a fixed list. Parameters: $min_members, $limit.
// lint-values: rel_type=REPRESENTS,DIRECTOR_OF
MATCH (s:Entity)-[r:{{rel_type}}]->(o:Organization)
WITH s, count(DISTINCT o) AS members
WHERE members >= $min_members
WITH s ORDER BY s.id LIMIT $limit
RETURN s.id AS hub,
       COLLECT { MATCH (s)-[r:{{rel_type}}]->(t:Organization)
                 RETURN {rel_type: type(r), rel_id: r.id, source: s.id, target: t.id, share_min: null, share_max: null,
                         share_min_exclusive: false, share_max_exclusive: false,
                         is_nominee: coalesce(r.is_nominee, false), role: coalesce(r.role, ''),
                         start_date: coalesce(r.start_date, ''), end_date: coalesce(r.end_date, ''), control_type: ''}
                 ORDER BY r.id } AS links
ORDER BY hub
```

### `detect/src/neonradar_detect/queries/links_from.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `29bcafbee65a846de052c055760e76b09e2355d8b6978289083df5fa34fa2914`.

```cypher
// links_from: registry relationships of the types in $types that start at each of $ids, by id, then by
// relationship id. Parameters: $ids, $types (relationship type names from the registry list in source.py).
UNWIND $ids AS entity_id
MATCH (s:Entity {id: entity_id})-[r]->(t)
WHERE type(r) IN $types
RETURN s.id AS key, type(r) AS rel_type, r.id AS rel_id, s.id AS source, t.id AS target,
       r.share_pct_min AS share_min, r.share_pct_max AS share_max,
       coalesce(r.share_min_exclusive, false) AS share_min_exclusive,
       coalesce(r.share_max_exclusive, false) AS share_max_exclusive, coalesce(r.is_nominee, false) AS is_nominee,
       coalesce(r.role, r.relationship, '') AS role, coalesce(r.start_date, '') AS start_date,
       coalesce(r.end_date, '') AS end_date, coalesce(r.control_type, '') AS control_type
ORDER BY key, rel_id
```

### `detect/src/neonradar_detect/queries/links_into.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `722cb359e9fbdff19af1a28fdaeaf2cb3b58ff806c0ebdaa65ba60bd805c2692`.

```cypher
// links_into: registry relationships of the types in $types that end at each of $ids, by id, then by
// relationship id. Parameters: $ids, $types (relationship type names from the registry list in source.py).
UNWIND $ids AS entity_id
MATCH (s)-[r]->(t:Entity {id: entity_id})
WHERE type(r) IN $types
RETURN t.id AS key, type(r) AS rel_type, r.id AS rel_id, s.id AS source, t.id AS target,
       r.share_pct_min AS share_min, r.share_pct_max AS share_max,
       coalesce(r.share_min_exclusive, false) AS share_min_exclusive,
       coalesce(r.share_max_exclusive, false) AS share_max_exclusive, coalesce(r.is_nominee, false) AS is_nominee,
       coalesce(r.role, r.relationship, '') AS role, coalesce(r.start_date, '') AS start_date,
       coalesce(r.end_date, '') AS end_date, coalesce(r.control_type, '') AS control_type
ORDER BY key, rel_id
```

### `detect/src/neonradar_detect/queries/listed_entities.cypher`

Verbatim. Cypher, 10 lines. SHA-256 `adb9de51400d6083f587687df0a331fd4bdc550f95ac2f3762653baf9a526788`.

```cypher
// listed_entities: every :Sanctioned entity with its labels, datasets and the :Sanction nodes it is SUBJECT_OF
// (by sanction id). By entity id.
MATCH (e:Entity:Sanctioned)
RETURN e.id AS entity, labels(e) AS labels, coalesce(e.datasets, []) AS datasets,
       COLLECT { MATCH (e)-[:SUBJECT_OF]->(s:Sanction)
                 RETURN {id: s.id, datasets: coalesce(s.datasets, []), authority: coalesce(s.authority, ''),
                         program: coalesce(s.program, ''), provisions: coalesce(s.provisions, []),
                         start_date: coalesce(s.start_date, ''), end_date: coalesce(s.end_date, '')}
                 ORDER BY s.id } AS sanctions
ORDER BY entity
```

### `detect/src/neonradar_detect/queries/node_info.cypher`

Verbatim. Cypher, 11 lines. SHA-256 `b19dfc376aeb4a701f086cc53f6ae39691dd6b9ff202325e578f2e2b8cb59590`.

```cypher
// node_info: evidence nodes, and the holders of evidence accounts, for the policy and the wording.
// Parameters: $ids. One row per node, by id; holders of an account sorted by id.
UNWIND $ids AS node_id
MATCH (n:Entity {id: node_id})
OPTIONAL MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(n)
WITH n, h ORDER BY h.id
WITH n, collect(h {.id, labels: labels(h), caption: coalesce(h.caption, h.id), .synthetic,
                   datasets: coalesce(h.datasets, [])}) AS holders
RETURN n.id AS id, labels(n) AS labels, coalesce(n.caption, n.id) AS caption, n.synthetic AS synthetic,
       coalesce(n.datasets, []) AS datasets, holders
ORDER BY id
```

### `detect/src/neonradar_detect/queries/ownership_cycles.cypher`

Verbatim. Cypher, 18 lines. SHA-256 `7823a26e6bb4562052508618a4248c2058a5605d3655c4b0ea03c57519450029`.

```cypher
// ownership_cycles: simple cycles of 2 to {{max_hops}} OWNS relationships that still hold on $as_of (no end_date,
// or one after it), each once, starting at its smallest node id (node_ids[0] = node_ids[-1]). Ordered by the
// node ids. Parameters: $limit, $as_of (an ISO date).
// lint-values: max_hops=2,6,8
MATCH p = (a:LegalEntity)-[:OWNS*2..{{max_hops}}]->(a)
WHERE all(r IN relationships(p) WHERE coalesce(r.end_date, '') = '' OR r.end_date > $as_of)
  AND all(n IN nodes(p) WHERE n.id >= a.id)
  AND size(tail(nodes(p))) = size(apoc.coll.toSet(tail(nodes(p))))
WITH [n IN nodes(p) | n.id] AS node_ids, relationships(p) AS rels
ORDER BY node_ids
LIMIT $limit
RETURN node_ids,
       [r IN rels | {rel_type: type(r), rel_id: r.id, source: startNode(r).id, target: endNode(r).id,
                     share_min: r.share_pct_min, share_max: r.share_pct_max,
                     share_min_exclusive: coalesce(r.share_min_exclusive, false),
                     share_max_exclusive: coalesce(r.share_max_exclusive, false),
                     is_nominee: coalesce(r.is_nominee, false), role: coalesce(r.role, ''),
                     start_date: coalesce(r.start_date, ''), end_date: coalesce(r.end_date, ''), control_type: ''}] AS links
```

### `detect/src/neonradar_detect/queries/ownership_paths.cypher`

Verbatim. Cypher, 21 lines. SHA-256 `e00a12a58fa161a644be9177ca80655f1763984234a363bb141fa97f0cffc7b3`.

```cypher
// ownership_paths: maximal paths of 1 to {{max_hops}} OWNS relationships that still hold on $as_of (no end_date,
// or one after it), from a top (a legal entity no such OWNS points to) that owns an organisation, through
// organisations, to a leaf company (one that owns no organisation through such an OWNS), never repeating a
// node. Ordered by the node ids along the path. Parameters: $limit, $as_of (an ISO date).
// lint-values: max_hops=2,6,8
MATCH p = (top:LegalEntity)-[:OWNS*1..{{max_hops}}]->(leaf:Company)
WHERE all(r IN relationships(p) WHERE coalesce(r.end_date, '') = '' OR r.end_date > $as_of)
  AND NOT EXISTS { ()-[o:OWNS]->(top) WHERE coalesce(o.end_date, '') = '' OR o.end_date > $as_of }
  AND all(n IN tail(nodes(p)) WHERE n:Organization)
  AND NOT EXISTS { (leaf)-[o:OWNS]->(:Organization) WHERE coalesce(o.end_date, '') = '' OR o.end_date > $as_of }
  AND size(nodes(p)) = size(apoc.coll.toSet(nodes(p)))
WITH [n IN nodes(p) | n.id] AS node_ids, relationships(p) AS rels
ORDER BY node_ids
LIMIT $limit
RETURN node_ids,
       [r IN rels | {rel_type: type(r), rel_id: r.id, source: startNode(r).id, target: endNode(r).id,
                     share_min: r.share_pct_min, share_max: r.share_pct_max,
                     share_min_exclusive: coalesce(r.share_min_exclusive, false),
                     share_max_exclusive: coalesce(r.share_max_exclusive, false),
                     is_nominee: coalesce(r.is_nominee, false), role: coalesce(r.role, ''),
                     start_date: coalesce(r.start_date, ''), end_date: coalesce(r.end_date, ''), control_type: ''}] AS links
```

### `detect/src/neonradar_detect/queries/paid_hop.cypher`

Verbatim. Cypher, 13 lines. SHA-256 `825389f6ae90262a62c4c72a5fc77233afbb81861b344ff8a2ff6358f8a9cad2`.

```cypher
// paid_hop: the next hop of every partial path (PHASE-3.md 7.1.3). Parameters: $frontier, a list of maps
// {key, account, after, until, min_amount, max_amount, currency, visited}; after and until are ISO strings.
// A hop leaves the frontier account after `after` and at or before `until`, in the currency, with an
// amount in [min_amount, max_amount], to a customer account not visited yet. By key, then (ts, id).
UNWIND $frontier AS f
MATCH (a:Entity:Account {id: f.account})-[r:PAID]->(b:Account)
WHERE r.ts > datetime(f.after) AND r.ts <= datetime(f.until)
  AND r.amount >= f.min_amount AND r.amount <= f.max_amount AND r.currency = f.currency
  AND NOT b.id IN f.visited AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
RETURN f.key AS key, r.id AS edge_id, a.id AS source, b.id AS target, r.ts AS ts, r.amount AS amount,
       r.currency AS currency,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(b) RETURN h.id ORDER BY h.id } AS target_holders
ORDER BY key, ts, edge_id
```

### `detect/src/neonradar_detect/queries/paid_starts.cypher`

Verbatim. Cypher, 10 lines. SHA-256 `59fca10b4c77e4232c3e61daf3fbc188cecd63c6444f3506ad1c492d7cfa1d04`.

```cypher
// paid_starts: payments of at least $min_amount in [$start, $end) between customer accounts, with the
// holders of both ends (sorted), in order of (ts, id). Parameters: $min_amount, $start, $end, $limit.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end) AND r.amount >= $min_amount
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
RETURN r.id AS edge_id, a.id AS source, b.id AS target, r.ts AS ts, r.amount AS amount, r.currency AS currency,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS source_holders,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(b) RETURN h.id ORDER BY h.id } AS target_holders
ORDER BY ts, edge_id
LIMIT $limit
```

### `detect/src/neonradar_detect/queries/paid_time_range.cypher`

Verbatim. Cypher, 3 lines. SHA-256 `531f75523e4f3c8e057956a1cb2e698199b0c306cba11503503801b854ffcde8`.

```cypher
// paid_time_range: the first and last PAID time in the graph (null, null when there is none).
MATCH ()-[r:PAID]->()
RETURN min(r.ts) AS first, max(r.ts) AS last
```

### `detect/src/neonradar_detect/queries/paid_times.cypher`

Verbatim. Cypher, 8 lines. SHA-256 `22369dd07e2ce8eccb62429782d48d82a4ec34dae0c6ccda74140df3273a774e`.

```cypher
// paid_times: for each (payer account, payee account) pair, the times of every PAID between them, sorted;
// pairs with none are left out. Parameters: $pairs, a list of [payer, payee].
UNWIND $pairs AS pair
MATCH (a:Entity:Account {id: pair[0]})-[r:PAID]->(b:Entity:Account {id: pair[1]})
WITH a.id AS payer, b.id AS payee, r.ts AS ts
ORDER BY payer, payee, ts
RETURN payer, payee, collect(ts) AS times
ORDER BY payer, payee
```

### `detect/src/neonradar_detect/queries/payments_among.cypher`

Verbatim. Cypher, 6 lines. SHA-256 `21b3acc815c0441c5c1875fc4015760d2fe43d908c38f0a6a5e1c3d52bc3950b`.

```cypher
// payments_among: (edge id, payer, payee) for every PAID between two of $ids in [$start, $end), by edge id.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})-[r:PAID]->(b:Account)
WHERE b.id IN $ids AND r.ts >= datetime($start) AND r.ts < datetime($end)
RETURN r.id AS edge_id, a.id AS payer, b.id AS payee
ORDER BY edge_id
```

### `detect/src/neonradar_detect/queries/payments_from.cypher`

Verbatim. Cypher, 8 lines. SHA-256 `1a942a31849ce1d50621a19e28205df128e2791ac41f4b25e8ce26a7a48c5143`.

```cypher
// payments_from: each account's outgoing payments in [$start, $end), in order of (ts, id).
// Parameters: $ids, $start, $end. Accounts without one are left out.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})-[r:PAID]->(x:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
RETURN a.id AS account, r.id AS edge_id, x.id AS counterparty, r.ts AS ts, r.amount AS amount, r.currency AS currency,
       coalesce(r.channel, '') AS channel
ORDER BY account, ts, edge_id
```

### `detect/src/neonradar_detect/queries/payments_into.cypher`

Verbatim. Cypher, 8 lines. SHA-256 `bdc849188e394687a4e14307cfda34d2a259bfc232b4c4595b1d37ad20bc35f5`.

```cypher
// payments_into: each account's incoming payments in [$start, $end), in order of (ts, id).
// Parameters: $ids, $start, $end. Accounts without one are left out.
UNWIND $ids AS account_id
MATCH (x:Account)-[r:PAID]->(a:Entity:Account {id: account_id})
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
RETURN a.id AS account, r.id AS edge_id, x.id AS counterparty, r.ts AS ts, r.amount AS amount, r.currency AS currency,
       coalesce(r.channel, '') AS channel
ORDER BY account, ts, edge_id
```

### `detect/src/neonradar_detect/queries/quiet_account_histories.cypher`

Verbatim. Cypher, 32 lines. SHA-256 `9ac51af0ab4d4433387020f0379acb2b4e7108e0f7c41b9205b5659df04aec51`.

```cypher
// quiet_account_histories: customer accounts with a quiet period that ends with a payment in
// [$start, $end): at least $min_gap_days from a payment, or from the opening date when that is on or after
// $history_start, to that payment, with at most $max_quiet_payments payments between them totalling at most
// $max_quiet_amount. Each with every payment of the account before $end, in order of (ts, id).
// Parameters: $min_gap_days, $max_quiet_payments, $max_quiet_amount, $history_start, $start, $end, $limit.
MATCH (a:Account)
WHERE coalesce(a.account_kind, 'customer') <> 'cash_ledger'
CALL (a) {
  MATCH (a)-[r:PAID]-(x:Account)
  WHERE r.ts < datetime($end)
  WITH r, x, startNode(r) = a AS out
  ORDER BY r.ts, r.id
  RETURN collect({edge_id: r.id, counterparty: x.id, ts: r.ts, amount: r.amount, currency: r.currency,
                  channel: coalesce(r.channel, ''), direction: CASE WHEN out THEN 'out' ELSE 'in' END}) AS pays
}
WITH a, pays, size(pays) AS n
WHERE n > 0
WITH a, pays, n,
     CASE WHEN size(coalesce(a.opening_date, '')) = 10 AND a.opening_date >= $history_start
          THEN datetime(a.opening_date + 'T00:00:00Z') ELSE null END AS opened
WITH a, pays, [j IN range(0, n - 1) WHERE pays[j].ts >= datetime($start) AND pays[j].ts < datetime($end) AND (
       any(m IN range(0, $max_quiet_payments) WHERE j - m - 1 >= 0
           AND duration.inSeconds(pays[j - m - 1].ts, pays[j].ts).seconds >= $min_gap_days * 86400
           AND reduce(s = 0.0, i IN range(j - m, j - 1) | s + pays[i].amount) <= $max_quiet_amount)
       OR (opened IS NOT NULL AND j <= $max_quiet_payments
           AND reduce(s = 0.0, i IN range(0, j - 1) | s + pays[i].amount) <= $max_quiet_amount
           AND duration.inSeconds(opened, pays[j].ts).seconds >= $min_gap_days * 86400))] AS ends
WHERE size(ends) > 0
WITH a, pays ORDER BY a.id LIMIT $limit
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders, pays
ORDER BY account
```

### `detect/src/neonradar_detect/queries/recent_account_components_drop.cypher`

Verbatim. Cypher, 4 lines. SHA-256 `744dd21c8d2e5eb06c4f4acfee6485f60bfb0e69e95c9ac6e81e2879dce5df86`.

```cypher
// Ring variant, step 3: drop the projection (always, also after a failure).
CALL gds.graph.drop($graph_name, false)
YIELD graphName
RETURN graphName
```

### `detect/src/neonradar_detect/queries/recent_account_components_project.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `d3eae91f34a019a2f6ee6d127c6835546c89ae93f69a520044251b29c203c893`.

```cypher
// Ring variant, step 1: project the recent-account payments (recent_account_edges) as an undirected graph.
// $graph_name is unique per call ("nr-ring-" and 32 random hex digits); the source drops it in a finally block.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND size(coalesce(a.opening_date, '')) = 10 AND size(coalesce(b.opening_date, '')) = 10
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
  AND date(a.opening_date) <= date(r.ts) AND date(r.ts) <= date(a.opening_date) + duration({days: $new_days})
  AND date(b.opening_date) <= date(r.ts) AND date(r.ts) <= date(b.opening_date) + duration({days: $new_days})
WITH a, b, count(r) AS payments
WITH gds.graph.project($graph_name, a, b, {relationshipProperties: {payments: payments}},
                       {undirectedRelationshipTypes: ['*'], readConcurrency: 4}) AS g
RETURN g.graphName AS graph_name, g.nodeCount AS node_count, g.relationshipCount AS relationship_count
```

### `detect/src/neonradar_detect/queries/recent_account_components_wcc.cypher`

Verbatim. Cypher, 6 lines. SHA-256 `31656585f67768839a64d9d56a5d0366153c97121f4df2c4e123d7ca7fb5cdb9`.

```cypher
// Ring variant, step 2: weakly connected components (concurrency 4; components are stable, ids are not, so
// the source names each component by its smallest account id).
CALL gds.wcc.stream($graph_name, {concurrency: 4})
YIELD nodeId, componentId
RETURN gds.util.asNode(nodeId).id AS account_id, componentId AS component_id
ORDER BY component_id, account_id
```

### `detect/src/neonradar_detect/queries/recent_account_edges.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `f61d28bb395c464e467717efa7445985fa9ad8ad5b8c6d629854e0e5339786b4`.

```cypher
// recent_account_edges: the PAID relationships in [$start, $end) whose two customer accounts were each
// opened at most $new_days before the payment (the projection of the ring variant; MemSource reference:
// recent_account_components). Parameters: $new_days, $start, $end.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND size(coalesce(a.opening_date, '')) = 10 AND size(coalesce(b.opening_date, '')) = 10
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
  AND date(a.opening_date) <= date(r.ts) AND date(r.ts) <= date(a.opening_date) + duration({days: $new_days})
  AND date(b.opening_date) <= date(r.ts) AND date(r.ts) <= date(b.opening_date) + duration({days: $new_days})
RETURN r.ts AS ts, r.id AS edge_id, a.id AS source, b.id AS target, r.amount AS amount, r.currency AS currency,
       coalesce(r.channel, '') AS channel
ORDER BY ts, edge_id
```

### `detect/src/neonradar_detect/queries/registered_clusters.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `c992251caa519ec723fbe8372ef5c151da6fc991b0b4a948704104c76c6db9f6`.

```cypher
// registered_clusters: addresses with at least $min_members organisations whose HAS_ADDRESS role is
// registered (with $active_only, only organisations without a dissolution date and not in an inactive status),
// by address id; members by organisation id. Parameters: $min_members, $active_only, $limit.
MATCH (o:Organization)-[h:HAS_ADDRESS]->(addr:Address)
WHERE h.role = 'registered' AND (NOT $active_only OR (coalesce(o.dissolution_date, '') = ''
                       AND NOT toLower(coalesce(o.status, '')) IN ['dissolved', 'converted-closed', 'removed', 'closed']))
WITH addr, o, h ORDER BY o.id
WITH addr, collect([o.id, h.id]) AS members
WHERE size(members) >= $min_members
RETURN addr.id AS address, coalesce(addr.full, '') AS full, coalesce(addr.postal_code, '') AS postal_code, members
ORDER BY address
LIMIT $limit
```

### `detect/src/neonradar_detect/queries/registered_count_quantile.cypher`

Verbatim. Cypher, 12 lines. SHA-256 `b5e71fdbe95e606d8f42165dfb9464751d55d5684a76f53b8a6ca553b6b044c7`.

```cypher
// registered_count_quantile: the nearest-rank $q quantile of the number of registered organisations per
// address, over addresses with at least one: the value at position max(1, ceil($q * n)) in ascending order;
// 0 when no address has one. Parameters: $q, $active_only.
MATCH (o:Organization)-[h:HAS_ADDRESS]->(addr:Address)
WHERE h.role = 'registered' AND (NOT $active_only OR (coalesce(o.dissolution_date, '') = ''
                       AND NOT toLower(coalesce(o.status, '')) IN ['dissolved', 'converted-closed', 'removed', 'closed']))
WITH addr, count(DISTINCT o) AS members
WITH members ORDER BY members
WITH collect(members) AS counts
RETURN CASE WHEN size(counts) = 0 THEN 0
            ELSE counts[CASE WHEN ceil($q * size(counts)) < 1 THEN 0 ELSE toInteger(ceil($q * size(counts))) - 1 END]
       END AS value
```

### `detect/typologies/circular_flow.yaml`

Verbatim. YAML, 84 lines. SHA-256 `772d7daa49b0c217e923926fdb6124e3d81fe8a78f9d9b44fcd1585a429559e7`.

```yaml
slug: circular_flow
name: Round-tripping or circular flows
shape_name: funds returning to where they started
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  Funds leave an account, pass through other accounts and return to the originator or to another account of the
  same holder.
doc: docs/typologies/circular-flow.md
citations:
- fatf_egmont_tbml_indicators_2021
- fatf_egmont_concealment_2018
- ffiec_appendix_f
- fatf_pml_2018
graph_pattern: >-
  A directed cycle of PAID relationships starting and ending at the same Account (three hops or more) or at two
  Accounts held by the same LegalEntity (two hops or more), with time-ordered hops, near-equal amounts and a short
  total duration.
parameters:
  min_hops:
    default: 2
    min: 2
    max: 8
  min_hops_same_account:
    default: 3
    min: 2
    max: 8
  max_hops:
    default: 6
    min: 1
    max: 8
  max_window_days:
    default: 14
    min: 1
    max: 140
  min_return_ratio:
    default: 0.8
    min: 0.0
    max: 1.0
  min_amount:
    default: 1000.0
    min: 0.0
    max: 10000.0
  max_hop_gain:
    default: 0.05
    min: 0.0
    max: 0.5
  same_holder:
    default: true
  max_starts:
    default: 1000000
    min: 1
    max: 10000000
  max_branching:
    default: 20
    min: 1
    max: 200
  max_frontier:
    default: 50000
    min: 1
    max: 500000
metrics:
- cycle_length
- sent_amount
- returned_amount
- currency
- duration_hours
- duration_days
- return_ratio
- return_point
wording:
  headline_structural: Funds returned to {return_point} through {cycle_length} transfers within {duration_days|n:day}
  headline_synthetic: >-
    Synthetic scenario: funds returned to {return_point} through {cycle_length} transfers within {duration_days|n:day}
false_positives:
- Refunds and payment reversals
- Loan drawdown followed by repayment
- Intra-group cash pooling and treasury sweeps
synthetic_support: high
generator_scenario: circular_flow
detector: neonradar_detect.detectors.circular_flow
```

### `detect/tests/kit.py`

Verbatim. Python, 396 lines. SHA-256 `4bbe61863998c1a2901416dec543965f639cad55d20977f0fe6054f280b4aa2c`.

```python
"""Builds small C1 record sets for detector fixtures and unit tests (PHASE-3.md 7.4).

Every id is synthetic (`syn-fx-...`) unless a test asks for a non-synthetic look-alike with
`real=True`, which gives a `gb_companies_house` record built at run time (PHASE-2.md 2.9: such
records are never committed). Times are UTC strings `YYYY-MM-DDTHH:MM`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from neonradar_detect import catalog, runner
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource
from neonradar_detect.source import Source, Window

Record = dict[str, Any]


def _memory(records: list[Record]) -> Source:
    return MemSource(from_records(records))


# How detector tests turn records into a Source. With NR_DETECT_SOURCE=neo4j, the conftest
# replaces it with a factory that loads the records into a test database and returns a
# Neo4jSource, so the same tests check the Cypher candidate steps (M3.2).
SOURCE_FACTORY: Callable[[list[Record]], Source] = _memory


def source_of(records: list[Record]) -> Source:
    return SOURCE_FACTORY(records)


WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def detect(records: list[Record], params: Mapping[str, Any]) -> runner.RunResult:
    """Run the given typologies through the runner with the catalog, as `detect run` does."""
    return runner.run_detection(
        source_of(records),
        params,
        WINDOW,
        catalog.load(),
        run_id="run-20261102T090000-0001",
        created_at=datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
    )


PREFIXES = {
    "nr_synthetic": "syn",
    "gb_companies_house": "gbch",
    "gb_fcdo_sanctions": "uksl",
    "us_ofac_sdn": "ofac",
    "eu_fsf": "eufsf",
    "un_sc_sanctions": "unsc",
    "icij_offshore_leaks": "icij",
}
BANDS = {
    "25-50": (25.0, 50.0, True, False, "ownership-of-shares-25-to-50-percent"),
    "50-75": (50.0, 75.0, True, True, "ownership-of-shares-50-to-75-percent"),
    "75-100": (75.0, 100.0, False, False, "ownership-of-shares-75-to-100-percent"),
}


def _nr(kind: str, **extra: Any) -> dict[str, Any]:
    return {"v": "1.1", "synthetic": True, "synthetic_kind": kind, **extra}


class Kit:
    def __init__(self) -> None:
        self.records: list[Record] = []
        self._holder: dict[str, str] = {}
        self._n = 0

    def _add(
        self,
        rid: str,
        schema: str,
        props: dict[str, list[str]],
        nr: dict[str, Any] | None,
        real: bool,
        dataset: str = "",
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        record: Record = {
            "id": rid,
            "schema": schema,
            "datasets": [dataset or ("gb_companies_house" if real else "nr_synthetic")],
            "properties": {k: v for k, v in props.items() if v},
        }
        nr = nr or _nr("registry")
        if real:
            # a non-synthetic record never sets nr.synthetic (C1 R6); keep its other nr keys
            nr = {k: v for k, v in nr.items() if k not in ("synthetic", "synthetic_kind")}
            if len(nr) > 1:
                record["nr"] = nr
        else:
            record["nr"] = nr
        self.records.append(record)
        return rid

    def _next(self, kind: str) -> str:
        self._n += 1
        return f"syn-fx-{kind}-{self._n:05d}"

    # entities ------------------------------------------------------------------------------

    def company(
        self,
        cid: str,
        name: str = "",
        *,
        jurisdiction: str = "gb",
        incorporated: str = "2015-01-01",
        sector: str = "",
        real: bool = False,
        topics: tuple[str, ...] = (),
        address: str = "",
        accounts_category: str = "",
        dataset: str = "",
        psc_statements: tuple[str, ...] = (),
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = cid if real else f"syn-fx-co-{cid}"
        props = {
            "name": [name or f"Fixture {cid} Ltd"],
            "jurisdiction": [jurisdiction],
            "incorporationDate": [incorporated],
            "sector": [sector] if sector else [],
            "topics": sorted(topics),
            "addressEntity": [address] if address else [],
        }
        extra: dict[str, Any] = {"address_roles": {address: "registered"}} if address else {}
        if accounts_category:
            extra["accounts_category"] = accounts_category
        if psc_statements:
            extra["psc_statements"] = list(psc_statements)
        return self._add(rid, "Company", props, _nr("registry", **extra), real, dataset)

    def person(
        self,
        pid: str,
        name: str = "",
        *,
        real: bool = False,
        topics: tuple[str, ...] = (),
        dataset: str = "",
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = pid if real else f"syn-fx-p-{pid}"
        props = {"name": [name or f"Fixture Person {pid}"], "topics": sorted(topics)}
        return self._add(rid, "Person", props, _nr("registry"), real, dataset)

    def legal_entity(
        self, lid: str, name: str = "", *, real: bool = False, dataset: str = ""
    ) -> str:
        """A legal entity whose kind the source does not state (an ICIJ officer, say)."""
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = lid if real else f"syn-fx-le-{lid}"
        props = {"name": [name or f"Fixture Entity {lid}"]}
        return self._add(rid, "LegalEntity", props, _nr("registry"), real, dataset)

    def sanction(
        self,
        entity: str,
        dataset: str = "nr_synthetic",
        *,
        provisions: tuple[str, ...] = (),
        authority: str = "Fixture Authority",
        end: str = "",
    ) -> str:
        """A designation of `entity` on the list `dataset` (a non-synthetic dataset gives a
        look-alike record built at run time, never committed)."""
        props = {
            "entity": [entity],
            "authority": [authority],
            "provisions": list(provisions),
            "endDate": [end] if end else [],
        }
        rid = self._next("sanction")
        if dataset != "nr_synthetic":
            rid = f"{PREFIXES[dataset]}-sanction-T{rid.rsplit('-', 1)[1]}"
        return self._add(rid, "Sanction", props, _nr("list"), False, dataset)

    def address(self, aid: str, full: str = "") -> str:
        rid = f"syn-fx-addr-{aid}"
        return self._add(
            rid,
            "Address",
            {"full": [full or f"{aid} Fixture Street, QQ1 1QQ"], "country": ["gb"]},
            None,
            False,
        )

    def account(
        self,
        aid: str,
        holder: str,
        *,
        currency: str = "GBP",
        opened: str = "2024-01-01",
        kind: str = "customer",
    ) -> str:
        rid = f"syn-fx-acct-{aid}"
        self._n += 1
        number = f"NRSYN{self._n:010d}"
        props = {
            "accountNumber": [number],
            "bankName": ["Fixture Bank"],
            "currency": [currency],
            "openingDate": [opened],
        }
        self._add(rid, "BankAccount", props, _nr("activity", account_kind=kind), False)
        self._add(
            f"syn-fx-hold-{aid}",
            "Ownership",
            {"owner": [holder], "asset": [rid], "role": ["account holder"]},
            _nr("activity"),
            False,
        )
        self._holder[rid] = holder
        return rid

    def hold(self, holder: str, account_id: str) -> None:
        """A second holder for an existing account."""
        self._add(
            self._next("hold"),
            "Ownership",
            {"owner": [holder], "asset": [account_id], "role": ["account holder"]},
            _nr("activity"),
            False,
        )

    # links ---------------------------------------------------------------------------------

    def pay(
        self,
        src: str,
        dst: str,
        amount: float,
        when: str,
        *,
        channel: str = "wire",
        currency: str = "GBP",
        pid: str = "",
    ) -> str:
        rid = pid or self._next("pay")
        moment = datetime.strptime(when, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%dT%H:%M:%S")
        props = {
            "payer": [self._holder[src]],
            "beneficiary": [self._holder[dst]],
            "payerAccount": [src],
            "beneficiaryAccount": [dst],
            "amount": [f"{amount:.2f}"],
            "currency": [currency],
            "date": [moment],
        }
        return self._add(rid, "Payment", props, _nr("activity", channel=channel), False)

    def owns(
        self,
        owner: str,
        asset: str,
        band: str = "75-100",
        *,
        nominee: bool = False,
        start: str = "",
        end: str = "",
    ) -> str:
        """`band` is a PSC band ("25-50", "50-75", "75-100") or an exact share ("exact:40");
        `end` is the date the holding ceased."""
        if band.startswith("exact:"):
            value = float(band.split(":", 1)[1])
            low, high, low_x, high_x, nature = value, value, False, False, ""
        else:
            low, high, low_x, high_x, nature = BANDS[band]
        extra: dict[str, Any] = {"share_pct_min": low, "share_pct_max": high}
        if nature:
            extra["natures_of_control"] = [nature]
        if low_x:
            extra["share_pct_min_exclusive"] = True
        if high_x:
            extra["share_pct_max_exclusive"] = True
        if nominee:
            extra["is_nominee"] = True
        props = {
            "owner": [owner],
            "asset": [asset],
            "percentage": [band.removeprefix("exact:")],
            "role": [nature] if nature else [],
            "startDate": [start] if start else [],
            "endDate": [end] if end else [],
        }
        return self._add(self._next("own"), "Ownership", props, _nr("registry", **extra), False)

    def director(
        self,
        person_id: str,
        company_id: str,
        *,
        start: str = "2020-01-01",
        end: str = "",
        nominee: bool = False,
    ) -> str:
        props = {
            "director": [person_id],
            "organization": [company_id],
            "role": ["director"],
            "startDate": [start],
            "endDate": [end] if end else [],
        }
        extra = {"is_nominee": True} if nominee else {}
        return self._add(self._next("dir"), "Directorship", props, _nr("registry", **extra), False)

    def represents(self, agent: str, client: str) -> str:
        props = {"agent": [agent], "client": [client], "role": ["formation agent"]}
        return self._add(self._next("rep"), "Representation", props, None, False)

    def family(self, person_id: str, relative: str, relationship: str = "sibling") -> str:
        props = {"person": [person_id], "relative": [relative], "relationship": [relationship]}
        return self._add(self._next("fam"), "Family", props, None, False)

    def controls(
        self,
        controller: str,
        controlled: str,
        control_type: str = "influence",
        band: str = "",
        *,
        start: str = "",
        end: str = "",
    ) -> str:
        """A PSC control (C2 `control_type`: voting, appointment, influence, trust-or-firm,
        nominee); `band` gives a voting band ("25-50", "50-75", "75-100")."""
        props = {
            "controller": [controller],
            "controlled": [controlled],
            "controlType": [control_type],
            "startDate": [start] if start else [],
            "endDate": [end] if end else [],
        }
        extra: dict[str, Any] = {}
        if band:
            low, high, low_x, high_x, _ = BANDS[band]
            extra = {
                "natures_of_control": [f"voting-rights-{band.replace('-', '-to-')}-percent"],
                "share_pct_min": low,
                "share_pct_max": high,
            }
            if low_x:
                extra["share_pct_min_exclusive"] = True
            if high_x:
                extra["share_pct_max_exclusive"] = True
        return self._add(self._next("ctl"), "Control", props, _nr("registry", **extra), False)

    def consolidates(self, parent: str, child: str) -> str:
        props = {"owner": [parent], "asset": [child], "role": ["consolidation"]}
        return self._add(
            self._next("cons"), "Ownership", props, _nr("registry", consolidation="ultimate"), False
        )

    def associate(self, person_id: str, other: str, relationship: str = "business partner") -> str:
        props = {"person": [person_id], "associate": [other], "relationship": [relationship]}
        return self._add(self._next("assoc"), "Associate", props, None, False)

    def position(self, pid: str, name: str = "", *, country: str = "zz") -> str:
        props = {"name": [name or f"Fixture Office {pid}"], "country": [country]}
        return self._add(f"syn-fx-pos-{pid}", "Position", props, None, False)

    def occupancy(
        self, person_id: str, position_id: str, *, start: str = "2020-01-01", end: str = ""
    ) -> str:
        props = {
            "holder": [person_id],
            "post": [position_id],
            "startDate": [start],
            "endDate": [end] if end else [],
        }
        return self._add(self._next("occ"), "Occupancy", props, None, False)

    def address_at(self, aid: str, full: str, postcode: str, city: str = "Fixture Town") -> str:
        """An address with a postcode and a city (area peer groups, PO boxes, default addresses)."""
        rid = self.address(aid, full)
        record = next(r for r in self.records if r["id"] == rid)
        record["properties"]["postalCode"] = [postcode]
        record["properties"]["city"] = [city]
        return rid

    def history(self, when: str = "2025-10-01T10:00") -> str:
        """One unrelated payment that starts the data's history at `when`: detectors that judge
        earlier relationships skip windows less than their look-back after the first payment."""
        a = self.account("hist-a", self.company("hist-a"))
        b = self.account("hist-b", self.company("hist-b"))
        return self.pay(a, b, 100.0, when)
```

### `detect/tests/test_alert_builder.py`

Verbatim. Python, 204 lines. SHA-256 `5b8d8dc4a3faba2858d4824b7c6c3b319c0648c8892461731afb7ca2ee08bb03`.

```python
from kit import WINDOW, Kit, detect, source_of
from neonradar_detect import catalog, runner
from neonradar_detect.detectors import circular_flow
from neonradar_detect.wording_lint import violations


def _cycle(k: Kit, tag: str, holders: list[str] | None = None) -> None:
    accts = [
        k.account(f"{tag}{i}", holders[i] if holders else k.company(f"{tag}{i}")) for i in range(4)
    ]
    for i, (a, b) in enumerate(zip(accts, accts[1:] + accts[:1], strict=True)):
        k.pay(a, b, 50000 - 500 * i, f"2026-03-0{2 + i}T10:00")


def texts(alert: dict) -> list[str]:
    return [
        alert["headline"],
        alert["explanation"]["summary"],
        *(s["text"] for s in alert["explanation"]["steps"]),
    ]


def test_synthetic_alert_text_passes_the_lint_and_ids_are_stable():
    k = Kit()
    _cycle(k, "c")
    result = detect(k.records, {"circular_flow": circular_flow.Params()})
    [alert] = result.alerts
    captions = tuple(s["caption"] for s in alert["subjects"])
    assert alert["wording_class"] == "synthetic_scenario"
    assert alert["headline"].startswith("Synthetic scenario: ") and len(alert["headline"]) <= 140
    assert all(len(s["text"]) <= 280 for s in alert["explanation"]["steps"])
    for text in texts(alert):
        assert violations(text, captions) == [], text
    assert alert["explanation"]["steps"][0]["text"].endswith("on 2 March 2026.")
    assert alert["evidence"]["query"]["parameters"]["edge_ids"] == alert["evidence"]["edge_ids"]
    again = detect(k.records, {"circular_flow": circular_flow.Params()})
    assert [a["alert_id"] for a in again.alerts] == [alert["alert_id"]]


def test_r_real_withholds_activity_on_a_real_entity():
    """PHASE-1.md M1.9b case F under R-REAL: the cycle through a real company's synthetic
    account is found, then withheld and counted (G12)."""
    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    _cycle(k, "r", holders=[real_co, *(k.company(f"other{i}") for i in range(3))])
    result = detect(k.records, {"circular_flow": circular_flow.Params()})
    assert result.alerts == []
    assert result.summary["withheld"] == {
        "activity_on_real": 1,
        "real_person_subject": 0,
        "real_person_evidence": 0,
        "registry_on_real": 0,
    }
    per = result.summary["typologies"]["circular_flow"]
    assert per["findings"] == 1 and per["alerts"] == 0


def test_r_real_names_no_real_person_anywhere():
    """No alert names a real person (G12, rules (b) and (c)): a person, or a legal entity whose
    kind the source does not state, is withheld as a subject and in the evidence; a registry
    finding whose evidence names only organisations is emitted unless the stricter option is on;
    a PAID in the evidence makes a finding rest on payments (rule (a))."""
    from neonradar_detect import policy
    from neonradar_detect.model import EdgeInfo, Finding, NodeInfo, Subject

    kinds = {
        "person": {"Entity", "LegalEntity", "Person"},
        "entity": {"Entity", "LegalEntity"},
        "company": {"Entity", "LegalEntity", "Organization", "Company"},
    }

    def node(nid: str, kind: str, synthetic: bool = False) -> NodeInfo:
        dataset = "nr_synthetic" if synthetic else "gb_companies_house"
        return NodeInfo(nid, frozenset(kinds[kind]), f"Test {nid}", synthetic, (dataset,))

    nodes = {
        n.id: n
        for n in (
            node("p", "person"),
            node("le", "entity"),
            node("co", "company"),
            node("parent", "company"),
            node("syn", "company", synthetic=True),
        )
    }
    edges = {
        "o1": EdgeInfo("o1", "OWNS", "parent", "co", False),
        "o2": EdgeInfo("o2", "OWNS", "p", "co", False),
        "o3": EdgeInfo("o3", "OWNS", "le", "co", False),
        "pay": EdgeInfo("pay", "PAID", "syn", "co", True),
    }

    def decide(
        subject: str, node_ids: tuple[str, ...], edge_ids: tuple[str, ...], **kw: bool
    ) -> policy.Decision:
        f = Finding("t", "", subject, node_ids, edge_ids, (Subject(subject, "x"),), {}, 0.5, ())
        return policy.decide(f, policy.data_flags(f, nodes, edges), nodes, edges, **kw)

    d = policy.Decision
    assert decide("co", ("co", "parent"), ("o1",)) is d.EMIT
    assert decide("co", ("co", "parent"), ("o1",), registry_on_real=False) is d.REGISTRY_ON_REAL
    assert decide("co", ("co", "p"), ("o2",)) is d.REAL_PERSON_EVIDENCE
    assert decide("co", ("co", "le"), ("o3",)) is d.REAL_PERSON_EVIDENCE
    assert decide("p", ("p",), ()) is d.REAL_PERSON_SUBJECT
    assert decide("le", ("le",), ()) is d.REAL_PERSON_SUBJECT
    assert decide("co", ("co", "syn"), ("pay",)) is d.ACTIVITY_ON_REAL


def test_records_from_icij_carry_its_caution():
    """Phase 1's register says to show ICIJ's disclaimer with its data: an alert whose evidence
    holds an ICIJ record carries ICIJ's caution among its notes, and other alerts do not."""
    from datetime import UTC, datetime

    from neonradar_detect import alerts, policy
    from neonradar_detect.model import Finding, NodeInfo, Subject
    from neonradar_detect.wording import Rendered

    org = frozenset({"Entity", "LegalEntity", "Organization"})
    leak = NodeInfo("icij-T0000001", org, "Test Offshore Ltd", False, ("icij_offshore_leaks",))
    finding = Finding("t", "", leak.id, (leak.id,), (), (Subject(leak.id, "x"),), {}, 0.5, ())

    def notes(datasets: tuple[str, ...]) -> list[str]:
        alert = alerts.build(
            finding,
            Rendered("Test headline", "Test summary.", ()),
            policy.DataFlags(True, True, datasets),
            {leak.id: leak},
            detector_module="neonradar_detect.detectors.t",
            detector_version="0.2.0",
            typology_version="0.2.0",
            query_sha256="0" * 64,
            run_id="run-20261102T090000-0004",
            created_at=datetime(2026, 11, 2, tzinfo=UTC),
            doc_path="docs/typologies/t.md",
            citations=("icij_faq",),
            false_positives=("A test note",),
        )
        return list(alert["explanation"]["false_positive_notes"])

    caution = alerts.DATASET_NOTES["icij_offshore_leaks"]
    assert notes(("icij_offshore_leaks",)) == ["A test note", caution]
    assert notes(("gb_companies_house",)) == ["A test note"]
    assert violations(caution) == []


def test_rendering_lints_every_text_with_the_captions_masked():
    import dataclasses

    import pytest
    from neonradar_detect import wording

    k = Kit()
    _cycle(k, "m")
    cat = catalog.load()
    source = source_of(k.records)
    [finding] = circular_flow.run(source, circular_flow.Params(), WINDOW).findings
    edges = source.edge_info(finding.edge_ids)
    nodes = source.node_info(sorted({x for e in edges.values() for x in (e.source, e.target)}))
    first = edges[finding.steps[0][0]].source
    nodes[first] = dataclasses.replace(nodes[first], caption="Test Mule Transport Ltd")
    rendered = wording.render(finding, cat["circular_flow"], "synthetic_scenario", nodes, edges)
    assert rendered.steps[0][0].startswith("Test Mule Transport Ltd paid")  # a caption, masked
    bad = dict(cat["circular_flow"].wording, headline_synthetic="Synthetic scenario: layering")
    broken = {**cat, "circular_flow": dataclasses.replace(cat["circular_flow"], wording=bad)}
    with pytest.raises(wording.WordingError, match="circular_flow: the headline"):
        runner.run_detection(
            source,
            {"circular_flow": circular_flow.Params()},
            WINDOW,
            broken,
            run_id="run-20261102T090000-0003",
            created_at=WINDOW.end,
        )


def test_catalog_templates_and_parameters_match_the_detectors():
    import dataclasses

    from neonradar_detect.wording import placeholders, render_template

    cat = catalog.load()
    found = runner.detectors(cat)
    assert list(found) == [s for s in runner.ORDER if s in cat and cat[s].detector]
    for slug, module in found.items():
        t = cat[slug]
        assert t.version == module.VERSION and t.detector == module.__name__
        defaults = {
            f.name: getattr(module.Params(), f.name) for f in dataclasses.fields(module.Params)
        }
        assert {
            k: tuple(v["default"]) if isinstance(v["default"], list) else v["default"]
            for k, v in t.parameters.items()
        } == defaults
        assert catalog.params_for(t, module) == module.Params()
        pairs = [t.wording, *t.wording.get("variants", {}).values()]
        for pair in pairs:
            for key in ("headline_structural", "headline_synthetic"):
                assert placeholders(pair[key]) <= set(t.metrics), (slug, key)
                sample = {m: 1 for m in t.metrics} | {"currency": "GBP"}
                assert violations(render_template(pair[key], sample)) == [], (slug, key)
            assert pair["headline_synthetic"].startswith("Synthetic scenario: ")
        assert violations(t.shape_name) == [] and all(
            violations(x) == [] for x in t.false_positives
        )
```

### `detect/tests/test_detector_circular_flow.py`

Verbatim. Python, 132 lines. SHA-256 `1d193824ae0a1d7e6d3704b2a422984f66db07d8089c1c60a77d43acac224db1`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import circular_flow as cf
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _cycle(
    k: Kit, tag: str, amounts: list[float], times: list[str], *, holder_real: bool = False
) -> list[str]:
    holder = (
        k.company(f"gbch-co-T{tag}", "Test Holder Ltd", real=True)
        if holder_real
        else k.company(f"{tag}o")
    )
    accounts = [k.account(f"{tag}0", holder)]
    for i in range(1, len(amounts)):
        accounts.append(k.account(f"{tag}{i}", k.company(f"{tag}{i}")))
    edges = []
    for i, (amount, when) in enumerate(zip(amounts, times, strict=True)):
        src = accounts[i]
        dst = accounts[(i + 1) % len(accounts)]
        edges.append(k.pay(src, dst, amount, when, pid=f"syn-fx-pay-{tag}{i}"))
    return edges


def _run(k: Kit, **overrides):
    out = cf.run(source_of(k.records), cf.Params(**overrides), WINDOW)
    return {f.edge_ids: f for f in out.findings}


def test_phase1_cases_a_to_e():
    k = Kit()
    a = _cycle(
        k,
        "a",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
    )
    b = _cycle(
        k, "b", [50000, 49000, 48500], ["2026-03-10T09:00", "2026-03-11T09:00", "2026-03-12T09:00"]
    )
    _cycle(
        k,
        "c",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-02T11:00", "2026-03-08T16:40"],
    )
    _cycle(
        k,
        "d",
        [120000, 117600, 115248, 115200],
        ["2026-04-01T09:00", "2026-04-15T10:00", "2026-04-30T11:00", "2026-05-11T16:40"],
    )
    _cycle(
        k,
        "e",
        [120000, 117600, 115248, 36000],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
    )
    found = _run(k)
    assert set(found) == {tuple(sorted(a)), tuple(sorted(b))}
    fa = found[tuple(sorted(a))]
    assert fa.variant == "same_account" and fa.metrics["cycle_length"] == 4
    assert fa.metrics["return_ratio"] == 0.96 and fa.metrics["duration_days"] == 7
    assert fa.pattern_strength == 0.7946  # 0.5 * 0.96 + 0.3 * (1 - 151.6667 / 336) + 0.2 * 0.75
    assert [s.role for s in fa.subjects] == ["origin", "origin_holder"]
    assert fa.steps == tuple((e,) for e in a)


def test_same_holder_return():
    k = Kit()
    holder = k.company("h")
    a1 = k.account("h1", holder)
    a2 = k.account("h2", holder)
    x = k.account("x", k.company("x"))
    y = k.account("y", k.company("y"))
    e = [
        k.pay(a1, x, 80000, "2026-02-02T09:00"),
        k.pay(x, y, 79000, "2026-02-03T09:00"),
        k.pay(y, a2, 78000, "2026-02-04T09:00"),
    ]
    found = _run(k)
    f = found[tuple(sorted(e))]
    assert (
        f.variant == "same_holder"
        and f.metrics["return_point"] == "another account of the same holder"
    )
    assert [s.role for s in f.subjects] == ["origin", "origin_holder", "return_account"]
    assert _run(k, same_holder=False) == {}


def test_hop_above_first_amount_and_own_account_transfer_are_not_cycles():
    k = Kit()
    _cycle(
        k, "m", [10000, 25000, 9800], ["2026-02-02T09:00", "2026-02-03T09:00", "2026-02-04T09:00"]
    )
    holder = k.company("own")
    a1, a2 = k.account("own1", holder), k.account("own2", holder)
    z = k.account("z", k.company("z"))
    k.pay(a1, a2, 20000, "2026-02-02T09:00")
    k.pay(a2, z, 19900, "2026-02-03T09:00")
    k.pay(z, a1, 19800, "2026-02-04T09:00")
    found = _run(k)
    # the merge hop breaks the first cycle; the own-account transfer closes at once (1 hop),
    # but the transfer a2 -> z -> a1 is a same-holder cycle of 2 hops starting at a2
    assert [f.variant for f in found.values()] == ["same_holder"]


def test_payment_straight_back_needs_three_hops_by_default():
    k = Kit()
    shop = k.account("shop", k.company("shop"))
    buyer = k.account("buyer", k.company("buyer"))
    e = [k.pay(buyer, shop, 5000, "2026-05-04T10:00"), k.pay(shop, buyer, 5000, "2026-05-06T15:00")]
    assert _run(k) == {}  # a refund's shape
    assert tuple(sorted(e)) in _run(k, min_hops_same_account=2)  # the documented false positive


def test_case_f_real_holder_is_reported_for_the_policy_to_withhold():
    k = Kit()
    edges = _cycle(
        k,
        "f",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
        holder_real=True,
    )
    found = _run(k)
    f = found[tuple(sorted(edges))]
    assert f.activity and "gbch-co-Tf" in {s.entity_id for s in f.subjects}
```

### `detect/tests/test_graphrows.py`

Verbatim. Python, 106 lines. SHA-256 `1530351d891fbff5afd19802f9f4a253303f5070de44c391739472346774d25b`.

```python
"""The C2 labels and properties the detectors read (PHASE-3.md 7.1.2), pinned on one small graph.

`graphrows.from_records` is the oracle's own reading of C2 and does not call the loader's
mapping; this test pins what it gives. The Neo4j test mode and the world parity test compare it
with the loader (PHASE-3.md 7.1.5): when they differ, find which side departs from C2 1.2.0 and
fix that side, never this test.
"""

from datetime import UTC, datetime

from kit import Kit
from neonradar_detect.graphrows import from_records


def _graph():
    k = Kit()
    addr = k.address_at("a", "Suite 2, 3 Fixture Road, Fixture Town, QQ3 3QQ", "QQ3 3QQ")
    co = k.company(
        "c",
        incorporated="2019-05-06",
        sector="retail",
        address=addr,
        accounts_category="DORMANT",
        psc_statements=("no-individual-or-entity-with-signficant-control",),
    )
    parent = k.company("p", jurisdiction="je")
    person = k.person("x", topics=("role.pep",))
    rel = k.person("y")
    listed = k.person("s", topics=("sanction",))
    k.sanction(listed, provisions=("Asset freeze",), end="2027-01-01")
    acct = k.account("1", co, opened="2024-02-03")
    ledger = k.account("2", k.company("bank"), kind="cash_ledger")
    pay = k.pay(ledger, acct, 9500, "2026-03-02T10:15", channel="cash_deposit")
    own = k.owns(parent, co, "50-75", nominee=True, start="2020-01-01")
    ctl = k.controls(person, co, "voting", band="25-50")
    k.consolidates(parent, co)
    k.director(person, co, start="2021-01-01", end="2023-01-01", nominee=True)
    k.represents(parent, co)
    k.family(person, rel, "spouse")
    k.associate(person, listed)
    post = k.position("m", country="zz")
    k.occupancy(person, post, start="2022-01-01", end="2025-06-30")
    return from_records(k.records), {"co": co, "acct": acct, "pay": pay, "own": own, "ctl": ctl}


def test_node_labels_and_properties():
    g, ids = _graph()
    co = g.node(ids["co"])
    assert {"Entity", "LegalEntity", "Organization", "Company", "Synthetic"} <= co.labels
    assert (co.get("incorporation_date"), co.get("sector")) == ("2019-05-06", "retail")
    assert co.get("accounts_category") == "DORMANT"
    assert co.get("psc_statements") == ["no-individual-or-entity-with-signficant-control"]
    assert co.get("datasets") == ["nr_synthetic"] and co.synthetic is True
    acct = g.node(ids["acct"])
    assert {"Entity", "Account"} <= acct.labels
    assert (acct.get("opening_date"), acct.get("account_kind")) == ("2024-02-03", "customer")
    assert acct.get("caption") == acct.get("account_number")
    addr = g.node("syn-fx-addr-a")
    assert (addr.get("postal_code"), addr.get("city")) == ("QQ3 3QQ", "Fixture Town")
    assert addr.get("full").startswith("Suite 2")
    assert {"PEP"} <= g.node("syn-fx-p-x").labels
    assert {"Sanctioned"} <= g.node("syn-fx-p-s").labels
    [sanction] = g.nodes("Sanction")
    assert (
        sanction.get("provisions") == ["Asset freeze"] and sanction.get("end_date") == "2027-01-01"
    )
    assert g.node("syn-fx-pos-m").get("country") == "zz"
    assert g.node("syn-fx-co-p").get("countries") == ["je"]


def test_relationship_types_and_properties():
    g, ids = _graph()
    [paid] = g.rels("PAID")
    assert paid.id == ids["pay"] and paid.get("ts") == datetime(2026, 3, 2, 10, 15, tzinfo=UTC)
    assert (paid.get("amount"), paid.get("currency"), paid.get("channel")) == (
        9500.0,
        "GBP",
        "cash_deposit",
    )
    [owns] = g.rels("OWNS")
    assert (owns.get("share_pct_min"), owns.get("share_pct_max")) == (50.0, 75.0)
    assert owns.get("share_min_exclusive") is True and owns.get("share_max_exclusive") is True
    assert owns.get("is_nominee") is True and owns.get("start_date") == "2020-01-01"
    [ctl] = g.rels("CONTROLS")
    assert ctl.get("control_type") == "voting" and ctl.get("share_pct_min") == 25.0
    assert ctl.get("share_min_exclusive") is True and ctl.get("share_max_exclusive") is False
    [cons] = g.rels("CONSOLIDATES")
    assert cons.get("level") == "ultimate"
    [d] = g.rels("DIRECTOR_OF")
    assert (d.get("start_date"), d.get("end_date"), d.get("is_nominee")) == (
        "2021-01-01",
        "2023-01-01",
        True,
    )
    [h] = g.rels("HAS_ADDRESS")
    assert h.get("role") == "registered" and h.id == f"{ids['co']}|addr|syn-fx-addr-a"
    [fam] = g.rels("FAMILY_OF")
    assert fam.get("relationship") == "spouse"
    [assoc] = g.rels("ASSOCIATE_OF")
    assert assoc.get("relationship") == "business partner"
    [occ] = g.rels("HOLDS_POSITION")
    assert (occ.get("start_date"), occ.get("end_date")) == ("2022-01-01", "2025-06-30")
    [subject] = g.rels("SUBJECT_OF")
    assert subject.source == "syn-fx-p-s"
    assert len(g.rels("HOLDS_ACCOUNT")) == 2 and len(g.rels("REPRESENTS")) == 1
    assert g.holders(ids["acct"])[0].id == ids["co"]
```

### `detect/tests/test_detector_queries.py`

Verbatim. Python, 91 lines. SHA-256 `18ed593e3a34a5373b8437f6349a13a0c9dfab4eebdaa16e275b1f33812c9ece`.

```python
"""Each detector's QUERIES names exactly the query files its candidate steps run (PHASE-3.md 7.1.2).

`detect run` hashes these files into the alert's `detector.query_sha256` (C4), so the list must be
complete. The check is static: the `source.<method>(...)` calls in the detector module and in the
functions it imports from other detector modules, plus `paid_hop` when it uses the path expansion.
"""

import ast
import importlib
import inspect
import textwrap
from importlib import resources

from neonradar_detect import catalog, runner

FILES = {
    "paid_time_range": ("paid_time_range",),
    "paid_starts": ("paid_starts",),
    "paid_hop": ("paid_hop",),
    "flows_by_inbound": ("flows_by_inbound",),
    "flows_by_outbound": ("flows_by_outbound",),
    "counterparty_info": ("counterparty_info",),
    "paid_times": ("paid_times",),
    "payments_from": ("payments_from",),
    "payments_into": ("payments_into",),
    "payments_among": ("payments_among",),
    "activity_counts": ("activity_counts",),
    "holder_cash_deposits": ("holder_cash_deposits",),
    "quiet_account_histories": ("quiet_account_histories",),
    "company_account_histories": ("company_account_histories",),
    "recent_account_components": (
        "recent_account_edges",
        "recent_account_components_project",
        "recent_account_components_wcc",
        "recent_account_components_drop",
    ),
    "entities": ("entities",),
    "links_into": ("links_into",),
    "links_from": ("links_from",),
    "appointment_counts": ("appointment_counts",),
    "ownership_paths": ("ownership_paths",),
    "ownership_cycles": ("ownership_cycles",),
    "registered_clusters": ("registered_clusters",),
    "registered_count_quantile": ("registered_count_quantile",),
    "listed_entities": ("listed_entities",),
    "flagged_ids": ("flagged_ids",),
    "hubs": ("hubs",),
    "cash_profiles": ("cash_profiles",),
}


def _calls(tree: ast.AST) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "source"
        ):
            found.add(node.func.attr)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "expand":
            found.add("paid_hop")
    return found


def _methods(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    found = _calls(tree)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "neonradar_detect.detectors."
        ):
            other = importlib.import_module(node.module)
            for alias in node.names:
                obj = getattr(other, alias.name)
                if inspect.isfunction(obj):
                    found |= _calls(ast.parse(textwrap.dedent(inspect.getsource(obj))))
    return found


def test_queries_lists_are_exact_and_the_files_exist():
    existing = {
        p.name for p in resources.files("neonradar_detect.queries").iterdir() if p.is_file()
    }
    for slug, module in runner.detectors(catalog.load()).items():
        methods = _methods(module)
        assert methods <= set(FILES), (slug, methods - set(FILES))
        expected = sorted({f"{name}.cypher" for m in methods for name in FILES[m]})
        assert list(module.QUERIES) == expected, slug
        assert set(module.QUERIES) <= existing, slug
```

### `detect/tests/conftest.py`

Reference. Python, 33 lines. SHA-256 `b231fc77ce2c237f2c616931492f37bf08406b60132c0380f4cd7b5b45bd2591`.

M3.2 merges these additions into Phase 1's `detect/tests/conftest.py`.

```python
"""Phase 3 additions to `detect/tests/conftest.py` (merge them into the existing file, M3.2)."""

import os
import sys
from pathlib import Path

import pytest

# helpers (kit.py, neo4j_mode.py) sit next to the tests; pytest runs with --import-mode=importlib
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kit


@pytest.fixture(scope="session")
def neo4j_source_factory():  # type: ignore[no-untyped-def]
    """Records to a Neo4jSource on a fresh test database (integration tests)."""
    pytest.importorskip("testcontainers")
    import neo4j_mode

    with neo4j_mode.container() as neo:
        yield neo4j_mode.factory(neo)


if os.environ.get("NR_DETECT_SOURCE") == "neo4j":

    @pytest.fixture(scope="session", autouse=True)
    def _detector_tests_on_neo4j(neo4j_source_factory):  # type: ignore[no-untyped-def]
        """NR_DETECT_SOURCE=neo4j: every detector test runs on Neo4j (7.1.5)."""
        before = kit.SOURCE_FACTORY
        kit.SOURCE_FACTORY = neo4j_source_factory
        yield
        kit.SOURCE_FACTORY = before
```

### `detect/tests/neo4j_mode.py`

Reference. Python, 77 lines. SHA-256 `ca57522c9673ec3a4092be2ab95ed0ac707286ec1b5674fae05d8328e09ff042`.

M3.2 adapts it to the project's Testcontainers fixture and loader (7.1.5).

```python
"""Detector tests on Neo4j (PHASE-3.md 7.1.5): records loaded into a test database, a Neo4jSource.

REFERENCE IMPLEMENTATION. M3.2 adapts it to the repository's Testcontainers fixture and loader
(PHASE-1.md M1.9a, PHASE-2.md M2.11). The behaviour to keep: one container per test session,
started like the project's integration tests (`neo4j:5.26.32-community` with APOC and GDS); for
each call, wipe the database, write the records to a temporary file, load them with the project's
own loader in strict mode, and return a `Neo4jSource` on that database. Records that are not all
synthetic cannot be loaded into the default instance (C2 L17), so a test that builds a
non-synthetic look-alike is skipped in this mode: R-REAL is decided after the Source, and the
in-memory run of the same test covers it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from neonradar_detect.neo4jsource import Neo4jSource
from neonradar_detect.source import Source
from neonradar_ingest.synth import writer

IMAGE = os.environ.get("NR_NEO4J_IMAGE", "neo4j:5.26.32-community")
Record = dict[str, Any]


def _cli(*args: str, env: dict[str, str]) -> None:
    exe = shutil.which("neonradar")
    if exe is None:
        raise RuntimeError("the neonradar command is not installed (uv sync --all-packages)")
    subprocess.run([exe, *args], check=True, env=env, capture_output=True, text=True)  # noqa: S603


@contextmanager
def container() -> Iterator[Any]:
    """A session's Neo4j container, like PHASE-1.md M1.6's integration fixture."""
    from testcontainers.community.neo4j import Neo4jContainer

    with (
        Neo4jContainer(IMAGE)
        .with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')
        .with_env("NEO4J_dbms_security_procedures_unrestricted", "apoc.*,gds.*")
        .with_env("NEO4J_server_memory_heap_max__size", "1G")
        .with_env("NEO4J_server_memory_pagecache_size", "512M") as neo
    ):
        yield neo


def factory(neo: Any) -> Callable[[list[Record]], Source]:
    env = {
        **os.environ,
        "NEO4J_URI": neo.get_connection_url(),
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": neo.password,
        "NEO4J_DATABASE": "neo4j",
    }
    _cli("graph", "migrate", env=env)
    driver = neo.get_driver()

    def make(records: list[Record]) -> Source:
        if not all(r["datasets"] == ["nr_synthetic"] for r in records):
            pytest.skip("non-synthetic look-alike records: covered by the in-memory run (L17)")
        _cli("graph", "wipe", "--yes", env=env)
        with tempfile.TemporaryDirectory() as tmp:
            writer.write_part(
                Path(tmp), "nr_synthetic-20261102-test", writer.items(records), seed=0, git_sha="t"
            )
            _cli("graph", "load", tmp, "--strict", env=env)
        return Neo4jSource(driver, "neo4j", timeout_s=60.0)

    return make
```

### `detect/tests/test_query_plans.py`

Reference. Python, 152 lines. SHA-256 `394e4cab18fcdc7e2af5a50e7d65ba144dab5072ecfe966149809a6d6e14d5c1`.

M3.2 adapts the fixture names; the fixture loads a small world and overlay made with M3.3's generator (a dependency of M3.2) with the settings that M3.6's `test_world_parity.py` uses.

```python
"""EXPLAIN every detector query on a test database (PHASE-3.md 7.1.6).

REFERENCE IMPLEMENTATION. M3.2 adapts the fixture names to the repository. The offline linters
cannot see the planner; this test asks the server. A query fails when it is not read only (the
three GDS ring files excepted, which project, stream and drop), when the server reports a
deprecation, an unfulfillable hint, a missing parameter (`01N` statuses other than `01N50` to
`01N52`, which mean a label, type or property is absent from the empty test graph), a cartesian
product (`03N90`), an unbounded or exhaustive shortest path (`03N91`, `03N92`) or a shadowed
subquery variable (`03N60`), or when an anchored window query does not seek the `paid_ts` index.
The planner chooses by statistics, so the fixture loads a small generated world first (80
companies, 120 people, one scenario and one look-alike per typology, seed 5: the settings of
`test_world_parity.py`); on an empty database it may not seek.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from neonradar_detect.neo4jsource import TEMPLATE_VALUES, query_text

pytestmark = pytest.mark.integration

START, END, PRIOR = "2026-01-01T00:00:00Z", "2026-07-01T00:00:00Z", "2025-07-01T00:00:00Z"
IDS = {"ids": ["syn-fx-co-a", "syn-fx-acct-b"]}
WINDOW = {"start": START, "end": END}
FRONTIER = [
    {
        "key": 0,
        "account": "syn-fx-acct-b",
        "after": START,
        "until": END,
        "min_amount": 100.0,
        "max_amount": 1000.0,
        "currency": "GBP",
        "visited": ["syn-fx-acct-b"],
    }
]
PARAMS: dict[str, dict[str, Any]] = {
    "activity_counts": {**IDS, **WINDOW},
    "appointment_counts": {**IDS, "as_of": "2026-07-01"},
    "cash_profiles": {"currency": "GBP", "prior_start": PRIOR, **WINDOW, "limit": 10},
    "company_account_histories": {
        **WINDOW,
        "incorporated_since": "2025-01-01",
        "min_payments": 1,
        "limit": 10,
    },
    "counterparty_info": IDS,
    "edge_info": IDS,
    "entities": IDS,
    "evidence": {"node_ids": IDS["ids"], "edge_ids": ["syn-fx-pay-00001"]},
    "flagged_ids": {},
    "flows_by_inbound": {
        "bucket_hours": 72,
        "channel": "wire",
        **WINDOW,
        "min_counterparties": 3,
        "limit": 10,
    },
    "flows_by_outbound": {"bucket_hours": 72, **WINDOW, "min_counterparties": 3, "limit": 10},
    "holder_cash_deposits": {
        "band_low": 9000.0,
        "threshold": 10000.0,
        "min_in_band": 3,
        **WINDOW,
        "limit": 10,
    },
    "hubs": {"min_members": 10, "limit": 10},
    "links_from": {**IDS, "types": ["OWNS", "CONTROLS"]},
    "links_into": {**IDS, "types": ["OWNS", "CONTROLS"]},
    "listed_entities": {},
    "node_info": IDS,
    "ownership_cycles": {"limit": 10, "as_of": "2026-07-01"},
    "ownership_paths": {"limit": 10, "as_of": "2026-07-01"},
    "paid_hop": {"frontier": FRONTIER},
    "paid_starts": {**WINDOW, "min_amount": 1000.0, "limit": 10},
    "paid_time_range": {},
    "paid_times": {"pairs": [["syn-fx-acct-b", "syn-fx-acct-c"]]},
    "payments_among": {**IDS, **WINDOW},
    "payments_from": {**IDS, **WINDOW},
    "payments_into": {**IDS, **WINDOW},
    "quiet_account_histories": {
        "min_gap_days": 180,
        "max_quiet_payments": 2,
        "max_quiet_amount": 500.0,
        "history_start": PRIOR,
        **WINDOW,
        "limit": 10,
    },
    "recent_account_components_project": {"graph_name": "nr-plan-test", **WINDOW, "new_days": 30},
    "recent_account_components_wcc": {"graph_name": "nr-plan-test"},
    "recent_account_components_drop": {"graph_name": "nr-plan-test"},
    "recent_account_edges": {**WINDOW, "new_days": 30},
    "registered_clusters": {"active_only": True, "min_members": 10, "limit": 10},
    "registered_count_quantile": {"active_only": True, "q": 0.99},
}
TEMPLATES = {
    "flagged_ids": {"flag": sorted(TEMPLATE_VALUES["flag"])},
    "hubs": {"rel_type": sorted(TEMPLATE_VALUES["rel_type"])},
    "ownership_cycles": {"max_hops": ["2", "6", "8"]},
    "ownership_paths": {"max_hops": ["2", "6", "8"]},
}
NOT_READ_ONLY = {
    "recent_account_components_project",
    "recent_account_components_wcc",
    "recent_account_components_drop",
}
MUST_SEEK = {"paid_starts", "flows_by_inbound", "flows_by_outbound", "recent_account_edges"}
ALLOWED = ("01N50", "01N51", "01N52")
FORBIDDEN = ("01N", "03N90", "03N91", "03N92", "03N60")


def _renders(name: str) -> list[str]:
    choices = TEMPLATES.get(name)
    if not choices:
        return [query_text(name)]
    [(key, values)] = choices.items()
    return [query_text(name, **{key: v}) for v in values]


def explain_problems(driver: Any, name: str, text: str) -> list[str]:
    _, summary, _ = driver.execute_query("EXPLAIN " + text, PARAMS[name], database_="neo4j")
    problems = []
    if name not in NOT_READ_ONLY and summary.query_type != "r":
        problems.append(f"query type {summary.query_type}")
    for status in summary.gql_status_objects:
        code = status.gql_status
        if code.startswith(FORBIDDEN) and code not in ALLOWED:
            problems.append(f"{code}: {status.status_description}")
    if name in MUST_SEEK and "RelationshipIndexSeekByRange" not in json.dumps(summary.plan):
        problems.append("no relationship index seek on PAID.ts")
    return problems


def test_every_query_plans_cleanly(neo4j_driver_with_world: Any) -> None:
    from importlib import resources

    names = sorted(
        p.name.removesuffix(".cypher")
        for p in resources.files("neonradar_detect.queries").iterdir()
        if p.name.endswith(".cypher")
    )
    assert set(names) == set(PARAMS), "every query file needs sample parameters here"
    problems = {
        f"{name}#{i}": found
        for name in names
        for i, text in enumerate(_renders(name))
        if (found := explain_problems(neo4j_driver_with_world, name, text))
    }
    assert problems == {}
```

## M3.3 Generator v1: world, overlay, scenarios and labels

Generator v1, its fourteen scenario modules, its tests and the three synthetic profiles; two reference files. 31 verbatim files and 2 reference files (PHASE-3.md M3.3).

### `ingest/src/neonradar_ingest/synth/streams.py`

Verbatim. Python, 40 lines. SHA-256 `57ad6fd34da679e4eb7f83ad165f95a74dd28286e2c47c79b96c57b9ff99101e`.

```python
"""Seeded random streams for the generator (PHASE-3.md 7.2.1).

Every stream is derived from the root seed and a tuple of string keys through
`numpy.random.SeedSequence(entropy=seed, spawn_key=...)`, so a stream depends only on what it is
for (for example `("background", "syn-w-co-000123")`), never on how many streams were drawn
before it. Adding a scenario therefore leaves the background of every other entity unchanged.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _key(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def stream(seed: int, *keys: str) -> np.random.Generator:
    """An independent generator for `keys` under the root `seed`."""
    if seed < 0:
        raise ValueError("seed must be a non-negative integer")
    sequence = np.random.SeedSequence(entropy=seed, spawn_key=tuple(_key(k) for k in keys))
    return np.random.Generator(np.random.PCG64(sequence))


def pick(rng: np.random.Generator, items: list[str]) -> str:
    """One item, uniformly; `items` must already be in a stable order."""
    if not items:
        raise ValueError("cannot pick from an empty list")
    return items[int(rng.integers(len(items)))]


def sample(rng: np.random.Generator, items: list[str], k: int) -> list[str]:
    """`k` distinct items in the order drawn; `items` must already be in a stable order."""
    if k > len(items):
        raise ValueError("sample larger than population")
    idx = rng.choice(len(items), size=k, replace=False)
    return [items[int(i)] for i in idx]
```

### `ingest/src/neonradar_ingest/synth/dates.py`

Verbatim. Python, 132 lines. SHA-256 `4b7f3c42319809e12d599c3f86172bda7d76fd62ab9bd8171ef135cf31e6e0fa`.

```python
"""Time helpers for generator v1 (PHASE-3.md 7.2.1).

Activity is generated in Europe/London local time and stored in UTC, as C1 R5 requires: clock
changes come from `zoneinfo` (with the pinned `tzdata` package). Working days exclude weekends and
the England and Wales bank holidays of 2025 and 2026 from GOV.UK (`synthetic-transactions.md` 2.6),
committed here as data because nothing may be fetched at run time (G3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

LONDON = ZoneInfo("Europe/London")

BANK_HOLIDAYS = frozenset(
    date.fromisoformat(d)
    for d in (
        "2025-01-01",
        "2025-04-18",
        "2025-04-21",
        "2025-05-05",
        "2025-05-26",
        "2025-08-25",
        "2025-12-25",
        "2025-12-26",
        "2026-01-01",
        "2026-04-03",
        "2026-04-06",
        "2026-05-04",
        "2026-05-25",
        "2026-08-31",
        "2026-12-25",
        "2026-12-28",
    )
)
COVERED = (date(2025, 1, 1), date(2027, 1, 1))  # the years the holiday table covers


@dataclass(frozen=True, slots=True)
class Period:
    """The generated activity period: start <= time < end, both UTC midnights."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        for moment in (self.start, self.end):
            if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
                raise ValueError("period bounds must be UTC")
        if self.end - self.start < timedelta(days=28):
            raise ValueError("a period needs at least 28 days")
        if not (COVERED[0] <= self.start.date() and self.end.date() <= COVERED[1]):
            raise ValueError("the bank holiday table covers 2025 and 2026 only; extend it first")

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    def months(self) -> list[date]:
        """The first day of every month that starts inside the period."""
        out = []
        d = date(self.start.year, self.start.month, 1)
        if d < self.start.date():
            d = _next_month(d)
        while d < self.end.date():
            out.append(d)
            d = _next_month(d)
        return out


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def is_working_day(d: date) -> bool:
    return d.weekday() < 5 and d not in BANK_HOLIDAYS


def working_days(start: date, end: date) -> list[date]:
    """Working days in England and Wales from start (inclusive) to end (exclusive)."""
    out = []
    d = start
    while d < end:
        if is_working_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


business_days = working_days


def previous_working_day(d: date) -> date:
    while not is_working_day(d):
        d -= timedelta(days=1)
    return d


def last_working_day(month_first: date) -> date:
    return previous_working_day(_next_month(month_first) - timedelta(days=1))


last_business_day = last_working_day


def local(day: date, seconds: int) -> datetime:
    """`seconds` after local midnight in London on `day`, as a UTC time to the second."""
    naive = datetime(day.year, day.month, day.day) + timedelta(seconds=seconds)
    return naive.replace(tzinfo=LONDON).astimezone(UTC)


def at(rng: np.random.Generator, day: date, first_hour: int = 8, last_hour: int = 18) -> datetime:
    """A London local time on `day` between first_hour:00 and last_hour:00, stored as UTC."""
    return local(day, int(rng.integers(first_hour * 3600, last_hour * 3600)))


def later(
    rng: np.random.Generator, moment: datetime, min_hours: float, max_hours: float
) -> datetime:
    """A time between min_hours and max_hours after `moment`, to the second."""
    seconds = int(rng.integers(int(min_hours * 3600), int(max_hours * 3600) + 1))
    return moment + timedelta(seconds=max(1, seconds))
```

### `ingest/src/neonradar_ingest/synth/records.py`

Verbatim. Python, 332 lines. SHA-256 `56a62233c450da1faf16ea066cea6026931a5a5dffd7fa5ed339d1fd455e3eb4`.

```python
"""C1 record builders for generator v1 (PHASE-3.md 7.2.2).

Every builder returns one C1 record as a plain dict in `ValueEntity.to_dict()` shape: dataset
`nr_synthetic`, `nr.v` "1.1", `nr.synthetic` true and the `synthetic_kind` the record needs
(`registry` for companies, people, addresses and their links; `activity` for accounts, account
holdings and payments). Nothing here carries a label (C1 R9): roles in a scenario live only in the
label files.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CHANNELS = ("wire", "card", "cash_deposit", "cash_withdrawal", "internal")
ADDRESS_ROLES = ("registered", "service", "residential", "business", "unknown")

Record = dict[str, Any]


def hashed_id(namespace: str, seed: int, key: str) -> str:
    """`syn-ov-<namespace>-<16 hex>`: an id that says nothing about the record's role."""
    digest = hashlib.sha256(f"{seed}|{namespace}|{key}".encode()).hexdigest()[:16]
    return f"syn-ov-{namespace}-{digest}"


def _nr(kind: str, **extra: Any) -> dict[str, Any]:
    return {"v": "1.1", "synthetic": True, "synthetic_kind": kind, **extra}


LIST_TOPICS = frozenset({"sanction", "role.pep", "role.rca"})


def _kind(topics: list[str] | None) -> str:
    """`list` for a synthetic list entry (a record with a flag topic), else `registry`."""
    return "list" if LIST_TOPICS & set(topics or []) else "registry"


def _record(rid: str, schema: str, props: dict[str, list[str]], nr: dict[str, Any]) -> Record:
    clean = {k: v for k, v in props.items() if v}
    return {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic"],
        "properties": clean,
        "nr": nr,
    }


def money(amount: float | Decimal) -> str:
    """A C1 amount: a decimal string with two decimals, greater than zero (R7)."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value <= 0:
        raise ValueError("payment amounts must be greater than zero")
    return f"{value:.2f}"


def ts(moment: datetime) -> str:
    """A C1 payment date: UTC, `YYYY-MM-DDTHH:MM:SS`, no offset (R5)."""
    offset = moment.utcoffset()
    if offset is not None and offset.total_seconds() != 0:
        raise ValueError("payment times must be UTC")
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def company(
    rid: str,
    name: str,
    *,
    jurisdiction: str,
    registration_number: str,
    incorporation_date: str,
    addresses: dict[str, str] | None = None,
    sector: str = "",
    status: str = "active",
    dissolution_date: str = "",
    topics: list[str] | None = None,
) -> Record:
    roles = addresses or {}
    props = {
        "name": [name],
        "jurisdiction": [jurisdiction],
        "registrationNumber": [registration_number],
        "incorporationDate": [incorporation_date],
        "dissolutionDate": [dissolution_date] if dissolution_date else [],
        "status": [status] if status else [],
        "sector": [sector] if sector else [],
        "addressEntity": sorted(roles),
        "topics": sorted(topics or []),
    }
    extra = {"address_roles": dict(sorted(roles.items()))} if roles else {}
    return _record(rid, "Company", props, _nr(_kind(topics), **extra))


def organization(rid: str, name: str, *, country: str, topics: list[str] | None = None) -> Record:
    props = {"name": [name], "country": [country], "topics": sorted(topics or [])}
    return _record(rid, "Organization", props, _nr(_kind(topics)))


def person(
    rid: str,
    names: list[str],
    *,
    birth_date: str,
    nationality: str,
    gender: str = "",
    addresses: dict[str, str] | None = None,
    topics: list[str] | None = None,
) -> Record:
    roles = addresses or {}
    props = {
        "name": names,
        "birthDate": [birth_date],
        "nationality": [nationality],
        "gender": [gender] if gender else [],
        "addressEntity": sorted(roles),
        "topics": sorted(topics or []),
    }
    extra = {"address_roles": dict(sorted(roles.items()))} if roles else {}
    return _record(rid, "Person", props, _nr(_kind(topics), **extra))


def address(rid: str, full: str, *, city: str, postal_code: str, country: str) -> Record:
    props = {"full": [full], "city": [city], "postalCode": [postal_code], "country": [country]}
    return _record(rid, "Address", props, _nr("registry"))


def account(
    rid: str,
    number: str,
    *,
    bank_name: str,
    currency: str,
    opening_date: str,
    kind: str = "customer",
) -> Record:
    if not (number.startswith("NRSYN") and len(number) == 15 and number[5:].isdigit()):
        raise ValueError("synthetic account numbers are NRSYN plus 10 digits (R8)")
    if kind not in ("customer", "cash_ledger"):
        raise ValueError("account_kind is customer or cash_ledger")
    props = {
        "accountNumber": [number],
        "bankName": [bank_name],
        "currency": [currency],
        "openingDate": [opening_date],
    }
    return _record(rid, "BankAccount", props, _nr("activity", account_kind=kind))


def holding(rid: str, owner: str, account_id: str) -> Record:
    props = {"owner": [owner], "asset": [account_id], "role": ["account holder"]}
    return _record(rid, "Ownership", props, _nr("activity"))


BANDS: dict[str, tuple[float, float, bool, bool, str]] = {
    # band: (min, max, min exclusive, max exclusive, Companies House nature of control)
    "25-50": (25.0, 50.0, True, False, "ownership-of-shares-25-to-50-percent"),
    "50-75": (50.0, 75.0, True, True, "ownership-of-shares-50-to-75-percent"),
    "75-100": (75.0, 100.0, False, False, "ownership-of-shares-75-to-100-percent"),
}


def ownership(
    rid: str, owner: str, asset: str, *, band: str, start_date: str = "", nominee: bool = False
) -> Record:
    """`band` is a Companies House band ("25-50", "50-75", "75-100") or an exact share such as
    "exact:12.5" (a registered shareholding outside the PSC bands, for synthetic look-alikes)."""
    if band.startswith("exact:"):
        value = float(band.split(":", 1)[1])
        if not 0 < value <= 100:
            raise ValueError("an exact share lies in (0, 100]")
        props = {
            "owner": [owner],
            "asset": [asset],
            "percentage": [f"{value:g}"],
            "role": ["shareholder"],
            "startDate": [start_date] if start_date else [],
        }
        nr_extra: dict[str, Any] = {"share_pct_min": value, "share_pct_max": value}
        if nominee:
            nr_extra["is_nominee"] = True
        return _record(rid, "Ownership", props, _nr("registry", **nr_extra))
    low, high, low_x, high_x, nature = BANDS[band]
    props = {
        "owner": [owner],
        "asset": [asset],
        "percentage": [band],
        "role": [nature],
        "startDate": [start_date] if start_date else [],
    }
    extra: dict[str, Any] = {
        "natures_of_control": [nature],
        "share_pct_min": low,
        "share_pct_max": high,
    }
    if low_x:
        extra["share_pct_min_exclusive"] = True
    if high_x:
        extra["share_pct_max_exclusive"] = True
    if nominee:
        extra["is_nominee"] = True
    return _record(rid, "Ownership", props, _nr("registry", **extra))


def directorship(
    rid: str,
    director: str,
    organization_id: str,
    *,
    role: str = "director",
    start_date: str,
    end_date: str = "",
    nominee: bool = False,
) -> Record:
    props = {
        "director": [director],
        "organization": [organization_id],
        "role": [role],
        "startDate": [start_date],
        "endDate": [end_date] if end_date else [],
    }
    extra = {"is_nominee": True} if nominee else {}
    return _record(rid, "Directorship", props, _nr("registry", **extra))


def representation(rid: str, agent: str, client: str, *, role: str = "formation agent") -> Record:
    props = {"agent": [agent], "client": [client], "role": [role]}
    return _record(rid, "Representation", props, _nr("registry"))


def family(rid: str, person_id: str, relative: str, *, relationship: str) -> Record:
    props = {"person": [person_id], "relative": [relative], "relationship": [relationship]}
    return _record(rid, "Family", props, _nr("registry"))


def associate(rid: str, person_id: str, other: str, *, relationship: str) -> Record:
    props = {"person": [person_id], "associate": [other], "relationship": [relationship]}
    return _record(rid, "Associate", props, _nr("registry"))


def sanction(rid: str, entity: str, *, authority: str, program: str, start_date: str) -> Record:
    props = {
        "entity": [entity],
        "authority": [authority],
        "program": [program],
        "startDate": [start_date],
        "provisions": ["Asset freeze"],
    }
    return _record(rid, "Sanction", props, _nr("list"))


def control(
    rid: str, controller: str, controlled: str, *, control_type: str, band: str = ""
) -> Record:
    """A PSC `Control`: `control_type` voting, appointment or influence (C2 `control_type`); a
    voting band carries the four share keys as on `Ownership` (PHASE-2.md 4.5)."""
    if control_type not in ("voting", "appointment", "influence"):
        raise ValueError(f"unknown control type {control_type}")
    if (control_type == "voting") != bool(band):
        raise ValueError("a voting control needs a band, and only a voting control has one")
    nature = {
        "appointment": "right-to-appoint-and-remove-directors",
        "influence": "significant-influence-or-control",
    }.get(control_type, f"voting-rights-{band.replace('-', '-to-')}-percent")
    props = {
        "controller": [controller],
        "controlled": [controlled],
        "controlType": [control_type],
        "role": [nature],
    }
    extra: dict[str, Any] = {"natures_of_control": [nature]}
    if band:
        low, high, low_x, high_x, _ = BANDS[band]
        extra.update(share_pct_min=low, share_pct_max=high)
        if low_x:
            extra["share_pct_min_exclusive"] = True
        if high_x:
            extra["share_pct_max_exclusive"] = True
    return _record(rid, "Control", props, _nr("registry", **extra))


def consolidation(rid: str, parent: str, child: str, *, level: str = "direct") -> Record:
    """A GLEIF-style accounting consolidation (C2 `CONSOLIDATES`)."""
    props = {"owner": [parent], "asset": [child], "role": ["consolidation"]}
    return _record(rid, "Ownership", props, _nr("registry", consolidation=level))


def position(rid: str, name: str, *, country: str) -> Record:
    return _record(rid, "Position", {"name": [name], "country": [country]}, _nr("registry"))


def occupancy(rid: str, holder: str, post: str, *, start_date: str, end_date: str = "") -> Record:
    props = {
        "holder": [holder],
        "post": [post],
        "startDate": [start_date],
        "endDate": [end_date] if end_date else [],
        "status": ["current" if not end_date else "ended"],
    }
    return _record(rid, "Occupancy", props, _nr("registry"))


def payment(
    rid: str,
    *,
    payer: str,
    beneficiary: str,
    payer_account: str,
    beneficiary_account: str,
    amount: float | Decimal,
    currency: str,
    moment: datetime,
    channel: str,
    purpose: str = "",
) -> Record:
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel {channel}")
    if payer_account == beneficiary_account:
        raise ValueError("a payment needs two different accounts")
    props = {
        "payer": [payer],
        "beneficiary": [beneficiary],
        "payerAccount": [payer_account],
        "beneficiaryAccount": [beneficiary_account],
        "amount": [money(amount)],
        "currency": [currency],
        "date": [ts(moment)],
        "purpose": [purpose] if purpose else [],
    }
    return _record(rid, "Payment", props, _nr("activity", channel=channel))
```

### `ingest/src/neonradar_ingest/synth/ctx.py`

Verbatim. Python, 631 lines. SHA-256 `5e9228ef653221bc4146d4b6cb02c521ce1b3fa551cba19b4e24d0519907a5c5`.

```python
"""The generation context of generator v1 (PHASE-3.md 7.2.3).

`Ctx` owns everything an overlay writes: records by id (payments, nine in ten of them, kept as
their C1 lines so that a scale world fits in memory), the holder of every new account, the names
already used, the bank branches and the background counterparties. Background code may pay the
accounts of base organisations; scenario code works through `ScenarioCtx`, which refuses any
record that touches a base entity or a base entity's account (G1, D3 in 7.2.4), so a scenario can
only ever involve entities it created itself.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import numpy as np

from neonradar_ingest.synth import records as rec
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.streams import stream
from neonradar_ingest.synth.writer import line

Record = dict[str, Any]


class NameSource(Protocol):
    """Names for new synthetic people and companies (M3.3 adapts the Phase 1 name modules)."""

    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """All spellings of one invented person's name, and a gender ("male" or "female")."""
        ...

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """The same with an invented surname, for people on synthetic lists, PEP personas and
        their relatives and associates, so that no realistic full name is ever put on a
        synthetic list (PHASE-2.md M2.9)."""
        ...

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str: ...

    def street(self, rng: np.random.Generator) -> str: ...

    def town(self, rng: np.random.Generator) -> str: ...


FLAG_TOPICS = frozenset({"sanction", "role.pep", "role.rca"})
PERSONA_LOCALES = ("en_GB", "ar_SA", "ru_RU")


def letter(rng: np.random.Generator) -> str:
    return chr(65 + int(rng.integers(26)))


def name_key(name: str) -> str:
    """NFC, case-folded, spaces collapsed: the comparison form for name collisions."""
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


@dataclass(slots=True)
class LabelRows:
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    participants: list[dict[str, Any]] = field(default_factory=list)
    params: list[dict[str, Any]] = field(default_factory=list)


class Ctx:
    def __init__(
        self,
        seed: int,
        period: Period,
        names: NameSource,
        *,
        base_ids: Iterable[str] = (),
        base_names: Iterable[str] = (),
        soft_names: Iterable[str] = (),
        currency: str = "GBP",
    ) -> None:
        self.seed = seed
        self.period = period
        self.names = names
        self.currency = currency
        self.records: dict[str, Record] = {}  # every record except payments
        self.payments: dict[str, str] = {}  # payment id -> its C1 line
        self.holder_of: dict[str, str] = {}
        self.base_ids = frozenset(base_ids)
        self.base_accounts: set[str] = set()
        self.base_name_keys = frozenset(name_key(n) for n in base_names)
        self.used_names = set(self.base_name_keys) | {name_key(n) for n in soft_names}
        self.branches: list[str] = []
        self.labels = LabelRows()
        self.split = "dev"
        self._company_numbers: set[str] = set()

    # streams and ids ---------------------------------------------------------------------------

    def rng(self, *keys: str) -> np.random.Generator:
        return stream(self.seed, *keys)

    def rid(self, namespace: str, key: str) -> str:
        rid = rec.hashed_id(namespace, self.seed, key)
        if rid in self.records or rid in self.payments:
            raise ValueError(f"id collision for {namespace}:{key}")
        return rid

    def add(self, record: Record) -> str:
        rid = str(record["id"])
        if rid in self.records or rid in self.payments:
            raise ValueError(f"duplicate record id {rid}")
        if record["schema"] == "Payment":
            self.payments[rid] = line(record)
        else:
            self.records[rid] = record
        return rid

    def record(self, rid: str) -> Record:
        """Any record of this overlay; a payment is parsed back from its line."""
        found = self.records.get(rid)
        if found is not None:
            return found
        parsed: Record = json.loads(self.payments[rid])
        return parsed

    # entities ----------------------------------------------------------------------------------

    def _unique(self, make: Any, attempts: int = 50) -> Any:
        """A name that no base record uses (PHASE-1.md 7.1, synthetic-join mode) and, when one turns
        up within `attempts` draws, that no synthetic record uses yet; after that a synthetic
        repeat is accepted, because a large world can exhaust the word lists (real registers
        repeat names too). Only the name stream moves, so structure never depends on it."""
        for i in range(2 * attempts):
            value = make()
            names = value[0] if isinstance(value, tuple) else [value]
            keys = [name_key(n) for n in names]
            if any(k in self.base_name_keys for k in keys):
                continue
            if i >= attempts or not any(k in self.used_names for k in keys):
                self.used_names.update(keys)
                return value
        raise RuntimeError("could not find a name that no base record uses")

    def company_number(self, rng: np.random.Generator) -> str:
        """`SY9` plus five digits: the overlay range of synthetic company numbers (7.2.2)."""
        for _ in range(1000):
            number = f"SY9{int(rng.integers(0, 100_000)):05d}"
            if number not in self._company_numbers:
                self._company_numbers.add(number)
                return number
        raise RuntimeError("synthetic company numbers exhausted")

    def address(self, key: str, *, country: str = "gb", district: str = "") -> str:
        """A new address; `district` fixes the postcode district (outward code), else one of QQ1 to
        QQ98. QQ is not a UK postcode area, so no synthetic postcode is a real one."""
        rng = self.rng("address", key)
        number = int(rng.integers(1, 200))
        outward = district or f"QQ{int(rng.integers(1, 99))}"
        postcode = f"{outward} {int(rng.integers(1, 9))}{letter(rng)}{letter(rng)}"
        name_rng = self.rng("address-name", key)  # names never move a structural draw
        street = self.names.street(name_rng)
        town = self.names.town(name_rng)
        full = f"{number} {street}, {town}, {postcode}"
        rid = self.rid("addr", key)
        return self.add(rec.address(rid, full, city=town, postal_code=postcode, country=country))

    def company(
        self,
        key: str,
        *,
        jurisdiction: str = "gb",
        incorporated: date,
        sector: str = "",
        address: str = "",
        accounts_category: str = "",
        topics: tuple[str, ...] = (),
    ) -> str:
        rng = self.rng("company", key)
        name_rng = self.rng("company-name", key)
        name = self._unique(lambda: self.names.company(name_rng, jurisdiction))
        rid = self.rid("co", key)
        record = rec.company(
            rid,
            name,
            jurisdiction=jurisdiction,
            registration_number=self.company_number(rng),
            incorporation_date=incorporated.isoformat(),
            addresses={address: "registered"} if address else None,
            sector=sector,
            topics=list(topics),
        )
        if accounts_category:
            record["nr"]["accounts_category"] = accounts_category
        return self.add(record)

    def organization(
        self, key: str, name: str, *, country: str = "gb", topics: tuple[str, ...] = ()
    ) -> str:
        if name_key(name) in self.used_names:
            raise ValueError(f"name already used: {name}")
        self.used_names.add(name_key(name))
        return self.add(
            rec.organization(self.rid("org", key), name, country=country, topics=list(topics))
        )

    def person(
        self,
        key: str,
        *,
        locale: str = "en_GB",
        nationality: str = "gb",
        born: tuple[int, int] = (1950, 2004),
        topics: tuple[str, ...] = (),
        invented: bool = False,
    ) -> str:
        """A synthetic person. A person with a list, PEP or RCA topic, or `invented`, gets an
        invented surname; `locale="any"` lets the name stream choose the script."""
        rng = self.rng("person", key)
        name_rng = self.rng("person-name", key)
        if locale == "any":
            locale = str(name_rng.choice(PERSONA_LOCALES))
        if invented or set(topics) & FLAG_TOPICS:
            names, gender = self._unique(lambda: self.names.invented_person(name_rng, locale))
        else:
            names, gender = self._unique(lambda: self.names.person(name_rng, locale))
        year = int(rng.integers(born[0], born[1] + 1))
        month = int(rng.integers(1, 13))
        rid = self.rid("p", key)
        return self.add(
            rec.person(
                rid,
                names,
                birth_date=f"{year:04d}-{month:02d}",
                nationality=nationality,
                gender=gender,
                topics=list(topics),
            )
        )

    def account(
        self,
        key: str,
        holder: str,
        *,
        opened: date,
        currency: str = "",
        kind: str = "customer",
        bank: str = "",
    ) -> str:
        rid = self.rid("acct", key)
        self.add(
            rec.account(
                rid,
                "NRSYN0000000000",  # replaced by assign_account_numbers() before writing
                bank_name=bank or "Synthetic Bank One",
                currency=currency or self.currency,
                opening_date=opened.isoformat(),
                kind=kind,
            )
        )
        self.add(rec.holding(self.rid("hold", key), holder, rid))
        self.holder_of[rid] = holder
        if holder in self.base_ids:
            self.base_accounts.add(rid)
        return rid

    # relationships -----------------------------------------------------------------------------

    def pay(
        self,
        key: str,
        src: str,
        dst: str,
        amount: float,
        moment: datetime,
        *,
        channel: str = "wire",
        purpose: str = "",
        currency: str = "",
    ) -> str:
        if not self.period.start <= moment < self.period.end:
            raise ValueError(f"payment {key} at {moment} lies outside the period")
        rid = self.rid("pay", key)
        return self.add(
            rec.payment(
                rid,
                payer=self.holder_of[src],
                beneficiary=self.holder_of[dst],
                payer_account=src,
                beneficiary_account=dst,
                amount=amount,
                currency=currency or self._currency_of(src),
                moment=moment,
                channel=channel,
                purpose=purpose,
            )
        )

    def _currency_of(self, account: str) -> str:
        return str(self.records[account]["properties"]["currency"][0])

    def owns(
        self,
        key: str,
        owner: str,
        asset: str,
        *,
        band: str,
        start: date | None = None,
        nominee: bool = False,
    ) -> str:
        return self.add(
            rec.ownership(
                self.rid("own", key),
                owner,
                asset,
                band=band,
                start_date=start.isoformat() if start else "",
                nominee=nominee,
            )
        )

    def director(
        self,
        key: str,
        person: str,
        org: str,
        *,
        start: date,
        end: date | None = None,
        nominee: bool = False,
    ) -> str:
        return self.add(
            rec.directorship(
                self.rid("dir", key),
                person,
                org,
                start_date=start.isoformat(),
                end_date=end.isoformat() if end else "",
                nominee=nominee,
            )
        )

    def represents(self, key: str, agent: str, client: str) -> str:
        return self.add(rec.representation(self.rid("rep", key), agent, client))

    def family(self, key: str, person: str, relative: str, relationship: str) -> str:
        return self.add(
            rec.family(self.rid("fam", key), person, relative, relationship=relationship)
        )

    def control(
        self,
        key: str,
        controller: str,
        controlled: str,
        *,
        control_type: str = "influence",
        band: str = "",
    ) -> str:
        """A PSC control: `control_type` is a C2 measure (voting, appointment, influence); `band` a
        voting band ("25-50", "50-75", "75-100") for `voting`."""
        return self.add(
            rec.control(
                self.rid("ctl", key), controller, controlled, control_type=control_type, band=band
            )
        )

    def associate(self, key: str, person: str, other: str, relationship: str) -> str:
        return self.add(
            rec.associate(self.rid("assoc", key), person, other, relationship=relationship)
        )

    def position(self, key: str, name: str, *, country: str) -> str:
        return self.add(rec.position(self.rid("pos", key), name, country=country))

    def occupancy(
        self, key: str, person: str, position: str, *, start: date, end: date | None = None
    ) -> str:
        return self.add(
            rec.occupancy(
                self.rid("occ", key),
                person,
                position,
                start_date=start.isoformat(),
                end_date=end.isoformat() if end else "",
            )
        )

    def consolidates(self, key: str, parent: str, child: str) -> str:
        return self.add(rec.consolidation(self.rid("cons", key), parent, child))

    def sanction(self, key: str, entity: str, *, start: date) -> str:
        return self.add(
            rec.sanction(
                self.rid("san", key),
                entity,
                authority="Synthetic Authority A",
                program="Synthetic Programme 1",
                start_date=start.isoformat(),
            )
        )

    # finishing ---------------------------------------------------------------------------------

    def assign_account_numbers(self, taken: Iterable[str] = ()) -> None:
        """Give every new account a stable `NRSYN` number: 10 digits from a hash of its id, the next
        free number on a collision, in id order (R8)."""
        used = set(taken)
        for rid in sorted(r for r, x in self.records.items() if x["schema"] == "BankAccount"):
            value = int(hashlib.sha256(f"{self.seed}|{rid}".encode()).hexdigest(), 16) % 10**10
            while f"NRSYN{value:010d}" in used:
                value = (value + 1) % 10**10
            number = f"NRSYN{value:010d}"
            used.add(number)
            self.records[rid]["properties"]["accountNumber"] = [number]


class ScenarioCtx:
    """What a scenario module may do: create its own entities, link them, pay between them.

    Every id a scenario passes must be one it created (or a bank branch ledger); anything else is a
    programming error and raises, so no scenario can reach a base entity (G1)."""

    def __init__(self, ctx: Ctx, scenario_id: str, typology: str, *, lookalike: bool) -> None:
        self.ctx = ctx
        self.scenario_id = scenario_id
        self.typology = typology
        self.lookalike = lookalike
        self.created: set[str] = set()
        self.core_payments: list[tuple[str, str, bool]] = []  # (payment id, role, is_core)
        self.roles: dict[str, tuple[str, bool]] = {}  # object id -> (role, is_core)
        self._n = 0

    def rng(self, *keys: str) -> np.random.Generator:
        return self.ctx.rng("scenario", self.scenario_id, *keys)

    def _key(self, kind: str) -> str:
        self._n += 1
        return f"{self.scenario_id}|{kind}|{self._n}"

    def _check(self, *ids: str) -> None:
        for i in ids:
            if i not in self.created and i not in self.ctx.branches:
                raise PermissionError(f"scenario {self.scenario_id} may not use {i}")

    def _own(self, rid: str) -> str:
        self.created.add(rid)
        return rid

    @property
    def period(self) -> Period:
        return self.ctx.period

    def address(self, *, country: str = "gb", district: str = "") -> str:
        return self._own(self.ctx.address(self._key("addr"), country=country, district=district))

    def company(self, **kw: Any) -> str:
        if kw.get("address"):
            self._check(kw["address"])
        return self._own(self.ctx.company(self._key("co"), **kw))

    def person(self, **kw: Any) -> str:
        return self._own(self.ctx.person(self._key("p"), **kw))

    def organization(self, name: str, **kw: Any) -> str:
        return self._own(self.ctx.organization(self._key("org"), name, **kw))

    def account(
        self, holder: str, *, opened: date, currency: str = "", kind: str = "customer"
    ) -> str:
        self._check(holder)
        return self._own(
            self.ctx.account(self._key("acct"), holder, opened=opened, currency=currency, kind=kind)
        )

    def pay(self, src: str, dst: str, amount: float, moment: datetime, **kw: Any) -> str:
        self._check(src, dst)
        return self.ctx.pay(self._key("pay"), src, dst, amount, moment, **kw)

    def owns(self, owner: str, asset: str, **kw: Any) -> str:
        self._check(owner, asset)
        return self.ctx.owns(self._key("own"), owner, asset, **kw)

    def director(self, person: str, org: str, **kw: Any) -> str:
        self._check(person, org)
        return self.ctx.director(self._key("dir"), person, org, **kw)

    def represents(self, agent: str, client: str) -> str:
        self._check(agent, client)
        return self.ctx.represents(self._key("rep"), agent, client)

    def family(self, person: str, relative: str, relationship: str = "sibling") -> str:
        self._check(person, relative)
        return self.ctx.family(self._key("fam"), person, relative, relationship)

    def control(self, controller: str, controlled: str, **kw: Any) -> str:
        self._check(controller, controlled)
        return self.ctx.control(self._key("ctl"), controller, controlled, **kw)

    def associate(self, person: str, other: str, relationship: str = "business partner") -> str:
        self._check(person, other)
        return self.ctx.associate(self._key("assoc"), person, other, relationship)

    def position(self, name: str, *, country: str) -> str:
        return self._own(self.ctx.position(self._key("pos"), name, country=country))

    def occupancy(self, person: str, position: str, *, start: date, end: date | None = None) -> str:
        self._check(person, position)
        return self.ctx.occupancy(self._key("occ"), person, position, start=start, end=end)

    def consolidates(self, parent: str, child: str) -> str:
        self._check(parent, child)
        return self.ctx.consolidates(self._key("cons"), parent, child)

    def sanction(self, entity: str, *, start: date) -> str:
        self._check(entity)
        return self.ctx.sanction(self._key("san"), entity, start=start)

    # labels ------------------------------------------------------------------------------------

    def label_payment(self, payment_id: str, role: str, *, core: bool = True) -> str:
        """Mark a payment as part of the pattern (labels/transactions.csv)."""
        if payment_id not in self.ctx.payments:
            raise ValueError(f"not a payment of this overlay: {payment_id}")
        self.core_payments.append((payment_id, role, core))
        return payment_id

    def label(self, object_id: str, role: str, *, core: bool = True) -> str:
        """Mark a participant with its role (labels/participants.csv): an entity, account or
        address this scenario created, or a relationship record between two of them."""
        record = self.ctx.records.get(object_id)
        if record is None or record["schema"] not in RELATIONSHIP_SCHEMAS:
            self._check(object_id)  # anything this scenario did not create is refused (G1)
        if record is None:
            raise ValueError(f"unknown object {object_id}")
        self.roles[object_id] = (role, core)
        return object_id

    def finish(
        self,
        variant: str,
        difficulty: str,
        params: dict[str, Any],
        expected: dict[str, Any] | None = None,
    ) -> None:
        if not self.roles:
            raise ValueError(f"scenario {self.scenario_id} labelled no participant")
        records = self.ctx.records
        dates = {p: self.ctx.record(p)["properties"]["date"][0] for p, _, _ in self.core_payments}
        pays = sorted(self.core_payments, key=lambda x: (dates[x[0]], x[0]))
        times = [dates[p] for p, _, _ in pays]
        kinds = {oid: object_kind(records[oid]) for oid in self.roles}
        self.ctx.labels.scenarios.append(
            {
                "scenario_id": self.scenario_id,
                "typology": self.typology,
                "variant": variant,
                "is_lookalike": self.lookalike,
                "start_ts": min(times) if times else "",
                "end_ts": max(times) if times else "",
                "participants": "",
                "difficulty": difficulty,
                "split": self.ctx.split,
                "n_transactions": len({p for p, _, _ in pays}),
                "n_accounts": sum(1 for k in kinds.values() if k == "account"),
                "n_entities": sum(1 for k in kinds.values() if k == "entity"),
                "n_relationships": sum(1 for k in kinds.values() if k == "relationship"),
            }
        )
        for step, (payment_id, role, core) in enumerate(pays, 1):
            self.ctx.labels.transactions.append(
                {
                    "tx_id": payment_id,
                    "scenario_id": self.scenario_id,
                    "typology": self.typology,
                    "step": step,
                    "role": role,
                    "is_illicit": not self.lookalike,
                    "variant": variant,
                    "is_lookalike": self.lookalike,
                    "is_core": core,
                }
            )
        for object_id, (role, core) in sorted(self.roles.items()):
            self.ctx.labels.participants.append(
                {
                    "scenario_id": self.scenario_id,
                    "object_kind": kinds[object_id],
                    "object_id": c2_id(records[object_id]),
                    "role": role,
                    "is_core": core,
                }
            )
        self.ctx.labels.params.append(
            {
                "scenario_id": self.scenario_id,
                "params": params,
                "expected_metrics": expected or {},
                "stream_key": ["scenario", self.scenario_id],
                "generator": {
                    "component": f"scenarios.{self.typology}",
                    "version": GENERATOR_VERSION,
                },
            }
        )


RELATIONSHIP_SCHEMAS = frozenset(
    {"Ownership", "Control", "Directorship", "Representation", "Family", "Associate", "Occupancy"}
)
GENERATOR_VERSION = "1.0.0"


def object_kind(record: Record) -> str:
    schema = record["schema"]
    if schema == "BankAccount":
        return "account"
    if schema == "Address":
        return "address"
    if schema in RELATIONSHIP_SCHEMAS:
        return "relationship"
    return "entity"


def c2_id(record: Record) -> str:
    """The C2 id of a labelled object: the record id (FtM interval entity id for relationships)."""
    return str(record["id"])
```

### `ingest/src/neonradar_ingest/synth/base.py`

Verbatim. Python, 129 lines. SHA-256 `c0fc800894654fe1828df5ca5ac5ce2dac4c386fb8fc5481b350ad78d79a61c9`.

```python
"""The base an overlay attaches to (PHASE-3.md 7.2.3, D3).

`BaseView.from_records` reads C1 entity records (a synthetic world, a fixture, or the records of a
real profile) and, when the profile was resolved, the resolution run's `canonical.csv`. It keeps:
every base id (so no scenario can use one), every name of a non-synthetic base record (no new name
may repeat one) and of a synthetic base record (new names avoid them where they can), the account
numbers already in use, and the eligible organisations. An organisation is eligible for an
account when it is a `Company` or `Organization` from a registry or synthetic dataset, carries no
flag topic, and is not dissolved. People are never eligible: generated payments next to an
identifiable person would be invented financial data about them. A merged entity counts once,
through its anchor record, and is not eligible if any of its records is flagged or comes from a
list or leak dataset.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_ingest.synth.background import BaseOrg

ENTITY_SCHEMAS = frozenset(
    {"Person", "Company", "Organization", "LegalEntity", "PublicBody", "Address"}
)
ELIGIBLE_SCHEMAS = frozenset({"Company", "Organization"})
DESCRIPTIVE = frozenset({"corp.public", "fin", "gov", "pol.party", "pol.union", "rel", "mil"})
CLOSED = frozenset({"dissolved", "closed", "inactive", "liquidation", "struck off", "removed"})


def flag_topics(topics: Iterable[str]) -> set[str]:
    """Topics that are more than descriptive (PHASE-2.md 7.1.1)."""
    return {t for t in topics if t not in DESCRIPTIVE and not t.startswith(("fin.", "gov."))}


@dataclass(slots=True)
class BaseView:
    ids: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)  # of non-synthetic records: never reused
    synthetic_names: set[str] = field(default_factory=set)  # of synthetic records: avoided
    account_numbers: set[str] = field(default_factory=set)
    eligible: list[BaseOrg] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_records(
        cls,
        records: Iterable[Mapping[str, Any]],
        dataset_kinds: Mapping[str, str],
        canonical_csv: Path | None = None,
    ) -> BaseView:
        view = cls()
        by_id: dict[str, Mapping[str, Any]] = {}
        for r in records:
            view.ids.add(r["id"])
            props = r.get("properties", {})
            synthetic = dataset_kinds.get(r["datasets"][0]) == "synthetic"
            for key in ("name", "alias", "previousName"):
                (view.synthetic_names if synthetic else view.names).update(props.get(key, []))
            if r["schema"] == "BankAccount":
                view.account_numbers.update(props.get("accountNumber", []))
            if r["schema"] in ENTITY_SCHEMAS:
                by_id[r["id"]] = r
        clusters = _clusters(by_id, canonical_csv)
        for anchor, members in sorted(clusters.items()):
            reason = _ineligible(by_id[anchor], [by_id[m] for m in members], dataset_kinds)
            if reason:
                view.skipped[reason] = view.skipped.get(reason, 0) + 1
                continue
            r = by_id[anchor]
            props = r.get("properties", {})
            view.eligible.append(
                BaseOrg(
                    anchor,
                    (props.get("sector") or [""])[0],
                    (props.get("incorporationDate") or [""])[0],
                    str((r.get("nr") or {}).get("accounts_category", "")),
                )
            )
        return view


def _clusters(
    by_id: Mapping[str, Mapping[str, Any]], canonical_csv: Path | None
) -> dict[str, list[str]]:
    """Anchor record id to member record ids: one cluster per record without a resolution run."""
    if canonical_csv is None:
        return {i: [i] for i in by_id}
    groups: dict[str, list[str]] = {}
    with canonical_csv.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["record_id"] in by_id:
                groups.setdefault(row["canonical_id"], []).append(row["record_id"])
    out = {}
    clustered: set[str] = set()
    for canonical, members in groups.items():
        anchor = (
            canonical[3:]
            if canonical.startswith("nr-") and canonical[3:] in members
            else min(members)
        )
        out[anchor] = sorted(members)
        clustered.update(members)
    for i in by_id:
        if i not in clustered:
            out[i] = [i]
    return out


def _ineligible(
    anchor: Mapping[str, Any], members: list[Mapping[str, Any]], kinds: Mapping[str, str]
) -> str:
    if anchor["schema"] not in ELIGIBLE_SCHEMAS:
        return "not_an_organisation"
    for m in members:
        kind = kinds.get(m["datasets"][0], "")
        if kind in ("list", "leak"):
            return "list_or_leak_record"
        if kind not in ("registry", "synthetic"):
            return "unknown_dataset_kind"
        if flag_topics(m.get("properties", {}).get("topics", [])):
            return "flagged"
    props = anchor.get("properties", {})
    status = " ".join(props.get("status", [])).casefold()
    if props.get("dissolutionDate") or any(word in status for word in CLOSED):
        return "dissolved"
    return ""
```

### `ingest/src/neonradar_ingest/synth/background.py`

Verbatim. Python, 479 lines. SHA-256 `01025dc122321c031c4af84ca320915a0f5005d12b030793840f8b936391ec08`.

```python
"""Background activity of generator v1 (PHASE-3.md 7.2.4).

Every eligible base organisation (or the share `BackgroundConfig.share` of them, chosen by a hash
of the seed and the organisation's id, so the choice draws nothing from any stream) gets an account
and the ordinary activity of a UK business for the whole period, calibrated as
`synthetic-transactions.md` section 2 describes (the values below are the defaults of
`BackgroundConfig`; every one is a documented assumption or a published figure): payroll on the
last working day (most businesses have no employees), PAYE on the 22nd of the next month, VAT a
month and seven days after each quarter, rent on the first working day, supplier payment runs,
customer receipts, card settlements and cash banking for the sectors that take them, and sometimes
a loan. Employees pay rent, shop by card and draw cash. Times follow London working hours and bank
holidays, stored in UTC.

Payments only ever join a base organisation and a synthetic counterparty, or two synthetic
counterparties: never two base entities (I16). The background of a base organisation is a plain
profile with nothing typology-shaped in it (no cash just under a threshold, no pass-through, no
cycles, no quiet gap followed by a burst), as `synthetic-transactions.md` 2.8 recommends.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from neonradar_ingest.synth.ctx import Ctx
from neonradar_ingest.synth.dates import at, last_working_day, previous_working_day, working_days

CARD_SECTORS = frozenset(
    {"retail", "hospitality", "restaurant", "tourism", "convenience store", "car wash"}
)
CASH_SECTORS = frozenset(
    {"retail", "hospitality", "restaurant", "car wash", "convenience store", "tourism"}
)
SEASONAL_SECTORS = frozenset({"tourism"})


@dataclass(frozen=True, slots=True)
class BackgroundConfig:
    banks: int = 3
    branches_per_bank: int = 4
    no_employee_share: float = 0.70  # 75 percent of UK businesses have no employees (S42)
    small_employer_share: float = 0.25  # 1 to 9 employees; the rest employ 10 to 30
    suppliers: tuple[int, int] = (2, 6)
    customers: tuple[int, int] = (1, 4)
    pool_ratio: float = 0.2
    salary_median: float = 2300.0  # net a month; full-time median net about 2,636 (S39, S48)
    salary_sigma: float = 0.35
    rent_median: float = 1500.0
    supplier_median: float = 1800.0
    customer_median: float = 3200.0
    card_settlement_median: float = 850.0
    cash_deposit_median: float = 1200.0
    cash_banking_days: tuple[int, int] = (1, 5)  # times a week a cash business banks its takings
    loan_share: float = 0.08
    refund_share: float = 0.05
    person_rent_share: float = 0.6
    person_rent_median: float = 1400.0  # UK average rent, August 2026 (S40)
    person_cards: tuple[int, int] = (2, 6)  # a month; fewer than the UK rate, to bound volume
    card_median: float = 15.0  # debit card median assumed; mean about 29 (S30)
    card_sigma: float = 1.16
    cash_withdrawal_median: float = 100.0  # Post Office mean withdrawal about 140 (S49)
    personal: bool = True
    scale: float = 1.0
    share: float = (
        1.0  # of eligible organisations with an account and activity (7.11: real profiles)
    )
    spend_share: tuple[float, float] = (
        0.85,
        0.97,
    )  # outflows over inflows for a business (assumption)


@dataclass(frozen=True, slots=True)
class BaseOrg:
    id: str
    sector: str
    incorporated: str
    accounts_category: str


def _amount(rng: np.random.Generator, median: float, sigma: float) -> float:
    return round(max(1.0, float(median * np.exp(sigma * rng.standard_normal()))), 2)


def _opened(rng: np.random.Generator, period_start: date, incorporated: str) -> date:
    opened = period_start - timedelta(days=int(rng.integers(90, 3650)))
    if len(incorporated) == 10:
        inc = date.fromisoformat(incorporated)
        if inc + timedelta(days=60) > opened:
            opened = inc + timedelta(
                days=int(rng.integers(0, 61))
            )  # 0 to 60 days after incorporation
    return opened


def setup_banks(ctx: Ctx, cfg: BackgroundConfig) -> None:
    """Synthetic banks with cash ledger accounts at their branches (C1 `cash_ledger`)."""
    opened = ctx.period.start.date() - timedelta(days=5000)
    words = ("One", "Two", "Three", "Four", "Five")
    for b in range(cfg.banks):
        bank = ctx.organization(f"bank|{b}", f"Synthetic Bank {words[b % 5]} plc")
        for k in range(cfg.branches_per_bank):
            ctx.branches.append(
                ctx.account(
                    f"branch|{b}|{k}",
                    bank,
                    opened=opened,
                    kind="cash_ledger",
                    bank=f"Synthetic Bank {words[b % 5]}",
                )
            )


class Pools:
    """Synthetic counterparties shared by the base organisations, each with one account."""

    def __init__(self, ctx: Ctx, n_orgs: int, cfg: BackgroundConfig) -> None:
        rng = ctx.rng("pools")
        start = ctx.period.start.date()
        size = max(5, int(n_orgs * cfg.pool_ratio))

        def company_account(kind: str, i: int, sector: str) -> str:
            address = ctx.address(f"pool|{kind}|{i}")
            co = ctx.company(
                f"pool|{kind}|{i}",
                incorporated=start - timedelta(days=int(rng.integers(400, 9000))),
                sector=sector,
                address=address,
            )
            director = ctx.person(f"pool|{kind}|{i}|director")
            ctx.director(
                f"pool|{kind}|{i}",
                director,
                co,
                start=start - timedelta(days=int(rng.integers(100, 6000))),
            )
            return ctx.account(
                f"pool|{kind}|{i}", co, opened=start - timedelta(days=int(rng.integers(100, 5000)))
            )

        self.suppliers = [company_account("supplier", i, "wholesale") for i in range(size)]
        self.customers = [company_account("customer", i, "services") for i in range(size)]
        self.landlords = [
            company_account("landlord", i, "real estate") for i in range(max(3, size // 4))
        ]
        self.merchants = [
            company_account("merchant", i, "retail") for i in range(max(3, size // 3))
        ]
        opened = start - timedelta(days=6000)
        self.acquirer = ctx.account(
            "pool|acquirer",
            ctx.organization("pool|acquirer", "Synthetic Card Acquiring Ltd"),
            opened=opened,
        )
        self.lender = ctx.account(
            "pool|lender",
            ctx.organization("pool|lender", "Synthetic Business Lending plc"),
            opened=opened,
        )
        self.tax = ctx.account(
            "pool|tax", ctx.organization("pool|tax", "Synthetic Revenue Office"), opened=opened
        )

    @staticmethod
    def pick(rng: np.random.Generator, items: list[str], k: int) -> list[str]:
        """`k` distinct items; earlier items are more popular (heavy-tailed, S15 S20)."""
        k = min(k, len(items))
        weights = 1.0 / np.arange(1, len(items) + 1) ** 0.8
        idx = rng.choice(len(items), size=k, replace=False, p=weights / weights.sum())
        return [items[int(i)] for i in sorted(idx)]


def _employees(rng: np.random.Generator, cfg: BackgroundConfig) -> int:
    r = rng.random()
    if r < cfg.no_employee_share:
        return 0
    if r < cfg.no_employee_share + cfg.small_employer_share:
        return int(rng.integers(1, 10))
    return int(rng.integers(10, 31))


@dataclass(slots=True)
class _Planned:
    src: str
    dst: str
    amount: float
    day: date
    first_hour: int
    last_hour: int
    kind: str  # in | fixed | supplier
    channel: str = "wire"
    purpose: str = ""


def selected(seed: int, org_id: str, share: float) -> bool:
    """Whether an organisation is in the active share: a uniform number from SHA-256 of the seed
    and the id, below `share`."""
    digest = hashlib.sha256(f"{seed}|{org_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < share


def generate(ctx: Ctx, orgs: list[BaseOrg], cfg: BackgroundConfig) -> dict[str, int]:
    """Accounts and activity for `orgs`, which are already the eligible ones, in id order.

    Each business keeps a working balance: its outflows over the period come to `spend_share` of
    its inflows (drawn per business), so the money it pays out is not, first in first out, the
    money it has just received. Supplier payments take up what fixed costs leave; when fixed costs
    alone would exceed that share, the business's receipts are scaled up instead."""
    if cfg.share < 1.0:
        orgs = [o for o in orgs if selected(ctx.seed, o.id, cfg.share)]
    if not ctx.branches:
        setup_banks(ctx, cfg)
    pools = Pools(ctx, len(orgs), cfg)
    months = ctx.period.months()
    start, end = ctx.period.start.date(), ctx.period.end.date()
    days_all = working_days(start, end)
    counts = {"organisations": 0, "employees": 0}
    for org in orgs:
        counts["organisations"] += 1
        counts["employees"] += _organisation(ctx, org, pools, cfg, months, days_all)
    return counts


def _organisation(
    ctx: Ctx,
    org: BaseOrg,
    pools: Pools,
    cfg: BackgroundConfig,
    months: list[date],
    days_all: list[date],
) -> int:
    """One base organisation's account and activity; returns its number of employees."""
    start, end = ctx.period.start.date(), ctx.period.end.date()
    rng = ctx.rng("background", org.id)
    opened = _opened(rng, start, org.incorporated)
    acct = ctx.account(f"base|{org.id}", org.id, opened=opened)
    if org.accounts_category.upper() == "DORMANT":
        return 0  # a company that files dormant accounts has no activity
    first_day = max(start, opened + timedelta(days=1))
    closed = (10, 11, 12, 1, 2, 3) if org.sector in SEASONAL_SECTORS else ()

    def open_on(day: date) -> bool:
        return day >= first_day and day.month not in closed

    plan: list[_Planned] = []

    def add(
        src: str,
        dst: str,
        amount: float,
        day: date,
        kind: str,
        first_hour: int = 8,
        last_hour: int = 18,
        channel: str = "wire",
        purpose: str = "",
    ) -> None:
        if start <= day < end and amount > 0:
            plan.append(
                _Planned(src, dst, amount, day, first_hour, last_hour, kind, channel, purpose)
            )

    employees = []
    for e in range(int(_employees(rng, cfg) * cfg.scale + 0.5)):
        person = ctx.person(f"emp|{org.id}|{e}", born=(1955, 2006))
        emp_acct = ctx.account(
            f"emp|{org.id}|{e}",
            person,
            opened=start - timedelta(days=int(rng.integers(60, 9000))),
        )
        employees.append((emp_acct, _amount(rng, cfg.salary_median, cfg.salary_sigma)))
    suppliers = Pools.pick(
        rng, pools.suppliers, int(rng.integers(cfg.suppliers[0], cfg.suppliers[1] + 1))
    )
    customers = Pools.pick(
        rng, pools.customers, int(rng.integers(cfg.customers[0], cfg.customers[1] + 1))
    )
    landlord = pools.landlords[int(rng.integers(len(pools.landlords)))]
    rent = _amount(rng, cfg.rent_median, 0.6)
    spend_share = float(rng.uniform(*cfg.spend_share))
    # receipts
    for customer in customers:
        every = int(rng.choice([10, 20, 30]))
        median = _amount(rng, cfg.customer_median, 0.8)
        for day in days_all[int(rng.integers(0, every)) :: every]:
            if open_on(day):
                amount = _amount(rng, median, 0.3)
                add(customer, acct, amount, day, "in", purpose="Invoice")
                if rng.random() < cfg.refund_share:
                    add(
                        acct,
                        customer,
                        _amount(rng, amount * 0.2, 0.5),
                        day + timedelta(days=int(rng.integers(3, 20))),
                        "fixed",
                        purpose="Credit note",
                    )
    if org.sector in CARD_SECTORS:
        median = _amount(rng, cfg.card_settlement_median, 0.6)
        for day in days_all:
            if open_on(day):
                add(
                    pools.acquirer,
                    acct,
                    _amount(rng, median, 0.4),
                    day,
                    "in",
                    5,
                    7,
                    purpose="Card settlement",
                )
    if org.sector in CASH_SECTORS:
        per_week = int(rng.integers(cfg.cash_banking_days[0], cfg.cash_banking_days[1] + 1))
        median = _amount(rng, cfg.cash_deposit_median * 5 / per_week, 0.4)
        d = start
        while d < end:
            if open_on(d) and d.weekday() < 6 and rng.random() < per_week / 6 * cfg.scale:
                branch = ctx.branches[int(rng.integers(len(ctx.branches)))]
                add(
                    branch,
                    acct,
                    _amount(rng, median, 0.45),
                    d,
                    "in",
                    9,
                    17,
                    channel="cash_deposit",
                    purpose="Takings",
                )
            d += timedelta(days=1)
    # fixed costs
    for month in months:
        payday = last_working_day(month)
        if open_on(payday):
            for emp_acct, salary in employees:
                add(
                    acct,
                    emp_acct,
                    round(salary * float(rng.uniform(0.97, 1.03)), 2),
                    payday,
                    "fixed",
                    6,
                    8,
                    purpose="Salary",
                )
            if employees:
                due = previous_working_day(
                    date(month.year + month.month // 12, month.month % 12 + 1, 22)
                )
                add(
                    acct,
                    pools.tax,
                    round(sum(s for _, s in employees) * 0.32, 2),
                    due,
                    "fixed",
                    purpose="PAYE",
                )
        rent_day = next((d for d in days_all if d >= month), None)
        if rent_day and open_on(rent_day):
            add(acct, landlord, rent, rent_day, "fixed", purpose="Rent")
    if rng.random() < cfg.loan_share and len(days_all) > 60:
        principal = _amount(rng, 25000, 0.7)
        draw = days_all[int(rng.integers(0, len(days_all) // 2))]
        if open_on(draw):
            add(pools.lender, acct, principal, draw, "loan", purpose="Loan drawdown")
            for k in range(1, 13):
                add(
                    acct,
                    pools.lender,
                    round(principal / 12 * 1.06, 2),
                    previous_working_day(draw + timedelta(days=30 * k)),
                    "loan",
                    purpose="Loan repayment",
                )
    # supplier runs, scaled to what the business can spend
    raw: list[_Planned] = []
    for supplier in suppliers:
        every = int(rng.choice([5, 10, 20]))  # working days between payment runs
        median = _amount(rng, cfg.supplier_median, 0.8)
        for day in days_all[int(rng.integers(0, every)) :: every]:
            if open_on(day):
                raw.append(
                    _Planned(
                        acct,
                        supplier,
                        _amount(rng, median, 0.3),
                        day,
                        8,
                        18,
                        "supplier",
                        purpose="Invoice",
                    )
                )
    receipts = sum(x.amount for x in plan if x.kind == "in")
    fixed = sum(x.amount for x in plan if x.kind == "fixed") + 0.09 * receipts  # VAT, below
    if receipts > 0 and fixed > spend_share * receipts * 0.9:
        boost = fixed / (spend_share * receipts * 0.6)
        for x in plan:
            if x.kind == "in":
                x.amount = round(x.amount * boost, 2)
        receipts *= boost
        fixed = sum(x.amount for x in plan if x.kind == "fixed") + 0.09 * receipts
    budget = max(0.0, spend_share * receipts - fixed)
    total_raw = sum(x.amount for x in raw)
    for x in raw:
        x.amount = round(x.amount * budget / total_raw, 2) if total_raw else 0.0
    plan.extend(x for x in raw if x.amount >= 1.0)
    receipts_by_quarter: dict[tuple[int, int], float] = {}
    for x in plan:
        if x.kind == "in":
            q = (x.day.year, (x.day.month - 1) // 3)
            receipts_by_quarter[q] = receipts_by_quarter.get(q, 0.0) + x.amount
    for (year, quarter), received in sorted(receipts_by_quarter.items()):
        due_month = quarter * 3 + 5
        due = date(year + (due_month - 1) // 12, (due_month - 1) % 12 + 1, 7)
        add(
            acct,
            pools.tax,
            round(received * float(rng.uniform(0.07, 0.11)), 2),
            previous_working_day(due),
            "fixed",
            purpose="VAT",
        )
    for n, x in enumerate(plan, 1):
        ctx.pay(
            f"bg|{org.id}|{n}",
            x.src,
            x.dst,
            x.amount,
            at(rng, x.day, x.first_hour, x.last_hour),
            channel=x.channel,
            purpose=x.purpose,
        )
    n = len(plan)
    if cfg.personal:
        for e, (emp_acct, _salary) in enumerate(employees):
            prng = ctx.rng("personal", org.id, str(e))
            rents = prng.random() < cfg.person_rent_share
            person_rent = _amount(prng, cfg.person_rent_median, 0.4)
            for month in months:
                if rents:
                    n += 1
                    ctx.pay(
                        f"bg|{org.id}|{n}",
                        emp_acct,
                        pools.landlords[e % len(pools.landlords)],
                        person_rent,
                        at(prng, month, 7, 9),
                        purpose="Rent",
                    )
                for _ in range(int(prng.integers(cfg.person_cards[0], cfg.person_cards[1] + 1))):
                    day = month + timedelta(days=int(prng.integers(0, 28)))
                    if day < end:
                        merchant = pools.merchants[int(prng.integers(len(pools.merchants)))]
                        n += 1
                        ctx.pay(
                            f"bg|{org.id}|{n}",
                            emp_acct,
                            merchant,
                            _amount(prng, cfg.card_median, cfg.card_sigma),
                            at(prng, day, 7, 22),
                            channel="card",
                            purpose="Purchase",
                        )
                day = month + timedelta(days=int(prng.integers(0, 28)))
                if day < end and prng.random() < 0.6:
                    n += 1
                    ctx.pay(
                        f"bg|{org.id}|{n}",
                        emp_acct,
                        ctx.branches[int(prng.integers(len(ctx.branches)))],
                        _amount(prng, cfg.cash_withdrawal_median, 0.5),
                        at(prng, day, 8, 21),
                        channel="cash_withdrawal",
                    )
    return len(employees)
```

### `ingest/src/neonradar_ingest/synth/world.py`

Verbatim. Python, 347 lines. SHA-256 `916950ebf8a1a77b948af517230f9e4fc4c81fc385b0b6da2e4e9ef5bd52070d`.

```python
"""The synthetic register of generator v1 (PHASE-3.md 7.2.6).

A world stands in for the register on synthetic profiles: companies with sectors, incorporation
dates, a few dissolved and a few filed as dormant; people; addresses, including registered agents'
and serviced offices' addresses that host many companies; ownership as Companies House bands, with
corporate groups (some with a foreign top company, some with no recorded owner); directors,
including professional directors with many appointments; family links; formation agents; and a few
synthetic list entries, two of them holding small stakes in ordinary companies; and a few
politically exposed people holding synthetic offices, with no links (exposure is planted only by
the overlay's scenarios, so the evaluation can count it). Addresses fall in `districts` postcode
districts, so businesses of one sector have local peers. It plants no scenario: worlds carry no
labels, and every pattern found in a world alone is background.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from neonradar_ingest.synth import records as rec
from neonradar_ingest.synth.ctx import NameSource, letter, name_key
from neonradar_ingest.synth.streams import stream

SECTORS = (
    ("services", 0.22),
    ("construction", 0.12),
    ("retail", 0.10),
    ("wholesale", 0.08),
    ("manufacturing", 0.07),
    ("hospitality", 0.06),
    ("restaurant", 0.05),
    ("real estate", 0.08),
    ("transport", 0.05),
    ("technology", 0.08),
    ("tourism", 0.02),
    ("car wash", 0.01),
    ("convenience store", 0.02),
    ("holding", 0.04),
)
PARENT_PLACES = ("gb", "gb", "gb", "ie", "nl", "lu", "je", "gg", "us", "de", "cy", "vg")


@dataclass(frozen=True, slots=True)
class WorldConfig:
    companies: int = 600
    people: int = 900
    today: date = date(2026, 7, 1)
    agent_every: int = 300
    professional_every: int = 200
    dissolved_share: float = 0.05
    dormant_share: float = 0.08
    corporate_owner_share: float = 0.15
    parent_owner_share: float = 0.85
    no_owner_share: float = 0.06
    listed: int = 6
    peps: int = 4
    districts: int = 30


class _W:
    def __init__(self, seed: int, names: NameSource) -> None:
        self.seed = seed
        self.names = names
        self.records: list[dict[str, Any]] = []
        self.used: set[str] = set()
        self.counts: dict[str, int] = {}

    def company_name(self, rid: str, jurisdiction: str, suffix: str = "") -> str:
        """A company name not used before, drawn from the record's own name stream."""
        rng = self.names_rng(rid)
        return str(
            self.unique(
                lambda: self.names.company(rng, jurisdiction).replace(" Ltd", suffix or " Ltd")
            )
        )

    def person_names(self, rid: str, locale: str) -> tuple[list[str], str]:
        rng = self.names_rng(rid)
        names, gender = self.unique(lambda: self.names.person(rng, locale))
        return list(names), str(gender)

    def names_rng(self, rid: str) -> np.random.Generator:
        """The stream names of record `rid` come from: separate from the structure's stream, so a
        different name source changes names only, never ids, links, amounts or dates."""
        return stream(self.seed, "world", "name", rid)

    def rid(self, kind: str) -> str:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return f"syn-w-{kind}-{self.counts[kind]:06d}"

    def unique(self, make: Any, attempts: int = 100) -> Any:
        """A name not used yet when one turns up within `attempts` draws, else a repeat (as
        `Ctx._unique`); only the name stream moves."""
        value = make()
        for _ in range(attempts):
            names = value[0] if isinstance(value, tuple) else [value]
            keys = [name_key(n) for n in names]
            if not any(k in self.used for k in keys):
                break
            value = make()
        names = value[0] if isinstance(value, tuple) else [value]
        self.used.update(name_key(n) for n in names)
        return value


def generate(seed: int, cfg: WorldConfig, names: NameSource) -> list[dict[str, Any]]:
    w = _W(seed, names)
    rng = stream(seed, "world")
    today = cfg.today

    # addresses: a few agents' and serviced offices' addresses host many companies
    n_agents = max(2, cfg.companies // cfg.agent_every)
    hubs = []
    for i in range(n_agents + 1):
        a = _address(w, rng, cfg.districts)
        hubs.append((a, int(rng.integers(25, 150)) if i < n_agents else int(rng.integers(15, 40))))
    # companies
    sectors, weights = zip(*SECTORS, strict=True)
    p = np.array(weights) / sum(weights)
    companies: list[str] = []
    info: dict[str, dict[str, Any]] = {}
    hub_slots = [a for a, k in hubs for _ in range(k)]
    rng.shuffle(hub_slots)
    for i in range(cfg.companies):
        sector = sectors[int(rng.choice(len(sectors), p=p))]
        age = min(60 * 365, int(rng.exponential(9 * 365)))
        if rng.random() < 0.1:
            age = int(rng.integers(30, 365))
        inc = today - timedelta(days=age)
        address = hub_slots[i] if i < len(hub_slots) else _address(w, rng, cfg.districts)
        dissolved = rng.random() < cfg.dissolved_share and age > 400
        rid = w.rid("co")
        name = w.company_name(rid, "gb")
        record = rec.company(
            rid,
            name,
            jurisdiction="gb",
            registration_number=f"SY{6 + i // 100000}{i % 100000:05d}",
            incorporation_date=inc.isoformat(),
            addresses={address: "registered"},
            sector=sector,
            status="dissolved" if dissolved else "active",
            dissolution_date=(today - timedelta(days=int(rng.integers(10, 300)))).isoformat()
            if dissolved
            else "",
        )
        if rng.random() < cfg.dormant_share:
            record["nr"]["accounts_category"] = "DORMANT"
        w.records.append(record)
        companies.append(rid)
        info[rid] = {"incorporated": inc, "sector": sector}
    # people
    people = []
    for _ in range(cfg.people):
        r = rng.random()
        locale, nationality = (
            ("ar_SA", "sa") if r < 0.1 else (("ru_RU", "ru") if r < 0.2 else ("en_GB", "gb"))
        )
        pid = w.rid("p")
        spellings, gender = w.person_names(pid, locale)
        year = int(rng.integers(1945, 2001))
        w.records.append(
            rec.person(
                pid,
                spellings,
                birth_date=f"{year}-{int(rng.integers(1, 13)):02d}",
                nationality=nationality,
                gender=gender,
            )
        )
        people.append(pid)
    # ownership: people, corporate parents (some abroad), or nobody recorded
    parents: list[str] = []
    for idx, co in enumerate(companies):
        r = rng.random()
        start = info[co]["incorporated"].isoformat()
        if r < cfg.no_owner_share:
            continue
        if r < cfg.no_owner_share + cfg.corporate_owner_share and idx > 10:
            if parents and rng.random() < 0.5:
                parent = parents[int(rng.integers(len(parents)))]
            else:
                parent = _parent(w, rng, today, names, people, cfg.parent_owner_share)
                parents.append(parent)
            w.records.append(
                rec.ownership(w.rid("own"), parent, co, band="75-100", start_date=start)
            )
            continue
        if rng.random() < 0.7:
            w.records.append(
                rec.ownership(
                    w.rid("own"),
                    people[int(rng.integers(len(people)))],
                    co,
                    band="75-100",
                    start_date=start,
                )
            )
        else:
            for owner in rng.choice(len(people), size=2, replace=False):
                w.records.append(
                    rec.ownership(
                        w.rid("own"), people[int(owner)], co, band="25-50", start_date=start
                    )
                )
    # directors, and professional directors with many appointments
    pros = [
        people[int(i)]
        for i in rng.choice(
            len(people), size=max(2, cfg.companies // cfg.professional_every), replace=False
        )
    ]
    for co in companies:
        start = (info[co]["incorporated"] + timedelta(days=int(rng.integers(0, 30)))).isoformat()
        for _ in range(int(rng.integers(1, 4))):
            w.records.append(
                rec.directorship(
                    w.rid("dir"), people[int(rng.integers(len(people)))], co, start_date=start
                )
            )
    for pro in pros:
        for co in rng.choice(len(companies), size=int(rng.integers(10, 30)), replace=False):
            w.records.append(
                rec.directorship(
                    w.rid("dir"),
                    pro,
                    companies[int(co)],
                    start_date=(today - timedelta(days=int(rng.integers(30, 4000)))).isoformat(),
                )
            )
    # family links
    for _ in range(cfg.people // 20):
        a, b = rng.choice(len(people), size=2, replace=False)
        w.records.append(
            rec.family(
                w.rid("fam"),
                people[int(a)],
                people[int(b)],
                relationship=str(rng.choice(["spouse", "sibling", "child"])),
            )
        )
    # formation agents represent many of the companies at their address
    by_address: dict[str, list[str]] = {}
    for record in w.records:
        if record["schema"] == "Company":
            for a in record["properties"].get("addressEntity", []):
                by_address.setdefault(a, []).append(record["id"])
    for a, _ in hubs[:n_agents]:
        agent = w.rid("org")
        agent_name = w.company_name(agent, "gb", " Formations Ltd")
        w.records.append(rec.organization(agent, agent_name, country="gb"))
        for co in by_address.get(a, []):
            if rng.random() < 0.5:
                w.records.append(rec.representation(w.rid("rep"), agent, co))
    # synthetic list entries: most unconnected, two with small stakes in ordinary companies
    for i in range(cfg.listed):
        entity = w.rid("lst")
        w.records.append(
            rec.company(
                entity,
                w.company_name(entity, "ae"),
                jurisdiction="ae",
                registration_number=f"SL{i:06d}",
                incorporation_date="2010-01-01",
                topics=["sanction"],
            )
        )
        w.records.append(
            rec.sanction(
                w.rid("san"),
                entity,
                authority="Synthetic Authority A",
                program="Synthetic Programme 1",
                start_date="2022-03-01",
            )
        )
        if i < 2:
            target = companies[int(rng.integers(len(companies)))]
            w.records.append(
                rec.ownership(
                    w.rid("own"), entity, target, band=f"exact:{int(rng.integers(5, 20))}"
                )
            )
    for i in range(cfg.peps):
        pid = w.rid("p")
        spellings, gender = w.person_names(pid, "en_GB")
        w.records.append(
            rec.person(
                pid,
                spellings,
                birth_date="1961-04",
                nationality="gb",
                gender=gender,
                topics=["role.pep"],
            )
        )
        post = w.rid("pos")
        w.records.append(rec.position(post, f"Synthetic Member of Assembly {i + 1}", country="zz"))
        w.records.append(rec.occupancy(w.rid("occ"), pid, post, start_date="2021-05-01"))
    return sorted(w.records, key=lambda r: r["id"])


def _address(w: _W, rng: np.random.Generator, districts: int) -> str:
    rid = w.rid("addr")
    district = int(rng.integers(1, districts + 1))
    town = w.names.town(stream(w.seed, "world", "town", str(district)))
    postcode = f"QQ{district} {int(rng.integers(1, 9))}{letter(rng)}{letter(rng)}"
    w.records.append(
        rec.address(
            rid,
            f"{int(rng.integers(1, 300))} {w.names.street(w.names_rng(rid))}, {town}, {postcode}",
            city=town,
            postal_code=postcode,
            country="gb",
        )
    )
    return rid


def _parent(
    w: _W,
    rng: np.random.Generator,
    today: date,
    names: NameSource,
    people: list[str],
    owner_share: float,
) -> str:
    place = PARENT_PLACES[int(rng.integers(len(PARENT_PLACES)))]
    rid = w.rid("co")
    w.records.append(
        rec.company(
            rid,
            w.company_name(rid, place),
            jurisdiction=place,
            registration_number=f"SH{w.counts['co']:06d}",
            incorporation_date=(today - timedelta(days=int(rng.integers(1500, 12000)))).isoformat(),
            sector="holding",
        )
    )
    if rng.random() < owner_share:
        w.records.append(
            rec.ownership(w.rid("own"), people[int(rng.integers(len(people)))], rid, band="75-100")
        )
    return rid
```

### `ingest/src/neonradar_ingest/synth/overlay.py`

Verbatim. Python, 238 lines. SHA-256 `e0a95f568b6c89c6c8a11a248371b96d5ffcb8871bb9c6f14be5cbf462ac8509`.

```python
"""The overlay of generator v1: background activity, scenarios and look-alikes on a base
(PHASE-3.md 7.2.7).

`generate` reads nothing and writes nothing: it takes the base's records (any iterable, so the CLI
can stream them from the base's files), returns the overlay's records and labels, and the CLI
writes them (`writer.py`, `labels.py`). The same seed and the same
base give the same records and labels, byte for byte once written. Scenario ids are numbered in
catalog order (`scn-000001` upwards); each scenario draws from its own named stream, so adding a
typology at the end changes no earlier scenario.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import Any

from neonradar_ingest.synth import background, writer
from neonradar_ingest.synth.base import BaseView
from neonradar_ingest.synth.ctx import Ctx, LabelRows, NameSource, ScenarioCtx
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.scenarios import (
    cash_commingling,
    circular_flow,
    dormant_reactivation,
    fan_in_collection,
    fan_out_distribution,
    formation_agent_cluster,
    layering_chain,
    mass_registration_address,
    pep_exposure,
    rapid_pass_through,
    recycled_directors,
    sanctions_exposure,
    shell_chain,
    structuring,
)

SCENARIOS: dict[str, ModuleType] = {
    m.TYPOLOGY: m
    for m in (
        structuring,
        rapid_pass_through,
        layering_chain,
        circular_flow,
        fan_in_collection,
        fan_out_distribution,
        dormant_reactivation,
        shell_chain,
        mass_registration_address,
        sanctions_exposure,
        formation_agent_cluster,
        recycled_directors,
        pep_exposure,
        cash_commingling,
    )
}
HISTORY_DAYS = 100  # transaction scenarios start after the detectors' 90-day look-back has data


@dataclass(frozen=True, slots=True)
class OverlayConfig:
    seed: int
    start: date = date(2025, 1, 1)
    end: date = date(2026, 7, 1)
    split: str = "dev"
    illicit: int = 10
    lookalikes: int = 10
    typologies: tuple[str, ...] = tuple(SCENARIOS)
    background: background.BackgroundConfig = field(default_factory=background.BackgroundConfig)


@dataclass(slots=True)
class Overlay:
    """The overlay's records and labels. Payments stay as their C1 lines: `items()` gives every
    record's schema and line in id order (the writer), and `records` parses them into dicts in id
    order (the in-memory graph of small worlds, and the tests)."""

    other_records: dict[str, dict[str, Any]]  # every record except payments
    payments: dict[str, str]  # payment id -> C1 line
    labels: LabelRows
    stats: dict[str, Any]

    def _ids(self) -> list[str]:
        return sorted(self.other_records.keys() | self.payments.keys())

    def items(self) -> Iterator[tuple[str, str]]:
        for rid in self._ids():
            text = self.payments.get(rid)
            if text is not None:
                yield "Payment", text
            else:
                record = self.other_records[rid]
                yield str(record["schema"]), writer.line(record)

    @property
    def records(self) -> list[dict[str, Any]]:
        return [
            self.other_records[rid] if rid in self.other_records else json.loads(self.payments[rid])
            for rid in self._ids()
        ]


def _start(ctx: Ctx, module: ModuleType, scenario_id: str) -> date:
    """A start day that leaves the scenario's lead time and history before it and its span after."""
    rng = ctx.rng("place", scenario_id)
    first = ctx.period.start.date() + timedelta(days=max(module.LEAD_DAYS, HISTORY_DAYS))
    last = ctx.period.end.date() - timedelta(days=module.SPAN_DAYS + 7)
    if last <= first:
        raise ValueError(f"the period is too short for {module.TYPOLOGY}")
    return first + timedelta(days=int(rng.integers(0, (last - first).days + 1)))


def generate(
    base_records: Iterable[Mapping[str, Any]],
    dataset_kinds: Mapping[str, str],
    cfg: OverlayConfig,
    names: NameSource,
    canonical_csv: Path | None = None,
) -> Overlay:
    """`canonical_csv` is the base's latest resolution run (`canonical.csv`), when the profile
    resolves: a merged entity then gets one account, through its anchor record, and none when any
    of its records is flagged or comes from a list or a leak (`BaseView`)."""
    view = BaseView.from_records(base_records, dataset_kinds, canonical_csv)
    period = Period(
        datetime.combine(cfg.start, datetime.min.time(), UTC),
        datetime.combine(cfg.end, datetime.min.time(), UTC),
    )
    ctx = Ctx(
        cfg.seed,
        period,
        names,
        base_ids=view.ids,
        base_names=view.names,
        soft_names=view.synthetic_names,
    )
    ctx.split = cfg.split
    bg = background.generate(ctx, view.eligible, cfg.background)
    counts: dict[str, dict[str, int]] = {}
    n = 0
    for slug, module in SCENARIOS.items():
        if slug not in cfg.typologies:
            continue
        counts[slug] = {"illicit": 0, "lookalike": 0}
        for i in range(cfg.illicit):
            n += 1
            sid = f"scn-{n:06d}"
            variant, difficulty = module.ILLICIT[i % len(module.ILLICIT)]
            module.illicit(
                ScenarioCtx(ctx, sid, slug, lookalike=False),
                variant,
                difficulty,
                _start(ctx, module, sid),
            )
            counts[slug]["illicit"] += 1
        for i in range(cfg.lookalikes):
            n += 1
            sid = f"scn-{n:06d}"
            kind = module.LOOKALIKES[i % len(module.LOOKALIKES)]
            module.lookalike(
                ScenarioCtx(ctx, sid, slug, lookalike=True), kind, _start(ctx, module, sid)
            )
            counts[slug]["lookalike"] += 1
    ctx.assign_account_numbers(view.account_numbers)
    check_bridge(
        chain(ctx.records.values(), (json.loads(text) for text in ctx.payments.values())),
        view.ids,
        ctx.base_accounts,
    )
    stats = {
        "background": bg,
        "scenarios": counts,
        "eligible": len(view.eligible),
        "skipped": dict(view.skipped),
        "records": len(ctx.records) + len(ctx.payments),
    }
    return Overlay(ctx.records, ctx.payments, ctx.labels, stats)


# Every FtM property the generator writes that names another entity (PHASE-3.md 7.2.3).
REFERENCE_PROPERTIES = (
    "owner",
    "asset",
    "director",
    "organization",
    "agent",
    "client",
    "person",
    "relative",
    "associate",
    "controller",
    "controlled",
    "entity",
    "holder",
    "post",
    "addressEntity",
)


def check_bridge(
    records: Iterable[Mapping[str, Any]],
    base_ids: frozenset[str] | set[str],
    base_accounts: set[str],
) -> None:
    """I15 and I16 on the overlay's own records: the only record that names a base entity is the
    account holding of a base organisation (`base_accounts` are the accounts such holdings
    hold), a payment names a base entity only as the payer or beneficiary of one of those
    accounts, and no payment joins two of them. Every property that can name an entity counts,
    `addressEntity` included."""
    for r in records:
        p = r["properties"]
        if r["schema"] == "Payment":
            if (
                p["payerAccount"][0] in base_accounts
                and p["beneficiaryAccount"][0] in base_accounts
            ):
                raise ValueError(f"payment {r['id']} joins two base holders (I16)")
            for party, account in (
                ("payer", "payerAccount"),
                ("beneficiary", "beneficiaryAccount"),
            ):
                if set(p.get(party, [])) & base_ids and p[account][0] not in base_accounts:
                    raise ValueError(f"payment {r['id']} names a base entity (I15)")
            continue
        named = {v for key in REFERENCE_PROPERTIES for v in p.get(key, [])}
        if not named.isdisjoint(base_ids):
            holding = (
                r["schema"] == "Ownership"
                and p.get("role") == ["account holder"]
                and p["asset"][0] in base_accounts
            )
            if not holding:
                raise ValueError(f"record {r['id']} links a base entity (I15)")
```

### `ingest/src/neonradar_ingest/synth/labels.py`

Verbatim. Python, 121 lines. SHA-256 `62def856d29d20d6b244496d2ba445107b1526b16cedfe8ba64f33572f858de8`.

```python
"""Label files v2 (PHASE-3.md 7.2.8; `synthetic-transactions.md` 4.2).

Labels never enter records (C1 R9) or the graph. Every CSV file starts with `# synthetic: true`
and `# label_schema: 2.0.0`; the Phase 1 columns come first, in their Phase 1 order, and new columns
follow, so a reader that selects columns by name keeps working. Rows are sorted, numbers and
booleans have one spelling (`true` and `false`), and files end with a newline: the same seed gives
the same bytes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from neonradar_ingest.synth.ctx import LabelRows

LABEL_SCHEMA = "2.0.0"
SCENARIO_COLUMNS = (
    "scenario_id",
    "typology",
    "variant",
    "is_lookalike",
    "start_ts",
    "end_ts",
    "participants",
    "difficulty",
    "split",
    "n_transactions",
    "n_accounts",
    "n_entities",
    "n_relationships",
)
TRANSACTION_COLUMNS = (
    "tx_id",
    "scenario_id",
    "typology",
    "step",
    "role",
    "is_illicit",
    "variant",
    "is_lookalike",
    "is_core",
)
PARTICIPANT_COLUMNS = ("scenario_id", "object_kind", "object_id", "role", "is_core")


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def csv_text(columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    out = io.StringIO()
    out.write("# synthetic: true\n")
    out.write(f"# label_schema: {LABEL_SCHEMA}\n")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row[c]) for c in columns])
    return out.getvalue()


def files(
    labels: LabelRows, *, seed: int, record_sha256: Mapping[str, str], generator_version: str
) -> dict[str, str]:
    """File name to text for `labels/`."""
    scenarios = sorted(labels.scenarios, key=lambda r: r["scenario_id"])
    transactions = sorted(
        labels.transactions, key=lambda r: (r["scenario_id"], r["step"], r["tx_id"])
    )
    participants = sorted(
        labels.participants, key=lambda r: (r["scenario_id"], r["object_kind"], r["object_id"])
    )
    params = sorted(labels.params, key=lambda r: r["scenario_id"])
    by = Counter((r["typology"], r["variant"], r["is_lookalike"]) for r in scenarios)
    manifest = {
        "label_schema": LABEL_SCHEMA,
        "synthetic": True,
        "seed": seed,
        "records": dict(sorted(record_sha256.items())),
        "counts": [
            {"typology": t, "variant": v, "is_lookalike": look, "scenarios": n}
            for (t, v, look), n in sorted(by.items())
        ],
        "splits": sorted({r["split"] for r in scenarios}),
        "generator_version": generator_version,
    }
    return {
        "scenarios.csv": csv_text(SCENARIO_COLUMNS, scenarios),
        "transactions.csv": csv_text(TRANSACTION_COLUMNS, transactions),
        "participants.csv": csv_text(PARTICIPANT_COLUMNS, participants),
        "scenario_params.jsonl": "".join(
            json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in params
        ),
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    }


def write(directory: Path, texts: Mapping[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(texts.items()):
        (directory / name).write_text(text, encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    """Rows of a label CSV, skipping the comment lines."""
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")
    ]
    return list(csv.DictReader(lines))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

### `ingest/src/neonradar_ingest/synth/writer.py`

Verbatim. Python, 87 lines. SHA-256 `9195b6ff6a1fbcffcc9af457cede82f5f81bc1b20f82cdb3dda0472105e98338`.

```python
"""C1 record files for generator v1 (PHASE-3.md 7.2.8; PHASE-1.md 5.1).

One `.ftm.jsonl` file per part with its sibling `.manifest.json` (C1 1.1.0). Lines are the records
in id order, as compact JSON with sorted keys, so the same seed gives the same bytes; the manifest
differs only in `created_at`. `write_part` streams the lines to the file and hashes them as it
goes, so a scale world never holds its whole text in memory. The CLI validates every record with
`neonradar_contracts.records.validate_record` in strict mode before writing (M3.3).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRODUCER = "neonradar_ingest.synth"
GENERATOR_VERSION = "1.0.0"


def line(record: Mapping[str, Any]) -> str:
    """One record as its C1 line, without the newline."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def items(records: Iterable[Mapping[str, Any]]) -> Iterator[tuple[str, str]]:
    """(schema, line) for each record, in id order."""
    for r in sorted(records, key=lambda r: r["id"]):
        yield str(r["schema"]), line(r)


def record_lines(records: Iterable[Mapping[str, Any]]) -> str:
    return "".join(text + "\n" for _, text in items(records))


def manifest(
    name: str,
    sha256: str,
    count: int,
    by_schema: Mapping[str, int],
    *,
    seed: int,
    git_sha: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "record_contract": "1.1.0",
        "dataset": "nr_synthetic",
        "files": [{"path": name, "sha256": sha256, "records": count}],
        "created_at": (created_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": {"name": PRODUCER, "version": GENERATOR_VERSION, "git_sha": git_sha},
        "source": {"urls": [], "retrieved_at": None, "source_version": None},
        "licence": {"id": "Apache-2.0", "attribution": None},
        "counts": {"by_schema": dict(sorted(by_schema.items())), "skipped": {}},
        "dependencies": {"followthemoney": "4.11.0"},
        "synthetic": True,
        "seed": seed,
        "notes": [],
    }


def write_part(
    directory: Path, name: str, lines: Iterable[tuple[str, str]], *, seed: int, git_sha: str
) -> str:
    """Write `<name>.ftm.jsonl` from (schema, line) pairs in id order, and its manifest; return
    the records file's SHA-256."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.ftm.jsonl"
    digest = hashlib.sha256()
    by_schema: Counter[str] = Counter()
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for schema, text in lines:
            data = text + "\n"
            fh.write(data)
            digest.update(data.encode("utf-8"))
            by_schema[schema] += 1
            count += 1
    meta = manifest(path.name, digest.hexdigest(), count, by_schema, seed=seed, git_sha=git_sha)
    (directory / f"{name}.manifest.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return digest.hexdigest()
```

### `ingest/src/neonradar_ingest/synth/namesource.py`

Reference. Python, 171 lines. SHA-256 `bd30ba0f51cad376bce64e2794e5c428822001dc0493475db641340fe637e163`.

M3.3 writes `default_names()` as an adapter over the Phase 1 name modules and their denylist, and over the invented surnames of Phase 2's `variants.py` (M2.9), keeping the five methods of `ctx.NameSource` (7.2.3); this version uses Faker, neutral words and a small syllable table directly.

```python
"""The generator's NameSource (PHASE-3.md 7.2.3).

REFERENCE IMPLEMENTATION. In the repository, M3.3 writes this module as an adapter over the
Phase 1 name modules (`names.py` with its denylist and script variants, `companies.py` with its
neutral word lists, M1.8e) and Phase 2's invented surnames (`variants.py`, M2.9), keeping the
interface: `default_names()` returns an object with the five methods of `ctx.NameSource`, each
drawing only from the generator it is given. Extra words for company names live here, never in
Phase 1's lists, so `synth demo-mini` keeps producing its committed fixture. This version uses
Faker directly, neutral word lists and a small syllable table, so the prototype tests can run on
their own.
"""

from __future__ import annotations

import numpy as np
from faker import Faker

WORDS_A = [
    "Quarry",
    "Linden",
    "Harbour",
    "Cedar",
    "Maple",
    "Juniper",
    "Slate",
    "Copper",
    "Meadow",
    "Falcon",
    "Heron",
    "Willow",
    "Granite",
    "Amber",
    "Bramble",
    "Larch",
    "Orchard",
    "Kestrel",
    "Thistle",
    "Beacon",
]
WORDS_B = [
    "Lane",
    "Ridge",
    "Gate",
    "Field",
    "Brook",
    "Point",
    "Crest",
    "Vale",
    "Works",
    "Row",
    "Yard",
    "Cross",
]
WORDS_C = [
    "Trading",
    "Holdings",
    "Services",
    "Logistics",
    "Supplies",
    "Consulting",
    "Foods",
    "Interiors",
    "Engineering",
    "Imports",
    "Ventures",
    "Partners",
    "Systems",
    "Textiles",
    "Motors",
    "Studios",
]
FORMS = {
    "gb": "Ltd",
    "vg": "Limited",
    "cy": "Ltd",
    "ae": "FZE",
    "je": "Limited",
    "pa": "S.A.",
    "sc": "Ltd",
    "ie": "Limited",
    "nl": "B.V.",
    "lu": "S.a r.l.",
    "us": "LLC",
    "hk": "Limited",
    "mt": "Ltd",
    "bz": "Ltd",
}


# Invented syllables in three scripts (Latin, Cyrillic, Arabic): sounds, not names.
SYLLABLES = (
    ("ka", "ка", "كا"),
    ("ro", "ро", "رو"),  # noqa: RUF001 (Cyrillic letters on purpose)
    ("vel", "вел", "فيل"),
    ("dra", "дра", "درا"),
    ("mo", "мо", "مو"),
    ("ske", "ске", "سكي"),
    ("ta", "та", "تا"),
    ("brin", "брин", "برين"),
    ("zo", "зо", "زو"),
    ("lan", "лан", "لان"),
    ("ve", "ве", "في"),
    ("nor", "нор", "نور"),
    ("ki", "ки", "كي"),
    ("sar", "сар", "سار"),  # noqa: RUF001 (Cyrillic letters on purpose)
    ("du", "ду", "دو"),
    ("mesh", "меш", "مش"),
)
SCRIPT = {"en_GB": 0, "ru_RU": 1, "ar_SA": 2}


class FakerNames:
    def __init__(self) -> None:
        self._fakers = {loc: Faker(loc) for loc in ("en_GB", "ar_SA", "ru_RU")}
        self._surnames: set[str] = set()
        for fake in self._fakers.values():
            for provider in fake.get_providers():
                names = getattr(provider, "last_names", ())
                self._surnames |= {str(n).casefold() for n in names}

    def invented_surname(self, rng: np.random.Generator, locale: str) -> str:
        """Two or three invented syllables in the locale's script, redrawn while the result is a
        surname of one of the Faker locales."""
        script = SCRIPT.get(locale, 0)
        while True:
            n = 2 + int(rng.integers(2))
            parts = [SYLLABLES[int(rng.integers(len(SYLLABLES)))][script] for _ in range(n)]
            name = "".join(parts)
            name = name if script == 2 else name.capitalize()
            if name.casefold() not in self._surnames:
                return name

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        fake = self._fakers[locale]
        fake.seed_instance(int(rng.integers(0, 2**31)))
        gender = "female" if rng.random() < 0.5 else "male"
        first = fake.first_name_female() if gender == "female" else fake.first_name_male()
        return [f"{first} {self.invented_surname(rng, locale)}"], gender

    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        fake = self._fakers[locale]
        fake.seed_instance(int(rng.integers(0, 2**31)))
        gender = "female" if rng.random() < 0.5 else "male"
        first = fake.first_name_female() if gender == "female" else fake.first_name_male()
        return [f"{first} {fake.last_name()}"], gender

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str:
        """Three neutral words, or (in a large world) a surname and two words: over four million
        distinct names before the legal form."""
        a = WORDS_A[int(rng.integers(len(WORDS_A)))]
        b = WORDS_B[int(rng.integers(len(WORDS_B)))]
        c = WORDS_C[int(rng.integers(len(WORDS_C)))]
        if rng.random() < 0.5:
            fake = self._fakers["en_GB"]
            fake.seed_instance(int(rng.integers(0, 2**31)))
            a = f"{fake.last_name()} {a}"
        return f"{a} {b} {c} {FORMS.get(jurisdiction, 'Ltd')}"

    def street(self, rng: np.random.Generator) -> str:
        fake = self._fakers["en_GB"]
        fake.seed_instance(int(rng.integers(0, 2**31)))
        return fake.street_name()

    def town(self, rng: np.random.Generator) -> str:
        fake = self._fakers["en_GB"]
        fake.seed_instance(int(rng.integers(0, 2**31)))
        return fake.city()


def default_names() -> FakerNames:
    return FakerNames()
```

### `ingest/src/neonradar_ingest/synth/scenarios/__init__.py`

Verbatim. Python, 1 lines. SHA-256 `a404072a9d2fb768a24256621160d5205abbf96c4fddb8cb4278fdeeaf4dd2c2`.

```python
"""Scenario modules of generator v1, one per typology (PHASE-3.md 7.2.5)."""
```

### `ingest/src/neonradar_ingest/synth/scenarios/common.py`

Verbatim. Python, 59 lines. SHA-256 `d4669a10c7ad8ce39af1fa90d24d11c6610573185b99eeb514fcbc747659cc35`.

```python
"""Helpers shared by the scenario modules (PHASE-3.md 7.2.5)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, business_days

FOREIGN = ("vg", "cy", "ae", "pa", "sc", "bz", "mt", "hk")


def lognormal(
    rng: np.random.Generator, median: float, sigma: float, low: float, high: float
) -> float:
    """A lognormal amount around `median`, kept inside [low, high], rounded to pennies."""
    value = float(median * np.exp(sigma * rng.standard_normal()))
    return round(min(high, max(low, value)), 2)


def uniform(rng: np.random.Generator, low: float, high: float) -> float:
    return round(float(rng.uniform(low, high)), 2)


def opened_before(rng: np.random.Generator, day: date, min_days: int, max_days: int) -> date:
    return day - timedelta(days=int(rng.integers(min_days, max_days + 1)))


def camouflage(
    s: ScenarioCtx, account: str, start: datetime, end: datetime, n: int = 4, median: float = 600.0
) -> None:
    """A few ordinary payments in and out of `account` with two counterparties the scenario owns,
    spread over [start, end), so a scenario account is not an account with nothing else on it.
    They carry no label: they are background as far as the evaluation knows."""
    rng = s.rng("camouflage", account)
    start, end = max(start, s.period.start), min(end, s.period.end)
    if end - start < timedelta(days=2):
        return
    people = [
        s.account(s.person(), opened=opened_before(rng, start.date(), 400, 3000)) for _ in range(2)
    ]
    days = business_days(start.date(), end.date())
    if not days:
        return
    for i in range(n):
        day = days[int(rng.integers(len(days)))]
        moment = at(rng, day)
        amount = lognormal(rng, median, 0.5, 20, 5000)
        other = people[i % 2]
        if i % 2 == 0:
            s.pay(other, account, amount, moment, channel="wire", purpose="Invoice")
        else:
            s.pay(account, other, amount, moment, channel="card", purpose="Purchase")


def foreign(rng: np.random.Generator) -> str:
    return FOREIGN[int(rng.integers(len(FOREIGN)))]
```

### `ingest/src/neonradar_ingest/synth/scenarios/structuring.py`

Verbatim. Python, 119 lines. SHA-256 `c78d854fc3c1708027c1d6e0fafd3701f1c5d45c0cb6a31cba9dc5676441f7a0`.

```python
"""structuring scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 1).

Illicit `single_account` (easy): 4 to 8 cash deposits of 9,100 to 9,980 into one account within 1
to 4 days, at 2 to 4 branches. Illicit `multi_account` (hard): 4 to 9 deposits of 8,600 to 9,990
spread over 2 or 3 accounts of one holder within 2 to 7 days, so some fall outside a 10 percent
band or a 4-day window. Look-alikes: a cash business banking its takings (`daily_takings`), a
business whose insurer caps each deposit at 9,500 (`deposit_cap`), a person saving 9,500 a week
(`weekly_savings`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, business_days, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, lognormal, opened_before, uniform

TYPOLOGY = "structuring"
ILLICIT = (("single_account", "easy"), ("multi_account", "hard"))
LOOKALIKES = ("daily_takings", "deposit_cap", "weekly_savings")
SPAN_DAYS = 40
LEAD_DAYS = 0


def _holder(s: ScenarioCtx, start: date, person: bool) -> str:
    if person:
        return s.person()
    return s.company(incorporated=opened_before(s.rng("inc"), start, 400, 4000), sector="wholesale")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    holder = s.label(_holder(s, start, rng.random() < 0.5), "holder")
    n_accounts = 1 if variant == "single_account" else int(rng.integers(2, 4))
    accounts = [
        s.label(s.account(holder, opened=opened_before(rng, start, 200, 3000)), "receiving_account")
        for _ in range(n_accounts)
    ]
    branches = s.ctx.branches
    n = int(rng.integers(4, 9)) if variant == "single_account" else int(rng.integers(4, 10))
    span = int(rng.integers(1, 5)) if variant == "single_account" else int(rng.integers(2, 8))
    low, high = (9100, 9980) if variant == "single_account" else (8600, 9990)
    first = at(rng, start, 9, 12)
    for i in range(n):
        moment = first if i == 0 else later(rng, first, 0.2, span * 24)
        branch = branches[int(rng.integers(min(len(branches), 4)))]
        account = accounts[i % n_accounts]
        p = s.pay(
            branch,
            account,
            uniform(rng, low, high),
            moment,
            channel="cash_deposit",
            purpose="Cash deposit",
        )
        s.label_payment(p, "deposit")
    for a in accounts:
        camouflage(
            s,
            a,
            utc(start.year, start.month, start.day) - timedelta(days=60),
            utc(start.year, start.month, start.day),
        )
    s.finish(
        variant,
        difficulty,
        {"deposits": n, "span_days": span, "accounts": n_accounts, "amount_range": [low, high]},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    branches = s.ctx.branches
    if kind == "weekly_savings":
        holder = s.label(s.person(), "holder")
        account = s.label(
            s.account(holder, opened=opened_before(rng, start, 300, 3000)), "receiving_account"
        )
        for week in range(5):
            day = start + timedelta(days=7 * week)
            p = s.pay(
                branches[0],
                account,
                9500.0,
                at(rng, day),
                channel="cash_deposit",
                purpose="Savings",
            )
            s.label_payment(p, "deposit")
        s.finish(kind, "", {"weeks": 5})
        return
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail"), "holder"
    )
    account = s.label(
        s.account(holder, opened=opened_before(rng, start, 300, 3000)), "receiving_account"
    )
    days = business_days(start, start + timedelta(days=30))
    step = 0
    for i, day in enumerate(days):
        if kind == "deposit_cap" and i % 2 == 1:
            continue
        amount = (
            lognormal(rng, 4200, 0.6, 300, 18000)
            if kind == "daily_takings"
            else uniform(rng, 9000, 9500)
        )
        step += 1
        p = s.pay(
            branches[step % min(2, len(branches))],
            account,
            amount,
            at(rng, day, 16, 18),
            channel="cash_deposit",
            purpose="Takings",
        )
        s.label_payment(p, "deposit")
    s.finish(kind, "", {"days": len(days)})
```

### `ingest/src/neonradar_ingest/synth/scenarios/rapid_pass_through.py`

Verbatim. Python, 153 lines. SHA-256 `23339d9c442f6352ac943fb762d469c5ebf3573afb8b982b916740e14bb0bf82`.

```python
"""rapid_pass_through scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 2).

Illicit `funnel` (easy): 3 to 8 payers send 25,000 to 200,000 in all within 1 to 4 days; within 2
to 36 hours of each arrival the account sends 90 to 98 percent on to 1 or 2 beneficiaries, one of
them abroad. Illicit `slow_funnel` (hard): dwell of 20 to 70 hours and 2 to 5 beneficiaries, so
part of it falls outside a 48-hour, 3-beneficiary rule. Look-alikes: a payroll bureau (one client
in, many employees out), a marketplace settlement account (many buyers in, one payout to the
merchant next day), an escrow account (holds for 20 to 40 days).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "rapid_pass_through"
ILLICIT = (("funnel", "easy"), ("slow_funnel", "hard"))
LOOKALIKES = ("payroll_bureau", "marketplace_settlement", "escrow")
SPAN_DAYS = 45
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    hub_holder = s.label(
        s.company(incorporated=opened_before(rng, start, 200, 2000), sector="trading"), "holder"
    )
    hub = s.label(
        s.account(hub_holder, opened=opened_before(rng, start, 100, 1500)), "pass_through_account"
    )
    n_in = int(rng.integers(3, 9))
    total = uniform(rng, 25000, 200000)
    shares = rng.dirichlet([2.0] * n_in)
    n_out = int(rng.integers(1, 3)) if variant == "funnel" else int(rng.integers(2, 6))
    dests = []
    for i in range(n_out):
        jurisdiction = foreign(rng) if i == 0 else "gb"
        dests.append(
            s.account(
                s.company(
                    incorporated=opened_before(rng, start, 300, 3000), jurisdiction=jurisdiction
                ),
                opened=opened_before(rng, start, 200, 3000),
            )
        )
    first = at(rng, start)
    lo, hi = (2, 36) if variant == "funnel" else (20, 70)
    for i in range(n_in):
        payer = s.account(
            s.company(incorporated=opened_before(rng, start, 300, 5000)),
            opened=opened_before(rng, start, 300, 4000),
        )
        moment = first if i == 0 else later(rng, first, 1, 72)
        amount = round(total * float(shares[i]), 2) or 1.0
        s.label_payment(s.pay(payer, hub, amount, moment, purpose="Consultancy"), "inflow")
        out = round(amount * float(rng.uniform(0.90, 0.98)), 2)
        dest = dests[i % n_out]
        s.label_payment(
            s.pay(hub, dest, out, later(rng, moment, lo, hi), purpose="Services"), "outflow"
        )
    camouflage(
        s,
        hub,
        utc(start.year, start.month, start.day) - timedelta(days=40),
        utc(start.year, start.month, start.day),
    )
    s.finish(
        variant,
        difficulty,
        {"inflows": n_in, "beneficiaries": n_out, "dwell_hours": [lo, hi], "total": total},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector="services"), "holder"
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 300, 3000)), "pass_through_account"
    )
    if kind == "payroll_bureau":
        client = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        n = int(rng.integers(12, 30))
        salaries = [uniform(rng, 1400, 3200) for _ in range(n)]
        s.label_payment(
            s.pay(client, acct, round(sum(salaries) * 1.01, 2), moment, purpose="Payroll funding"),
            "inflow",
        )
        for amount in salaries:
            emp = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            s.label_payment(
                s.pay(acct, emp, amount, later(rng, moment, 3, 20), purpose="Salary"), "outflow"
            )
    elif kind == "marketplace_settlement":
        merchant = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail"),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        received = 0.0
        for _ in range(int(rng.integers(8, 20))):
            buyer = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            amount = uniform(rng, 900, 4000)
            received += amount
            s.label_payment(
                s.pay(
                    buyer, acct, amount, later(rng, moment, 0, 40), channel="card", purpose="Order"
                ),
                "inflow",
            )
        s.label_payment(
            s.pay(
                acct,
                merchant,
                round(received * 0.97, 2),
                later(rng, moment, 44, 50),
                purpose="Settlement",
            ),
            "outflow",
        )
    else:  # escrow
        seller = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        received = 0.0
        for _ in range(int(rng.integers(3, 6))):
            payer = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            amount = uniform(rng, 8000, 15000)
            received += amount
            s.label_payment(
                s.pay(payer, acct, amount, later(rng, moment, 0, 72), purpose="Deposit"), "inflow"
            )
        s.label_payment(
            s.pay(
                acct,
                seller,
                round(received, 2),
                later(rng, moment, 20 * 24, 40 * 24),
                purpose="Completion",
            ),
            "outflow",
        )
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/layering_chain.py`

Verbatim. Python, 122 lines. SHA-256 `3ae76eef8bff4bed96d21cd2def57cca9c5a7df72552ab2f8f5280476f2a470d`.

```python
"""layering_chain scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 3).

Illicit `chain` (easy): 50,000 to 500,000 passes through 3 to 6 accounts of different companies,
each keeping 0.5 to 3 percent and passing the rest on within 2 to 48 hours; two or more of the
intermediate companies share a registered address or a director. Illicit `split_chain` (hard): the
same, but one hop is split into two payments that merge again, or one dwell lasts 60 to 100 hours.
Look-alikes: a supply chain in which each tier adds a margin (`supply_chain`), and treasury sweeps
between companies of one group (`group_treasury`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "layering_chain"
ILLICIT = (("chain", "easy"), ("split_chain", "hard"))
LOOKALIKES = ("supply_chain", "group_treasury")
SPAN_DAYS = 30
LEAD_DAYS = 0


def _companies(s: ScenarioCtx, start: date, n: int, shared: bool) -> list[str]:
    rng = s.rng("companies")
    address = s.address() if shared else ""
    director = s.person() if shared else ""
    out = []
    for i in range(n):
        jurisdiction = foreign(rng) if rng.random() < 0.4 else "gb"
        co = s.company(
            incorporated=opened_before(rng, start, 60, 900),
            jurisdiction=jurisdiction,
            address=address if shared and i % 2 == 1 else "",
        )
        if shared and i % 2 == 0 and 0 < i < n - 1:
            s.director(director, co, start=opened_before(rng, start, 30, 600))
        out.append(co)
    return out


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    hops = int(rng.integers(3, 7))
    holders = _companies(s, start, hops + 1, True)
    accounts = [s.account(h, opened=opened_before(rng, start, 30, 700)) for h in holders]
    for h in holders[1:-1]:
        s.label(h, "intermediary_holder")
    s.label(accounts[0], "origin")
    s.label(accounts[-1], "destination")
    amount = uniform(rng, 50000, 500000)
    moment = at(rng, start)
    split_at = int(rng.integers(1, hops)) if variant == "split_chain" and rng.random() < 0.5 else -1
    slow_at = int(rng.integers(1, hops)) if variant == "split_chain" and split_at < 0 else -1
    for i in range(hops):
        dwell = (60, 100) if i == slow_at else (2, 48)
        if i > 0:
            moment = later(rng, moment, *dwell)
        if i == split_at:
            part = round(amount * float(rng.uniform(0.35, 0.65)), 2)
            for piece in (part, round(amount - part, 2)):
                s.label_payment(
                    s.pay(
                        accounts[i],
                        accounts[i + 1],
                        piece,
                        later(rng, moment, 0.1, 3),
                        purpose="Services",
                    ),
                    "hop",
                )
        else:
            s.label_payment(
                s.pay(accounts[i], accounts[i + 1], amount, moment, purpose="Services"), "hop"
            )
        amount = round(amount * float(rng.uniform(0.97, 0.995)), 2)
    for a in accounts[1:-1]:
        camouflage(
            s,
            a,
            utc(start.year, start.month, start.day) - timedelta(days=45),
            utc(start.year, start.month, start.day),
            n=2,
        )
    s.finish(variant, difficulty, {"hops": hops, "split_at": split_at, "slow_at": slow_at})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    tiers = int(rng.integers(3, 6))
    if kind == "group_treasury":
        parent = s.company(incorporated=opened_before(rng, start, 2000, 8000))
        holders = [parent] + [
            s.company(incorporated=opened_before(rng, start, 1000, 6000)) for _ in range(tiers)
        ]
        for child in holders[1:]:
            s.owns(parent, child, band="75-100", start=opened_before(rng, start, 900, 4000))
    else:
        holders = [
            s.company(incorporated=opened_before(rng, start, 1000, 8000), sector=sec)
            for sec in ["retail"] + ["wholesale"] * (tiers - 1) + ["manufacturing"]
        ]
    accounts = [s.account(h, opened=opened_before(rng, start, 400, 4000)) for h in holders]
    s.label(accounts[0], "origin")
    s.label(accounts[-1], "destination")
    amount = uniform(rng, 40000, 300000)
    moment = at(rng, start)
    for i in range(len(accounts) - 1):
        if i > 0:
            moment = later(rng, moment, 4, 60)
        s.label_payment(
            s.pay(accounts[i], accounts[i + 1], amount, moment, purpose="Invoice"), "hop"
        )
        if kind == "supply_chain":
            amount = round(
                amount * float(rng.uniform(0.80, 0.92)), 2
            )  # the upstream supplier is paid less
        else:
            amount = round(amount * float(rng.uniform(0.98, 1.0)), 2)
    s.finish(kind, "", {"tiers": tiers})
```

### `ingest/src/neonradar_ingest/synth/scenarios/circular_flow.py`

Verbatim. Python, 125 lines. SHA-256 `1ad826ed7647d467e69b99de8a7e231d27a94d5911afaad30efa2e205b320c5e`.

```python
"""circular_flow scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 4; M1.8e `round_trip`).

Illicit `round_trip` (easy): 30,000 to 400,000 leaves an account, passes through 2 to 5 other
companies (often abroad), each keeping 0.5 to 3 percent, and comes back to the same account within
2 to 12 days. Illicit `same_holder_return` (hard): the money comes back to another account of the
same holder, or the trip lasts 12 to 20 days. Look-alikes: a refund (`refund`), a short loan
drawdown and repayment (`loan`), and an intra-group cash pooling sweep and return (`cash_pool`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "circular_flow"
ILLICIT = (("round_trip", "easy"), ("same_holder_return", "hard"))
LOOKALIKES = ("refund", "loan", "cash_pool")
SPAN_DAYS = 45
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    origin_holder = s.label(
        s.company(incorporated=opened_before(rng, start, 300, 5000)), "origin_holder"
    )
    origin = s.label(
        s.account(origin_holder, opened=opened_before(rng, start, 300, 4000)), "origin"
    )
    back = origin
    total_days = float(rng.uniform(2, 12))
    if variant == "same_holder_return":
        if rng.random() < 0.6:
            back = s.label(
                s.account(origin_holder, opened=opened_before(rng, start, 300, 4000)),
                "return_account",
            )
        else:
            total_days = float(rng.uniform(12, 20))
    hops = int(rng.integers(3, 7))
    intermediaries = []
    for _ in range(hops - 1):
        co = s.company(
            incorporated=opened_before(rng, start, 60, 1500),
            jurisdiction=foreign(rng) if rng.random() < 0.6 else "gb",
        )
        intermediaries.append(s.account(co, opened=opened_before(rng, start, 30, 900)))
    path = [origin, *intermediaries, back]
    amount = uniform(rng, 30000, 400000)
    moment = at(rng, start)
    gaps = rng.dirichlet([1.5] * hops) * total_days * 24
    for i in range(hops):
        if i > 0:
            moment = later(rng, moment, max(1.0, float(gaps[i]) * 0.9), max(1.5, float(gaps[i])))
        p = s.pay(
            path[i], path[i + 1], amount, moment, purpose="Investment" if i == 0 else "Services"
        )
        s.label_payment(p, "hop")
        amount = round(amount * float(rng.uniform(0.97, 0.995)), 2)
    camouflage(
        s,
        origin,
        utc(start.year, start.month, start.day) - timedelta(days=50),
        utc(start.year, start.month, start.day),
    )
    s.finish(
        variant,
        difficulty,
        {"hops": hops, "days": round(total_days, 1), "same_holder": back != origin},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    a_holder = s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail")
    a = s.label(s.account(a_holder, opened=opened_before(rng, start, 400, 4000)), "origin")
    s.label(a_holder, "origin_holder")
    moment = at(rng, start)
    if kind == "refund":
        b = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 400, 4000),
        )
        amount = uniform(rng, 1000, 30000)
        s.label_payment(s.pay(a, b, amount, moment, purpose="Order 4471"), "hop")
        s.label_payment(
            s.pay(b, a, amount, later(rng, moment, 24, 240), purpose="Refund order 4471"), "hop"
        )
    elif kind == "loan":
        lender = s.account(
            s.organization(f"Synthetic Lending {s.scenario_id[-5:]} Ltd"),
            opened=opened_before(rng, start, 2000, 8000),
        )
        amount = uniform(rng, 5000, 80000)
        s.label_payment(s.pay(lender, a, amount, moment, purpose="Loan drawdown"), "hop")
        s.label_payment(
            s.pay(
                a,
                lender,
                round(amount * float(rng.uniform(1.0, 1.03)), 2),
                later(rng, moment, 5 * 24, 13 * 24),
                purpose="Loan repayment",
            ),
            "hop",
        )
    else:  # cash_pool
        parent = s.company(incorporated=opened_before(rng, start, 2000, 8000))
        s.owns(parent, a_holder, band="75-100", start=opened_before(rng, start, 900, 4000))
        pool = s.account(parent, opened=opened_before(rng, start, 400, 4000))
        amount = uniform(rng, 20000, 200000)
        s.label_payment(s.pay(a, pool, amount, moment, purpose="Cash pool sweep"), "hop")
        s.label_payment(
            s.pay(
                pool,
                a,
                round(amount * float(rng.uniform(0.95, 1.0)), 2),
                later(rng, moment, 16, 72),
                purpose="Cash pool return",
            ),
            "hop",
        )
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/fan_in_collection.py`

Verbatim. Python, 174 lines. SHA-256 `c1582cfac28ef4ce8bbe282b3dd35884ecaea706fafe72ed49c027b27943c796`.

```python
"""fan_in_collection scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 5).

Illicit `collector` (easy): 10 to 30 accounts of people, most of them years old (a fifth opened 10
to 60 days earlier: the senders are often victims, and recency belongs to the collector), each
pay 300 to 2,000 into one collection account within 2 to 6 days; the collector pays 80 to 95
percent on within 1 to 3 days or withdraws it in cash. Illicit `ring` (hard): 5 to 12 newly opened
accounts each receive from 2 to 4 people and pass the money to one or two hub accounts, also new,
which forward it. Look-alikes: a donation drive (`charity`), rent collection (`landlord`) and a
crowdfunding campaign that pays its beneficiary once (`crowdfunding`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import foreign, opened_before, uniform

TYPOLOGY = "fan_in_collection"
ILLICIT = (("collector", "easy"), ("ring", "hard"))
LOOKALIKES = ("charity", "landlord", "crowdfunding")
SPAN_DAYS = 100
LEAD_DAYS = 70


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    first = at(rng, start)
    branch = s.ctx.branches[0]
    if variant == "collector":
        collector_holder = s.label(s.person(born=(1985, 2005)), "collector_holder")
        collector = s.label(
            s.account(collector_holder, opened=opened_before(rng, start, 20, 90)), "collector"
        )
        n = int(rng.integers(10, 31))
        received = 0.0
        last = first
        for _ in range(n):
            new = rng.random() < 0.2
            sender = s.account(
                s.person(),
                opened=opened_before(rng, start, 10, 60)
                if new
                else opened_before(rng, start, 400, 4000),
            )
            amount = uniform(rng, 300, 2000)
            received += amount
            moment = later(rng, first, 0, float(rng.uniform(2, 6)) * 24)
            last = max(last, moment)
            s.label_payment(
                s.pay(sender, collector, amount, moment, purpose="Payment"), "contribution"
            )
        onward = round(received * float(rng.uniform(0.8, 0.95)), 2)
        if rng.random() < 0.5:
            s.label_payment(
                s.pay(
                    collector, branch, onward, later(rng, last, 24, 72), channel="cash_withdrawal"
                ),
                "cash_out",
            )
        else:
            dest = s.account(
                s.company(
                    incorporated=opened_before(rng, start, 100, 2000), jurisdiction=foreign(rng)
                ),
                opened=opened_before(rng, start, 100, 2000),
            )
            s.label_payment(
                s.pay(collector, dest, onward, later(rng, last, 24, 72), purpose="Goods"), "onward"
            )
        s.finish(variant, difficulty, {"senders": n})
        return
    hubs = [
        s.account(
            s.label(s.person(born=(1985, 2005)), "collector_holder"),
            opened=opened_before(rng, start, 5, 40),
        )
        for _ in range(int(rng.integers(1, 3)))
    ]
    for h in hubs:
        s.label(h, "collector")
    mules = int(rng.integers(5, 13))
    hub_in = {h: 0.0 for h in hubs}
    for m in range(mules):
        mule = s.account(s.person(born=(1990, 2006)), opened=opened_before(rng, start, 5, 45))
        got = 0.0
        for _ in range(int(rng.integers(2, 5))):
            victim = s.account(
                s.person(born=(1940, 1990)), opened=opened_before(rng, start, 1000, 9000)
            )
            amount = uniform(rng, 400, 2500)
            got += amount
            s.label_payment(
                s.pay(victim, mule, amount, later(rng, first, 0, 72), purpose="Transfer"),
                "victim_payment",
            )
        hub = hubs[m % len(hubs)]
        share = round(got * float(rng.uniform(0.85, 0.95)), 2)
        hub_in[hub] += share
        s.label_payment(
            s.pay(mule, hub, share, later(rng, first, 80, 120), purpose="Transfer"), "to_hub"
        )
    for hub in hubs:
        s.label_payment(
            s.pay(
                hub,
                branch,
                round(hub_in[hub] * 0.9, 2),
                later(rng, first, 130, 170),
                channel="cash_withdrawal",
            ),
            "cash_out",
        )
    s.finish(variant, difficulty, {"mules": mules, "hubs": len(hubs)})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    first = at(rng, start)
    sector = {"charity": "charity", "landlord": "real estate", "crowdfunding": "services"}[kind]
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector=sector),
        "collector_holder",
    )
    acct = s.label(s.account(holder, opened=opened_before(rng, start, 400, 4000)), "collector")
    if kind == "landlord":
        tenants = [
            s.account(s.person(), opened=opened_before(rng, start, 400, 5000))
            for _ in range(int(rng.integers(8, 20)))
        ]
        mortgage = s.account(
            s.organization(f"Synthetic Mortgages {s.scenario_id[-5:]} plc"),
            opened=opened_before(rng, start, 3000, 9000),
        )
        for month in range(3):
            day = start + timedelta(days=30 * month)
            for t in tenants:
                s.label_payment(s.pay(t, acct, 950.0, at(rng, day), purpose="Rent"), "contribution")
            s.label_payment(
                s.pay(acct, mortgage, 950.0 * len(tenants) * 0.7, at(rng, day + timedelta(days=2))),
                "onward",
            )
    else:
        n = int(rng.integers(25, 80))
        total = 0.0
        for _ in range(n):
            donor = s.account(s.person(), opened=opened_before(rng, start, 300, 6000))
            amount = uniform(rng, 10, 250)
            total += amount
            s.label_payment(
                s.pay(
                    donor,
                    acct,
                    amount,
                    later(rng, first, 0, 5 * 24),
                    channel="card",
                    purpose="Donation",
                ),
                "contribution",
            )
        if kind == "crowdfunding":
            beneficiary = s.account(s.person(), opened=opened_before(rng, start, 300, 6000))
            s.label_payment(
                s.pay(
                    acct,
                    beneficiary,
                    round(total * 0.95, 2),
                    later(rng, first, 6 * 24, 8 * 24),
                    purpose="Campaign payout",
                ),
                "onward",
            )
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/fan_out_distribution.py`

Verbatim. Python, 107 lines. SHA-256 `dc3927ab1c563773af14dcee17fae229dd24c6f3086dac7672cee71d0a1b3264`.

```python
"""fan_out_distribution scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 6).

Illicit `cash_out` (easy): one account pays 10 to 25 newly opened accounts of people similar or
round amounts within 1 to 2 days; most recipients withdraw 80 to 100 percent in cash or pass it on
within 1 to 4 days. Illicit `spread_out` (hard): amounts vary widely and only about half the
recipients move the money on, so some fall below a one-half rule. Look-alikes: a recurring
payroll (`payroll`), a one-off dividend to shareholders (`dividend`) and refunds after a cancelled
event (`event_refunds`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "fan_out_distribution"
ILLICIT = (("cash_out", "easy"), ("spread_out", "hard"))
LOOKALIKES = ("payroll", "dividend", "event_refunds")
SPAN_DAYS = 100
LEAD_DAYS = 70


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 30, 400)), "distributor_holder"
    )
    dist = s.label(s.account(holder, opened=opened_before(rng, start, 20, 300)), "distributor")
    branch = s.ctx.branches[int(rng.integers(len(s.ctx.branches)))]
    first = at(rng, start)
    n = int(rng.integers(10, 26))
    base = float(rng.choice([900.0, 950.0, 1000.0, 2000.0]))
    for _ in range(n):
        r = s.account(s.person(born=(1985, 2006)), opened=opened_before(rng, start, 5, 60))
        amount = base if variant == "cash_out" else uniform(rng, 300, 4500)
        moment = later(rng, first, 0, 40)
        s.label_payment(s.pay(dist, r, amount, moment, purpose="Payment"), "distribution")
        moves = rng.random() < (0.9 if variant == "cash_out" else 0.7)
        if moves:
            out = round(amount * float(rng.uniform(0.8, 1.0)), 2)
            s.label_payment(
                s.pay(r, branch, out, later(rng, moment, 20, 96), channel="cash_withdrawal"),
                "cash_out",
            )
    s.finish(
        variant, difficulty, {"recipients": n, "amount": base if variant == "cash_out" else None}
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 900, 8000)), "distributor_holder"
    )
    dist = s.label(s.account(holder, opened=opened_before(rng, start, 500, 5000)), "distributor")
    shop = s.account(
        s.company(incorporated=opened_before(rng, start, 900, 8000), sector="retail"),
        opened=opened_before(rng, start, 500, 5000),
    )
    n = int(rng.integers(10, 30))
    people = [s.account(s.person(), opened=opened_before(rng, start, 300, 6000)) for _ in range(n)]
    if kind == "payroll":
        salaries = [uniform(rng, 1500, 3500) for _ in range(n)]
        for month in range(3):
            day = start + timedelta(days=30 * month)
            for p, amount in zip(people, salaries, strict=True):
                moment = at(rng, day, 7, 9)
                s.label_payment(s.pay(dist, p, amount, moment, purpose="Salary"), "distribution")
                s.pay(
                    p,
                    shop,
                    round(amount * 0.15, 2),
                    later(rng, moment, 24, 200),
                    channel="card",
                    purpose="Groceries",
                )
    elif kind == "dividend":
        moment = at(rng, start)
        for p in people:
            s.label_payment(
                s.pay(
                    dist,
                    p,
                    float(rng.choice([500.0, 1000.0, 1500.0])),
                    later(rng, moment, 0, 6),
                    purpose="Dividend",
                ),
                "distribution",
            )
    else:  # event_refunds: the recipients had paid the organiser before
        moment = at(rng, start)
        for p in people:
            s.pay(
                p,
                dist,
                120.0,
                later(rng, moment - timedelta(days=40), 0, 240),
                channel="card",
                purpose="Ticket",
            )
            s.label_payment(
                s.pay(dist, p, 120.0, later(rng, moment, 0, 30), purpose="Refund"), "distribution"
            )
    s.finish(kind, "", {"recipients": n})
```

### `ingest/src/neonradar_ingest/synth/scenarios/dormant_reactivation.py`

Verbatim. Python, 235 lines. SHA-256 `fb6c4c2736e805ed0c8eecfa980f52378974d3ba43f7ba979d95d73ee5def585`.

```python
"""dormant_reactivation scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 7).

The burst starts on the scenario's start day; the quiet gap lies before it. Illicit
`reactivated` (easy): a company account with a few small payments, then 200 to 300 quiet days,
then 6 to 15 payments in and out totalling 50,000 to 300,000 within 3 to 10 days, 5 to 30 days
after a new director was appointed. Illicit `dormant_company` (hard): the holder filed dormant
accounts; a quiet gap of 150 to 260 days ends in 4 to 10 payments totalling 15,000 to 60,000 over up
to 20 days, so some bursts fall below the thresholds. Illicit `capital_flip` (medium): a company
incorporated 20 to 80 days earlier receives two or three large payments totalling 80,000 to
400,000 and pays 85 to 100 percent of it on to two to four accounts within five days ("large sums
of capital funding quickly following incorporation", FATF and Egmont 2018 Annex E).
Look-alikes: a seasonal business back after its closed season at its usual level (`seasonal`), a
property sale paid into a long-quiet personal account (`property_sale`, which the detector does
flag: the shape is the same), a business that restarts at its earlier level under a new owner
(`restart`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "dormant_reactivation"
ILLICIT = (("reactivated", "easy"), ("dormant_company", "hard"), ("capital_flip", "medium"))
LOOKALIKES = ("seasonal", "property_sale", "restart")
SPAN_DAYS = 25
LEAD_DAYS = 420


def _counterparties(s: ScenarioCtx, start: date, n: int) -> list[str]:
    rng = s.rng("counterparties")
    return [
        s.account(
            s.company(incorporated=opened_before(rng, start, 200, 4000)),
            opened=opened_before(rng, start, 200, 3000),
        )
        for _ in range(n)
    ]


def _burst(s: ScenarioCtx, acct: str, start: date, n: int, total: float, days: float) -> None:
    """Payments in from some counterparties and out to others, alternately."""
    rng = s.rng("burst", acct)
    payers = _counterparties(s, start, max(2, n // 4))
    payees = _counterparties(s, start, max(2, n // 4))
    first = at(rng, start)
    amount = total / n
    for i in range(n):
        moment = first if i == 0 else later(rng, first, 0.5, days * 24)
        if i % 2 == 0:
            other = payers[(i // 2) % len(payers)]
            s.label_payment(
                s.pay(
                    other,
                    acct,
                    round(amount * float(rng.uniform(0.8, 1.2)), 2),
                    moment,
                    purpose="Services",
                ),
                "burst_in",
            )
        else:
            other = payees[(i // 2) % len(payees)]
            s.label_payment(
                s.pay(
                    acct,
                    other,
                    round(amount * float(rng.uniform(0.7, 1.0)), 2),
                    moment,
                    purpose="Services",
                ),
                "burst_out",
            )


def _early(s: ScenarioCtx, acct: str, before: date) -> None:
    rng = s.rng("early", acct)
    other = _counterparties(s, before, 1)[0]
    for _ in range(int(rng.integers(1, 4))):
        s.pay(
            other,
            acct,
            uniform(rng, 50, 600),
            at(rng, before - timedelta(days=int(rng.integers(0, 20)))),
            purpose="Invoice",
        )


def _usual(s: ScenarioCtx, acct: str, until: date, days: int, monthly: float) -> None:
    """Ordinary activity at `monthly` volume over the `days` before `until` (unlabelled)."""
    rng = s.rng("usual", acct)
    others = _counterparties(s, until, 3)
    n = max(4, days // 7)
    for i in range(n):
        day = until - timedelta(days=int(rng.integers(1, days)))
        amount = round(monthly * days / 30 / n * float(rng.uniform(0.6, 1.4)), 2)
        if i % 2 == 0:
            s.pay(others[i % 3], acct, amount, at(rng, day), purpose="Invoice")
        else:
            s.pay(acct, others[i % 3], round(amount * 0.9, 2), at(rng, day), purpose="Invoice")


def _capital_flip(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("flip")
    holder = s.label(
        s.company(incorporated=start - timedelta(days=int(rng.integers(20, 81)))), "holder"
    )
    acct = s.label(
        s.account(holder, opened=start - timedelta(days=int(rng.integers(5, 15)))),
        "reactivated_account",
    )
    funders = _counterparties(s, start, int(rng.integers(2, 4)))
    total = uniform(rng, 80000, 400000)
    first = at(rng, start)
    for i, f in enumerate(funders):
        s.label_payment(
            s.pay(
                f,
                acct,
                round(total / len(funders), 2),
                later(rng, first, 0, 24) if i else first,
                purpose="Capital",
            ),
            "burst_in",
        )
    dests = _counterparties(s, start, int(rng.integers(2, 5)))
    moved = total * float(rng.uniform(0.85, 1.0))
    for d in dests:
        s.label_payment(
            s.pay(
                acct,
                d,
                round(moved / len(dests), 2),
                later(rng, first, 26, 120),
                purpose="Transfer",
            ),
            "burst_out",
        )
    s.finish(variant, difficulty, {"capital": total, "moved_share": round(moved / total, 3)})


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    if variant == "capital_flip":
        _capital_flip(s, variant, difficulty, start)
        return
    rng = s.rng("illicit")
    category = "DORMANT" if variant == "dormant_company" else ""
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 900, 6000), accounts_category=category),
        "holder",
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 600, 3000)), "reactivated_account"
    )
    gap = int(rng.integers(200, 301)) if variant == "reactivated" else int(rng.integers(150, 261))
    _early(s, acct, start - timedelta(days=gap))
    if variant == "reactivated" or rng.random() < 0.5:
        director = s.label(s.person(), "new_director")
        s.director(director, holder, start=start - timedelta(days=int(rng.integers(5, 31))))
    if variant == "reactivated":
        n, total, days = (
            int(rng.integers(6, 16)),
            uniform(rng, 50000, 300000),
            float(rng.uniform(3, 10)),
        )
    else:
        n, total, days = (
            int(rng.integers(4, 11)),
            uniform(rng, 15000, 60000),
            float(rng.uniform(3, 20)),
        )
    _burst(s, acct, start, n, total, days)
    s.finish(
        variant,
        difficulty,
        {"gap_days": gap, "burst_payments": n, "burst_total": total, "burst_days": round(days, 1)},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    if kind == "property_sale":
        holder = s.label(s.person(born=(1940, 1975)), "holder")
        acct = s.label(
            s.account(holder, opened=opened_before(rng, start, 2000, 9000)), "reactivated_account"
        )
        _early(s, acct, start - timedelta(days=int(rng.integers(200, 320))))
        solicitor = _counterparties(s, start, 3)
        moment = at(rng, start)
        s.label_payment(
            s.pay(
                solicitor[0], acct, uniform(rng, 150000, 450000), moment, purpose="Completion funds"
            ),
            "burst_in",
        )
        for dest in solicitor[1:] * 3:
            s.label_payment(
                s.pay(
                    acct,
                    dest,
                    uniform(rng, 8000, 60000),
                    later(rng, moment, 2, 240),
                    purpose="Transfer",
                ),
                "burst_out",
            )
        s.finish(kind, "", {})
        return
    sector = "tourism" if kind == "seasonal" else "manufacturing"
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 1500, 8000), sector=sector), "holder"
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 900, 5000)), "reactivated_account"
    )
    gap = int(rng.integers(170, 200)) if kind == "seasonal" else int(rng.integers(200, 260))
    total = uniform(rng, 30000, 150000)
    # the business was as busy before the quiet period as it is after it
    _usual(
        s,
        acct,
        start - timedelta(days=gap),
        120 if kind == "seasonal" else 150,
        total * float(rng.uniform(0.8, 1.5)),
    )
    if kind == "restart":
        owner = s.company(incorporated=opened_before(rng, start, 1500, 8000))
        s.owns(
            owner, holder, band="75-100", start=start - timedelta(days=int(rng.integers(10, 40)))
        )
    _burst(s, acct, start, int(rng.integers(6, 14)), total, float(rng.uniform(5, 14)))
    s.finish(kind, "", {"gap_days": gap})
```

### `ingest/src/neonradar_ingest/synth/scenarios/shell_chain.py`

Verbatim. Python, 131 lines. SHA-256 `57349b49c9d8fd7d61e694bfbe15dd1b2e388890153d7e3d702b120835fa63aa`.

```python
"""shell_chain scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 8).

Illicit `layered` (easy): a person, or a company with no recorded owner, owns a chain of 3 to 5
companies in 2 to 4 jurisdictions; one link has a nominee owner or a chain company has a nominee
director, and a professional director with 12 to 25 other appointments sits on one of them.
Illicit `loop` (hard): three or four companies in two or more jurisdictions own each other in a
loop, or a chain of only two companies, which falls below a three-layer rule. Look-alikes: a lawful
group holding structure with ordinary directors (`group_holding`), and a fund vehicle whose
directors are professional directors (`fund_vehicle`).
"""

from __future__ import annotations

from datetime import date

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import FOREIGN, opened_before

TYPOLOGY = "shell_chain"
ILLICIT = (("layered", "easy"), ("loop", "hard"))
LOOKALIKES = ("group_holding", "fund_vehicle")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _jurisdictions(s: ScenarioCtx, n: int, distinct: int) -> list[str]:
    rng = s.rng("jurisdictions")
    pool = ["gb", *FOREIGN]
    picked = [pool[0]] + [
        pool[1 + int(i)] for i in rng.choice(len(pool) - 1, size=distinct - 1, replace=False)
    ]
    return [picked[i % distinct] for i in range(n)]


def _professional(s: ScenarioCtx, start: date, appointments: int) -> str:
    rng = s.rng("professional")
    pro = s.person(locale="en_GB", nationality="je")
    for _ in range(appointments):
        client = s.company(incorporated=opened_before(rng, start, 200, 4000), jurisdiction="je")
        s.director(pro, client, start=opened_before(rng, start, 30, 1500))
    return pro


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    if variant == "loop" and rng.random() < 0.4:
        # two layers only: present, but below the three-layer rule
        top = s.label(s.person(), "top_owner")
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 1500), jurisdiction="vg"), "layer"
        )
        leaf = s.label(s.company(incorporated=opened_before(rng, start, 50, 900)), "owned_company")
        s.owns(top, mid, band="75-100", start=opened_before(rng, start, 30, 900))
        s.owns(mid, leaf, band="75-100", start=opened_before(rng, start, 20, 800), nominee=True)
        s.finish(variant, difficulty, {"layers": 2})
        return
    if variant == "loop":
        n = int(rng.integers(3, 5))
        places = _jurisdictions(s, n, 2)
        companies = [
            s.company(incorporated=opened_before(rng, start, 100, 2000), jurisdiction=j)
            for j in places
        ]
        for i, c in enumerate(companies):
            s.label(c, "layer" if i else "owned_company")
            s.owns(
                c, companies[(i + 1) % n], band="50-75", start=opened_before(rng, start, 20, 900)
            )
        s.finish(variant, difficulty, {"layers": n, "loop": True})
        return
    n = int(rng.integers(3, 6))
    places = _jurisdictions(s, n, int(rng.integers(2, min(4, n) + 1)))
    if rng.random() < 0.5:
        top = s.label(s.person(nationality="cy"), "top_owner")
    else:
        top = s.label(
            s.company(incorporated=opened_before(rng, start, 500, 4000), jurisdiction="pa"),
            "top_owner",
        )
    companies = [
        s.company(incorporated=opened_before(rng, start, 60, 1500), jurisdiction=j)
        for j in reversed(places)
    ]
    owner = top
    nominee_at = int(rng.integers(n))
    for i, c in enumerate(companies):
        s.label(c, "owned_company" if i == n - 1 else "layer")
        s.owns(
            owner,
            c,
            band="75-100",
            start=opened_before(rng, start, 20, 900),
            nominee=(i == nominee_at and rng.random() < 0.5),
        )
        owner = c
    nominee = s.label(s.person(), "nominee")
    s.director(
        nominee, companies[nominee_at], start=opened_before(rng, start, 20, 900), nominee=True
    )
    pro = s.label(_professional(s, start, int(rng.integers(12, 26))), "professional_director")
    s.director(pro, companies[int(rng.integers(n))], start=opened_before(rng, start, 20, 900))
    s.finish(variant, difficulty, {"layers": n, "jurisdictions": len(set(places))})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    n = int(rng.integers(3, 5))
    places = ["gb", "ie", "gb", "nl"][:n]
    top = s.label(
        s.person()
        if kind == "group_holding"
        else s.company(incorporated=opened_before(rng, start, 2000, 8000), jurisdiction="lu"),
        "top_owner",
    )
    owner = top
    companies = []
    for i in range(n):
        c = s.label(
            s.company(incorporated=opened_before(rng, start, 400, 6000), jurisdiction=places[i]),
            "owned_company" if i == n - 1 else "layer",
        )
        s.owns(owner, c, band="75-100", start=opened_before(rng, start, 100, 3000))
        companies.append(c)
        owner = c
    if kind == "fund_vehicle":
        pro = s.label(_professional(s, start, int(rng.integers(15, 40))), "professional_director")
        s.director(pro, companies[0], start=opened_before(rng, start, 100, 2000))
    else:
        for c in companies:
            s.director(s.person(), c, start=opened_before(rng, start, 100, 2000))
    s.finish(kind, "", {"layers": n})
```

### `ingest/src/neonradar_ingest/synth/scenarios/mass_registration_address.py`

Verbatim. Python, 71 lines. SHA-256 `c7bf9fbf8c13bc247e037549e1139bc4577a5cb4157b7850fb8e77074cc8c0b7`.

```python
"""mass_registration_address scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 9).

Illicit `factory` (easy): 25 to 60 companies registered at one address, most incorporated within
a month, two or three nominee directors shared across many of them, and payments between some of
them. Illicit `quiet_factory` (hard): 18 to 30 companies, spread over a year, one shared director,
no payments, so some fall below a 20-company rule. Look-alikes: a registered agent's address with
30 to 120 ordinary clients incorporated over many years (`registered_agent`) and a serviced office
(`serviced_office`).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "mass_registration_address"
ILLICIT = (("factory", "easy"), ("quiet_factory", "hard"))
LOOKALIKES = ("registered_agent", "serviced_office")
SPAN_DAYS = 30
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    address = s.label(s.address(), "registered_address")
    easy = variant == "factory"
    n = int(rng.integers(25, 61)) if easy else int(rng.integers(18, 31))
    spread = 30 if easy else 365
    companies = []
    for i in range(n):
        incorporated = start - timedelta(
            days=int(rng.integers(0, spread)) + (0 if easy or i % 3 else 400)
        )
        companies.append(s.label(s.company(incorporated=incorporated, address=address), "member"))
    directors = [
        s.label(s.person(), "shared_director")
        for _ in range(int(rng.integers(2, 4)) if easy else 1)
    ]
    for i, c in enumerate(companies):
        if rng.random() < (0.7 if easy else 0.3):
            s.director(
                directors[i % len(directors)],
                c,
                start=opened_before(rng, start, 0, 30),
                nominee=easy,
            )
    if easy:
        accounts = [
            s.account(c, opened=opened_before(rng, start, 0, 20))
            for c in companies[: max(4, n // 5)]
        ]
        moment = at(rng, start + timedelta(days=5))
        for a, b in pairwise(accounts):
            s.pay(a, b, uniform(rng, 20000, 150000), later(rng, moment, 1, 200), purpose="Services")
    s.finish(variant, difficulty, {"companies": n})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    address = s.label(s.address(), "registered_address")
    n = int(rng.integers(30, 121)) if kind == "registered_agent" else int(rng.integers(20, 41))
    for _ in range(n):
        c = s.company(
            incorporated=start - timedelta(days=int(rng.integers(30, 7000))), address=address
        )
        s.director(s.person(), c, start=opened_before(rng, start, 30, 3000))
    s.finish(kind, "", {"companies": n})
```

### `ingest/src/neonradar_ingest/synth/scenarios/sanctions_exposure.py`

Verbatim. Python, 118 lines. SHA-256 `f9312704c196a81f785b245e863681b3427f944e39b3602db262010ec4cdf347`.

```python
"""sanctions_exposure scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 10).

A synthetic listed entity carries the `sanction` topic and a `Sanction` record from "Synthetic
Authority A"; a listed person has an invented surname in a script the name stream chooses and the
synthetic nationality `zz`. Illicit `majority_chain` (easy): it owns 75 percent or more of a company
directly, or through one or two companies it holds more than half of; every company in the chain is
an exposed organisation (the target is the core one). Illicit `split_or_control` (hard): two listed
owners hold more than 25 percent each (the aggregate rule's case), or a listed person holds a board
appointment right, significant influence, or a directorship without owning the company. Look-alikes:
a minority stake of 20 to 40 percent two links away (`minority_stake`; the middle company is exposed
too, and an alert on it is a look-alike hit) and a listed entity holding 3 to 15 percent of a
company others hold the rest of (`diffuse_holding`), both recorded as exact shares.
"""

from __future__ import annotations

from datetime import date

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import foreign, opened_before

TYPOLOGY = "sanctions_exposure"
ILLICIT = (("majority_chain", "easy"), ("split_or_control", "hard"))
LOOKALIKES = ("minority_stake", "diffuse_holding")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _listed(s: ScenarioCtx, start: date, person: bool) -> str:
    rng = s.rng("listed")
    if person:
        entity = s.person(locale="any", nationality="zz", topics=("sanction",))
    else:
        entity = s.company(
            incorporated=opened_before(rng, start, 1000, 6000),
            jurisdiction=foreign(rng),
            topics=("sanction",),
        )
    s.sanction(entity, start=opened_before(rng, start, 100, 1500))
    return s.label(entity, "listed_owner")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    target = s.label(s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity")
    if variant == "majority_chain":
        owner = _listed(s, start, rng.random() < 0.5)
        links = int(rng.integers(1, 4))
        for i in range(links - 1):
            mid = s.label(
                s.company(
                    incorporated=opened_before(rng, start, 200, 3000), jurisdiction=foreign(rng)
                ),
                "exposed_entity",
                core=False,
            )
            s.owns(
                owner,
                mid,
                band="75-100" if i == 0 else "50-75",
                start=opened_before(rng, start, 30, 900),
            )
            owner = mid
        s.owns(owner, target, band="75-100", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"links": links})
        return
    if rng.random() < 0.5:
        a, b = _listed(s, start, False), _listed(s, start, True)
        s.owns(a, target, band="25-50", start=opened_before(rng, start, 30, 900))
        s.owns(b, target, band="25-50", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"form": "two listed owners"})
        return
    person = _listed(s, start, True)
    r = rng.random()
    if r < 0.35:
        s.control(person, target, control_type="appointment")
        form = "appointment right"
    elif r < 0.7:
        s.control(person, target, control_type="influence")
        form = "significant influence"
    else:
        s.director(person, target, start=opened_before(rng, start, 30, 900))
        form = "director"
    s.finish(variant, difficulty, {"form": form})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    target = s.label(s.company(incorporated=opened_before(rng, start, 500, 6000)), "exposed_entity")
    listed = _listed(s, start, False)
    if kind == "minority_stake":
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 500, 6000)),
            "exposed_entity",
            core=False,
        )
        s.owns(
            listed,
            mid,
            band=f"exact:{int(rng.integers(20, 40))}",
            start=opened_before(rng, start, 100, 2000),
        )
        s.owns(
            mid,
            target,
            band=f"exact:{int(rng.integers(20, 40))}",
            start=opened_before(rng, start, 100, 2000),
        )
    else:
        s.owns(
            listed,
            target,
            band=f"exact:{int(rng.integers(3, 15))}",
            start=opened_before(rng, start, 100, 2000),
        )
        for _ in range(2):
            s.owns(s.person(), target, band="25-50", start=opened_before(rng, start, 100, 2000))
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/formation_agent_cluster.py`

Verbatim. Python, 114 lines. SHA-256 `8f285583e2fb3626b5f8700b1442f53556cf8b7b9260c9a8672162186e119b68`.

```python
"""formation_agent_cluster scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 11).

Illicit `agent_factory` (easy): one agent represents 12 to 30 companies incorporated within three
weeks, most registered at the agent's own address, with two or three nominee directors shared
across them and payments between a few of them. Illicit `spread_agent` (hard): 12 to 18 companies
incorporated over 20 to 40 days, with two directors shared across about half of them, so some
bursts fall below ten companies within 30 days. Look-alikes: a busy lawful formation
agent with 40 to 80 clients formed over years, each with its own directors (`busy_agent`), and a
corporate group of 10 to 14 companies formed in one week by an agent, owned by one holding company
and sharing the group's two directors (`group_formation`, which the detector does flag: the shape
is the same).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "formation_agent_cluster"
ILLICIT = (("agent_factory", "easy"), ("spread_agent", "hard"))
LOOKALIKES = ("busy_agent", "group_formation")
SPAN_DAYS = 45
LEAD_DAYS = 0


def _agent(s: ScenarioCtx, start: date) -> tuple[str, str]:
    rng = s.rng("agent")
    office = s.address()
    agent = s.company(
        incorporated=opened_before(rng, start, 1500, 8000), sector="services", address=office
    )
    return s.label(agent, "agent"), office


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    agent, office = _agent(s, start)
    easy = variant == "agent_factory"
    n = int(rng.integers(12, 31)) if easy else int(rng.integers(12, 19))
    spread = 21 if easy else int(rng.integers(20, 41))
    clients = []
    for _ in range(n):
        at_office = rng.random() < (0.8 if easy else 0.4)
        client = s.company(
            incorporated=start - timedelta(days=int(rng.integers(0, spread + 1))),
            address=office if at_office else s.address(),
        )
        s.label(client, "client")
        s.represents(agent, client)
        clients.append(client)
    officers = [
        s.label(s.person(), "shared_officer") for _ in range(int(rng.integers(2, 4)) if easy else 2)
    ]
    share = 0.8 if easy else 0.5
    for i, client in enumerate(clients):
        if rng.random() < share:
            s.director(
                officers[i % len(officers)],
                client,
                start=opened_before(rng, start, 0, 10),
                nominee=easy,
            )
        else:
            s.director(s.person(), client, start=opened_before(rng, start, 0, 10))
    if easy:
        accounts = [s.account(c, opened=opened_before(rng, start, 0, 10)) for c in clients[:4]]
        moment = at(rng, start + timedelta(days=10))
        for a, b in pairwise(accounts):
            s.pay(
                a, b, uniform(rng, 15000, 90000), later(rng, moment, 1, 240), purpose="Consultancy"
            )
    s.finish(
        variant,
        difficulty,
        {"clients": n, "spread_days": spread, "shared_officers": len(officers)},
        {"incorporated_in_burst": n if easy else None},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    agent, office = _agent(s, start)
    if kind == "busy_agent":
        n = int(rng.integers(40, 81))
        for _ in range(n):
            client = s.company(
                incorporated=start - timedelta(days=int(rng.integers(30, 4000))),
                address=office if rng.random() < 0.5 else s.address(),
            )
            s.represents(agent, client)
            s.director(s.person(), client, start=opened_before(rng, start, 30, 3000))
        s.finish(kind, "", {"clients": n})
        return
    n = int(rng.integers(10, 15))
    holding = s.label(
        s.company(incorporated=opened_before(rng, start, 400, 4000), sector="holding"), "client"
    )
    s.owns(s.person(), holding, band="75-100")  # a group with a person at the top
    directors = [s.label(s.person(), "shared_officer") for _ in range(2)]
    s.represents(agent, holding)
    for _ in range(n):
        sub = s.label(
            s.company(incorporated=start - timedelta(days=int(rng.integers(0, 7))), address=office),
            "client",
        )
        s.represents(agent, sub)
        s.owns(holding, sub, band="75-100", start=start)
        for d in directors:
            s.director(d, sub, start=start)
    s.finish(kind, "", {"subsidiaries": n})
```

### `ingest/src/neonradar_ingest/synth/scenarios/recycled_directors.py`

Verbatim. Python, 81 lines. SHA-256 `7c076aa9fc7b6e1fd00a24377b1b69201ae0f29ccba412bb5147d2f1e903bd86`.

```python
"""recycled_directors scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 12).

Illicit `strawman` (easy): one person is appointed director of 12 to 20 unrelated new companies,
eight or more within a month, resigns from some within three months, and a few of the companies pay
each other. Illicit `slow_strawman` (hard): 8 to 13 unrelated companies over four to eight months
and no payments, so the counts sit near the thresholds ("small numbers can matter": ten nominees,
25 companies in FATF PML Box 10). Look-alikes: a professional director of 12 to 25 fund companies
in fund jurisdictions with long tenures (`fund_director`, which the detector flags: the shape is
the same) and the director of a group's 12 to 20 subsidiaries (`group_director`, one group).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "recycled_directors"
ILLICIT = (("strawman", "easy"), ("slow_strawman", "hard"))
LOOKALIKES = ("fund_director", "group_director")
SPAN_DAYS = 240
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    director = s.label(s.person(), "director")
    easy = variant == "strawman"
    n = int(rng.integers(12, 21)) if easy else int(rng.integers(8, 14))
    companies = []
    for i in range(n):
        offset = (
            int(rng.integers(0, 30))
            if easy and i < 8
            else int(rng.integers(0, 120 if easy else 240))
        )
        appointed = start + timedelta(days=offset)
        company = s.label(
            s.company(incorporated=appointed - timedelta(days=int(rng.integers(0, 5)))),
            "company",
            core=False,
        )
        resigned = (
            appointed + timedelta(days=int(rng.integers(30, 90)))
            if easy and rng.random() < 0.3
            else None
        )
        s.director(director, company, start=appointed, end=resigned)
        companies.append(company)
    if easy:
        accounts = [s.account(c, opened=start) for c in companies[:4]]
        moment = at(rng, start + timedelta(days=35))
        for a, b in pairwise(accounts):
            s.pay(a, b, uniform(rng, 10000, 60000), later(rng, moment, 1, 300), purpose="Services")
    s.finish(variant, difficulty, {"companies": n})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    director = s.label(s.person(), "director")
    if kind == "fund_director":
        for _ in range(int(rng.integers(12, 26))):
            fund = s.company(
                incorporated=opened_before(rng, start, 400, 5000),
                jurisdiction=str(rng.choice(["je", "gg", "ky", "lu"])),
                sector="fund",
            )
            s.director(director, fund, start=opened_before(rng, start, 200, 3000))
        s.finish(kind, "", {})
        return
    parent = s.company(incorporated=opened_before(rng, start, 2000, 8000), sector="holding")
    s.owns(s.person(), parent, band="75-100")  # a group with a person at the top
    s.director(director, parent, start=opened_before(rng, start, 500, 3000))
    for _ in range(int(rng.integers(12, 21))):
        sub = s.company(incorporated=opened_before(rng, start, 100, 3000))
        s.owns(parent, sub, band="75-100")
        s.director(director, sub, start=opened_before(rng, start, 50, 2000))
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/pep_exposure.py`

Verbatim. Python, 96 lines. SHA-256 `1acdb7644ca27130abaf8874e590702619d874afd96a0068252cc82645bcb411`.

```python
"""pep_exposure scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 13).

A synthetic politically exposed person carries the `role.pep` topic and holds a synthetic public
office (`Position` with an `Occupancy`) in a synthetic country (`zz`) or, for some, in `gb`. The
PEP, the relatives and the associates have invented surnames.
Illicit `family_vehicle` (easy): the PEP is in office and a spouse, child or parent owns 75 percent
or more of a company, which owns a second company (both exposed; the first is the core one).
Illicit `associate_vehicle` (hard): a business partner of the PEP (ASSOCIATE_OF) holds more than
half of a company through two intermediate companies, three links in all. Look-alikes: a PEP who
left office 18 to 36 months ago and whose spouse owns a company (`former_pep`: family measures end
with the office, MLR 2017 reg 35(11)) and a cousin of a PEP in office who owns a company
(`distant_relative`: cousins are outside the family members the regulations name).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import foreign, opened_before

TYPOLOGY = "pep_exposure"
ILLICIT = (("family_vehicle", "easy"), ("associate_vehicle", "hard"))
LOOKALIKES = ("former_pep", "distant_relative")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _pep(s: ScenarioCtx, start: date, *, left_months: int = 0) -> str:
    rng = s.rng("pep")
    pep = s.label(s.person(locale="any", born=(1950, 1980), topics=("role.pep",)), "pep")
    country = "gb" if rng.random() < 0.3 else "zz"
    post = s.position(
        f"Synthetic Minister of Department {int(rng.integers(1, 40))}", country=country
    )
    began = opened_before(rng, start, 400, 3000)
    ended = start - timedelta(days=30 * left_months) if left_months else None
    s.occupancy(pep, post, start=began, end=ended)
    return pep


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    pep = _pep(s, start)
    if variant == "family_vehicle":
        relation = str(rng.choice(["spouse", "child", "parent"]))
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, relation)
        first = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity"
        )
        second = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 3000)),
            "exposed_entity",
            core=False,
        )
        s.owns(relative, first, band="75-100", start=opened_before(rng, start, 30, 900))
        s.owns(first, second, band="50-75", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"relationship": relation})
        return
    partner = s.label(s.person(invented=True), "associate")
    s.associate(pep, partner, "business partner")
    owner = partner
    for i in range(2):
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 200, 4000), jurisdiction=foreign(rng)),
            "exposed_entity",
            core=False,
        )
        s.owns(
            owner,
            mid,
            band="75-100" if i == 0 else "50-75",
            start=opened_before(rng, start, 30, 900),
        )
        owner = mid
    target = s.label(s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity")
    s.owns(owner, target, band="50-75", start=opened_before(rng, start, 30, 900))
    s.finish(variant, difficulty, {"links": 3})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    if kind == "former_pep":
        pep = _pep(s, start, left_months=int(rng.integers(18, 37)))
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, "spouse")
    else:
        pep = _pep(s, start)
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, "cousin")
    company = s.label(
        s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity"
    )
    s.owns(relative, company, band="75-100", start=opened_before(rng, start, 30, 900))
    s.finish(kind, "", {})
```

### `ingest/src/neonradar_ingest/synth/scenarios/cash_commingling.py`

Verbatim. Python, 195 lines. SHA-256 `88fdc071afae52caff1f6045320997b5bd1e2847dd1f9ec772c88a7f30933117`.

```python
"""cash_commingling scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 14).

Each scenario creates its own neighbourhood: five to eight ordinary businesses of one cash sector
in one postcode district (their own peer group, so the scenario works on any base), and the
business the scenario is about. Peers bank their takings on two to five days a week, Monday to
Saturday. Illicit `front_business` (easy): the business banks four to eight times its peers' cash,
some of it on Sundays, and pays most of it on to its owner and the owner's relative. Illicit
`blended_business` (hard): three to four times the peers, no Sunday deposits, about a third paid
on to the owner. Look-alikes: a busy business banking one and a half to two and a half times its
peers' cash and paying suppliers (`busy_business`) and a business that opened a second site half
way through and banks more from then on (`new_site`), both paying suppliers rather than people.
The business's cash deposits and its payments to related people are labelled; the peers are
context participants.
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at
from neonradar_ingest.synth.scenarios.common import lognormal, opened_before

TYPOLOGY = "cash_commingling"
ILLICIT = (("front_business", "easy"), ("blended_business", "hard"))
LOOKALIKES = ("busy_business", "new_site")
SPAN_DAYS = 120
LEAD_DAYS = 0
SECTORS = ("restaurant", "convenience store", "car wash", "hospitality")


def _area(s: ScenarioCtx) -> tuple[str, str]:
    """A postcode district of the scenario's own, and its sector."""
    rng = s.rng("area")
    return f"QQ{int(rng.integers(100, 990))}", str(rng.choice(SECTORS))


def _business(s: ScenarioCtx, district: str, sector: str, start: date) -> tuple[str, str]:
    rng = s.rng("business", str(len(s.created)))
    address = s.address(district=district)
    company = s.company(
        incorporated=opened_before(rng, start, 400, 6000), sector=sector, address=address
    )
    return company, s.account(company, opened=opened_before(rng, start, 200, 3000))


def _bank(
    s: ScenarioCtx,
    account: str,
    start: date,
    days: int,
    weekly: float,
    *,
    sundays: bool,
    label: bool,
    boost_from: date | None = None,
    boost: float = 1.0,
) -> list[str]:
    rng = s.rng("bank", account)
    per_week = int(rng.integers(2, 6))
    out = []
    for d in range(days):
        day = start + timedelta(days=d)
        if day.weekday() == 6 and not sundays:
            continue
        if rng.random() >= per_week / (7 if sundays else 6):
            continue
        amount = lognormal(
            rng,
            weekly / per_week * (boost if boost_from and day >= boost_from else 1.0),
            0.35,
            50,
            9500,
        )
        branch = s.ctx.branches[int(rng.integers(len(s.ctx.branches)))]
        p = s.pay(
            branch, account, amount, at(rng, day, 9, 17), channel="cash_deposit", purpose="Takings"
        )
        if label:
            s.label_payment(p, "deposit")
        out.append(p)
    return out


def _peers(
    s: ScenarioCtx, district: str, sector: str, start: date, days: int, weekly: float
) -> None:
    rng = s.rng("peers")
    for _ in range(int(rng.integers(5, 9))):
        company, account = _business(s, district, sector, start)
        s.label(company, "peer", core=False)
        _bank(
            s,
            account,
            start,
            days,
            weekly * float(rng.uniform(0.75, 1.3)),
            sundays=False,
            label=False,
        )


def _pay_on(
    s: ScenarioCtx,
    account: str,
    to: list[str],
    total: float,
    start: date,
    days: int,
    *,
    label: bool,
) -> None:
    rng = s.rng("onward", account)
    months = max(1, days // 30)
    for m in range(months):
        moment = at(rng, start + timedelta(days=30 * m + 27), 10, 15)
        for i, dst in enumerate(to):
            p = s.pay(
                account,
                dst,
                round(total / months / len(to) * (1.1 if i == 0 else 0.9), 2),
                moment,
                purpose="Transfer",
            )
            if label:
                s.label_payment(p, "related_party")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    district, sector = _area(s)
    days = SPAN_DAYS
    weekly = float(rng.uniform(1500, 4000))
    _peers(s, district, sector, start, days, weekly)
    company, account = _business(s, district, sector, start)
    s.label(company, "business")
    s.label(account, "receiving_account")
    easy = variant == "front_business"
    ratio = float(rng.uniform(4, 8)) if easy else float(rng.uniform(3.2, 4))
    deposits = _bank(s, account, start, days, weekly * ratio, sundays=easy, label=True)
    owner = s.label(s.person(), "owner", core=False)
    s.owns(owner, company, band="75-100", start=opened_before(rng, start, 300, 3000))
    s.director(owner, company, start=opened_before(rng, start, 300, 3000))
    relative = s.label(s.person(), "relative", core=False)
    s.family(owner, relative, "spouse")
    targets = [
        s.account(owner, opened=opened_before(rng, start, 300, 3000)),
        s.account(relative, opened=opened_before(rng, start, 300, 3000)),
    ]
    banked = sum(float(s.ctx.record(p)["properties"]["amount"][0]) for p in deposits)
    _pay_on(s, account, targets, banked * (0.7 if easy else 0.33), start, days, label=True)
    s.finish(
        variant,
        difficulty,
        {"district": district, "sector": sector, "ratio": round(ratio, 2)},
        {"peer_ratio_at_least": 3.0},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    district, sector = _area(s)
    days = SPAN_DAYS
    weekly = float(rng.uniform(1500, 4000))
    _peers(s, district, sector, start, days, weekly)
    company, account = _business(s, district, sector, start)
    s.label(company, "business")
    s.label(account, "receiving_account")
    if kind == "busy_business":
        deposits = _bank(
            s,
            account,
            start,
            days,
            weekly * float(rng.uniform(1.5, 2.5)),
            sundays=False,
            label=True,
        )
    else:
        deposits = _bank(
            s,
            account,
            start,
            days,
            weekly * 1.3,
            sundays=False,
            label=True,
            boost_from=start + timedelta(days=days // 2),
            boost=2.0,
        )
    supplier = s.company(incorporated=opened_before(rng, start, 1000, 6000), sector="wholesale")
    supplier_account = s.account(supplier, opened=opened_before(rng, start, 500, 4000))
    banked = sum(float(s.ctx.record(p)["properties"]["amount"][0]) for p in deposits)
    _pay_on(s, account, [supplier_account], banked * 0.6, start, days, label=False)
    s.finish(kind, "", {"district": district, "sector": sector})
```

### `ingest/tests/test_synth_v1.py`

Verbatim. Python, 169 lines. SHA-256 `9b96f85437f42040df024141fcb41ac1e5513408a8bfe53cea9808af8672b8a6`.

```python
import json
from datetime import UTC, date, datetime

import pytest
from names_simple import SimpleNames
from neonradar_ingest.synth import labels, overlay, world, writer
from neonradar_ingest.synth.ctx import Ctx, ScenarioCtx
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.namesource import default_names
from neonradar_ingest.synth.streams import stream

SMALL = world.WorldConfig(companies=60, people=90, agent_every=30, professional_every=30)
KINDS = {"nr_synthetic": "synthetic"}
NAME_KEYS = ("name", "full", "street", "city", "gender")  # what a name source decides


def _overlay(seed: int, names=None, **kw):
    names = names or default_names()
    base = world.generate(seed, SMALL, names)
    cfg = overlay.OverlayConfig(
        seed, illicit=kw.pop("illicit", 2), lookalikes=kw.pop("lookalikes", 2), **kw
    )
    return base, overlay.generate(base, KINDS, cfg, names)


def test_streams_depend_only_on_their_keys():
    a = stream(7, "background", "x").integers(0, 10**9, size=3).tolist()
    stream(7, "other").integers(0, 10**9, size=100)
    assert stream(7, "background", "x").integers(0, 10**9, size=3).tolist() == a
    assert stream(8, "background", "x").integers(0, 10**9, size=3).tolist() != a
    with pytest.raises(ValueError):
        stream(-1, "x")


def test_same_seed_same_bytes():
    _, a = _overlay(11)
    _, b = _overlay(11)
    assert writer.record_lines(a.records) == writer.record_lines(b.records)
    la = labels.files(a.labels, seed=11, record_sha256={}, generator_version="1.0.0")
    lb = labels.files(b.labels, seed=11, record_sha256={}, generator_version="1.0.0")
    assert la == lb
    assert la["scenarios.csv"].startswith(
        "# synthetic: true\n# label_schema: 2.0.0\nscenario_id,typology,variant,"
    )


def _strip_names(records):
    out = []
    for r in records:
        props = {k: v for k, v in r["properties"].items() if k not in NAME_KEYS}
        out.append({**r, "properties": props})
    return out


def test_names_never_move_a_structural_draw():
    base_a, a = _overlay(12)
    base_b, b = _overlay(12, SimpleNames())
    assert _strip_names(base_a) == _strip_names(base_b)
    assert _strip_names(a.records) == _strip_names(b.records)
    assert (
        a.labels.transactions == b.labels.transactions
        and a.labels.participants == b.labels.participants
    )


def test_bridge_rules_and_no_labels_in_records():
    base, ov = _overlay(13)
    base_ids = {r["id"] for r in base}
    records = ov.records
    for r in records:
        assert (
            r["id"].startswith("syn-ov-")
            and r["datasets"] == ["nr_synthetic"]
            and r["nr"]["synthetic"] is True
        )
        text = json.dumps(r).casefold()
        assert not any(
            word in text for word in ("scenario", "typology", "illicit", "lookalike", "scn-")
        )
    holdings = [
        r for r in records if r["schema"] == "Ownership" and r["properties"]["owner"][0] in base_ids
    ]
    assert holdings and all(r["properties"]["role"] == ["account holder"] for r in holdings)
    payments = [r for r in records if r["schema"] == "Payment"]
    base_held = {r["properties"]["asset"][0] for r in holdings}
    assert not any(
        r["properties"]["payerAccount"][0] in base_held
        and r["properties"]["beneficiaryAccount"][0] in base_held
        for r in payments
    )
    doctored = {r["id"]: r for r in records}
    rogue = dict(next(r for r in records if r["schema"] == "Directorship"))
    rogue = {
        **rogue,
        "id": "syn-ov-dir-rogue",
        "properties": {**rogue["properties"], "organization": [sorted(base_ids)[0]]},
    }
    doctored[rogue["id"]] = rogue
    with pytest.raises(ValueError, match="I15"):
        overlay.check_bridge(doctored.values(), base_ids, set())
    base_address = next(r["id"] for r in base if r["schema"] == "Address")
    company = next(r for r in records if r["schema"] == "Company")
    moved = {**company, "properties": {**company["properties"], "addressEntity": [base_address]}}
    with pytest.raises(ValueError, match="I15"):
        overlay.check_bridge([moved], base_ids, set())
    pay = next(r for r in payments if r["properties"]["payerAccount"][0] not in base_held)
    named = {**pay, "properties": {**pay["properties"], "payer": [sorted(base_ids)[0]]}}
    with pytest.raises(ValueError, match="names a base entity"):
        overlay.check_bridge([named], base_ids, base_held)


def test_scenarios_never_reach_base_entities():
    period = Period(datetime(2025, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))
    ctx = Ctx(5, period, default_names(), base_ids={"syn-w-co-000001"})
    s = ScenarioCtx(ctx, "scn-000001", "shell_chain", lookalike=False)
    mine = s.company(incorporated=date(2020, 1, 1))
    with pytest.raises(PermissionError):
        s.owns("syn-w-co-000001", mine, band="75-100")
    with pytest.raises(PermissionError):
        s.label("syn-w-co-000001", "layer")


def test_every_scenario_fits_its_period_and_labels_something():
    for seed in (1, 2, 3):
        _, ov = _overlay(seed, illicit=3, lookalikes=3)
        by = {}
        for row in ov.labels.scenarios:
            by.setdefault(row["typology"], []).append(row)
        assert set(by) == set(overlay.SCENARIOS)
        parts = {row["scenario_id"] for row in ov.labels.participants}
        assert {row["scenario_id"] for row in ov.labels.scenarios} == parts
        assert {row["tx_id"] for row in ov.labels.transactions} <= set(ov.payments)


def test_a_merged_entity_with_a_list_record_gets_no_account(tmp_path):
    """With the base's resolution run, a company merged with a list record is not eligible, and a
    merged pair of registry records gets one account, through its anchor (`BaseView`)."""
    from neonradar_ingest.synth.base import BaseView

    def company(rid: str, dataset: str) -> dict:
        props = {"name": [f"Test Company {rid[-3:]}"], "jurisdiction": ["gb"]}
        return {"id": rid, "schema": "Company", "datasets": [dataset], "properties": props}

    records = [
        company("gbch-co-T0000101", "gb_companies_house"),
        company("uksl-gT0000101", "gb_fcdo_sanctions"),
        company("gbch-co-T0000102", "gb_companies_house"),
        company("gleif-T0000102", "gleif_golden_copy"),
    ]
    kinds = {
        "gb_companies_house": "registry",
        "gleif_golden_copy": "registry",
        "gb_fcdo_sanctions": "list",
    }
    canonical = tmp_path / "canonical.csv"
    canonical.write_text(
        "record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,"
        "path_methods,features\n"
        "gbch-co-T0000101,nr-gbch-co-T0000101,org,2,anchor,,1.0,,,\n"
        "uksl-gT0000101,nr-gbch-co-T0000101,org,2,deterministic,,1.0,,,\n"
        "gbch-co-T0000102,nr-gbch-co-T0000102,org,2,anchor,,1.0,,,\n"
        "gleif-T0000102,nr-gbch-co-T0000102,org,2,deterministic,,1.0,,,\n",
        encoding="utf-8",
    )
    view = BaseView.from_records(records, kinds, canonical)
    assert [o.id for o in view.eligible] == ["gbch-co-T0000102"]
    assert view.skipped == {"list_or_leak_record": 1}
    unresolved = BaseView.from_records(records, kinds)
    assert len(unresolved.eligible) == 3  # without the run, each record stands alone
```

### `ingest/tests/names_simple.py`

Verbatim. Python, 24 lines. SHA-256 `fe57da82f377d7d0fe20d671db05a4e1f7243c01c9f4c32720ffaad9d8651559`.

```python
"""A second NameSource for the name-independence test: plain invented words, no Faker."""

import numpy as np


class SimpleNames:
    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        return [
            f"Testperson {int(rng.integers(10**9))}"
        ], "female" if rng.random() < 0.5 else "male"

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        return [
            f"Testlisted {int(rng.integers(10**9))}"
        ], "female" if rng.random() < 0.5 else "male"

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str:
        return f"Testcompany {int(rng.integers(10**9))} Ltd"

    def street(self, rng: np.random.Generator) -> str:
        return f"Teststreet {int(rng.integers(10**6))}"

    def town(self, rng: np.random.Generator) -> str:
        return f"Testtown {int(rng.integers(10**6))}"
```

### `ingest/tests/conftest.py`

Reference. Python, 5 lines. SHA-256 `8d60e8ad7214d7a518609947906abea1517ea3d21085f32c5eb8b8237905f51d`.

M3.3 merges these lines into the ingest tests' conftest (helpers sit next to the tests).

```python
import sys
from pathlib import Path

# test helpers sit next to the tests (pytest runs with --import-mode=importlib)
sys.path.insert(0, str(Path(__file__).resolve().parent))
```

### `ingest/profiles/synth-eval.yaml`

Verbatim. YAML, 36 lines. SHA-256 `51c1be08b412f67c97af0086d8bb9e98095caecae4fee54c0ebfd5446ea04d0d`.

```yaml
# ingest/profiles/synth-eval.yaml (PHASE-3.md 7.11)
profile: synth-eval
description: >-
  Synthetic evaluation worlds: a synthetic register of 600 companies and 900 people, 18 months
  of ordinary background payments, and 10 planted scenarios and 10 benign look-alikes for each
  of the 14 typologies. Generated from a seed (eval/seeds.yaml); nothing is committed.
real_data: false
sources:
  nr_synthetic:
    enabled: true
    fixtures: []
    world:
      name: eval
      seed: 1                           # --seed overrides; eval/seeds.yaml lists the seeds
      companies: 600
      people: 900
      today: 2026-07-01
      agent_every: 300
      professional_every: 200
      districts: 30
resolution:
  enabled: false
overlay:
  enabled: true
  seed: null                            # null: the world's seed
  start: 2025-01-01
  end: 2026-07-01
  illicit: 10                           # per typology
  lookalikes: 10                        # per typology
  typologies: all
  background: {}                        # BackgroundConfig defaults (7.2.4)
detection:
  enabled: true
  window: overlay                       # the overlay period
  overrides:
    mass_registration_address: { top_share: 0.0 }   # 600 companies are too few for a percentile
```

### `ingest/profiles/synth-demo.yaml`

Verbatim. YAML, 37 lines. SHA-256 `3e3fdfa55a153278b7e7e8cb82a424c4a13f85c0ee3ec2f7e3902c39743d6626`.

```yaml
# ingest/profiles/synth-demo.yaml (PHASE-3.md 7.11)
profile: synth-demo
description: >-
  The synthetic demo: a small synthetic register (300 companies, 450 people) with 18 months of
  background payments and three planted scenarios and three look-alikes for each of the 14
  typologies, about 5,500 nodes and 156,000 relationships. Small enough for an 8 GB laptop or a
  Codespace. Nothing in it exists.
real_data: false
sources:
  nr_synthetic:
    enabled: true
    fixtures: []
    world:
      name: demo
      seed: 20261103
      companies: 300
      people: 450
      today: 2026-07-01
      agent_every: 150
      professional_every: 100
      districts: 15
resolution:
  enabled: false
overlay:
  enabled: true
  seed: null
  start: 2025-01-01
  end: 2026-07-01
  illicit: 3
  lookalikes: 3
  typologies: all
  background: {}
detection:
  enabled: true
  window: overlay
  overrides:
    mass_registration_address: { top_share: 0.0 }
```

### `ingest/profiles/synth-scale.yaml`

Verbatim. YAML, 36 lines. SHA-256 `ce2b8dba19ebdf2c1b78f4ce8769558f1d84f03d17053ebad42b466038f4e9a0`.

```yaml
# ingest/profiles/synth-scale.yaml (PHASE-3.md 7.11)
profile: synth-scale
description: >-
  The scale world at the plan's target: a synthetic register of 142,000 companies and 213,000
  people with background payments for 3 percent of the companies and two planted scenarios and
  two look-alikes per typology, about 500,000 nodes and 2.2 million relationships. For the load
  and query benchmark (M3.9); needs the standard memory profile.
real_data: false
sources:
  nr_synthetic:
    enabled: true
    fixtures: []
    world:
      name: scale
      seed: 20261105
      companies: 142000
      people: 213000
      today: 2026-07-01
      agent_every: 300
      professional_every: 200
      districts: 710
resolution:
  enabled: false
overlay:
  enabled: true
  seed: null
  start: 2025-01-01
  end: 2026-07-01
  illicit: 2
  lookalikes: 2
  typologies: all
  background: { share: 0.03, personal: false }
detection:
  enabled: true
  window: overlay
  overrides: {}
```

## M3.4 Overlay loading and real profiles

The two query files of L18 (5.2). 2 verbatim files (PHASE-3.md M3.4).

### `graph/src/neonradar_graph/queries/overlay_purge.cypher`

Verbatim. Cypher, 9 lines. SHA-256 `bbbbb77880d60474cfe7e429a9242fd9bc3ea35fbffb92b639ec7d7e4637772c`.

```cypher
// L18: before an overlay load, remove the previous overlay (every node whose id starts with
// syn-ov-, with its relationships, including the HOLDS_ACCOUNT links from base organisations) and
// every detection result, which an overlay change makes stale
MATCH (n:Entity) WHERE n.id STARTS WITH 'syn-ov-'
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n:Sanction) WHERE n.id STARTS WITH 'syn-ov-'
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
```

### `graph/src/neonradar_graph/queries/overlay_unresolved.cypher`

Verbatim. Cypher, 9 lines. SHA-256 `913b4840116d330cd82235872a1c749d47a98502805c20f65ac4c3d839679cbe`.

```cypher
// L18: the base references of an overlay ($refs: every id an overlay record names that is not an
// overlay id) that resolve to no node, directly or through a source record (L13); the loader
// stops before writing when the count is not zero
UNWIND $refs AS ref
OPTIONAL MATCH (direct:Entity {id: ref})
OPTIONAL MATCH (:SourceRecord {id: ref})-[:RESOLVED_TO]->(via:Entity)
WITH ref, coalesce(direct, via) AS node
WHERE node IS NULL
RETURN count(ref) AS unresolved;
```

## M3.5a Cash deposits and pass-through: `structuring`, `rapid_pass_through`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 6 verbatim files (PHASE-3.md M3.5a).

### `detect/src/neonradar_detect/detectors/structuring.py`

Verbatim. Python, 146 lines. SHA-256 `ea730d3c399cdbd2bbe187eba8be88e3216292db5dea32a2ffc5bed64bd844b0`.

```python
"""structuring 0.2.0: several cash deposits just below a threshold, within a few days, into the
accounts of one holder (PHASE-1.md 7.2 entry 1, corrected by `typology-detection-definitions.md`
section 1; PHASE-3.md 7.3.1).

The threshold is `threshold` in the deposit's currency. Whether a deposit of exactly the threshold
counts as below it depends on the rule the threshold stands for: the US report covers cash "of
more than $10,000" (31 CFR 1010.311), so 10,000 exactly is below it. GBP is modelled on the UK
high value dealer rule ("£10,000 or more", MLR 2017 reg 27(3)) and EUR on the AMLR's due diligence
threshold ("at least EUR 10 000", from 10 July 2027), so there it is not; both mappings are
modelling choices (7.3.1). `below_inclusive_currencies` lists the currencies that use the US form.
A deposit is in band when `threshold * (1 - band) <= amount` and it is below the threshold.

For each holder and currency, a window of `window_days` starting at a deposit qualifies when it
holds at least `min_deposits` in-band deposits and in-band deposits are at least `min_band_share` of
the holder's cash deposits in it. A daily total above the threshold is not required (the US
definition covers amounts that "need not exceed" it "on any single day"): it adds to the strength.
Overlapping qualifying windows merge into one finding.

pattern_strength = 0.3 * min(1, deposits / (2 * min_deposits)) + 0.3 * mean closeness to the
threshold (0 at the lower edge of the band, 1 at the threshold) + 0.2 * min(1, (branches - 1) / 2)
+ 0.2 if some day's in-band total exceeds the threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Deposit, HolderDeposits
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "structuring"
VERSION = "0.2.0"
QUERIES = ("holder_cash_deposits.cypher",)


@dataclass(frozen=True, slots=True)
class Params:
    threshold: float = 10000.0
    band: float = 0.1
    below_inclusive_currencies: tuple[str, ...] = ("USD",)
    window_days: int = 7
    min_deposits: int = 3
    min_band_share: float = 0.5
    max_candidates: int = 100_000


def in_band(amount: float, currency: str, p: Params) -> bool:
    low = p.threshold * (1 - p.band)
    if currency in p.below_inclusive_currencies:
        return low <= amount <= p.threshold
    return low <= amount < p.threshold


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    band_low = p.threshold * (1 - p.band)
    candidates = source.holder_cash_deposits(
        band_low, p.threshold, p.min_deposits, window.start, window.end, p.max_candidates
    )
    findings: dict[tuple[str, ...], Finding] = {}
    for cand in candidates:
        for f in _evaluate(cand, p):
            findings.setdefault(f.edge_ids, f)  # a joint account appears under each holder
    ordered = sorted(
        findings.values(), key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids)
    )
    return DetectorOutput(ordered, {"candidates": len(candidates)})


def _evaluate(cand: HolderDeposits, p: Params) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    for currency in sorted({d.currency for d in cand.deposits}):
        deps = [d for d in cand.deposits if d.currency == currency]
        spans: list[tuple[int, int]] = []
        j = 0
        for i, d in enumerate(deps):
            j = max(j, i)
            while j + 1 < len(deps) and deps[j + 1].ts < d.ts + span:
                j += 1
            banded = [x for x in deps[i : j + 1] if in_band(x.amount, currency, p)]
            if len(banded) >= p.min_deposits and len(banded) / (j - i + 1) >= p.min_band_share:
                spans.append((i, j))
        for i, j in _merge(spans):
            out.append(_finding(cand.holder, deps[i : j + 1], currency, p))
    return out


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for i, j in sorted(spans):
        if merged and i <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], j))
        else:
            merged.append((i, j))
    return merged


def _finding(holder: str, window_deps: list[Deposit], currency: str, p: Params) -> Finding:
    band_low = p.threshold * (1 - p.band)
    banded = [d for d in window_deps if in_band(d.amount, currency, p)]
    total = sum(d.amount for d in banded)
    branches = sorted({d.branch for d in banded})
    accounts = sorted({d.account for d in banded})
    by_day: dict[str, list[Deposit]] = {}
    for d in banded:
        by_day.setdefault(d.ts.date().isoformat(), []).append(d)
    day_totals = {day: sum(d.amount for d in ds) for day, ds in by_day.items()}
    closeness = sum((d.amount - band_low) / (p.threshold - band_low) for d in banded) / len(banded)
    above = any(t > p.threshold for t in day_totals.values())
    strength = clip01(
        0.3 * min(1.0, len(banded) / (2 * p.min_deposits))
        + 0.3 * min(1.0, closeness)
        + 0.2 * min(1.0, (len(branches) - 1) / 2)
        + (0.2 if above else 0.0)
    )
    first, last = banded[0].ts, banded[-1].ts
    metrics = {
        "deposits": len(banded),
        "total_amount": round(total, 2),
        "threshold": p.threshold,
        "band_low": round(band_low, 2),
        "currency": currency,
        "branches": len(branches),
        "accounts": len(accounts),
        "days": len(by_day),
        "span_days": max(1, math.ceil((last - first).total_seconds() / 86400)),
        "max_day_total": round(max(day_totals.values()), 2),
        "band_share": round(len(banded) / len(window_deps), 4),
    }
    subjects = [Subject(holder, "holder")] + [Subject(a, "receiving_account") for a in accounts]
    return Finding(
        typology=SLUG,
        variant="multi_account" if len(accounts) > 1 else "single_account",
        anchor=accounts[0],
        node_ids=tuple(sorted(set(accounts) | set(branches))),
        edge_ids=tuple(sorted(d.edge_id for d in banded)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(tuple(d.edge_id for d in ds) for _, ds in sorted(by_day.items())),
        window=(first, last),
        activity=True,
    )
```

### `detect/src/neonradar_detect/detectors/rapid_pass_through.py`

Verbatim. Python, 212 lines. SHA-256 `85c602b926e3a4029b61b6e7ce57751f967870ab6e5e9792d7978cc04be1f0b9`.

```python
"""rapid_pass_through 0.2.0: an account that passes on what it receives within hours or days,
from several sources (PHASE-1.md 7.2 entry 2; `typology-detection-definitions.md` section 2;
PHASE-3.md 7.3.2).

Per account and currency, inflows are matched to later outflows first in, first out, over the
window and the `history_days` before it, so money an account already held is spent before new
money (a business with a working balance does not pass on what it has just received); the part of
an inflow that leaves within `max_dwell_hours` of arriving counts as passed through (money is
fungible, so this allocation is a modelling choice, not a fact). Windows that start less than
`history_days` after the first payment in the data are skipped: there the earlier balance is
unknown (left-censoring). A window of `window_days` starting at an inflow qualifies when its
inflows total at least `min_inflow`, at least `min_pass_ratio` of that total was passed through,
and the inflows came from at least `min_sources` accounts. Few
beneficiaries make the pattern stronger but are not required ("a small number of foreign
beneficiaries" is a red flag, not the definition). Among qualifying windows the detector takes the
one with the largest passed amount, then the largest that overlaps no window already taken, and so
on, so findings never share an inflow.

pattern_strength = 0.35 * pass ratio + 0.3 * (1 - median dwell / max_dwell_hours)
+ 0.15 * min(1, sources / (2 * min_sources)) + 0.2 * concentration, where concentration is 1 with
at most `max_beneficiaries` beneficiaries and max_beneficiaries / beneficiaries above that.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "rapid_pass_through"
VERSION = "0.2.0"
QUERIES = ("flows_by_inbound.cypher", "paid_time_range.cypher")


@dataclass(frozen=True, slots=True)
class Params:
    window_days: int = 7
    max_dwell_hours: int = 72
    min_inflow: float = 10000.0
    min_pass_ratio: float = 0.9
    min_sources: int = 3
    max_beneficiaries: int = 3
    history_days: int = 90
    max_candidates: int = 100_000


def cents(amount: float) -> int:
    """Amounts carry two decimals (C1 R7), so whole cents keep every sum exact."""
    return round(amount * 100)


@dataclass(slots=True)
class _Lot:
    pay: Pay
    left: int  # cents
    passed: int = 0  # cents
    dwell_hours: list[float] = field(default_factory=list)
    out_edges: set[str] = field(default_factory=set)
    beneficiaries: set[str] = field(default_factory=set)


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.history_days))
    candidates = source.flows_by_inbound(
        math.ceil(p.min_sources / 2),
        window.start - timedelta(days=p.history_days),
        window.end,
        None,
        p.window_days * 24,
        p.max_candidates,
    )
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_evaluate(flows, judged_from, p))
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates)})


def _match(flows: AccountFlows, currency: str, p: Params) -> list[_Lot]:
    """FIFO matching of outflows to earlier inflows of one currency."""
    dwell = timedelta(hours=p.max_dwell_hours)
    events = [(x.ts, 0, x) for x in flows.inflows if x.currency == currency]
    events += [(x.ts, 1, x) for x in flows.outflows if x.currency == currency]
    events.sort(key=lambda e: (e[0], e[1], e[2].edge_id))
    lots: list[_Lot] = []
    queue: list[_Lot] = []
    for _, kind, pay in events:
        if kind == 0:
            lot = _Lot(pay, cents(pay.amount))
            lots.append(lot)
            queue.append(lot)
            continue
        need = cents(pay.amount)
        while need > 0 and queue:
            lot = queue[0]
            take = min(lot.left, need)
            lot.left -= take
            need -= take
            if pay.ts - lot.pay.ts <= dwell:
                lot.passed += take
                lot.dwell_hours.append((pay.ts - lot.pay.ts).total_seconds() / 3600)
                lot.out_edges.add(pay.edge_id)
                lot.beneficiaries.add(pay.counterparty)
            if lot.left == 0:
                queue.pop(0)
    return lots


def _evaluate(flows: AccountFlows, judged_from: datetime, p: Params) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    for currency in sorted({x.currency for x in flows.inflows}):
        lots = _match(flows, currency, p)
        windows = [w for w in _windows(lots, span, p) if lots[w[1]].pay.ts >= judged_from]
        chosen: list[tuple[int, int]] = []
        for _, i, j in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
        for i, j in sorted(chosen):
            out.append(_finding(flows, lots[i:j], currency, p))
    return out


def _windows(lots: list[_Lot], span: timedelta, p: Params) -> list[tuple[int, int, int]]:
    """Qualifying windows as (passed cents, first lot, end lot), two pointers over time order."""
    sources: Counter[str] = Counter()
    beneficiaries: Counter[str] = Counter()
    inflow = passed = 0
    found = []
    j = 0
    for i, lot in enumerate(lots):
        while j < len(lots) and lots[j].pay.ts < lot.pay.ts + span:
            inflow += cents(lots[j].pay.amount)
            passed += lots[j].passed
            sources[lots[j].pay.counterparty] += 1
            beneficiaries.update(lots[j].beneficiaries)
            j += 1
        if (
            inflow >= cents(p.min_inflow)
            and passed >= p.min_pass_ratio * inflow
            and len(sources) >= p.min_sources
            and len(beneficiaries) > 0
        ):
            found.append((passed, i, j))
        inflow -= cents(lot.pay.amount)
        passed -= lot.passed
        sources[lot.pay.counterparty] -= 1
        if sources[lot.pay.counterparty] == 0:
            del sources[lot.pay.counterparty]
        beneficiaries.subtract(lot.beneficiaries)
        beneficiaries = +beneficiaries
    return found


def _finding(flows: AccountFlows, lots: list[_Lot], currency: str, p: Params) -> Finding:
    inflow = sum(cents(lot.pay.amount) for lot in lots) / 100
    passed = sum(lot.passed for lot in lots) / 100
    sources = sorted({lot.pay.counterparty for lot in lots})
    beneficiaries = sorted(set().union(*(lot.beneficiaries for lot in lots)))
    dwells = sorted(h for lot in lots for h in lot.dwell_hours)
    median_dwell = statistics.median(dwells) if dwells else float(p.max_dwell_hours)
    out_edges = sorted(set().union(*(lot.out_edges for lot in lots)))
    in_edges = sorted(lot.pay.edge_id for lot in lots)
    ratio = passed / inflow
    concentration = (
        1.0
        if len(beneficiaries) <= p.max_beneficiaries
        else p.max_beneficiaries / len(beneficiaries)
    )
    strength = clip01(
        0.35 * min(1.0, ratio)
        + 0.3 * (1 - min(1.0, median_dwell / p.max_dwell_hours))
        + 0.15 * min(1.0, len(sources) / (2 * p.min_sources))
        + 0.2 * concentration
    )
    first = min(lot.pay.ts for lot in lots)
    last_out = max((x.ts for x in flows.outflows if x.edge_id in set(out_edges)), default=first)
    metrics = {
        "inflow_amount": round(inflow, 2),
        "passed_amount": round(passed, 2),
        "pass_ratio": round(ratio, 4),
        "currency": currency,
        "sources": len(sources),
        "beneficiaries": len(beneficiaries),
        "median_dwell_hours": round(median_dwell, 1),
        "window_days": p.window_days,
    }
    subjects = [Subject(flows.account, "pass_through_account")]
    subjects += [Subject(h, "holder") for h in flows.holders]
    in_steps = tuple((e,) for e in in_edges)
    return Finding(
        typology=SLUG,
        variant="",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *sources, *beneficiaries})),
        edge_ids=tuple(sorted(set(in_edges) | set(out_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(*in_steps, tuple(out_edges)),
        window=(first, last_out),
        activity=True,
    )
```

### `detect/typologies/structuring.yaml`

Verbatim. YAML, 76 lines. SHA-256 `14eb480cfec35c5702cf13a84e86eed67270cbdc0802b663fd0c8eaed50c6d69`.

```yaml
slug: structuring
name: Structuring cash deposits
shape_name: cash deposits just below a threshold
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  Several cash deposits just below a threshold (10,000 in the deposit's currency), within a few days, into the
  accounts of one holder.
doc: docs/typologies/structuring.md
citations:
- cfr_31_1010_100_2026
- cfr_31_1010_311_2026
- cfr_31_1010_313_2026
- cfr_31_1010_314
- ffiec_appendix_g
- fincen_fin_2014_a005
- mlr_reg_27_2017
graph_pattern: >-
  Cash deposits (PAID from cash ledger accounts) into the accounts of one LegalEntity, at least three in a 7-day
  window, within 10 percent below the threshold.
parameters:
  threshold:
    default: 10000.0
    min: 0.0
    max: 100000.0
  band:
    default: 0.1
    min: 0.0
    max: 0.5
  below_inclusive_currencies:
    default:
    - USD
  window_days:
    default: 7
    min: 1
    max: 70
  min_deposits:
    default: 3
    min: 1
    max: 30
  min_band_share:
    default: 0.5
    min: 0.0
    max: 1.0
  max_candidates:
    default: 100000
    min: 1
    max: 1000000
metrics:
- deposits
- total_amount
- threshold
- band_low
- currency
- branches
- accounts
- days
- span_days
- max_day_total
- band_share
wording:
  headline_structural: >-
    {deposits} cash deposits just below {threshold|money} within {span_days|n:day}, {total_amount|money} in total
  headline_synthetic: >-
    Synthetic scenario: {deposits} cash deposits just below {threshold|money} within {span_days|n:day}, {total_amount|money}
    in total
false_positives:
- A cash business banking its daily takings
- A business that caps each cash deposit (an insurer's or a carrier's limit; no source confirmed this)
- A person saving the same sum every week
synthetic_support: high
generator_scenario: structuring
detector: neonradar_detect.detectors.structuring
```

### `detect/typologies/rapid_pass_through.yaml`

Verbatim. YAML, 72 lines. SHA-256 `8c31862c3b45cb3be28e18eaa80555c56ee7116b235f50ab77497efa9381d9d8`.

```yaml
slug: rapid_pass_through
name: Rapid pass-through
shape_name: funds paid on soon after they arrive
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: An account that pays on what it receives within hours or days, from several sources.
doc: docs/typologies/rapid-pass-through.md
citations:
- ffiec_appendix_f
- fincen_fin_2014_a005
- fatf_pml_2018
graph_pattern: >-
  Inflows to one Account from at least three accounts in a 7-day window, at least 90 percent of which leave within
  72 hours (first in, first out, after earlier balances).
parameters:
  window_days:
    default: 7
    min: 1
    max: 70
  max_dwell_hours:
    default: 72
    min: 1
    max: 720
  min_inflow:
    default: 10000.0
    min: 0.0
    max: 100000.0
  min_pass_ratio:
    default: 0.9
    min: 0.0
    max: 1.0
  min_sources:
    default: 3
    min: 1
    max: 30
  max_beneficiaries:
    default: 3
    min: 1
    max: 30
  history_days:
    default: 90
    min: 1
    max: 900
  max_candidates:
    default: 100000
    min: 1
    max: 1000000
metrics:
- inflow_amount
- passed_amount
- pass_ratio
- currency
- sources
- beneficiaries
- median_dwell_hours
- window_days
wording:
  headline_structural: >-
    {pass_ratio|pct} of {inflow_amount|money} received from {sources|n:account} paid on within {window_days|n:day}
  headline_synthetic: >-
    Synthetic scenario: {pass_ratio|pct} of {inflow_amount|money} received from {sources|n:account} paid on within
    {window_days|n:day}
false_positives:
- Payroll bureaus funding salaries
- Marketplaces settling with sellers
- Escrow and client accounts
synthetic_support: high
generator_scenario: rapid_pass_through
detector: neonradar_detect.detectors.rapid_pass_through
```

### `detect/tests/test_detector_structuring.py`

Verbatim. Python, 116 lines. SHA-256 `5488e2587f2b76adf53df045ef1ff48bcce77e575868b9c022ddcedc6a4d661a`.

```python
from datetime import UTC, datetime

from kit import Kit, detect, source_of
from neonradar_detect.detectors import structuring as st
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _branches(k: Kit, n: int = 3) -> list[str]:
    bank = k.company("bank", "Fixture Bank plc")
    return [k.account(f"branch{i}", bank, kind="cash_ledger") for i in range(n)]


def _run(k: Kit, **overrides):
    return st.run(source_of(k.records), st.Params(**overrides), WINDOW).findings


def test_burst_below_threshold_across_branches():
    k = Kit()
    b = _branches(k)
    acct = k.account("s1", k.company("s1"))
    e = [
        k.pay(b[0], acct, 9500, "2026-03-02T10:00", channel="cash_deposit"),
        k.pay(b[1], acct, 9700, "2026-03-02T15:00", channel="cash_deposit"),
        k.pay(b[2], acct, 9300, "2026-03-03T11:00", channel="cash_deposit"),
        k.pay(b[0], acct, 9800, "2026-03-04T09:30", channel="cash_deposit"),
    ]
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted(e))
    assert f.metrics["deposits"] == 4 and f.metrics["total_amount"] == 38300.0
    assert (
        f.metrics["branches"] == 3
        and f.metrics["days"] == 3
        and f.metrics["max_day_total"] == 19200.0
    )
    assert f.variant == "single_account" and len(f.steps) == 3


def test_two_accounts_of_one_holder():
    k = Kit()
    b = _branches(k, 2)
    holder = k.company("s2")
    a1, a2 = k.account("s2a", holder), k.account("s2b", holder)
    k.pay(b[0], a1, 9400, "2026-04-06T10:00", channel="cash_deposit")
    k.pay(b[1], a2, 9600, "2026-04-06T12:00", channel="cash_deposit")
    k.pay(b[0], a2, 9900, "2026-04-07T10:00", channel="cash_deposit")
    [f] = _run(k)
    assert f.variant == "multi_account" and f.metrics["accounts"] == 2
    assert [s.role for s in f.subjects] == ["holder", "receiving_account", "receiving_account"]


def test_lookalikes_are_not_found():
    k = Kit()
    b = _branches(k, 1)
    shop = k.account("shop", k.company("shop", sector="retail"))
    amounts = [3200, 12500, 9100, 4100, 15000, 2800, 11000, 6400, 9900, 7300, 13800, 5100]
    for day, amount in enumerate(amounts, start=2):
        k.pay(b[0], shop, amount, f"2026-02-{day:02d}T18:00", channel="cash_deposit")
    saver = k.account("saver", k.person("saver"))
    for week in range(8):
        k.pay(
            b[0],
            saver,
            9500,
            f"2026-03-{2 + 7 * week:02d}T12:00"
            if 2 + 7 * week <= 31
            else f"2026-04-{2 + 7 * week - 31:02d}T12:00",
            channel="cash_deposit",
        )
    two = k.account("two", k.company("two"))
    k.pay(b[0], two, 9500, "2026-05-04T10:00", channel="cash_deposit")
    k.pay(b[0], two, 9500, "2026-05-04T14:00", channel="cash_deposit")
    assert _run(k) == []


def test_band_edges():
    k = Kit()
    b = _branches(k, 1)
    acct = k.account("edge", k.company("edge"))
    k.pay(b[0], acct, 9000.00, "2026-06-01T10:00", channel="cash_deposit")  # lower edge: in band
    k.pay(b[0], acct, 9999.99, "2026-06-01T11:00", channel="cash_deposit")
    k.pay(
        b[0], acct, 10000.00, "2026-06-01T12:00", channel="cash_deposit"
    )  # at the threshold: not in band
    assert _run(k) == []  # two in band out of three: below min_deposits
    k.pay(b[0], acct, 9500.00, "2026-06-02T12:00", channel="cash_deposit")
    [f] = _run(k)
    assert f.metrics["deposits"] == 3 and f.metrics["band_share"] == 0.75


def test_a_usd_deposit_of_exactly_the_threshold_is_below_it():
    """31 CFR 1010.311 covers cash "of more than $10,000"; GBP and EUR are modelled on "or more"."""
    k = Kit()
    b = _branches(k, 1)
    usd = k.account("usd", k.company("usd"), currency="USD")
    gbp = k.account("gbp", k.company("gbp"))
    for day in range(3):
        when = f"2026-06-0{2 + day}T10:00"
        k.pay(b[0], usd, 10000, when, channel="cash_deposit", currency="USD")
        k.pay(b[0], gbp, 10000, when, channel="cash_deposit")
    [f] = _run(k)
    assert f.anchor == usd and f.metrics["currency"] == "USD" and f.metrics["deposits"] == 3


def test_headline_through_the_runner():
    k = Kit()
    acct = k.account("dep", k.person("depositor"))
    branch = k.account("branch", k.company("bank"), kind="cash_ledger")
    for d, amount in enumerate((9500, 9800, 9700, 9900)):
        k.pay(branch, acct, amount, f"2026-04-0{1 + d}T11:00", channel="cash_deposit")
    [alert] = detect(k.records, {"structuring": st.Params()}).alerts
    assert alert["headline"] == (
        "Synthetic scenario: 4 cash deposits just below GBP 10,000 within 3 days, "
        "GBP 38,900 in total"
    )
```

### `detect/tests/test_detector_rapid_pass_through.py`

Verbatim. Python, 77 lines. SHA-256 `b110efc82553e63d0451c1351ff099793123f1bde826521d3f78828e2a281da5`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import rapid_pass_through as rp
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    if not any(r["id"] == "syn-fx-acct-hist-a" for r in k.records):
        k.history()  # data from 2025-10-01: the 90-day history before the window is known
    return rp.run(source_of(k.records), rp.Params(**overrides), WINDOW).findings


def _senders(k: Kit, tag: str, n: int) -> list[str]:
    return [k.account(f"{tag}s{i}", k.person(f"{tag}s{i}")) for i in range(n)]


def test_funnel_found_and_slow_dwell_not():
    k = Kit()
    hub = k.account("hub", k.company("hub"))
    out = k.account("dest", k.company("dest", jurisdiction="ae"))
    ins = [
        k.pay(s, hub, 6000, f"2026-03-0{2 + i % 2}T1{i}:00")
        for i, s in enumerate(_senders(k, "a", 4))
    ]
    o = k.pay(hub, out, 23500, "2026-03-04T09:00")
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted([*ins, o]))
    assert (
        f.metrics["pass_ratio"] == 0.9792
        and f.metrics["sources"] == 4
        and f.metrics["beneficiaries"] == 1
    )
    slow = Kit()
    hub2 = slow.account("hub", slow.company("hub"))
    out2 = slow.account("dest", slow.company("dest"))
    for i, s in enumerate(_senders(slow, "b", 4)):
        slow.pay(s, hub2, 6000, f"2026-03-02T1{i}:00")
    slow.pay(hub2, out2, 23500, "2026-03-09T09:00")
    assert _run(slow) == []


def test_lookalikes():
    k = Kit()
    bureau = k.account("bureau", k.company("bureau"))
    client = k.account("client", k.company("client"))
    k.pay(client, bureau, 30000, "2026-04-01T09:00")
    for i in range(20):
        k.pay(bureau, k.account(f"emp{i}", k.person(f"emp{i}")), 1450, "2026-04-01T15:00")
    escrow = k.account("escrow", k.company("escrow"))
    for i, s in enumerate(_senders(k, "e", 3)):
        k.pay(s, escrow, 10000, f"2026-04-0{i + 1}T10:00")
    k.pay(escrow, k.account("seller", k.company("seller")), 29900, "2026-05-15T10:00")
    assert _run(k) == []
    # a marketplace settlement account has the same shape and is found (documented false positive)
    market = k.account("market", k.company("market"))
    merchant = k.account("merchant", k.company("merchant"))
    for i, s in enumerate(_senders(k, "m", 10)):
        k.pay(s, market, 3000, f"2026-06-0{1 + i % 3}T1{i % 9}:00")
    k.pay(market, merchant, 29000, "2026-06-04T08:00")
    [f] = _run(k)
    assert f.anchor == market


def test_two_bursts_give_two_findings():
    k = Kit()
    hub = k.account("hub", k.company("hub"))
    dest = k.account("dest", k.company("dest"))
    senders = _senders(k, "t", 3)
    for day in (2, 20):
        for i, s in enumerate(senders):
            k.pay(s, hub, 8000, f"2026-02-{day:02d}T1{i}:00")
        k.pay(hub, dest, 23900, f"2026-02-{day + 1:02d}T10:00")
    found = _run(k)
    assert len(found) == 2 and found[0].window[0] < found[1].window[0]
```

## M3.5b Registry patterns: `mass_registration_address`, `shell_chain`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 6 verbatim files (PHASE-3.md M3.5b).

### `detect/src/neonradar_detect/detectors/mass_registration_address.py`

Verbatim. Python, 185 lines. SHA-256 `f1b8c1d172c92e2df801aa2ddafcbda614e9b9a2a4c59f67d60e6397f5eb69f1`.

```python
"""mass_registration_address 0.2.0: many active organisations registered at one address, with the
signals that set a formation factory apart from an ordinary registered agent (PHASE-1.md 7.2
entry 9, corrected by `typology-detection-definitions.md` section 9; PHASE-3.md 7.3.9).

An address qualifies when at least `min_companies` active organisations (no dissolution date, and
a status that is not an inactive one) have it as their registered address and, when `top_share`
is set, its count is at least the nearest-rank (1 - `top_share`) quantile of the counts of all
loaded addresses ("in the top 0.1 percent"). Small synthetic worlds set `top_share` to 0 in their
profile: a quantile over a few thousand addresses would leave only the largest one. The three
Companies House default addresses (by postcode, `exclude_postcodes`) are never findings: companies
are moved there when their own address was not appropriate (Registrar's Rules, Volume 6).

The strength adds four signals: incorporations in bursts (the most organisations incorporated
within `burst_days` of each other, as a share of all), directors shared between organisations at
the address (current directorships only: no end date, or one after the end of the window),
payments among their accounts ("Transacting businesses share the same address", FinCEN; only
when every organisation at the address is synthetic, R-REAL), and a PO box address (Annex E's
"Only a post-box address"; for UK companies, Companies House has also refused PO boxes as
registered offices since 4 March 2024). The evidence
holds at most `max_evidence_companies` organisations (those in the largest burst first, then by
id); the metrics count all of them.

pattern_strength = 0.3 * min(1, companies / (5 * min_companies)) + 0.2 * burst share + 0.2 * share
of organisations with a shared director + 0.2 * min(1, paying pairs / 3) + 0.1 if a PO box.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AddressCluster, EntityRow, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "mass_registration_address"
VERSION = "0.2.0"
QUERIES = (
    "entities.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
    "registered_clusters.cypher",
    "registered_count_quantile.cypher",
)
DEFAULT_ADDRESS_POSTCODES = ("CF14 8LH", "EH7 9HR", "BT1 9DY")
PO_BOX = re.compile(r"\bP\.?\s?O\.?\s+BOX\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Params:
    min_companies: int = 25
    top_share: float = 0.001
    active_only: bool = True
    exclude_postcodes: tuple[str, ...] = DEFAULT_ADDRESS_POSTCODES
    burst_days: int = 30
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def normalise_postcode(value: str) -> str:
    compact = re.sub(r"\s+", "", value).upper()
    return f"{compact[:-3]} {compact[-3:]}" if len(compact) > 3 else compact


def is_po_box(cluster: AddressCluster) -> bool:
    return bool(PO_BOX.search(cluster.full))


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    threshold = p.min_companies
    if p.top_share > 0:
        threshold = max(threshold, source.registered_count_quantile(1 - p.top_share, p.active_only))
    clusters = source.registered_clusters(threshold, p.active_only, p.max_candidates)
    excluded = {normalise_postcode(x) for x in p.exclude_postcodes}
    findings = []
    skipped = 0
    for cluster in clusters:
        if normalise_postcode(cluster.postal_code) in excluded:
            skipped += 1
            continue
        findings.append(_evaluate(cluster, source, p, window))
    return DetectorOutput(
        findings,
        {"candidates": len(clusters), "threshold": threshold, "default_addresses": skipped},
    )


def _burst(members: list[str], entities: dict[str, EntityRow], days: int) -> list[str]:
    dated = sorted(
        (date.fromisoformat(entities[m].incorporation_date), m)
        for m in members
        if len(entities[m].incorporation_date) == 10
    )
    best: list[str] = []
    j = 0
    for i, (start, _) in enumerate(dated):
        while j < len(dated) and dated[j][0] <= start + timedelta(days=days):
            j += 1
        if j - i > len(best):
            best = [m for _, m in dated[i:j]]
    return best


def _evaluate(cluster: AddressCluster, source: Source, p: Params, window: Window) -> Finding:
    members = [m for m, _ in cluster.members]
    rel_of = dict(cluster.members)
    entities = source.entities(members)
    burst = _burst(members, entities, p.burst_days)
    directors = source.links_into(members, ("DIRECTOR_OF",))
    as_of = window.end.date().isoformat()
    by_director: dict[str, list[LinkRow]] = defaultdict(list)
    for m in members:
        for d in directors.get(m, []):
            if d.current(as_of):
                by_director[d.source].append(d)
    shared = {d: links for d, links in by_director.items() if len({x.target for x in links}) >= 2}
    with_shared = {x.target for links in shared.values() for x in links}
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[m].synthetic for m in members):
        for m, links in source.links_from(members, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = m
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
    pairs = {
        tuple(sorted((holder_of[a], holder_of[b])))
        for _, a, b in paying
        if holder_of[a] != holder_of[b]
    }
    n = len(members)
    po_box = is_po_box(cluster)
    strength = clip01(
        0.3 * min(1.0, n / (5 * p.min_companies))
        + 0.2 * (len(burst) / n)
        + 0.2 * (len(with_shared) / n)
        + 0.2 * min(1.0, len(pairs) / 3)
        + (0.1 if po_box else 0.0)
    )
    shown = [*burst, *sorted(set(members) - set(burst))][: p.max_evidence_companies]
    shown_set = set(shown)
    dir_links = sorted(
        (x for links in shared.values() for x in links if x.target in shown_set),
        key=lambda x: x.rel_id,
    )
    metrics = {
        "companies": n,
        "companies_shown": len(shown),
        "incorporated_in_burst": len(burst),
        "burst_days": p.burst_days,
        "shared_directors": len(shared),
        "companies_with_shared_director": len(with_shared),
        "paying_pairs": len(pairs),
        "po_box": po_box,
    }
    steps: list[tuple[str, ...]] = [tuple(sorted(rel_of[m] for m in shown))]
    if dir_links:
        steps.append(tuple(x.rel_id for x in dir_links))
    pay_edges = sorted(
        e for e, a, b in paying if holder_of.get(a) in shown_set and holder_of.get(b) in shown_set
    )
    if pay_edges:
        steps.append(tuple(pay_edges))
    shown_pay = set(pay_edges)
    pay_nodes = {x for e, a, b in paying if e in shown_pay for x in (a, b)}
    return Finding(
        typology=SLUG,
        variant="",
        anchor=cluster.address,
        node_ids=tuple(
            sorted({cluster.address, *shown, *(x.source for x in dir_links), *pay_nodes})
        ),
        edge_ids=tuple(
            sorted({rel_of[m] for m in shown} | {x.rel_id for x in dir_links} | shown_pay)
        ),
        subjects=(Subject(cluster.address, "registered_address"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
```

### `detect/src/neonradar_detect/detectors/shell_chain.py`

Verbatim. Python, 279 lines. SHA-256 `1e4712a377811494fd89b7fb60c3b30d3468e1195fe14fcef99b1c547ebd7d8b`.

```python
"""shell_chain 0.2.0: ownership of a company layered through other companies, with the concealment
indicators of FATF and Egmont 2018 Annex E (PHASE-1.md 7.2 entry 8, corrected by
`typology-detection-definitions.md` section 8; PHASE-3.md 7.3.8).

Registry evidence only, so the detector also runs on real profiles (R-REAL allows registry
patterns about organisations whose evidence names no person). Only relationships that still hold
at the end of the window count (no end date, or a later one): a resigned director or a sold
holding is history, not structure. Candidates are the maximal OWNS paths from a top owner (a node
no OWNS points to) down to a leaf company (one that owns no organisation), and the OWNS cycles.
The paths to a leaf qualify when they pass through at least `min_company_layers` organisations,
the leaf included, and the leaf's paths show at least `min_indicators` of:

- `nominee`: `is_nominee` on an OWNS relationship of a path or on a directorship of a path company;
- `professional_director`: a director of a path company with at least `professional_appointments`
  current appointments ("mass" nominees, Annex E);
- `unknown_owner`: a top owner that is an organisation with no recorded owner or controller, or a
  path company whose PSC statements say no registrable person was found or identified;
- `loop`: the ownership returns to itself (the cycle variant);
- `mass_registration_address`: a path company registered at an address shared by at least
  `mass_address_companies` active organisations (Companies House default addresses excepted);
- `po_box`: a path company whose registered address is a PO box ("Only a post-box address").

A loop needs no other indicator. `min_indicators` is 2 because each indicator alone is common in
lawful groups (a foreign parent with no owner on the UK register, a professional director in a
fund jurisdiction): on the development worlds one indicator flagged most corporate groups
(PHASE-3.md 7.6.5), and a red flag on its own is not evidence (FFIEC, quoted in
`typology-detection-definitions.md` 16.1). Jurisdictions are a
strength factor, not a condition ("different jurisdictions", with no number). One finding per
leaf company (or per loop), with every qualifying path in its evidence.

pattern_strength = 0.15 * min(1, (layers - 1) / 3) + 0.15 * min(1, (jurisdictions - 1) / 2)
+ 0.2 * nominee + 0.15 * professional director + 0.15 * (unknown owner or loop)
+ 0.1 * mass registration address + 0.1 * PO box.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from neonradar_detect.detectors.mass_registration_address import (
    DEFAULT_ADDRESS_POSTCODES,
    PO_BOX,
    normalise_postcode,
)
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow, OwnershipPath
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "shell_chain"
VERSION = "0.2.0"
QUERIES = (
    "appointment_counts.cypher",
    "entities.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "ownership_cycles.cypher",
    "ownership_paths.cypher",
)
# PSC statement values (Companies House spelling, prefixes) that leave the owner unknown
UNKNOWN_OWNER_STATEMENTS = (
    "no-individual-or-entity-with-signficant-control",
    "psc-exists-but-not-identified",
    "psc-details-not-confirmed",
    "steps-to-find-psc-not-yet-completed",
    "psc-contacted-but-no-response",
    "restrictions-notice-issued-to-psc",
)
INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})
INDICATORS = (
    "nominee",
    "professional_director",
    "unknown_owner",
    "loop",
    "mass_registration_address",
    "po_box",
)
INDICATOR_TEXT = {
    "nominee": "a nominee recorded",
    "professional_director": "a director of many companies",
    "unknown_owner": "no recorded top owner",
    "loop": "ownership that returns to itself",
    "mass_registration_address": "a widely shared address",
    "po_box": "a PO box address",
}


@dataclass(frozen=True, slots=True)
class Params:
    min_company_layers: int = 2
    min_indicators: int = 2
    professional_appointments: int = 10
    mass_address_companies: int = 25
    max_hops: int = 6
    max_paths: int = 200_000


@dataclass(slots=True)
class Context:
    entities: dict[str, EntityRow]
    directors: dict[str, list[LinkRow]]
    appointments: dict[str, int]
    owned_by: dict[str, list[LinkRow]]
    registered: dict[str, list[LinkRow]]  # organisation -> its registered HAS_ADDRESS links
    crowded: set[str]  # addresses with at least mass_address_companies active organisations
    boxes: set[str]  # PO box addresses


def _active(e: EntityRow) -> bool:
    return not e.dissolution_date and e.status.casefold() not in INACTIVE


def _current(links: dict[str, list[LinkRow]], as_of: str) -> dict[str, list[LinkRow]]:
    return {k: [x for x in v if x.current(as_of)] for k, v in links.items()}


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date().isoformat()
    paths = source.ownership_paths(p.max_hops, p.max_paths, as_of)
    cycles = source.ownership_cycles(p.max_hops, p.max_paths, as_of)
    ids = sorted({n for x in [*paths, *cycles] for n in x.nodes})
    entities = source.entities(ids)
    orgs = [i for i in ids if "Organization" in entities[i].labels]
    directors = _current(source.links_into(orgs, ("DIRECTOR_OF",)), as_of)
    appointments = source.appointment_counts(
        sorted({d.source for links in directors.values() for d in links}), as_of
    )
    owned_by = _current(source.links_into(ids, ("OWNS", "CONTROLS")), as_of)
    registered = {
        o: [x for x in links if x.role == "registered"]
        for o, links in source.links_from(orgs, ("HAS_ADDRESS",)).items()
    }
    addresses = sorted({x.target for links in registered.values() for x in links})
    address_rows = source.entities(addresses)
    excluded = {normalise_postcode(x) for x in DEFAULT_ADDRESS_POSTCODES}
    at_address = source.links_into(addresses, ("HAS_ADDRESS",))
    members = sorted(
        {x.source for links in at_address.values() for x in links if x.role == "registered"}
    )
    member_rows = source.entities(members)
    crowded = set()
    for a in addresses:
        if normalise_postcode(address_rows[a].postal_code) in excluded:
            continue
        active = {
            x.source
            for x in at_address.get(a, [])
            if x.role == "registered"
            and "Organization" in member_rows[x.source].labels
            and _active(member_rows[x.source])
        }
        if len(active) >= p.mass_address_companies:
            crowded.add(a)
    boxes = {a for a in addresses if PO_BOX.search(address_rows[a].full)}
    ctx = Context(entities, directors, appointments, owned_by, registered, crowded, boxes)
    by_leaf: dict[str, list[OwnershipPath]] = defaultdict(list)
    for path in paths:
        by_leaf[path.nodes[-1]].append(path)
    findings = []
    for leaf in sorted(by_leaf):
        f = _evaluate(leaf, by_leaf[leaf], False, ctx, p)
        if f is not None:
            findings.append(f)
    for cycle in cycles:
        f = _evaluate(cycle.nodes[0], [cycle], True, ctx, p)
        if f is not None:
            findings.append(f)
    return DetectorOutput(
        findings, {"paths": len(paths), "cycles": len(cycles), "crowded_addresses": len(crowded)}
    )


def _layers(path: OwnershipPath, entities: dict[str, EntityRow]) -> int:
    return len([n for n in dict.fromkeys(path.nodes) if "Organization" in entities[n].labels])


def _evaluate(
    anchor: str, paths: list[OwnershipPath], loop: bool, ctx: Context, p: Params
) -> Finding | None:
    e = ctx.entities
    kept = [x for x in paths if _layers(x, e) >= p.min_company_layers]
    if not kept:
        return None
    nodes = sorted({n for x in kept for n in x.nodes})
    orgs = [n for n in nodes if "Organization" in e[n].labels]
    links = sorted(
        {link.rel_id: link for x in kept for link in x.links}.values(), key=lambda x: x.rel_id
    )
    nominee_links = [x for x in links if x.is_nominee]
    nominee_dirs = [d for n in orgs for d in ctx.directors.get(n, []) if d.is_nominee]
    pro_dirs = [
        d
        for n in orgs
        for d in ctx.directors.get(n, [])
        if ctx.appointments.get(d.source, 0) >= p.professional_appointments
    ]
    tops = sorted({x.nodes[0] for x in kept}) if not loop else []
    ownerless = [t for t in tops if "Organization" in e[t].labels and not ctx.owned_by.get(t)]
    statements = [
        n for n in orgs if any(s.startswith(UNKNOWN_OWNER_STATEMENTS) for s in e[n].psc_statements)
    ]
    crowded_links = [x for n in orgs for x in ctx.registered.get(n, []) if x.target in ctx.crowded]
    box_links = [x for n in orgs for x in ctx.registered.get(n, []) if x.target in ctx.boxes]
    present = {
        "nominee": bool(nominee_links or nominee_dirs),
        "professional_director": bool(pro_dirs),
        "unknown_owner": bool(ownerless or statements),
        "loop": loop,
        "mass_registration_address": bool(crowded_links),
        "po_box": bool(box_links),
    }
    if not loop and sum(present.values()) < p.min_indicators:
        return None
    layers = max(_layers(x, e) for x in kept)
    jurisdictions = sorted({e[n].jurisdiction for n in orgs if e[n].jurisdiction})
    strength = clip01(
        0.15 * min(1.0, (layers - 1) / 3)
        + 0.15 * min(1.0, (len(jurisdictions) - 1) / 2)
        + 0.2 * present["nominee"]
        + 0.15 * present["professional_director"]
        + 0.15 * (present["unknown_owner"] or loop)
        + 0.1 * present["mass_registration_address"]
        + 0.1 * present["po_box"]
    )
    if loop:
        top_kind = "loop"
    elif ownerless:
        top_kind = "company without a recorded owner"
    elif any("Person" in e[t].labels for t in tops):
        top_kind = "person"
    elif any("Organization" not in e[t].labels for t in tops):
        top_kind = "legal entity of unstated kind"
    else:
        top_kind = "company"
    director_links = sorted(
        {d.rel_id: d for d in [*nominee_dirs, *pro_dirs]}.values(), key=lambda d: d.rel_id
    )
    address_links = sorted(
        {x.rel_id: x for x in [*crowded_links, *box_links]}.values(), key=lambda x: x.rel_id
    )
    metrics = {
        "company_layers": layers,
        "jurisdictions": len(jurisdictions),
        "jurisdiction_list": ", ".join(jurisdictions),
        "indicators": ", ".join(k for k in INDICATORS if present[k]),
        "indicator_text": " and ".join(
            [INDICATOR_TEXT[k] for k in INDICATORS if present[k] and k != "loop"][:2]
        )
        or INDICATOR_TEXT["loop"],
        "nominee_links": len(nominee_links) + len(nominee_dirs),
        "professional_directors": len({d.source for d in pro_dirs}),
        "unknown_owner_statements": len(statements),
        "top_kind": top_kind,
        "paths": len(kept),
    }
    path_steps = tuple(tuple(link.rel_id for link in x.links) for x in kept)
    extra_steps = tuple((d.rel_id,) for d in director_links) + tuple(
        (x.rel_id,) for x in address_links
    )
    extra_nodes = {d.source for d in director_links} | {x.target for x in address_links}
    return Finding(
        typology=SLUG,
        variant="loop" if loop else "chain",
        anchor=anchor,
        node_ids=tuple(sorted(set(nodes) | extra_nodes)),
        edge_ids=tuple(
            sorted(
                {x.rel_id for x in links}
                | {d.rel_id for d in director_links}
                | {x.rel_id for x in address_links}
            )
        ),
        subjects=(Subject(anchor, "owned_company"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=path_steps + extra_steps,
        window=None,
        activity=False,
    )
```

### `detect/typologies/mass_registration_address.yaml`

Verbatim. YAML, 73 lines. SHA-256 `7375ba04a78abf29c4de6aebe78da02da6b0079e2134bbedca4499fcfe2e7578`.

```yaml
slug: mass_registration_address
name: Mass registration address
shape_name: many companies registered at one address
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  Many active organisations registered at one address, with the signals that set a formation factory apart from
  an ordinary registered agent.
doc: docs/typologies/mass-registration-address.md
citations:
- fatf_egmont_concealment_2018
- fatf_egmont_tbml_indicators_2021
- fatf_tcsp_2010
- fincen_fin_2006_g014
- ca_registered_office_s86_2006
- ch_default_address_rules_2024
graph_pattern: >-
  An Address with at least 25 active organisations whose HAS_ADDRESS role is registered (Companies House default
  addresses excepted), scored by incorporation bursts, shared directors, payments among them and PO boxes.
parameters:
  min_companies:
    default: 25
    min: 1
    max: 250
  top_share:
    default: 0.001
    min: 0.0
    max: 0.1
  active_only:
    default: true
  exclude_postcodes:
    default:
    - CF14 8LH
    - EH7 9HR
    - BT1 9DY
  burst_days:
    default: 30
    min: 1
    max: 300
  max_evidence_companies:
    default: 100
    min: 1
    max: 1000
  max_candidates:
    default: 50000
    min: 1
    max: 500000
metrics:
- companies
- companies_shown
- incorporated_in_burst
- burst_days
- shared_directors
- companies_with_shared_director
- paying_pairs
- po_box
wording:
  headline_structural: >-
    {companies} active companies registered at one address, {incorporated_in_burst} of them incorporated within
    {burst_days} days
  headline_synthetic: >-
    Synthetic scenario: {companies} active companies registered at one address, {incorporated_in_burst} of them
    incorporated within {burst_days} days
false_positives:
- Registered agents and company secretarial firms
- Serviced offices
- Accountants and law firms
synthetic_support: medium
generator_scenario: mass_registration_address
detector: neonradar_detect.detectors.mass_registration_address
```

### `detect/typologies/shell_chain.yaml`

Verbatim. YAML, 75 lines. SHA-256 `1eda66394b514f37cb6cb2c7c3bd985cb3e86fb9310e1a19b8207e58139d998e`.

```yaml
slug: shell_chain
name: Layered company ownership
shape_name: ownership layered through companies
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  Ownership of a company layered through other companies, with at least two of the Annex E indicators, or an ownership
  loop.
doc: docs/typologies/shell-chain.md
citations:
- fatf_egmont_concealment_2018
- fincen_fin_2006_g014
- europol_shadow_money_2021
- fatf_pml_2018
graph_pattern: >-
  A maximal OWNS path through at least two organisations to a leaf company, with at least two of: a nominee, a director
  with many appointments, no recorded owner at the top, a widely shared registered address, a PO box; or an OWNS
  cycle.
parameters:
  min_company_layers:
    default: 2
    min: 1
    max: 20
  min_indicators:
    default: 2
    min: 1
    max: 20
  professional_appointments:
    default: 10
    min: 1
    max: 100
  mass_address_companies:
    default: 25
    min: 1
    max: 250
  max_hops:
    default: 6
    min: 1
    max: 8
  max_paths:
    default: 200000
    min: 1
    max: 2000000
metrics:
- company_layers
- jurisdictions
- jurisdiction_list
- indicators
- indicator_text
- nominee_links
- professional_directors
- unknown_owner_statements
- top_kind
- paths
wording:
  headline_structural: >-
    Ownership layered through {company_layers|n:company:companies} in {jurisdictions|n:jurisdiction}, with {indicator_text}
  headline_synthetic: >-
    Synthetic scenario: ownership layered through {company_layers|n:company:companies} in {jurisdictions|n:jurisdiction},
    with {indicator_text}
  variants:
    loop:
      headline_structural: Ownership loop through {company_layers|n:company:companies} with no outside owner recorded
      headline_synthetic: >-
        Synthetic scenario: ownership loop through {company_layers|n:company:companies} with no outside owner recorded
false_positives:
- Holding company groups with a person at the top
- Funds and special purpose vehicles with professional directors
- Subsidiaries of foreign groups whose owners are not on the UK register
synthetic_support: medium
generator_scenario: shell_chain
detector: neonradar_detect.detectors.shell_chain
```

### `detect/tests/test_detector_mass_registration_address.py`

Verbatim. Python, 93 lines. SHA-256 `7b30357a6f0459b110211c42d5bdad136e34358317fc4b5a15d21e05dd5643ce`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import mass_registration_address as mr
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    overrides.setdefault("top_share", 0.0)
    return mr.run(source_of(k.records), mr.Params(**overrides), WINDOW).findings


def _address(k: Kit, aid: str, full: str, postcode: str) -> str:
    rid = k.address(aid, full)
    record = next(r for r in k.records if r["id"] == rid)
    record["properties"]["postalCode"] = [postcode]
    return rid


def test_factory_address_with_bursts_shared_directors_and_payments():
    k = Kit()
    addr = _address(k, "factory", "Suite 1, 1 Fixture Lane, QQ9 9QQ", "QQ9 9QQ")
    cos = [
        k.company(
            f"f{i:02d}",
            incorporated=f"2025-09-{1 + i:02d}" if i < 15 else f"2023-0{1 + i % 9}-10",
            address=addr,
        )
        for i in range(25)
    ]
    d1, d2, d3 = k.person("d1"), k.person("d2"), k.person("d3")
    for c in cos[:5]:
        k.director(d1, c)
    for c in cos[5:10]:
        k.director(d2, c)
    for c in cos[10:14]:
        k.director(d3, c, start="2019-01-01", end="2024-01-01")  # resigned: not shared now
    accts = [k.account(f"fa{i}", c) for i, c in enumerate(cos[:4])]
    for a, b in ((0, 1), (1, 2), (2, 3)):
        k.pay(accts[a], accts[b], 40000, f"2026-02-0{a + 2}T10:00")
    [f] = _run(k)
    assert f.anchor == addr and f.metrics["companies"] == 25
    assert f.metrics["incorporated_in_burst"] == 15 and f.metrics["shared_directors"] == 2
    assert f.metrics["companies_with_shared_director"] == 10 and f.metrics["paying_pairs"] == 3
    assert f.activity and len(f.steps) == 3 and f.metrics["po_box"] is False
    assert f.pattern_strength == round(0.3 * 25 / 125 + 0.2 * 15 / 25 + 0.2 * 10 / 25 + 0.2, 4)


def test_below_threshold_dissolved_and_real_cluster_without_payment_terms():
    k = Kit()
    small = k.address("small")
    for i in range(24):
        k.company(f"s{i}", address=small)
    gone = k.company("gone", address=small)
    next(r for r in k.records if r["id"] == gone)["properties"]["dissolutionDate"] = ["2024-05-01"]
    assert _run(k) == []  # 24 active organisations
    assert len(_run(k, active_only=False)) == 1
    agent = k.address("agent")
    cos = [k.company(f"r{i}", address=agent) for i in range(24)]
    k.company("gbch-co-T0000001", "Test Holder Ltd", real=True, address=agent)
    accts = [k.account(f"ra{i}", c) for i, c in enumerate(cos[:2])]
    k.pay(accts[0], accts[1], 5000, "2026-03-03T10:00")
    [f] = _run(k)
    assert f.metrics["companies"] == 25 and f.metrics["paying_pairs"] == 0 and not f.activity


def test_default_addresses_are_skipped_and_po_boxes_flagged():
    k = Kit()
    default = _address(
        k, "chdefault", "Companies House Default Address, PO Box 4385, Cardiff", "cf148lh"
    )
    box = _address(k, "box", "PO Box 77, Fixture Town", "QQ7 7QQ")
    for i in range(30):
        k.company(f"m{i}", address=default)
        k.company(f"b{i}", address=box)
    [f] = _run(k)
    assert f.anchor == box and f.metrics["po_box"] is True


def test_top_share_raises_the_threshold_to_the_quantile():
    k = Kit()
    big, mid = k.address("big"), k.address("mid")
    for i in range(40):
        k.company(f"g{i}", address=big)
    for i in range(30):
        k.company(f"h{i}", address=mid)
    for i in range(98):
        k.company(f"o{i}", address=k.address(f"own{i}"))
    # 100 addresses: the nearest-rank 0.99 quantile is the 99th count in order, 30
    assert {f.anchor for f in _run(k, top_share=0.01)} == {big, mid}
    assert {f.anchor for f in _run(k, top_share=0.001)} == {big}  # the 100th count, 40
```

### `detect/tests/test_detector_shell_chain.py`

Verbatim. Python, 143 lines. SHA-256 `271fa63946f7a04a31739e33171af7b6bb9f68455b9a4d3a7c7896e1ea453fd8`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import shell_chain as sc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    overrides.setdefault("min_indicators", 1)  # these cases test each indicator on its own
    return sc.run(source_of(k.records), sc.Params(**overrides), WINDOW).findings


def test_chain_across_jurisdictions_with_a_nominee_owner():
    k = Kit()
    person = k.person("ubo")
    a = k.company("a", jurisdiction="vg")
    b = k.company("b", jurisdiction="cy")
    c = k.company("c", jurisdiction="gb")
    k.owns(person, a)
    k.owns(a, b, nominee=True)
    k.owns(b, c, "50-75")
    [f] = _run(k)
    assert f.anchor == c and f.variant == "chain" and f.metrics["indicators"] == "nominee"
    assert f.metrics["company_layers"] == 3 and f.metrics["jurisdiction_list"] == "cy, gb, vg"
    assert f.metrics["top_kind"] == "person" and f.metrics["nominee_links"] == 1
    assert [s.role for s in f.subjects] == ["owned_company"]
    assert not f.activity
    assert f.pattern_strength == round(0.15 * 2 / 3 + 0.15 + 0.2, 4)


def test_layers_alone_are_not_enough_and_two_layers_with_an_indicator_are():
    k = Kit()
    person = k.person("p2")
    a, b, c = (k.company(x, jurisdiction=j) for x, j in (("a2", "vg"), ("b2", "cy"), ("c2", "gb")))
    k.owns(person, a)
    k.owns(a, b)
    k.owns(b, c)
    assert _run(k) == []  # a group across three jurisdictions with a person at the top
    hold, op = k.company("hold"), k.company("op")
    k.owns(k.person("p3"), hold)
    k.owns(hold, op)
    k.director(k.person("nd"), op, nominee=True)
    [f] = _run(k)
    assert f.anchor == op and f.metrics["company_layers"] == 2 and f.metrics["jurisdictions"] == 1
    assert _run(k, min_company_layers=3) == []


def test_ownerless_top_loop_and_professional_director():
    k = Kit()
    x = k.company("x", jurisdiction="vg")
    y, z = k.company("y"), k.company("z")
    k.owns(x, y)
    k.owns(y, z)
    l1, l2, l3 = k.company("l1", jurisdiction="pa"), k.company("l2"), k.company("l3")
    k.owns(l1, l2, "50-75")
    k.owns(l2, l3, "50-75")
    k.owns(l3, l1, "25-50")
    found = {f.variant: f for f in _run(k)}
    assert (
        found["chain"].anchor == z
        and found["chain"].metrics["top_kind"] == "company without a recorded owner"
    )
    assert (
        found["loop"].metrics["top_kind"] == "loop" and found["loop"].metrics["company_layers"] == 3
    )
    k.controls(
        k.person("ctl"), x, "influence"
    )  # a recorded controller: the top is no longer ownerless
    assert {f.variant for f in _run(k)} == {"loop"}
    k2 = Kit()
    person = k2.person("u")
    m, n, o = k2.company("m", jurisdiction="je"), k2.company("n"), k2.company("o")
    k2.owns(person, m)
    k2.owns(m, n)
    k2.owns(n, o)
    pro = k2.person("pro")
    for i in range(12):
        k2.director(pro, k2.company(f"client{i}", jurisdiction="je"))
    k2.director(pro, m)
    [f] = _run(k2)
    assert f.metrics["professional_directors"] == 1 and pro in f.node_ids


def test_psc_statement_po_box_and_crowded_address():
    k = Kit()
    person = k.person("own")
    box = k.address("box", "PO Box 12, Fixture Town")
    a = k.company("sa", psc_statements=("psc-exists-but-not-identified",), address=box)
    b = k.company("sb")
    k.owns(person, a)
    k.owns(a, b)
    [f] = _run(k)
    assert f.metrics["indicators"] == "unknown_owner, po_box" and box in f.node_ids
    k2 = Kit()
    hub = k2.address("hub")
    for i in range(25):
        k2.company(f"tenant{i}", address=hub)
    c = k2.company("sc", address=hub)
    d = k2.company("sd")
    k2.owns(k2.person("own2"), c)
    k2.owns(c, d)
    [f2] = _run(k2)
    assert f2.metrics["indicators"] == "mass_registration_address"
    assert _run(k2, mass_address_companies=27) == []


def test_default_needs_two_indicators_except_for_a_loop():
    k = Kit()
    x = k.company("tx", jurisdiction="us")  # a foreign parent with no owner recorded
    y = k.company("ty")
    k.owns(x, y)
    assert sc.run(source_of(k.records), sc.Params(), WINDOW).findings == []
    k.director(k.person("nd2"), y, nominee=True)
    [f] = sc.run(source_of(k.records), sc.Params(), WINDOW).findings
    assert f.metrics["indicators"] == "nominee, unknown_owner"
    loop = Kit()
    a, b = loop.company("la"), loop.company("lb", jurisdiction="pa")
    loop.owns(a, b, "50-75")
    loop.owns(b, a, "50-75")
    [g] = sc.run(source_of(loop.records), sc.Params(), WINDOW).findings
    assert g.variant == "loop"


def test_ended_holdings_and_resigned_appointments_are_history():
    k = Kit()
    a, b, c = k.company("ea", jurisdiction="vg"), k.company("eb"), k.company("ec")
    k.owns(k.person("old-ubo"), a)
    k.owns(a, b, nominee=True, end="2025-06-30")  # sold before the end of the window
    k.owns(b, c)
    [f] = _run(k)  # B is now the top: B and C, with no recorded owner above B
    assert f.anchor == c and f.metrics["company_layers"] == 2
    assert f.metrics["indicators"] == "unknown_owner" and f.metrics["nominee_links"] == 0
    k2 = Kit()
    m, n = k2.company("rm", jurisdiction="je"), k2.company("rn")
    k2.owns(k2.person("u2"), m)
    k2.owns(m, n)
    pro = k2.person("retired")
    for i in range(12):
        k2.director(pro, k2.company(f"past{i}"), start="2015-01-01", end="2020-01-01")
    k2.director(pro, m)
    assert _run(k2) == []  # one current appointment: not a director of many companies
```

## M3.5c Fans and dormancy: `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 9 verbatim files (PHASE-3.md M3.5c).

### `detect/src/neonradar_detect/detectors/fan_in_collection.py`

Verbatim. Python, 330 lines. SHA-256 `899c670537e9ca19c7d89b6b97e03e8a04efc36606cd4d5e5528bdd29ab91185`.

```python
"""fan_in_collection 0.2.0: many unrelated accounts paying one account in a short window, which
passes the money on; and the ring variant, a connected group of recently opened accounts
(PHASE-1.md 7.2 entry 5, corrected by `typology-detection-definitions.md` section 5; PHASE-3.md
7.3.5).

Variant `collector`: per account and currency (cash deposits excluded), a window of `window_days`
starting at an inflow qualifies when at least `min_senders` accounts paid in at least `min_total`,
at least `min_person_share` of them are held by people, at most `max_prior_share` of them had a
payment with the account (either way) in the `prior_days` before the window, and the account paid
on at least `min_onward_ratio` of the inflow by `onward_hours` after the window's last inflow.
Windows that start less than `prior_days` after the first payment in the data are skipped, because
earlier relationships cannot be judged there. Recency counts on the collector's side, not the
senders' (senders are often victims): a collector account opened within `new_account_days` before
the window adds to the strength. Findings never share an inflow (largest total first).

Variant `ring`: the PAID relationships of the period between two accounts that were each opened
at most `new_account_days` before the payment form weakly connected components (GDS WCC on Neo4j,
union-find in the reference). A component of `min_ring_accounts` to `max_ring_accounts` accounts,
at least `min_person_share` of them held by people, moving at least `min_total`, with one to three
hubs (accounts paid by at least three other accounts of the component) that at least half of the
component's accounts pay, is a finding. Its evidence adds what fed the ring (payments into its
accounts from outside it in the `window_days` before the ring's first payment and during it) and
what left it (the hubs' payments out up to `onward_hours` after its last payment). WCC is used
rather than Louvain because its result does not depend on the run (7.1.6).

pattern_strength (collector) = 0.3 * min(1, senders / (2 * min_senders)) + 0.25 * (1 - prior
share) + 0.25 * min(1, onward ratio) + 0.2 if the collector account is new.
pattern_strength (ring) = 0.4 * share of accounts paying a hub + 0.3 * min(1, accounts /
(2 * min_ring_accounts)) + 0.3 * person share.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Component, CounterpartyInfo, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "fan_in_collection"
VERSION = "0.2.0"
QUERIES = (
    "counterparty_info.cypher",
    "flows_by_inbound.cypher",
    "paid_time_range.cypher",
    "paid_times.cypher",
    "payments_from.cypher",
    "payments_into.cypher",
    "recent_account_components_drop.cypher",
    "recent_account_components_project.cypher",
    "recent_account_components_wcc.cypher",
    "recent_account_edges.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    window_days: int = 7
    min_senders: int = 10
    min_total: float = 5000.0
    min_person_share: float = 0.8
    prior_days: int = 90
    max_prior_share: float = 0.2
    onward_hours: int = 72
    min_onward_ratio: float = 0.8
    new_account_days: int = 90
    ring: bool = True
    min_ring_accounts: int = 5
    max_ring_accounts: int = 200
    max_candidates: int = 100_000


def _opened(info: CounterpartyInfo) -> date | None:
    return date.fromisoformat(info.opening_date) if len(info.opening_date) == 10 else None


def related_before(
    a: str, b: str, before: datetime, days: int, times: dict[tuple[str, str], tuple[datetime, ...]]
) -> bool:
    """Whether a payment joined a and b, either way, in the `days` before `before` (the times of
    each pair are sorted, so this is two binary searches)."""
    since = before - timedelta(days=days)
    for pair in ((a, b), (b, a)):
        ts = times.get(pair, ())
        i = bisect_left(ts, since)
        if i < len(ts) and ts[i] < before:
            return True
    return False


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0, "components": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.prior_days))
    candidates = source.flows_by_inbound(
        math.ceil(p.min_senders / 2),
        window.start,
        window.end,
        None,
        p.window_days * 24,
        p.max_candidates,
    )
    senders = {x.counterparty for c in candidates for x in c.inflows if x.channel != "cash_deposit"}
    info = source.counterparty_info(senders | {c.account for c in candidates})
    pairs: set[tuple[str, str]] = set()
    for c in candidates:
        for x in c.inflows:
            if x.channel != "cash_deposit":
                pairs.add((x.counterparty, c.account))
                pairs.add((c.account, x.counterparty))
    times = source.paid_times(pairs)
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_collector(flows, info, times, judged_from, p))
    rings = 0
    if p.ring:
        components = source.recent_account_components(
            p.new_account_days, window.start, window.end, p.min_ring_accounts
        )
        rings = len(components)
        ring_info = source.counterparty_info({a for comp in components for a in comp.accounts})
        for comp in components:
            f = _ring(comp, ring_info, source, p)
            if f is not None:
                findings.append(f)
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates), "components": rings})


def _collector(
    flows: AccountFlows,
    info: dict[str, CounterpartyInfo],
    times: dict[tuple[str, str], tuple[datetime, ...]],
    judged_from: datetime,
    p: Params,
) -> list[Finding]:
    out = []
    span = timedelta(days=p.window_days)
    onward = timedelta(hours=p.onward_hours)
    for currency in sorted({x.currency for x in flows.inflows}):
        ins = [x for x in flows.inflows if x.currency == currency and x.channel != "cash_deposit"]
        outs = [x for x in flows.outflows if x.currency == currency]
        windows = []
        j = 0
        for i, start in enumerate(ins):
            if start.ts < judged_from:
                continue
            j = max(j, i)
            while j < len(ins) and ins[j].ts < start.ts + span:
                j += 1
            members = ins[i:j]
            senders = sorted({x.counterparty for x in members})
            total = sum(x.amount for x in members)
            if len(senders) < p.min_senders or total < p.min_total:
                continue
            people = sum(1 for s in senders if "Person" in info[s].holder_labels)
            prior = sum(
                1
                for s in senders
                if related_before(s, flows.account, start.ts, p.prior_days, times)
            )
            onward_pays = [x for x in outs if start.ts <= x.ts <= members[-1].ts + onward]
            onward_total = sum(x.amount for x in onward_pays)
            if (
                people / len(senders) >= p.min_person_share
                and prior / len(senders) <= p.max_prior_share
                and onward_total >= p.min_onward_ratio * total
            ):
                windows.append((round(total * 100), i, j, onward_pays, people, prior))
        chosen: list[tuple[int, int]] = []
        for _, i, j, onward_pays, people, prior in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
                out.append(
                    _collector_finding(
                        flows, ins[i:j], onward_pays, info, people, prior, currency, p
                    )
                )
    return out


def _collector_finding(
    flows: AccountFlows,
    members: list[Pay],
    onward_pays: list[Pay],
    info: dict[str, CounterpartyInfo],
    people: int,
    prior: int,
    currency: str,
    p: Params,
) -> Finding:
    senders = sorted({x.counterparty for x in members})
    total = sum(x.amount for x in members)
    opened = _opened(info[flows.account])
    new_collector = (
        opened is not None and (members[0].ts.date() - opened).days <= p.new_account_days
    )
    onward_total = sum(x.amount for x in onward_pays)
    n = len(senders)
    strength = clip01(
        0.3 * min(1.0, n / (2 * p.min_senders))
        + 0.25 * (1 - prior / n)
        + 0.25 * min(1.0, onward_total / total)
        + (0.2 if new_collector else 0.0)
    )
    beneficiaries = sorted({x.counterparty for x in onward_pays})
    metrics = {
        "senders": n,
        "total_amount": round(total, 2),
        "currency": currency,
        "window_days": p.window_days,
        "person_share": round(people / n, 4),
        "prior_share": round(prior / n, 4),
        "onward_ratio": round(onward_total / total, 4),
        "onward_beneficiaries": len(beneficiaries),
        "collector_account_days": (members[0].ts.date() - opened).days if opened else -1,
    }
    subjects = [Subject(flows.account, "collector")] + [
        Subject(h, "collector_holder") for h in flows.holders
    ]
    in_edges = sorted(x.edge_id for x in members)
    out_edges = sorted(x.edge_id for x in onward_pays)
    end = max([members[-1].ts] + [x.ts for x in onward_pays])
    return Finding(
        typology=SLUG,
        variant="collector",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *senders, *beneficiaries})),
        edge_ids=tuple(sorted(set(in_edges) | set(out_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(tuple(in_edges), tuple(out_edges)) if out_edges else (tuple(in_edges),),
        window=(members[0].ts, end),
        activity=True,
    )


def _ring(
    comp: Component, info: dict[str, CounterpartyInfo], source: Source, p: Params
) -> Finding | None:
    n = len(comp.accounts)
    if not p.min_ring_accounts <= n <= p.max_ring_accounts:
        return None
    currencies = Counter(e.currency for e in comp.edges)
    currency = sorted(currencies, key=lambda c: (-currencies[c], c))[0]
    edges = [e for e in comp.edges if e.currency == currency]
    total = sum(e.amount for e in edges)
    people = sum(1 for a in comp.accounts if "Person" in info[a].holder_labels)
    if total < p.min_total or people / n < p.min_person_share:
        return None
    payers: dict[str, set[str]] = {a: set() for a in comp.accounts}
    for e in edges:
        payers[e.target].add(e.source)
    hubs = sorted(a for a in comp.accounts if len(payers[a]) >= 3)
    feeding = set().union(*(payers[h] for h in hubs)) if hubs else set()
    feed_share = len(feeding) / n
    if not 1 <= len(hubs) <= 3 or feed_share < 0.5:
        return None
    strength = clip01(
        0.4 * feed_share + 0.3 * min(1.0, n / (2 * p.min_ring_accounts)) + 0.3 * (people / n)
    )
    first = min(e.ts for e in edges)
    last = max(e.ts for e in edges)
    members = set(comp.accounts)
    fed = sorted(
        (
            x
            for pays in source.payments_into(
                comp.accounts, first - timedelta(days=p.window_days), last
            ).values()
            for x in pays
            if x.counterparty not in members and x.currency == currency
        ),
        key=lambda x: (x.ts, x.edge_id),
    )
    left = sorted(
        (
            x
            for pays in source.payments_from(
                hubs, last, last + timedelta(hours=p.onward_hours)
            ).values()
            for x in pays
            if x.counterparty not in members and x.currency == currency
        ),
        key=lambda x: (x.ts, x.edge_id),
    )
    metrics = {
        "ring_accounts": n,
        "hubs": len(hubs),
        "total_amount": round(total, 2),
        "currency": currency,
        "span_days": max(1, math.ceil((last - first).total_seconds() / 86400)),
        "person_share": round(people / n, 4),
        "feeding_share": round(feed_share, 4),
    }
    metrics["fed_payments"] = len(fed)
    metrics["out_payments"] = len(left)
    subjects = [Subject(a, "collector") for a in hubs]
    subjects += [Subject(h, "collector_holder") for a in hubs for h in info[a].holders]
    into_hubs = tuple(e.edge_id for e in edges if e.target in hubs)
    rest = tuple(e.edge_id for e in edges if e.target not in hubs)
    steps = tuple(
        s
        for s in (tuple(x.edge_id for x in fed), rest, into_hubs, tuple(x.edge_id for x in left))
        if s
    )
    nodes = members | {x.counterparty for x in fed} | {x.counterparty for x in left}
    return Finding(
        typology=SLUG,
        variant="ring",
        anchor=hubs[0],
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(
            sorted(
                {e.edge_id for e in edges} | {x.edge_id for x in fed} | {x.edge_id for x in left}
            )
        ),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=steps,
        window=(min([first, *(x.ts for x in fed)]), max([last, *(x.ts for x in left)])),
        activity=True,
    )
```

### `detect/src/neonradar_detect/detectors/fan_out_distribution.py`

Verbatim. Python, 216 lines. SHA-256 `5886ed0713aaab7c4fcd550baf09dfeb8105b902948f093a036f3475555f5fed`.

```python
"""fan_out_distribution 0.2.0: one account paying many new counterparties in a short window, who
then move the money on (PHASE-1.md 7.2 entry 6; `typology-detection-definitions.md` section 6;
PHASE-3.md 7.3.6).

Per account and currency, a window of `window_hours` starting at an outflow qualifies when it pays
at least `min_recipients` accounts at least `min_total` in all, at most `max_prior_share` of the
recipients had a payment with the account (either way) in the `prior_days` before the window, and
at least `min_onward_share` of the recipients paid out at least `onward_fraction` of what they
received within `onward_hours` of receiving it (cash withdrawals or transfers). Similar amounts and
round amounts add to the strength but are not required. Windows that start less than `prior_days`
after the first payment in the data are skipped. Findings never share an outflow (largest total
first).

pattern_strength = 0.3 * min(1, recipients / (2 * min_recipients)) + 0.3 * (1 - prior share)
+ 0.2 * onward share + 0.2 * max(amount similarity, round share), where amount similarity is
1 - min(1, coefficient of variation / max_amount_cv).
"""

from __future__ import annotations

import math
import statistics
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta

from neonradar_detect.detectors.fan_in_collection import related_before
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountFlows, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "fan_out_distribution"
VERSION = "0.2.0"
QUERIES = (
    "flows_by_outbound.cypher",
    "paid_time_range.cypher",
    "paid_times.cypher",
    "payments_from.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    window_hours: int = 72
    min_recipients: int = 10
    min_total: float = 5000.0
    prior_days: int = 90
    max_prior_share: float = 0.2
    max_amount_cv: float = 0.2
    round_unit: float = 100.0
    onward_hours: int = 72
    onward_fraction: float = 0.8
    min_onward_share: float = 0.5
    max_candidates: int = 100_000


def _cv(amounts: list[float]) -> float:
    mean = statistics.fmean(amounts)
    return statistics.pstdev(amounts) / mean if mean > 0 else 0.0


def _round(amount: float, unit: float) -> bool:
    return round(amount * 100) % round(unit * 100) == 0


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"candidates": 0})
    judged_from = max(window.start, span[0] + timedelta(days=p.prior_days))
    candidates = source.flows_by_outbound(
        math.ceil(p.min_recipients / 2), window.start, window.end, p.window_hours, p.max_candidates
    )
    pairs: set[tuple[str, str]] = set()
    recipients: set[str] = set()
    for c in candidates:
        for x in c.outflows:
            pairs.add((c.account, x.counterparty))
            pairs.add((x.counterparty, c.account))
            recipients.add(x.counterparty)
    times = source.paid_times(pairs)
    onward = source.payments_from(
        recipients, window.start, window.end + timedelta(hours=p.onward_hours)
    )
    findings: list[Finding] = []
    for flows in candidates:
        findings.extend(_evaluate(flows, times, onward, judged_from, p))
    findings.sort(key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids))
    return DetectorOutput(findings, {"candidates": len(candidates)})


def _moved_on(
    received: list[Pay], paid_out: list[Pay], times: list[datetime], p: Params
) -> list[Pay] | None:
    """The recipient's payments (`paid_out`, in time order, with their `times`) that moved on
    `onward_fraction` of what it received within `onward_hours` of receiving it, or None."""
    got = sum(x.amount for x in received)
    start = min(x.ts for x in received)
    until = max(x.ts for x in received) + timedelta(hours=p.onward_hours)
    moved = paid_out[bisect_left(times, start) : bisect_right(times, until)]
    return moved if sum(x.amount for x in moved) >= p.onward_fraction * got else None


def _evaluate(
    flows: AccountFlows,
    times: dict[tuple[str, str], tuple[datetime, ...]],
    onward: dict[str, list[Pay]],
    judged_from: datetime,
    p: Params,
) -> list[Finding]:
    out = []
    span = timedelta(hours=p.window_hours)
    for currency in sorted({x.currency for x in flows.outflows}):
        outs = [x for x in flows.outflows if x.currency == currency]
        paid_out = {
            r: sorted(
                (x for x in onward.get(r, []) if x.currency == currency),
                key=lambda x: (x.ts, x.edge_id),
            )
            for r in {x.counterparty for x in outs}
        }
        paid_times = {r: [x.ts for x in pays] for r, pays in paid_out.items()}
        windows = []
        j = 0
        for i, first in enumerate(outs):
            if first.ts < judged_from:
                continue
            j = max(j, i)
            while j < len(outs) and outs[j].ts < first.ts + span:
                j += 1
            members = outs[i:j]
            recips = sorted({x.counterparty for x in members})
            total = sum(x.amount for x in members)
            if len(recips) < p.min_recipients or total < p.min_total:
                continue
            allowed_prior = math.floor(p.max_prior_share * len(recips) + 1e-9)
            prior = 0
            for r in recips:
                if related_before(flows.account, r, first.ts, p.prior_days, times):
                    prior += 1
                    if prior > allowed_prior:
                        break
            if prior > allowed_prior:
                continue
            moved_by: dict[str, list[Pay]] = {}
            for r in recips:
                received = [x for x in members if x.counterparty == r]
                moved = _moved_on(received, paid_out[r], paid_times[r], p)
                if moved is not None:
                    moved_by[r] = moved
            if (
                prior / len(recips) <= p.max_prior_share
                and len(moved_by) / len(recips) >= p.min_onward_share
            ):
                windows.append((round(total * 100), i, j, prior, moved_by))
        chosen: list[tuple[int, int]] = []
        for _, i, j, prior, moved_by in sorted(windows, key=lambda w: (-w[0], w[1])):
            if all(j <= a or i >= b for a, b in chosen):
                chosen.append((i, j))
                out.append(_finding(flows, outs[i:j], prior, moved_by, currency, p))
    return out


def _finding(
    flows: AccountFlows,
    members: list[Pay],
    prior: int,
    moved_by: dict[str, list[Pay]],
    currency: str,
    p: Params,
) -> Finding:
    recips = sorted({x.counterparty for x in members})
    n = len(recips)
    total = sum(x.amount for x in members)
    amounts = [x.amount for x in members]
    cv = _cv(amounts)
    round_share = sum(1 for a in amounts if _round(a, p.round_unit)) / len(amounts)
    similarity = 1 - min(1.0, cv / p.max_amount_cv) if p.max_amount_cv > 0 else 0.0
    onward_share = len(moved_by) / n
    strength = clip01(
        0.3 * min(1.0, n / (2 * p.min_recipients))
        + 0.3 * (1 - prior / n)
        + 0.2 * onward_share
        + 0.2 * max(similarity, round_share)
    )
    moved = sorted((x for pays in moved_by.values() for x in pays), key=lambda x: (x.ts, x.edge_id))
    second = sorted({x.counterparty for x in moved})
    metrics = {
        "recipients": n,
        "total_amount": round(total, 2),
        "currency": currency,
        "window_hours": p.window_hours,
        "amount_cv": round(cv, 4),
        "round_share": round(round_share, 4),
        "prior_share": round(prior / n, 4),
        "onward_share": round(onward_share, 4),
    }
    subjects = [Subject(flows.account, "distributor")] + [
        Subject(h, "distributor_holder") for h in flows.holders
    ]
    out_edges = tuple(sorted(x.edge_id for x in members))
    onward_edges = tuple(sorted(x.edge_id for x in moved))
    end = max([members[-1].ts] + [x.ts for x in moved])
    return Finding(
        typology=SLUG,
        variant="",
        anchor=flows.account,
        node_ids=tuple(sorted({flows.account, *recips, *second})),
        edge_ids=tuple(sorted(set(out_edges) | set(onward_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=(out_edges, onward_edges) if onward_edges else (out_edges,),
        window=(members[0].ts, end),
        activity=True,
    )
```

### `detect/src/neonradar_detect/detectors/dormant_reactivation.py`

Verbatim. Python, 350 lines. SHA-256 `c49943290d02bab738a0ea33c8ddab32303d338b61f2b5c9cad4938ec68039cd`.

```python
"""dormant_reactivation 0.2.0: an account with little activity for a long time that suddenly moves
large sums in and out, often soon after a change of director or owner; and the company variants
(PHASE-1.md 7.2 entry 7, corrected by `typology-detection-definitions.md` section 7; PHASE-3.md
7.3.7).

Variant `account`. A quiet period is at least `min_gap_days` with at most `max_quiet_payments`
payments totalling at most `max_quiet_amount` ("an account with little activity", FFIEC), between
a payment of the account, or its opening date, and the payment that ends it. An opening date
counts only when it is on or after the first payment in the data: before that, the data cannot say
whether the account was quiet (left-censoring). The quiet period must end inside the detection
window. A burst follows: the payments from the one that ends the quiet period to `burst_days`
after it, at least `min_burst_payments` of them, in both directions, totalling at least
max(`min_burst_amount`, `burst_ratio` times the account's mean monthly volume before the quiet
period). The ratio keeps seasonal businesses and genuine restarts, which come back at their usual
level, below the threshold. A director appointed to, or an owner acquiring, a holder within
`change_days` before the burst is the change event.

Variant `dormant_company`: an account whose holder's last accounts were filed as dormant
(`accounts_category` DORMANT) with a burst in the window, quiet period or not; an account finding
on such an account takes this variant. Variant `new_company`: a burst that starts at most
`new_company_days` after the holder's incorporation in which "large sums of capital funding" are
"spent or transferred elsewhere in a short period of time" (FATF and Egmont 2018 Annex E): the
burst's inflow alone is at least `min_burst_amount`, its three largest inflows bring at least
`min_inflow_concentration` of it and at least `min_moved_on` of it leaves in the burst. A new
business's ordinary trading, receipts and supplier payments of similar size, does not qualify.
Both variants use `min_burst_amount`.

pattern_strength = 0.3 * min(1, gap days / (2 * min_gap_days)) (0.3 for the company variants)
+ 0.3 * min(1, burst amount / (5 * threshold)) + 0.2 * min(1, burst payments /
(3 * min_burst_payments)) + 0.2 if there is a change event.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import AccountHistory, EntityRow, LinkRow, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "dormant_reactivation"
VERSION = "0.2.0"
QUERIES = (
    "company_account_histories.cypher",
    "entities.cypher",
    "links_into.cypher",
    "paid_time_range.cypher",
    "quiet_account_histories.cypher",
)
DAYS_PER_MONTH = 30.4375


@dataclass(frozen=True, slots=True)
class Params:
    min_gap_days: int = 180
    max_quiet_payments: int = 2
    max_quiet_amount: float = 1000.0
    burst_days: int = 14
    min_burst_payments: int = 4
    min_burst_amount: float = 50000.0
    burst_ratio: float = 10.0
    change_days: int = 30
    company_variants: bool = True
    new_company_days: int = 90
    min_inflow_concentration: float = 0.8
    min_moved_on: float = 0.8
    max_candidates: int = 100_000


@dataclass(frozen=True, slots=True)
class Quiet:
    end: int  # index of the payment that ends the quiet period
    before: (
        int | None
    )  # index of the last payment before it; None when it starts at the opening date
    began: datetime
    payments: int  # payments inside the quiet period


def quiet_periods(
    pays: list[tuple[Pay, str]], opened: datetime | None, window: Window, p: Params
) -> list[Quiet]:
    """The longest quiet period ending at each payment inside the window, in order (the
    explanation says how many payments it holds)."""
    gap = timedelta(days=p.min_gap_days)
    ts = [x.ts for x, _ in pays]
    amt = [x.amount for x, _ in pays]
    out = []
    for j in range(len(pays)):
        if not window.start <= ts[j] < window.end:
            continue
        best: Quiet | None = None
        for m in range(p.max_quiet_payments + 1):
            k = j - m - 1
            if k < 0:
                break
            if ts[j] - ts[k] >= gap and sum(amt[k + 1 : j]) <= p.max_quiet_amount:
                best = Quiet(j, k, ts[k], m)
        if (
            opened is not None
            and j <= p.max_quiet_payments
            and sum(amt[:j]) <= p.max_quiet_amount
            and ts[j] - opened >= gap
        ):
            best = Quiet(j, None, opened, j)
        if best is not None:
            out.append(best)
    return out


def _burst(
    pays: list[tuple[Pay, str]], start: int, threshold: float, p: Params
) -> list[tuple[Pay, str]] | None:
    first = pays[start][0].ts
    burst = [x for x in pays[start:] if x[0].ts <= first + timedelta(days=p.burst_days)]
    directions = {d for _, d in burst}
    if (
        len(burst) >= p.min_burst_payments
        and directions == {"in", "out"}
        and sum(x[0].amount for x in burst) >= threshold
    ):
        return burst
    return None


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"histories": 0, "company_accounts": 0})
    history_start = span[0].date().isoformat()
    histories = source.quiet_account_histories(
        p.min_gap_days,
        p.max_quiet_payments,
        p.max_quiet_amount,
        history_start,
        window.start,
        window.end,
        p.max_candidates,
    )
    company_rows: list[AccountHistory] = []
    if p.company_variants:
        since = (window.start - timedelta(days=p.new_company_days)).date().isoformat()
        company_rows = source.company_account_histories(
            since, window.start, window.end, p.min_burst_payments, p.max_candidates
        )
    holders = sorted({h for x in [*histories, *company_rows] for h in x.holders})
    entities = source.entities(holders)
    changes = source.links_into(holders, ("DIRECTOR_OF", "OWNS"))
    findings: dict[tuple[str, ...], Finding] = {}
    for hist in histories:
        for f in _account_variant(hist, history_start, span[0], entities, changes, p, window):
            findings.setdefault(f.edge_ids, f)
    for hist in company_rows:
        company = _company_variant(hist, entities, changes, p, window)
        if company is not None:
            findings.setdefault(company.edge_ids, company)
    ordered = sorted(
        findings.values(), key=lambda f: (f.window[0] if f.window else window.start, f.edge_ids)
    )
    return DetectorOutput(
        ordered, {"histories": len(histories), "company_accounts": len(company_rows)}
    )


def _account_variant(
    hist: AccountHistory,
    history_start: str,
    data_start: datetime,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
    window: Window,
) -> list[Finding]:
    pays = list(hist.payments)
    opened = None
    if len(hist.opening_date) == 10 and hist.opening_date >= history_start:
        opened = datetime.fromisoformat(hist.opening_date).replace(tzinfo=pays[0][0].ts.tzinfo)
    dormant = any(entities[h].accounts_category.upper() == "DORMANT" for h in hist.holders)
    out = []
    covered = -1
    for q in quiet_periods(pays, opened, window, p):
        if q.end <= covered:
            continue
        if q.before is None:
            mean = 0.0
        else:
            begin = max(data_start, opened) if opened is not None else data_start
            months = max(
                1.0, (pays[q.before][0].ts - begin).total_seconds() / 86400 / DAYS_PER_MONTH
            )
            mean = sum(x.amount for x, _ in pays[: q.before + 1]) / months
        threshold = max(p.min_burst_amount, p.burst_ratio * mean)
        burst = _burst(pays, q.end, threshold, p)
        if burst is None:
            continue
        covered = q.end + len(burst) - 1
        variant = "dormant_company" if dormant and p.company_variants else "account"
        gap_days = (pays[q.end][0].ts - q.began).total_seconds() / 86400
        out.append(
            _finding(
                hist, burst, variant, gap_days, q.payments, mean, threshold, entities, changes, p
            )
        )
    return out


def _company_variant(
    hist: AccountHistory,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
    window: Window,
) -> Finding | None:
    pays = [x for x in hist.payments if window.start <= x[0].ts < window.end]
    for i in range(len(pays)):
        burst = _burst(pays, i, p.min_burst_amount, p)
        if burst is None:
            continue
        begin = burst[0][0].ts.date()
        for h in hist.holders:
            e = entities[h]
            if e.accounts_category.upper() == "DORMANT":
                return _finding(
                    hist,
                    burst,
                    "dormant_company",
                    None,
                    0,
                    0.0,
                    p.min_burst_amount,
                    entities,
                    changes,
                    p,
                )
            if len(e.incorporation_date) == 10:
                age = (begin - date.fromisoformat(e.incorporation_date)).days
                if 0 <= age <= p.new_company_days and _flipped(burst, p):
                    return _finding(
                        hist,
                        burst,
                        "new_company",
                        None,
                        0,
                        0.0,
                        p.min_burst_amount,
                        entities,
                        changes,
                        p,
                    )
    return None


def _flipped(burst: list[tuple[Pay, str]], p: Params) -> bool:
    """Large sums in from few payments, most of it out again within the burst."""
    ins = sorted((x.amount for x, d in burst if d == "in"), reverse=True)
    total_in = sum(ins)
    total_out = sum(x.amount for x, d in burst if d == "out")
    return (
        total_in >= p.min_burst_amount
        and sum(ins[:3]) >= p.min_inflow_concentration * total_in
        and total_out >= p.min_moved_on * total_in
    )


def _change_event(
    holders: tuple[str, ...], begin: datetime, changes: dict[str, list[LinkRow]], p: Params
) -> tuple[str, list[LinkRow]]:
    found: list[LinkRow] = []
    for h in holders:
        for link in changes.get(h, []):
            if len(link.start_date) == 10:
                started = date.fromisoformat(link.start_date)
                if 0 <= (begin.date() - started).days <= p.change_days:
                    found.append(link)
    found.sort(key=lambda x: (x.start_date, x.rel_id))
    if not found:
        return "none", []
    kinds = {x.rel_type for x in found}
    if kinds == {"DIRECTOR_OF"}:
        return "director appointed", found
    if kinds == {"OWNS"}:
        return "new owner", found
    return "director appointed and new owner", found


def _finding(
    hist: AccountHistory,
    burst: list[tuple[Pay, str]],
    variant: str,
    gap_days: float | None,
    quiet_payments: int,
    mean: float,
    threshold: float,
    entities: dict[str, EntityRow],
    changes: dict[str, list[LinkRow]],
    p: Params,
) -> Finding:
    begin = burst[0][0].ts
    end = burst[-1][0].ts
    amount_in = sum(x.amount for x, d in burst if d == "in")
    amount_out = sum(x.amount for x, d in burst if d == "out")
    currencies = Counter(x.currency for x, _ in burst)
    currency = sorted(currencies, key=lambda c: (-currencies[c], c))[0]
    event, links = _change_event(hist.holders, begin, changes, p)
    gap_score = 0.3 * min(1.0, gap_days / (2 * p.min_gap_days)) if gap_days is not None else 0.3
    strength = clip01(
        gap_score
        + 0.3 * min(1.0, (amount_in + amount_out) / (5 * threshold))
        + 0.2 * min(1.0, len(burst) / (3 * p.min_burst_payments))
        + (0.2 if links else 0.0)
    )
    metrics = {
        "gap_days": math.floor(gap_days) if gap_days is not None else 0,
        "quiet_payments": quiet_payments,
        "pre_gap_monthly_mean": round(mean, 2),
        "burst_threshold": round(threshold, 2),
        "burst_payments": len(burst),
        "burst_in_amount": round(amount_in, 2),
        "burst_out_amount": round(amount_out, 2),
        "burst_amount": round(amount_in + amount_out, 2),
        "currency": currency,
        "burst_days": max(1, math.ceil((end - begin).total_seconds() / 86400)),
        "change_event": event,
    }
    counterparties = {x.counterparty for x, _ in burst}
    subjects = [Subject(hist.account, "reactivated_account")] + [
        Subject(h, "holder") for h in hist.holders
    ]
    pay_edges = tuple(x.edge_id for x, _ in burst)
    link_edges = tuple(x.rel_id for x in links)
    node_ids = {hist.account, *counterparties}
    if links:
        node_ids |= {x.source for x in links} | set(hist.holders)
    steps = (pay_edges,) + ((link_edges,) if link_edges else ())
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=hist.account,
        node_ids=tuple(sorted(node_ids)),
        edge_ids=tuple(sorted(set(pay_edges) | set(link_edges))),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=steps,
        window=(begin, end),
        activity=True,
    )
```

### `detect/typologies/fan_in_collection.yaml`

Verbatim. YAML, 110 lines. SHA-256 `18d2a2cfd0e932c6307ff40fa22efcd2704b31045049a9eaf499110584ebb8ef`.

```yaml
slug: fan_in_collection
name: Fan-in collection
shape_name: many accounts paying into one
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  Many unrelated accounts pay one account in a short window, which passes the money on; or a connected group of
  new accounts feeding one or two hubs.
doc: docs/typologies/fan-in-collection.md
citations:
- ffiec_appendix_f
- fatf_cyber_fraud_2023
- europol_money_muling
- fincen_mule_advisory_2020
graph_pattern: >-
  At least ten distinct paying accounts, mostly of people and with no earlier relationship, into one Account within
  7 days, 80 percent paid on within 72 hours; or a weakly connected component of PAID between new accounts with
  one to three hubs.
parameters:
  window_days:
    default: 7
    min: 1
    max: 70
  min_senders:
    default: 10
    min: 1
    max: 100
  min_total:
    default: 5000.0
    min: 0.0
    max: 50000.0
  min_person_share:
    default: 0.8
    min: 0.0
    max: 1.0
  prior_days:
    default: 90
    min: 1
    max: 900
  max_prior_share:
    default: 0.2
    min: 0.0
    max: 1.0
  onward_hours:
    default: 72
    min: 1
    max: 720
  min_onward_ratio:
    default: 0.8
    min: 0.0
    max: 1.0
  new_account_days:
    default: 90
    min: 1
    max: 900
  ring:
    default: true
  min_ring_accounts:
    default: 5
    min: 1
    max: 50
  max_ring_accounts:
    default: 200
    min: 1
    max: 2000
  max_candidates:
    default: 100000
    min: 1
    max: 1000000
metrics:
- senders
- total_amount
- currency
- window_days
- person_share
- prior_share
- onward_ratio
- onward_beneficiaries
- collector_account_days
- ring_accounts
- hubs
- span_days
- feeding_share
- fed_payments
- out_payments
wording:
  headline_structural: >-
    {senders} accounts paid {total_amount|money} into one account within {window_days|n:day}, and {onward_ratio|pct}
    of it was paid on
  headline_synthetic: >-
    Synthetic scenario: {senders} accounts paid {total_amount|money} into one account within {window_days|n:day},
    and {onward_ratio|pct} of it was paid on
  variants:
    ring:
      headline_structural: >-
        {ring_accounts} recently opened accounts paying into {hubs|n:collecting account}, {total_amount|money} in
        total
      headline_synthetic: >-
        Synthetic scenario: {ring_accounts} recently opened accounts paying into {hubs|n:collecting account}, {total_amount|money}
        in total
false_positives:
- Donation drives
- Rent collection by a landlord
- Crowdfunding campaigns paying their beneficiary
synthetic_support: high
generator_scenario: fan_in_collection
detector: neonradar_detect.detectors.fan_in_collection
```

### `detect/typologies/fan_out_distribution.yaml`

Verbatim. YAML, 85 lines. SHA-256 `dc8b7934a963d7f38872e2a13a5b31fc4514c095533ead493797a3e6554a0e29`.

```yaml
slug: fan_out_distribution
name: Fan-out distribution
shape_name: one account paying many new counterparties
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: One account pays many new counterparties in a short window, who then move the money on.
doc: docs/typologies/fan-out-distribution.md
citations:
- ffiec_appendix_f
- fatf_pml_2018
- europol_money_muling
graph_pattern: >-
  One Account paying at least ten distinct accounts with no earlier relationship within 72 hours, half of which
  pay on 80 percent of what they received within 72 hours.
parameters:
  window_hours:
    default: 72
    min: 1
    max: 720
  min_recipients:
    default: 10
    min: 1
    max: 100
  min_total:
    default: 5000.0
    min: 0.0
    max: 50000.0
  prior_days:
    default: 90
    min: 1
    max: 900
  max_prior_share:
    default: 0.2
    min: 0.0
    max: 1.0
  max_amount_cv:
    default: 0.2
    min: 0.0
    max: 1.0
  round_unit:
    default: 100.0
    min: 0.0
    max: 1000.0
  onward_hours:
    default: 72
    min: 1
    max: 720
  onward_fraction:
    default: 0.8
    min: 0.0
    max: 1.0
  min_onward_share:
    default: 0.5
    min: 0.0
    max: 1.0
  max_candidates:
    default: 100000
    min: 1
    max: 1000000
metrics:
- recipients
- total_amount
- currency
- window_hours
- amount_cv
- round_share
- prior_share
- onward_share
wording:
  headline_structural: >-
    One account paid {total_amount|money} to {recipients} new counterparties within {window_hours} hours, and {onward_share|pct}
    of them paid it on
  headline_synthetic: >-
    Synthetic scenario: one account paid {total_amount|money} to {recipients} new counterparties within {window_hours}
    hours, and {onward_share|pct} of them paid it on
false_positives:
- Payroll
- Dividends to shareholders
- Refunds after a cancelled event
synthetic_support: high
generator_scenario: fan_out_distribution
detector: neonradar_detect.detectors.fan_out_distribution
```

### `detect/typologies/dormant_reactivation.yaml`

Verbatim. YAML, 111 lines. SHA-256 `e60bd530702e6304cbb973a4dd5999b5d1cd4b865fef0b70c4e4327913564456`.

```yaml
slug: dormant_reactivation
name: Dormant account reactivation
shape_name: a burst of payments after a quiet period
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  An account with little activity for a long time suddenly moves large sums in and out; a company filed as dormant
  that moves money; a new company that receives large sums and moves them on.
doc: docs/typologies/dormant-reactivation.md
citations:
- ffiec_appendix_f
- fatf_egmont_tbml_indicators_2021
- fatf_egmont_concealment_2018
- ca_dormant_company_s1169_2006
graph_pattern: >-
  A quiet period of at least 180 days (at most two payments, 1,000 in all) followed within 14 days by at least four
  payments in both directions above max(50,000, ten times the earlier monthly mean).
parameters:
  min_gap_days:
    default: 180
    min: 1
    max: 1800
  max_quiet_payments:
    default: 2
    min: 1
    max: 20
  max_quiet_amount:
    default: 1000.0
    min: 0.0
    max: 10000.0
  burst_days:
    default: 14
    min: 1
    max: 140
  min_burst_payments:
    default: 4
    min: 1
    max: 40
  min_burst_amount:
    default: 50000.0
    min: 0.0
    max: 500000.0
  burst_ratio:
    default: 10.0
    min: 1.0
    max: 100.0
  change_days:
    default: 30
    min: 1
    max: 300
  company_variants:
    default: true
  new_company_days:
    default: 90
    min: 1
    max: 900
  min_inflow_concentration:
    default: 0.8
    min: 0.0
    max: 1.0
  min_moved_on:
    default: 0.8
    min: 0.0
    max: 1.0
  max_candidates:
    default: 100000
    min: 1
    max: 1000000
metrics:
- gap_days
- quiet_payments
- pre_gap_monthly_mean
- burst_threshold
- burst_payments
- burst_in_amount
- burst_out_amount
- burst_amount
- currency
- burst_days
- change_event
wording:
  headline_structural: >-
    Account active again after {gap_days} quiet days: {burst_amount|money} in {burst_payments|n:payment} within
    {burst_days|n:day}
  headline_synthetic: >-
    Synthetic scenario: account active again after {gap_days} quiet days: {burst_amount|money} in {burst_payments|n:payment}
    within {burst_days|n:day}
  variants:
    dormant_company:
      headline_structural: >-
        Company whose last accounts were filed as dormant moved {burst_amount|money} in {burst_payments|n:payment}
        within {burst_days|n:day}
      headline_synthetic: >-
        Synthetic scenario: company whose last accounts were filed as dormant moved {burst_amount|money} in {burst_payments|n:payment}
        within {burst_days|n:day}
    new_company:
      headline_structural: >-
        Recently incorporated company moved {burst_amount|money} in {burst_payments|n:payment} within {burst_days|n:day}
      headline_synthetic: >-
        Synthetic scenario: recently incorporated company moved {burst_amount|money} in {burst_payments|n:payment}
        within {burst_days|n:day}
false_positives:
- Seasonal businesses reopening
- A property sale paid into a quiet personal account
- A business restarting under a new owner
synthetic_support: high
generator_scenario: dormant_reactivation
detector: neonradar_detect.detectors.dormant_reactivation
```

### `detect/tests/test_detector_fan_in_collection.py`

Verbatim. Python, 81 lines. SHA-256 `3b33538ec1aa24ca6547863b8c643be3160e9f73420fb0b9f10d30d0e5535042`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import fan_in_collection as fi
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return fi.run(source_of(k.records), fi.Params(**overrides), WINDOW).findings


def test_collector_opened_recently_pays_on():
    k = Kit()
    k.history()
    coll = k.account("coll", k.person("coll"), opened="2026-02-15")
    out = k.account("out", k.company("out", jurisdiction="hk"))
    ins = []
    for i in range(10):
        s = k.account(
            f"m{i}", k.person(f"m{i}"), opened="2012-05-01"
        )  # senders: often victims, old accounts
        ins.append(k.pay(s, coll, 800, f"2026-03-0{1 + i % 3}T1{i}:00"))
    o = k.pay(coll, out, 7500, "2026-03-05T10:00")
    [f] = _run(k, ring=False)
    assert f.variant == "collector" and f.edge_ids == tuple(sorted([*ins, o]))
    assert f.metrics["senders"] == 10 and f.metrics["collector_account_days"] == 14
    assert f.metrics["onward_ratio"] == 0.9375 and f.metrics["prior_share"] == 0.0
    assert (
        f.pattern_strength == 0.8344
    )  # 0.3 * 10/20 + 0.25 * (1 - 0) + 0.25 * 0.9375 + 0.2 (new collector)
    late = Kit()
    late.history()
    c2 = late.account("c2", late.person("c2"))
    for i in range(10):
        late.pay(late.account(f"n{i}", late.person(f"n{i}")), c2, 800, f"2026-03-02T1{i}:00")
    late.pay(c2, late.account("o2", late.company("o2")), 7500, "2026-03-10T10:00")  # after 72 hours
    assert _run(late, ring=False) == []


def test_charity_and_landlord_lookalikes():
    k = Kit()
    charity = k.account("charity", k.company("charity", sector="charity"))
    for i in range(40):
        s = k.account(f"d{i}", k.person(f"d{i}"), opened="2018-01-01")
        k.pay(s, charity, 200, f"2026-04-0{1 + i % 5}T1{i % 9}:00")
    landlord_acct = k.account("landlord", k.person("landlord"))
    bank = k.account("mortgage", k.company("lender"))
    for i in range(10):
        t = k.account(f"t{i}", k.person(f"t{i}"), opened="2019-01-01")
        for month in ("2025-12", "2026-01", "2026-02"):
            k.pay(t, landlord_acct, 900, f"{month}-01T0{i % 9}:00")
    for month in ("2026-01", "2026-02"):
        k.pay(landlord_acct, bank, 8000, f"{month}-03T09:00")
    assert _run(k) == []


def test_ring_of_new_accounts():
    k = Kit()
    sink = k.account("sink", k.person("sink"), opened="2026-02-25")
    cash = k.account("cash", k.person("cash"), opened="2026-02-26")
    edges, fed = [], []
    for i in range(4):
        mule = k.account(f"r{i}", k.person(f"r{i}"), opened=f"2026-02-2{i}")
        for v in range(2):
            victim = k.account(f"v{i}{v}", k.person(f"v{i}{v}"), opened="2015-05-05")
            fed.append(k.pay(victim, mule, 1500, f"2026-03-0{2 + v}T10:00"))
        edges.append(k.pay(mule, sink, 2900, f"2026-03-04T1{i}:00"))
    edges.append(k.pay(sink, cash, 11000, "2026-03-05T09:00"))
    found = _run(k)
    [ring] = [f for f in found if f.variant == "ring"]
    # the ring's own payments, and the payments from old accounts that fed it
    assert ring.anchor == sink and ring.edge_ids == tuple(sorted(edges + fed))
    assert (
        ring.metrics["ring_accounts"] == 6
        and ring.metrics["hubs"] == 1
        and ring.metrics["fed_payments"] == 8
    )
    assert ring.metrics["feeding_share"] == 0.6667
    assert _run(k, ring=False) == []
```

### `detect/tests/test_detector_fan_out_distribution.py`

Verbatim. Python, 55 lines. SHA-256 `cd431e877335ba041fc72aa3946d44feb5c3b5ca343a2598ddc45a259077bff2`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import fan_out_distribution as fo
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return fo.run(source_of(k.records), fo.Params(**overrides), WINDOW).findings


def test_distribution_to_new_accounts_that_cash_out():
    k = Kit()
    k.history()
    branch = k.account("branch", k.company("bank"), kind="cash_ledger")
    dist = k.account("dist", k.company("dist"))
    edges = []
    for i in range(10):
        r = k.account(f"r{i}", k.person(f"r{i}"), opened="2026-02-01")
        edges.append(k.pay(dist, r, 950, f"2026-03-02T1{i % 9}:00"))
        edges.append(k.pay(r, branch, 900, "2026-03-04T12:00", channel="cash_withdrawal"))
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted(edges))
    assert f.metrics["recipients"] == 10 and f.metrics["onward_share"] == 1.0
    assert f.metrics["round_share"] == 0.0 and f.metrics["amount_cv"] == 0.0


def test_payroll_and_refund_lookalikes():
    k = Kit()
    employer = k.account("employer", k.company("employer"))
    employees = [k.account(f"e{i}", k.person(f"e{i}")) for i in range(10)]
    shop = k.account("shopx", k.company("shopx"))
    for month in ("01", "02", "03"):
        for i, e in enumerate(employees):
            k.pay(employer, e, 1800 + 140 * i, f"2026-{month}-25T08:00")
            k.pay(e, shop, 300, f"2026-{month}-26T12:00")
    organiser = k.account("organiser", k.company("organiser"))
    for i in range(12):
        c = k.account(f"c{i}", k.person(f"c{i}"))
        k.pay(c, organiser, 400, "2026-04-02T10:00")
        k.pay(organiser, c, 400, "2026-05-10T10:00")
    assert _run(k) == []


def test_first_payroll_is_not_found_because_salaries_stay():
    k = Kit()
    employer = k.account("employer", k.company("employer"))
    shop = k.account("shopy", k.company("shopy"))
    for i in range(10):
        e = k.account(f"n{i}", k.person(f"n{i}"))
        k.pay(employer, e, 2000, "2026-01-30T08:00")
        k.pay(e, shop, 250, "2026-02-01T12:00")
    assert _run(k) == []
```

### `detect/tests/test_detector_dormant_reactivation.py`

Verbatim. Python, 107 lines. SHA-256 `32177af700695006f2b5f39cfa5e5de96c74ff892427a676135b08987484e0bc`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import dormant_reactivation as dr
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return dr.run(source_of(k.records), dr.Params(**overrides), WINDOW).findings


def _burst(k: Kit, acct: str, day: str, n: int = 6, amount: float = 10000) -> list[str]:
    others = [k.account(f"{acct[-6:]}x{i}", k.company(f"{acct[-6:]}x{i}")) for i in range(n)]
    return [
        k.pay(o, acct, amount, f"{day}T1{i}:00")
        if i % 2 == 0
        else k.pay(acct, o, amount * 0.95, f"{day}T1{i}:30")
        for i, o in enumerate(others)
    ]


def _quiet_account(k: Kit, name: str, opened: str = "2013-01-01") -> tuple[str, str]:
    co = k.company(name, incorporated="2012-05-01")
    acct = k.account(name, co, opened=opened)
    old = k.account(f"{name}-old", k.company(f"{name}-old"))
    k.pay(old, acct, 500, "2025-02-03T10:00")
    k.pay(acct, old, 450, "2025-02-20T10:00")
    return co, acct


def test_long_gap_then_burst_after_new_director():
    k = Kit()
    co, acct = _quiet_account(k, "dorm")
    director = k.person("newdir")
    k.director(director, co, start="2026-02-10")
    e = _burst(k, acct, "2026-03-02")
    [f] = _run(k)
    # the longest quiet period: little activity (one payment of 450) for 392 days
    assert (
        f.variant == "account" and f.metrics["gap_days"] == 392 and f.metrics["quiet_payments"] == 1
    )
    assert f.metrics["change_event"] == "director appointed" and f.metrics["burst_payments"] == 6
    assert (
        f.metrics["burst_threshold"] == 50000.0
    )  # 10 times the pre-gap mean (500 a month) is lower
    assert set(e) <= set(f.edge_ids) and director in f.node_ids
    assert f.pattern_strength == round(0.3 + 0.3 * 58500 / 250000 + 0.2 * 6 / 12 + 0.2, 4)


def test_little_activity_is_allowed_in_the_quiet_period():
    k = Kit()
    _, acct = _quiet_account(k, "small")
    fee = k.account("fee", k.company("fee"))
    k.pay(acct, fee, 12.5, "2025-10-01T09:00")
    k.pay(fee, acct, 400, "2025-12-01T09:00")
    _burst(k, acct, "2026-03-02")
    [f] = _run(k)
    assert f.metrics["quiet_payments"] == 2 and f.metrics["gap_days"] == 375  # from 2025-02-20
    assert _run(k, max_quiet_payments=1) == []  # the second small payment breaks the gap


def test_quiet_period_needs_history_before_it():
    k = Kit()
    k.history("2025-02-03T10:00")
    old = k.account("censored", k.company("censored"), opened="2020-01-01")
    _burst(k, old, "2026-03-02")
    young = k.account("young", k.company("young"), opened="2025-03-01")
    _burst(k, young, "2026-03-03")
    # opened before the first payment in the data: nothing is known about its earlier activity
    assert [(f.anchor, f.metrics["gap_days"]) for f in _run(k)] == [(young, 367)]


def test_seasonal_business_comes_back_at_its_usual_level():
    k = Kit()
    acct = k.account("season", k.company("season", sector="tourism"), opened="2020-01-01")
    guests = [k.account(f"g{i}", k.person(f"g{i}")) for i in range(6)]
    for month in range(4, 10):  # open April to September 2025, then closed until April 2026
        for d, g in enumerate(guests):
            k.pay(g, acct, 4000, f"2025-{month:02d}-{d + 10:02d}T12:00")
        k.pay(acct, guests[0], 9000, f"2025-{month:02d}-28T12:00")
    _burst(k, acct, "2026-04-02")
    assert _run(k) == []  # a 183-day gap, but the burst is below 10 times the monthly mean
    assert len(_run(k, burst_ratio=1.0)) == 1


def test_company_variants():
    k = Kit()
    dormant = k.account(
        "dco", k.company("dco", incorporated="2016-01-01", accounts_category="DORMANT")
    )
    _burst(k, dormant, "2026-02-02")
    fresh = k.account("fresh", k.company("fresh", incorporated="2026-02-15"), opened="2026-02-20")
    funders = [k.account(f"fund{i}", k.company(f"fund{i}")) for i in range(2)]
    for i, f in enumerate(funders):
        k.pay(f, fresh, 40000, f"2026-03-0{3 + i}T10:00")
    for i in range(3):
        k.pay(fresh, k.account(f"away{i}", k.company(f"away{i}")), 25000, f"2026-03-0{5 + i}T12:00")
    trader = k.account(
        "trader", k.company("trader", incorporated="2026-02-15"), opened="2026-02-20"
    )
    _burst(k, trader, "2026-03-03")  # ordinary trading: GBP 30,000 in, 28,500 out
    found = {f.anchor: f.variant for f in _run(k)}
    assert found == {dormant: "dormant_company", fresh: "new_company"}
    # without them nothing is left: both accounts lack history before a quiet period
    assert _run(k, company_variants=False) == []
```

## M3.5d Payment chains: `layering_chain`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 3 verbatim files (PHASE-3.md M3.5d).

### `detect/src/neonradar_detect/detectors/layering_chain.py`

Verbatim. Python, 239 lines. SHA-256 `ca77f5252ea8e01c909e4a6f8ae139cc78974d2fecddf36674222b9d12244771`.

```python
"""layering_chain 0.2.0: funds passed on through a chain of accounts of different holders
(PHASE-1.md 7.2 entry 3; `typology-detection-definitions.md` section 3; PHASE-3.md 7.3.3).

Starts are payments of at least `min_amount`. Each next hop leaves the account the previous hop
reached, within `max_dwell_hours` after it, in the same currency, for between `min_hop_ratio` and
`1 + max_hop_gain` times the previous amount, to an account none of whose holders held an account
earlier in the chain (so a return to the origin's side is left to `circular_flow`). A chain of
`min_hops` to `max_hops` payments whose last amount is at least `min_retained_ratio` of its first
(fees of "5-20 %" of the sum, Europol EFECTA 2023) is a finding unless it lies inside a longer
chain that is one. Splits and merges are not followed: a chain that splits is found only up to the
split (a documented limitation; the generator plants such chains, 7.2.5).

What makes a chain more than commerce is the registry around it (PHASE-1.md 7.2): the detector
counts pairs of holders in the chain that share a registered address, a director or an agent, and
intermediate accounts with little other activity. On a real profile the policy withholds every
chain that touches a real entity (R-REAL), so these counts only ever combine synthetic data.

pattern_strength = 0.25 * min(1, (hops - 2) / 4) + 0.25 * retained ratio + 0.2 * (1 - longest
dwell / max_dwell_hours) + 0.15 * share of quiet intermediaries + 0.15 * min(1, linked holder
pairs / 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations, pairwise

from neonradar_detect.expand import FrontierItem, Path, expand
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import Hop
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "layering_chain"
VERSION = "0.2.0"
QUERIES = (
    "activity_counts.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "paid_hop.cypher",
    "paid_starts.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    min_hops: int = 3
    max_hops: int = 6
    max_dwell_hours: int = 72
    min_hop_ratio: float = 0.85
    max_hop_gain: float = 0.02
    min_retained_ratio: float = 0.8
    min_amount: float = 10000.0
    quiet_days: int = 30
    max_quiet_payments: int = 5
    max_starts: int = 1_000_000
    max_branching: int = 10
    max_frontier: int = 50_000


def _holders_so_far(path: Path) -> set[str]:
    held = set(path.first.source_holders)
    for h in path.hops:
        held.update(h.target_holders)
    return held


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    if not 3 <= p.min_hops <= p.max_hops <= 8:
        raise ValueError("need 3 <= min_hops <= max_hops <= 8")
    dwell = timedelta(hours=p.max_dwell_hours)
    starts = [
        h
        for h in source.paid_starts(p.min_amount, window.start, window.end, p.max_starts)
        if not set(h.source_holders) & set(h.target_holders)
    ]

    def extend(path: Path, key: int) -> FrontierItem | None:
        if len(path.hops) >= p.max_hops:
            return None
        last = path.last
        return FrontierItem(
            key=key,
            account=last.target,
            after=last.ts,
            until=last.ts + dwell,
            min_amount=p.min_hop_ratio * last.amount,
            max_amount=(1 + p.max_hop_gain) * last.amount,
            currency=last.currency,
            visited=tuple(sorted(set(path.accounts))),
        )

    def keep(path: Path, hop: Hop) -> bool:
        return bool(hop.target_holders) and not set(hop.target_holders) & _holders_so_far(path)

    def accept(path: Path) -> bool:
        return (
            len(path.hops) >= p.min_hops
            and path.last.amount >= p.min_retained_ratio * path.first.amount
        )

    chains, stats = expand(
        starts,
        source.paid_hop,
        extend=extend,
        keep=keep,
        accept=accept,
        max_hops=p.max_hops,
        max_branching=p.max_branching,
        max_frontier=p.max_frontier,
    )
    maximal = _maximal(chains)
    findings = [_finding(c, p, source) for c in maximal]
    return DetectorOutput(
        findings,
        {
            "starts": len(starts),
            "partial_paths": stats.partial_paths,
            "truncated": stats.truncated,
            "chains": len(chains),
        },
    )


def _maximal(chains: list[Path]) -> list[Path]:
    """Chains whose payments are not all part of a longer chain, in a stable order."""
    ordered = sorted(
        chains, key=lambda c: (-len(c.hops), c.first.ts, tuple(h.edge_id for h in c.hops))
    )
    kept: list[Path] = []
    kept_sets: list[frozenset[str]] = []
    for chain in ordered:
        edges = frozenset(h.edge_id for h in chain.hops)
        if any(edges <= other for other in kept_sets):
            continue
        kept.append(chain)
        kept_sets.append(edges)
    return sorted(kept, key=lambda c: (c.first.ts, tuple(h.edge_id for h in c.hops)))


def _finding(chain: Path, p: Params, source: Source) -> Finding:
    first, last = chain.first, chain.last
    hops = len(chain.hops)
    hours = (last.ts - first.ts).total_seconds() / 3600
    dwells = [(b.ts - a.ts).total_seconds() / 3600 for a, b in pairwise(chain.hops)]
    longest = max(dwells)
    retained = last.amount / first.amount
    # holders of each account in order; the chain rule keeps them disjoint
    holders = [tuple(sorted(first.source_holders))] + [
        tuple(sorted(h.target_holders)) for h in chain.hops
    ]
    all_holders = sorted({x for hs in holders for x in hs})
    linked, link_nodes, link_edges, link_steps = _linked_pairs(all_holders, source)
    quiet_from = first.ts - timedelta(days=p.quiet_days)
    quiet_to = last.ts + timedelta(days=p.quiet_days)
    intermediates = list(chain.accounts[1:-1])
    counts = source.activity_counts(intermediates, quiet_from, quiet_to)
    chain_edges = {h.edge_id for h in chain.hops}
    quiet = 0
    for account in intermediates:
        own = sum(1 for h in chain.hops if account in (h.source, h.target))
        if counts.get(account, 0) - own <= p.max_quiet_payments:
            quiet += 1
    quiet_share = quiet / len(intermediates)
    strength = clip01(
        0.25 * min(1.0, (hops - 2) / 4)
        + 0.25 * min(1.0, retained)
        + 0.2 * (1 - longest / p.max_dwell_hours)
        + 0.15 * quiet_share
        + 0.15 * min(1.0, linked / 2)
    )
    subjects = [Subject(first.source, "origin")]
    subjects += [Subject(h, "origin_holder") for h in holders[0]]
    subjects.append(Subject(last.target, "destination"))
    subjects += [Subject(h, "destination_holder") for h in holders[-1]]
    metrics = {
        "chain_length": hops,
        "first_amount": round(first.amount, 2),
        "last_amount": round(last.amount, 2),
        "currency": first.currency,
        "duration_hours": round(hours, 1),
        "duration_days": max(1, math.ceil(hours / 24)),
        "retained_ratio": round(retained, 4),
        "longest_dwell_hours": round(longest, 1),
        "holders": len(all_holders),
        "linked_holder_pairs": linked,
        "quiet_intermediaries": quiet,
    }
    node_ids = set(chain.accounts) | link_nodes
    if link_nodes:
        node_ids |= set(all_holders)
    return Finding(
        typology=SLUG,
        variant="",
        anchor=first.source,
        node_ids=tuple(sorted(node_ids)),
        edge_ids=tuple(sorted(chain_edges | link_edges)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple((h.edge_id,) for h in chain.hops) + tuple(link_steps),
        window=(first.ts, last.ts),
        activity=True,
    )


def _linked_pairs(
    holders: list[str], source: Source
) -> tuple[int, set[str], set[str], list[tuple[str, ...]]]:
    """Pairs of holders that share a registered address, a director or an agent."""
    addresses = source.links_from(holders, ("HAS_ADDRESS",))
    into = source.links_into(holders, ("DIRECTOR_OF", "REPRESENTS"))
    shared: dict[str, dict[str, str]] = {}  # holder -> {shared key: relationship id}
    for h in holders:
        keys: dict[str, str] = {}
        for link in addresses.get(h, []):
            if link.role == "registered":
                keys[f"address:{link.target}"] = link.rel_id
        for link in into.get(h, []):
            kind = "director" if link.rel_type == "DIRECTOR_OF" else "agent"
            keys[f"{kind}:{link.source}"] = link.rel_id
        shared[h] = keys
    linked = 0
    nodes: set[str] = set()
    edges: set[str] = set()
    steps: list[tuple[str, ...]] = []
    for a, b in combinations(holders, 2):
        common = sorted(set(shared[a]) & set(shared[b]))
        if not common:
            continue
        linked += 1
        key = common[0]
        node = key.split(":", 1)[1]
        pair_edges = tuple(sorted((shared[a][key], shared[b][key])))
        nodes.add(node)
        edges.update(pair_edges)
        steps.append(pair_edges)
    return linked, nodes, edges, steps
```

### `detect/typologies/layering_chain.yaml`

Verbatim. YAML, 92 lines. SHA-256 `046ec023787f2bcd5f8b3132168194c37bc555b61745e0328296c551a7d0bb9f`.

```yaml
slug: layering_chain
name: Layering chain
shape_name: a chain of onward transfers between different holders
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: Funds passed on through a chain of accounts of different holders, losing a little at each step.
doc: docs/typologies/layering-chain.md
citations:
- fatf_faq
- europol_efecta_2023
- fatf_pml_2018
- ffiec_appendix_f
graph_pattern: >-
  A time-ordered path of three to six PAID relationships, each within 72 hours of the last and between 85 and 102
  percent of it, through accounts of distinct holders.
parameters:
  min_hops:
    default: 3
    min: 2
    max: 8
  max_hops:
    default: 6
    min: 1
    max: 8
  max_dwell_hours:
    default: 72
    min: 1
    max: 720
  min_hop_ratio:
    default: 0.85
    min: 0.0
    max: 1.0
  max_hop_gain:
    default: 0.02
    min: 0.0
    max: 0.5
  min_retained_ratio:
    default: 0.8
    min: 0.0
    max: 1.0
  min_amount:
    default: 10000.0
    min: 0.0
    max: 100000.0
  quiet_days:
    default: 30
    min: 1
    max: 300
  max_quiet_payments:
    default: 5
    min: 1
    max: 50
  max_starts:
    default: 1000000
    min: 1
    max: 10000000
  max_branching:
    default: 10
    min: 1
    max: 100
  max_frontier:
    default: 50000
    min: 1
    max: 500000
metrics:
- chain_length
- first_amount
- last_amount
- currency
- duration_hours
- duration_days
- retained_ratio
- longest_dwell_hours
- holders
- linked_holder_pairs
- quiet_intermediaries
wording:
  headline_structural: >-
    {first_amount|money} passed on through {chain_length} transfers between accounts of different holders within
    {duration_days|n:day}
  headline_synthetic: >-
    Synthetic scenario: {first_amount|money} passed on through {chain_length} transfers between accounts of different
    holders within {duration_days|n:day}
false_positives:
- Supply chains paying on for goods
- Group treasury moving funds between subsidiaries
synthetic_support: high
generator_scenario: layering_chain
detector: neonradar_detect.detectors.layering_chain
```

### `detect/tests/test_detector_layering_chain.py`

Verbatim. Python, 88 lines. SHA-256 `b865542d4cd9e4919358296ef4c1bd76f64eb6d63e02d3480166bf7fd0f20447`.

```python
from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import layering_chain as lc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _chain(
    k: Kit, tag: str, amounts: list[float], times: list[str], *, shared_address: bool = False
) -> list[str]:
    addr = k.address(f"{tag}-addr") if shared_address else ""
    accounts = [
        k.account(f"{tag}{i}", k.company(f"{tag}{i}", address=addr if 0 < i < len(amounts) else ""))
        for i in range(len(amounts) + 1)
    ]
    return [k.pay(accounts[i], accounts[i + 1], amounts[i], times[i]) for i in range(len(amounts))]


def _run(k: Kit, **overrides):
    out = lc.run(source_of(k.records), lc.Params(**overrides), WINDOW)
    return out.findings


def test_four_hop_chain_with_shared_address():
    k = Kit()
    e = _chain(
        k,
        "a",
        [250000, 245000, 240100, 235300],
        ["2026-02-02T09:00", "2026-02-03T11:00", "2026-02-04T15:00", "2026-02-06T10:00"],
        shared_address=True,
    )
    [f] = _run(k)
    assert f.steps[:4] == tuple((x,) for x in e)
    assert f.metrics["chain_length"] == 4 and f.metrics["linked_holder_pairs"] == 3
    assert f.metrics["quiet_intermediaries"] == 3
    assert len(f.steps) == 7  # four payments, three shared-address links
    assert [s.role for s in f.subjects] == [
        "origin",
        "origin_holder",
        "destination",
        "destination_holder",
    ]


def test_prefix_and_suffix_are_not_reported_separately():
    k = Kit()
    _chain(
        k,
        "b",
        [50000, 49000, 48000, 47500, 47000],
        [
            "2026-03-02T09:00",
            "2026-03-02T15:00",
            "2026-03-03T09:00",
            "2026-03-04T09:00",
            "2026-03-05T09:00",
        ],
    )
    found = _run(k)
    assert [f.metrics["chain_length"] for f in found] == [5]


def test_dwell_amount_and_holder_rules():
    k = Kit()
    _chain(
        k, "c", [50000, 49000, 48000], ["2026-03-02T09:00", "2026-03-08T09:00", "2026-03-09T09:00"]
    )  # 6 days dwell
    _chain(
        k, "d", [50000, 30000, 29500], ["2026-03-02T09:00", "2026-03-02T15:00", "2026-03-03T09:00"]
    )  # split
    # third hop back to an account of the first holder: left to circular_flow
    holder = k.company("eh")
    a0, a3 = k.account("e0", holder), k.account("e3", holder)
    a1, a2 = k.account("e1", k.company("e1")), k.account("e2", k.company("e2"))
    k.pay(a0, a1, 40000, "2026-04-01T09:00")
    k.pay(a1, a2, 39500, "2026-04-01T12:00")
    k.pay(a2, a3, 39000, "2026-04-01T18:00")
    assert _run(k) == []


def test_three_hops_found_when_allowed_but_not_below_min_amount():
    k = Kit()
    _chain(k, "f", [9000, 8900, 8800], ["2026-05-02T09:00", "2026-05-02T12:00", "2026-05-02T18:00"])
    assert _run(k) == []
    assert len(_run(k, min_amount=5000)) == 1
```

## M3.5e Sanctions exposure: `sanctions_exposure`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 3 verbatim files (PHASE-3.md M3.5e).

### `detect/src/neonradar_detect/detectors/sanctions_exposure.py`

Verbatim. Python, 679 lines. SHA-256 `d22a157558da658171661b86d54c13a81255f99e7a82a0a51c058361372bfdf8`.

```python
"""sanctions_exposure 0.2.0: an organisation without a sanctions flag of its own that listed
parties own or control, judged with each regime's own test (PHASE-1.md 7.2 entry 10, corrected
by `typology-detection-definitions.md` section 10; PHASE-3.md 7.3.10).

Registry evidence only, and only relationships that still hold at the end of the window (no end
date, or a later one): a sold holding or a resigned director is history. Each regime is seeded
with its own list only:

- `us`, the OFAC 50 Percent Rule: entities designated on `us_ofac_sdn`. Owners count in full and
  are added up across all listed owners; "50 percent or greater" passes the status on, entity by
  entity (OFAC FAQ 399 and 401). Ownership only (FAQ 398).
- `eu`, Council Best Practices 2024 para 63: entities designated on `eu_fsf`. The same arithmetic
  with "50% or more"; the entity-by-entity chain is NeonRadar's reading. Control criteria are
  reported apart: an appointment right is criterion (a), a CONSOLIDATES link from a listed parent
  criterion (g) (a NeonRadar reading of "while publishing consolidated accounts").
- `uk`, Russia Regulations 2019 reg 7 and Schedule 1 (NeonRadar applies the same test to every UK
  regime): entities with a `gb_fcdo_sanctions` designation whose provisions include an asset
  freeze. Per listed person: OFSI "would not simply aggregate" different listed persons'
  holdings unless, for example, they are held under a joint arrangement or one party controls
  the rights of another, which C2 cannot show. More than 50 percent of the shares or of the
  voting rights, or a right to appoint or remove a majority of the board, held directly or
  through entities the person has a majority stake in (a voting band of more than 50 percent or
  a board right; when a link has no voting band, shares stand in for votes and the finding says
  so with `votes_follow_shares`); the person's direct and indirect holdings are added (a reading
  of "directly or indirectly" and para 4). A holding recorded as a nominee holding is not
  counted for the nominee (Schedule 1 para 10: it is treated as held by the person it is held
  for, whom the records do not name; `uk_nominee_holdings` counts them). A designation whose
  provisions are empty may or may not include an asset freeze: it gives `left open by the
  bands` at most, with `uk_measures_unknown`.

A synthetic listed entity (dataset `nr_synthetic`) seeds all three tests. A designation with an
end date on or before the end of the window seeds nothing. The candidate step collects the OWNS
and CONTROLS relationships within `max_hops` of a seed (one `links_from` call per hop) and the
CONSOLIDATES and DIRECTOR_OF relationships that start at a seed.

Each test runs on the lower and on the upper bounds of the published bands (a missing upper bound
counts as 100 and is reported as `unbounded`), giving `met on the records`, `left open by the
bands`, `not met on the records`, or `no listed owner from this list`. Nothing is multiplied for
the tests. `listed_share_min` and `listed_share_max` are the recorded holdings in the
organisation of listed parties and of entities that pass the US and EU test on the same bounds,
added up (capped at 100); the effective share (products along each OWNS path, summed per listed
owner, the largest owner reported) is a teaching figure only (PHASE-2.md 7.2 rule 6). Natural
persons are never owned; only organisations become subjects, while other non-person legal
entities pass a status on.

A finding is made for an organisation with a test met or left open, a direct CONTROLS,
CONSOLIDATES or DIRECTOR_OF link from a seed, or listed holdings that can reach
`min_reported_share` percent (a modelling choice: 25 is the PSC register's floor, below which
holdings are not recorded at all; OFAC advises caution with "a significant ownership interest that
is less than 50 percent"). The `assessment` metric puts every regime's result into words for the
summary (`wording.detail`), with the control results and the limits of the records; the headline
names only the shape and the lists.

pattern_strength = 0.6 * ownership score + 0.2 * proximity + 0.2 * control score: the ownership
score is 1 when a test is met, 0.7 when one is left open, else `listed_share_min` / 100; proximity
is 1 - (shortest path - 1) / max_hops; the control score is 1 for a direct CONTROLS or
CONSOLIDATES link from a seed, 0.5 for a directorship alone. Priority: high whenever a test is
met on the records (the typology's own rule, C4).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow, ListedRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "sanctions_exposure"
VERSION = "0.2.0"
QUERIES = ("entities.cypher", "links_from.cypher", "listed_entities.cypher")
REGIMES = ("us", "eu", "uk")
LISTS = {"us": "us_ofac_sdn", "eu": "eu_fsf", "uk": "gb_fcdo_sanctions"}
SYNTHETIC = "nr_synthetic"
ASSET_FREEZE = "asset freeze"
MET = "met on the records"
OPEN = "left open by the bands"
NOT_MET = "not met on the records"
NONE = "no listed owner from this list"
LIST_NAMES = {
    "us": "the OFAC SDN List",
    "eu": "the EU consolidated list",
    "uk": "the UK Sanctions List",
}
SYNTHETIC_LIST = "a synthetic sanctions list"
# The summary's sentences (typology-detection-definitions.md 10.4); {list} names the list.
RESULT = {
    ("us", MET): "US test: recorded holdings of parties on {list} reach at least 50 percent, "
    "counting in full any entity that itself reaches that level (the method of OFAC FAQ 401).",
    ("us", OPEN): "US test: the published share bands leave open whether recorded holdings of "
    "parties on {list} reach 50 percent; the share register would settle it.",
    ("us", NOT_MET): "US test: recorded holdings of parties on {list} stay below 50 percent on "
    "these records.",
    ("eu", MET): "EU test: recorded holdings of parties on {list} reach 50 percent or more, added "
    "together as the Council's Best Practices describe.",
    ("eu", OPEN): "EU test: the published share bands leave open whether recorded holdings of "
    "parties on {list} reach 50 percent.",
    ("eu", NOT_MET): "EU test: recorded holdings of parties on {list} stay below 50 percent on "
    "these records.",
    ("uk", MET): "UK test: one party on {list} is recorded with more than 50 percent of the shares "
    "or voting rights, or the right to appoint or remove a majority of the board, directly or "
    "through entities it has a majority stake in.",
    ("uk", OPEN): "UK test: the published share bands leave open whether one party on {list} "
    "holds more than 50 percent.",
    ("uk", NOT_MET): "UK test: on the records this test counts, no single party on {list} holds "
    "more than 50 percent of the shares or voting rights, or the right to appoint or remove a "
    "majority of the board.",
}
US_CAUTION = (
    "A party on {list} is recorded with control other than majority ownership; the OFAC test "
    "counts ownership only (FAQ 398), and OFAC advises caution where listed parties may control "
    "an entity by other means."
)
UK_CONTROL = (
    "A party on {list} is recorded with other control (significant influence or a "
    "directorship); whether the UK control condition is met cannot be decided from these records."
)
UK_SEVERAL = (
    "OFSI does not simply add different listed parties' holdings together unless, for example, "
    "they are held under a joint arrangement or one party controls the rights of another, which "
    "these records cannot show."
)
UK_VOTES = "Voting rights were taken to follow shares where the register records no voting band."
UK_NOMINEE = (
    "Holdings recorded as nominee holdings were not counted for their holders: UK law treats a "
    "nominee's share as held by the person it is held for, whom these records do not name."
)
UK_UNKNOWN = (
    "A UK list entry here does not record whether it includes an asset freeze, so the UK result "
    "is left open."
)
EU_CRITERIA = {
    "(a)": "the right to appoint or remove a majority of the board",
    "(g)": "management on a unified basis with consolidated accounts",
}
EU_CONTROL = (
    "EU control criterion {criteria} is recorded for a party on {list}; the criteria can be "
    "rebutted case by case, and control is for the national authorities to assess."
)
CLOSING = (
    "These are NeonRadar calculations from the recorded share bands and links, not findings by "
    "OFAC, OFSI, the EU or a national authority."
)


@dataclass(frozen=True, slots=True)
class Params:
    max_hops: int = 6
    max_links: int = 200_000
    max_paths: int = 1_000
    max_steps: int = 12
    min_reported_share: float = 25.0


Bound = tuple[float, bool]  # (value, exclusive)


def bound(link: LinkRow, upper: bool) -> Bound:
    if upper:
        return (
            (link.share_max, link.share_max_exclusive)
            if link.share_max is not None
            else (100.0, False)
        )
    return (
        (link.share_min, link.share_min_exclusive) if link.share_min is not None else (0.0, False)
    )


def passes(terms: list[Bound], strict: bool, upper: bool) -> bool:
    """Whether a sum of band bounds meets "at least 50" (or "more than 50" when `strict`).

    Lower bounds: the true sum is at least their total, and more if any is open. Upper bounds:
    at most their total (capped at 100), and less if any is open (section 10.2)."""
    if not terms:
        return False
    total = min(100.0, round(sum(v for v, _ in terms), 9))
    is_open = any(x for _, x in terms)
    if total != 50:
        return total > 50
    if upper:
        return not strict and not is_open
    return is_open or not strict


def seeds(listed: list[ListedRow], as_of: str) -> tuple[dict[str, set[str]], set[str]]:
    """The seed set of each regime, and the UK entries whose provisions are not recorded."""
    out: dict[str, set[str]] = {r: set() for r in REGIMES}
    unknown: set[str] = set()
    for row in listed:
        current = [s for s in row.sanctions if not (s.end_date and s.end_date <= as_of)]
        if SYNTHETIC in row.datasets:
            if current or not row.sanctions:
                for r in REGIMES:
                    out[r].add(row.entity)
            continue
        for s in current:
            if LISTS["us"] in s.datasets:
                out["us"].add(row.entity)
            if LISTS["eu"] in s.datasets:
                out["eu"].add(row.entity)
            if LISTS["uk"] in s.datasets:
                if any(x.casefold() == ASSET_FREEZE for x in s.provisions):
                    out["uk"].add(row.entity)
                elif not s.provisions:
                    unknown.add(row.entity)
    return out, unknown - out["uk"]


def _appoints(link: LinkRow) -> bool:
    return link.rel_type == "CONTROLS" and link.control_type == "appointment"


def _voting(link: LinkRow) -> bool:
    return (
        link.rel_type == "CONTROLS" and link.control_type == "voting" and link.share_min is not None
    )


def aggregate_test(
    start: set[str], owns_into: dict[str, list[LinkRow]], ownable: set[str], upper: bool
) -> set[str]:
    """US and EU: the entities that listed owners, and entities passing the test, own at least
    50 percent of together, entity by entity (section 10.2). The seeds are included."""
    held = set(start)
    changed = True
    while changed:
        changed = False
        for target in sorted(owns_into):
            if target in held or target not in ownable:
                continue
            terms = [bound(x, upper) for x in owns_into[target] if x.source in held]
            if passes(terms, False, upper):
                held.add(target)
                changed = True
    return held


def _stake(
    seed: str,
    owns_from: dict[str, list[LinkRow]],
    controls_from: dict[str, list[LinkRow]],
    ownable: set[str],
    upper: bool,
    proxy: bool,
) -> set[str]:
    """The seed and the entities it has a majority stake in, directly or down a chain: a voting
    band of more than 50 percent or a board appointment right; with `proxy`, shares of more than
    50 percent where a link has no voting band. Nominee holdings do not count (Sch 1 para 10)."""
    stake = {seed}
    changed = True
    while changed:
        changed = False
        for m in sorted(stake):
            for b in sorted({x.target for x in owns_from[m] + controls_from[m]} - stake):
                if b not in ownable:
                    continue
                links = [x for x in controls_from[m] if x.target == b]
                votes = [bound(x, upper) for x in links if _voting(x)]
                shares = [
                    bound(x, upper) for x in owns_from[m] if x.target == b and not x.is_nominee
                ]
                if (
                    any(_appoints(x) for x in links)
                    or passes(votes, True, upper)
                    or (proxy and not votes and passes(shares, True, upper))
                ):
                    stake.add(b)
                    changed = True
    return stake


def uk_test(
    seed: str,
    owns_from: dict[str, list[LinkRow]],
    controls_from: dict[str, list[LinkRow]],
    ownable: set[str],
    upper: bool,
) -> tuple[set[str], set[str]]:
    """UK, one listed person: the entities it owns or controls (shares or votes of more than 50
    percent held through its majority-stake entities, each in full, or a board right), and those
    of them whose result relies on shares standing in for votes (section 10.2)."""
    full = _stake(seed, owns_from, controls_from, ownable, upper, True)
    strict = _stake(seed, owns_from, controls_from, ownable, upper, False)

    def met(c: str, members: set[str]) -> bool:
        shares = [
            bound(x, upper)
            for m in members
            for x in owns_from[m]
            if x.target == c and not x.is_nominee
        ]
        votes = [
            bound(x, upper)
            for m in members
            for x in controls_from[m]
            if x.target == c and _voting(x)
        ]
        board = any(_appoints(x) for m in members for x in controls_from[m] if x.target == c)
        return passes(shares, True, upper) or passes(votes, True, upper) or board

    caught: set[str] = set()
    relied: set[str] = set()
    reach = {x.target for m in full for x in owns_from[m] + controls_from[m]}
    for c in sorted((reach & ownable) - {seed}):
        if met(c, full - {c}):
            caught.add(c)
            if not met(c, strict - {c}):
                relied.add(c)
    return caught, relied


def _reach(start: set[str], links: list[LinkRow]) -> dict[str, int]:
    """Shortest distance from `start` to every node `links` reach (start nodes excluded)."""
    out: dict[str, list[str]] = defaultdict(list)
    for x in links:
        out[x.source].append(x.target)
    dist = {s: 0 for s in start}
    todo = deque(sorted(start))
    while todo:
        n = todo.popleft()
        for t in sorted(out[n]):
            if t not in dist:
                dist[t] = dist[n] + 1
                todo.append(t)
    return {k: v for k, v in dist.items() if k not in start}


def _collect(
    source: Source, start: set[str], p: Params, as_of: str
) -> tuple[dict[str, LinkRow], bool]:
    links: dict[str, LinkRow] = {}
    seen = set(start)
    frontier = sorted(start)
    for _ in range(p.max_hops):
        if not frontier:
            break
        nxt: set[str] = set()
        for rows in source.links_from(frontier, ("OWNS", "CONTROLS")).values():
            for x in rows:
                if not x.current(as_of):
                    continue
                links[x.rel_id] = x
                if x.target not in seen:
                    seen.add(x.target)
                    nxt.add(x.target)
        if len(links) > p.max_links:
            return links, True
        frontier = sorted(nxt)
    return links, False


def _paths(
    start: set[str], target: str, links: list[LinkRow], max_hops: int, limit: int
) -> tuple[list[list[LinkRow]], bool]:
    """Simple paths over `links` from a start node to `target`, at most `max_hops` long, shortest
    first, at most `limit` of them (and whether that limit cut the list)."""
    out_links: dict[str, list[LinkRow]] = defaultdict(list)
    into: dict[str, list[str]] = defaultdict(list)
    for x in sorted(links, key=lambda x: x.rel_id):
        out_links[x.source].append(x)
        into[x.target].append(x.source)
    back = {target: 0}  # distance to the target
    todo = deque([target])
    while todo:
        n = todo.popleft()
        for s in into[n]:
            if s not in back:
                back[s] = back[n] + 1
                todo.append(s)
    found: list[list[LinkRow]] = []
    queue: deque[tuple[str, list[LinkRow], frozenset[str]]] = deque(
        (s, [], frozenset({s})) for s in sorted(start) if s in back and s != target
    )
    while queue:
        node, path, visited = queue.popleft()
        if node == target:
            found.append(path)
            if len(found) >= limit:
                return found, bool(queue)
            continue
        for x in out_links[node]:
            if (
                x.target in visited
                or x.target not in back
                or len(path) + 1 + back[x.target] > max_hops
            ):
                continue
            if x.target in start and x.target != target:
                continue  # a path through another listed party is that party's own path
            queue.append((x.target, [*path, x], visited | {x.target}))
    return found, False


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date().isoformat()
    listed = source.listed_entities()
    regime_seeds, uk_unknown = seeds(listed, as_of)
    every = set().union(*regime_seeds.values(), uk_unknown)
    collected, truncated = _collect(source, every, p, as_of)
    direct = [
        x
        for rows in source.links_from(sorted(every), ("CONSOLIDATES", "DIRECTOR_OF")).values()
        for x in rows
        if x.current(as_of)
    ]
    links = sorted(collected.values(), key=lambda x: x.rel_id)
    ids = every | {x.source for x in links} | {x.target for x in links} | {x.target for x in direct}
    entities = source.entities(sorted(ids))
    ownable = {
        i for i, e in entities.items() if "LegalEntity" in e.labels and "Person" not in e.labels
    }
    owns = [x for x in links if x.rel_type == "OWNS"]
    owns_into: dict[str, list[LinkRow]] = defaultdict(list)
    owns_from: dict[str, list[LinkRow]] = defaultdict(list)
    controls_from: dict[str, list[LinkRow]] = defaultdict(list)
    for x in owns:
        owns_into[x.target].append(x)
        owns_from[x.source].append(x)
    for x in links:
        if x.rel_type == "CONTROLS":
            controls_from[x.source].append(x)
    results: dict[str, tuple[set[str], set[str], dict[str, int]]] = {}
    for r in ("us", "eu"):
        s = regime_seeds[r]
        results[r] = (
            aggregate_test(s, owns_into, ownable, False),
            aggregate_test(s, owns_into, ownable, True),
            _reach(s, owns),
        )
    uk_low: set[str] = set()
    uk_high: set[str] = set()
    unknown_reach: set[str] = set()
    proxied: set[str] = set()
    for seed in sorted(regime_seeds["uk"] | uk_unknown):
        low, low_proxy = uk_test(seed, owns_from, controls_from, ownable, False)
        high, high_proxy = uk_test(seed, owns_from, controls_from, ownable, True)
        if seed in uk_unknown:
            unknown_reach |= low | high  # may or may not be an asset-freeze designation
            continue
        uk_low |= low
        uk_high |= high
        proxied |= low_proxy | high_proxy
    measures_unknown = unknown_reach - uk_low - uk_high
    results["uk"] = (
        uk_low,
        uk_high | unknown_reach,
        _reach(regime_seeds["uk"] | uk_unknown, links),
    )
    certain = aggregate_test(every, owns_into, ownable, False)
    possible = aggregate_test(every, owns_into, ownable, True)
    owned = _reach(every, owns)
    direct_into: dict[str, list[LinkRow]] = defaultdict(list)
    for x in direct + [x for x in links if x.rel_type == "CONTROLS" and x.source in every]:
        direct_into[x.target].append(x)
    candidates = set(owned) | set(direct_into) | ((uk_high | unknown_reach) - every)
    ctx = Context(regime_seeds, uk_unknown, every, certain, possible, entities)
    findings = []
    for target in sorted(candidates):
        e = entities[target]
        if "Organization" not in e.labels or "Sanctioned" in e.labels:
            continue
        f = _finding(
            target,
            links,
            owns,
            direct_into.get(target, []),
            results,
            ctx,
            target in proxied,
            target in measures_unknown,
            p,
        )
        if f is not None:
            findings.append(f)
    stats = {
        "listed": len(listed),
        "seeds": len(every),
        "links": len(links),
        "truncated": int(truncated),
    }
    return DetectorOutput(findings, stats)


def priority(finding: Finding) -> str | None:
    """The typology's own rule (C4): high whenever a test is met on the records."""
    return "high" if any(finding.metrics.get(f"{r}_test") == MET for r in REGIMES) else None


def _outcome(target: str, low: set[str], high: set[str], reached: dict[str, int]) -> str:
    if target not in reached:
        return NONE
    return MET if target in low else (OPEN if target in high else NOT_MET)


def _effective(paths: list[list[LinkRow]]) -> tuple[float, float]:
    """The largest listed owner's effective share: products along its OWNS paths, summed."""
    per_owner: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for path in paths:
        lo = hi = 1.0
        for x in path:
            lo *= bound(x, False)[0] / 100
            hi *= bound(x, True)[0] / 100
        acc = per_owner[path[0].source]
        acc[0] += lo
        acc[1] += hi
    if not per_owner:
        return 0.0, 0.0
    lo, hi = max(per_owner.values(), key=lambda v: (v[0], v[1]))
    return round(min(1.0, lo) * 100, 4), round(min(1.0, hi) * 100, 4)


@dataclass(frozen=True, slots=True)
class Context:
    regime_seeds: dict[str, set[str]]
    uk_unknown: set[str]
    every: set[str]
    certain: set[str]  # listed parties and entities passing the US and EU test on lower bounds
    possible: set[str]  # the same on upper bounds
    entities: dict[str, EntityRow]


def _listed_share(target: str, into: list[LinkRow], members: set[str], upper: bool) -> float:
    """Recorded holdings in `target` of `members`, added up and capped at 100."""
    total = sum(bound(x, upper)[0] for x in into if x.source in members and x.source != target)
    return round(min(100.0, total), 4)


def lists_text(sources: list[str], ctx: Context) -> str:
    """The lists the linked parties are on, in words."""
    if any(SYNTHETIC in ctx.entities[s].datasets for s in sources if s in ctx.entities):
        return SYNTHETIC_LIST
    names = [
        LIST_NAMES[r]
        for r in REGIMES
        if any(s in ctx.regime_seeds[r] or (r == "uk" and s in ctx.uk_unknown) for s in sources)
    ]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def assessment(m: dict[str, object], synthetic: bool, uk_holders: int) -> str:
    """Every regime's result in words, with the control results and the limits of the records."""

    def named(regime: str) -> str:
        return "the synthetic list" if synthetic else LIST_NAMES[regime]

    out: list[str] = []
    for r in REGIMES:
        test = str(m[f"{r}_test"])
        if test != NONE:
            out.append(RESULT[(r, test)].format(list=named(r)))
        if r == "us" and m["us_control_caution"]:
            out.append(US_CAUTION.format(list=named(r)))
        if r == "uk":
            if m["uk_control_to_assess"]:
                out.append(UK_CONTROL.format(list=named(r)))
            if test in (NOT_MET, OPEN) and uk_holders >= 2:
                out.append(UK_SEVERAL)
            if m["votes_follow_shares"]:
                out.append(UK_VOTES)
            if m["uk_nominee_holdings"] and test != NONE:
                out.append(UK_NOMINEE)
            if m["uk_measures_unknown"]:
                out.append(UK_UNKNOWN)
        if r == "eu" and m["eu_control_criteria"]:
            criteria = str(m["eu_control_criteria"]).split(", ")
            text = " and ".join(f"{c} ({EU_CRITERIA[c]})" for c in criteria)
            out.append(EU_CONTROL.format(criteria=text, list=named(r)))
    return " ".join([*out, CLOSING])


def _finding(
    target: str,
    links: list[LinkRow],
    owns: list[LinkRow],
    direct: list[LinkRow],
    results: dict[str, tuple[set[str], set[str], dict[str, int]]],
    ctx: Context,
    proxied: bool,
    measures_unknown: bool,
    p: Params,
) -> Finding | None:
    regime_seeds, every = ctx.regime_seeds, ctx.every
    tests = {r: _outcome(target, *results[r]) for r in REGIMES}
    own_paths, own_capped = _paths(every, target, owns, p.max_hops, p.max_paths)
    all_paths, all_capped = _paths(every, target, links, p.max_hops, p.max_paths)
    low, high = _effective(own_paths)
    into = [x for x in owns if x.target == target]
    share_min = _listed_share(target, into, ctx.certain, False)
    share_max = _listed_share(target, into, ctx.possible, True)
    if not direct and share_max < p.min_reported_share and not ({MET, OPEN} & set(tests.values())):
        return None
    extra = [x for x in direct if x.rel_type in ("CONSOLIDATES", "DIRECTOR_OF")]
    shortest = min([len(x) for x in all_paths] + [1 for _ in extra])
    if MET in tests.values():
        own_score = 1.0
    elif OPEN in tests.values():
        own_score = 0.7
    else:
        own_score = share_min / 100
    strong = any(x.rel_type in ("CONTROLS", "CONSOLIDATES") for x in direct)
    control_score = 1.0 if strong else (0.5 if direct else 0.0)
    strength = clip01(
        0.6 * own_score + 0.2 * (1 - (shortest - 1) / p.max_hops) + 0.2 * control_score
    )
    evidence = {x.rel_id: x for path in all_paths for x in path} | {x.rel_id: x for x in extra}
    sources = sorted({path[0].source for path in all_paths} | {x.source for x in extra})
    uk_seeds = regime_seeds["uk"] | ctx.uk_unknown
    eu_criteria = []
    if any(_appoints(x) and x.source in regime_seeds["eu"] for x in direct):
        eu_criteria.append("(a)")
    if any(x.rel_type == "CONSOLIDATES" and x.source in regime_seeds["eu"] for x in direct):
        eu_criteria.append("(g)")
    metrics: dict[str, object] = {
        "listed_parties": len(sources),
        "shortest_path": shortest,
        "ownership_paths": len(own_paths),
        "paths_capped": own_capped or all_capped,
        "listed_share_min": share_min,
        "listed_share_max": share_max,
        "effective_share_min": low,
        "effective_share_max": high,
        "us_test": tests["us"],
        "eu_test": tests["eu"],
        "uk_test": tests["uk"],
        "votes_follow_shares": proxied,
        "unbounded": any(x.share_max is None for x in evidence.values() if x.rel_type == "OWNS"),
        "bands_inconsistent": sum(bound(x, False)[0] for x in into) > 100,
        "control_links": sum(1 for x in direct if x.rel_type == "CONTROLS"),
        "consolidation_links": sum(1 for x in direct if x.rel_type == "CONSOLIDATES"),
        "director_links": sum(1 for x in direct if x.rel_type == "DIRECTOR_OF"),
        "us_control_caution": tests["us"] != MET
        and any(x.rel_type == "CONTROLS" and x.source in regime_seeds["us"] for x in direct),
        "uk_control_to_assess": tests["uk"] != MET
        and any(
            x.rel_type == "DIRECTOR_OF"
            or (x.rel_type == "CONTROLS" and not _appoints(x) and not _voting(x))
            for x in direct
            if x.source in uk_seeds
        ),
        "uk_nominee_holdings": sum(
            1 for x in evidence.values() if x.rel_type == "OWNS" and x.is_nominee
        ),
        "uk_measures_unknown": measures_unknown,
        "eu_control_criteria": ", ".join(eu_criteria),
        "lists": ", ".join(
            r
            for r in REGIMES
            if any(s in regime_seeds[r] or (r == "uk" and s in ctx.uk_unknown) for s in sources)
        ),
        "lists_text": lists_text(sources, ctx),
    }
    synthetic = metrics["lists_text"] == SYNTHETIC_LIST
    uk_holders = {path[0].source for path in own_paths if path[0].source in uk_seeds}
    metrics["assessment"] = assessment(metrics, synthetic, len(uk_holders))
    steps = [tuple(x.rel_id for x in path) for path in all_paths[: p.max_steps]]
    room = max(0, p.max_steps - len(steps))
    steps += [(x.rel_id,) for x in sorted(extra, key=lambda x: x.rel_id)][:room]
    if own_paths:
        variant = "ownership"
    elif strong or all_paths:
        variant = "control"
    else:
        variant = "director"
    nodes = {target, *sources} | {n for x in evidence.values() for n in (x.source, x.target)}
    return Finding(
        typology=SLUG,
        variant=variant,
        anchor=target,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(evidence)),
        subjects=(Subject(target, "exposed_entity"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=False,
    )
```

### `detect/typologies/sanctions_exposure.yaml`

Verbatim. YAML, 84 lines. SHA-256 `8be9398d6750a08472ea194cefe6197c002291a331476e0512b4850eaa4c043f`.

```yaml
slug: sanctions_exposure
name: Sanctions exposure through ownership or control
shape_name: ownership or control links to parties listed as sanctioned
version: 0.2.0
status: draft
tier: core
owner: '@TODO'
approved_by: null
summary: >-
  An organisation that parties listed as sanctioned own or control, judged with the US, UK and EU tests separately.
doc: docs/typologies/sanctions-exposure.md
citations:
- ofac_50_percent_2014
- ofac_50_percent_faqs
- ofsi_general_guidance_2026
- russia_sanctions_regs_2019
- eu_best_practices_2024
- eu_reg_2580_2001
- ec_asset_freeze_faq_2026
graph_pattern: >-
  OWNS and CONTROLS within six relationships of a listed entity, with each regime's own seed list and arithmetic
  on the published share bands; direct CONTROLS, CONSOLIDATES and DIRECTOR_OF links reported apart.
parameters:
  max_hops:
    default: 6
    min: 1
    max: 8
  max_links:
    default: 200000
    min: 1
    max: 2000000
  max_paths:
    default: 1000
    min: 1
    max: 10000
  max_steps:
    default: 12
    min: 1
    max: 120
  min_reported_share:
    default: 25.0
    min: 0.0
    max: 100.0
metrics:
- listed_parties
- shortest_path
- ownership_paths
- paths_capped
- listed_share_min
- listed_share_max
- effective_share_min
- effective_share_max
- us_test
- eu_test
- uk_test
- votes_follow_shares
- unbounded
- bands_inconsistent
- control_links
- consolidation_links
- director_links
- us_control_caution
- uk_control_to_assess
- uk_nominee_holdings
- uk_measures_unknown
- eu_control_criteria
- lists
- lists_text
- assessment
wording:
  headline_structural: Organisation with recorded ownership or control links to parties on {lists_text}
  headline_synthetic: 'Synthetic scenario: organisation with recorded ownership or control links to parties on {lists_text}'
  detail: '{assessment}'
  variants:
    director:
      headline_structural: Organisation with a current director on {lists_text}
      headline_synthetic: 'Synthetic scenario: organisation with a current director on {lists_text}'
false_positives:
- Minority stakes
- Diffuse shareholdings
- A listed record that is a different party with a similar name
synthetic_support: high
generator_scenario: sanctions_exposure
detector: neonradar_detect.detectors.sanctions_exposure
```

### `detect/tests/test_detector_sanctions_exposure.py`

Verbatim. Python, 354 lines. SHA-256 `47e920d5cb69b7115d66770518c6c3a1a5407328bb95c920a6fe380541e9ad16`.

```python
from datetime import UTC, datetime

import pytest
from kit import Kit, detect, source_of
from neonradar_detect.detectors import sanctions_exposure as se
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))
MET, OPEN, NOT_MET, NONE = se.MET, se.OPEN, se.NOT_MET, se.NONE


def _run(k: Kit, **overrides):
    out = se.run(source_of(k.records), se.Params(**overrides), WINDOW)
    return {f.anchor: f for f in out.findings}


def _tests(f):
    return f.metrics["us_test"], f.metrics["uk_test"], f.metrics["eu_test"]


def _listed(k: Kit, name: str, *, person: bool = True):
    return (k.person if person else k.company)(name, topics=("sanction",))


# OFAC FAQ 401, examples 1 to 5 (typology-detection-definitions.md 10.1 and 10.3) -----------------


def test_faq_401_example_1_status_passes_entity_by_entity():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "exact:50")
    k.owns(a, b, "exact:50")
    found = _run(k)
    assert _tests(found[a]) == (MET, NOT_MET, MET)  # 50 is not "more than 50" for the UK
    assert _tests(found[b]) == (MET, NOT_MET, MET)
    # multiplying gives 25 percent, which is why the effective share is a teaching figure only
    assert (found[b].metrics["effective_share_min"], found[b].metrics["effective_share_max"]) == (
        25.0,
        25.0,
    )
    assert found[b].metrics["shortest_path"] == 2 and found[b].variant == "ownership"
    assert [s.role for s in found[b].subjects] == ["exposed_entity"]
    assert se.priority(found[b]) == "high"


def test_faq_401_example_2_two_owned_entities_add_up():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:50")
    k.owns(a, c, "exact:25")
    k.owns(b, c, "exact:25")
    assert _tests(_run(k)[c]) == (MET, NOT_MET, MET)


def test_faq_401_example_3_direct_and_indirect_add_up():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:10")
    k.owns(a, b, "exact:40")
    assert _tests(_run(k)[b]) == (MET, NOT_MET, MET)


def test_faq_401_example_4_an_entity_below_50_does_not_pass_its_holding_on():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:25")
    k.owns(a, c, "exact:25")
    k.owns(b, c, "exact:25")
    found = _run(k)
    assert _tests(found[b]) == (NOT_MET, NOT_MET, NOT_MET) and se.priority(found[b]) is None
    # only A passes the test, so only A's 25 percent counts in C: reported, and not met
    assert _tests(found[c]) == (NOT_MET, NOT_MET, NOT_MET)
    assert (found[c].metrics["listed_share_min"], found[c].metrics["listed_share_max"]) == (
        25.0,
        25.0,
    )


def test_faq_401_example_5_two_minority_stakes_do_not_pass_on():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:25")
    k.owns(x, b, "exact:25")
    k.owns(a, c, "exact:50")
    k.owns(b, c, "exact:50")
    found = _run(k)
    assert (
        _tests(found[a]) == (NOT_MET, NOT_MET, NOT_MET)
        and found[a].metrics["listed_share_min"] == 25.0
    )
    assert c not in found  # neither A nor B passes the test, so no listed holding reaches C


# the worked examples with Companies House bands (10.3) ----------------------------------------


@pytest.mark.parametrize(
    ("band", "expected"),
    [
        ("25-50", (OPEN, NOT_MET, OPEN)),  # (25, 50]: the upper bound 50 is closed
        ("50-75", (MET, MET, MET)),  # (50, 75)
        ("75-100", (MET, MET, MET)),
    ],
)
def test_one_listed_owner_with_a_band(band, expected):
    k = Kit()
    x = _listed(k, "x")
    e = k.company("e")
    k.owns(x, e, band)
    assert _tests(_run(k)[e]) == expected


def test_two_listed_owners_add_up_except_in_the_uk():
    k = Kit()
    x, y = _listed(k, "x"), _listed(k, "y")
    e = k.company("e")
    k.owns(x, e, "25-50")
    k.owns(y, e, "25-50")
    f = _run(k)[e]
    assert _tests(f) == (MET, NOT_MET, MET)  # the sum is (50, 100]; OFSI does not add persons up
    assert f.metrics["listed_parties"] == 2


def test_band_left_open_down_a_chain():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "75-100")
    k.owns(a, b, "25-50")
    found = _run(k)
    # A meets reg 7(2)(a) on its own shares: no stand-in for votes is needed
    assert _tests(found[a]) == (MET, MET, MET) and found[a].metrics["votes_follow_shares"] is False
    assert _tests(found[b]) == (OPEN, NOT_MET, OPEN)
    assert se.priority(found[b]) is None and found[b].pattern_strength < found[a].pattern_strength


def test_uk_chain_through_shares_says_votes_follow_shares():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "75-100")
    k.owns(a, b, "75-100")
    f = _run(k)[b]
    assert _tests(f) == (MET, MET, MET) and f.metrics["votes_follow_shares"] is True
    k.controls(x, a, "voting", band="75-100")  # the register also records X's votes in A
    f = _run(k)[b]
    assert _tests(f) == (MET, MET, MET) and f.metrics["votes_follow_shares"] is False


def test_uk_majority_stake_chain():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "50-75")
    k.owns(a, b, "50-75")
    assert _tests(_run(k)[b]) == (MET, MET, MET)


def test_uk_voting_rights_carry_a_chain_that_ownership_does_not():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.controls(x, a, "voting", band="50-75")
    k.owns(a, b, "75-100")
    found = _run(k)
    assert _tests(found[b]) == (NONE, MET, NONE)  # control never counts for OFAC
    assert found[b].metrics["votes_follow_shares"] is False and found[b].variant == "control"
    assert _tests(found[a]) == (NONE, MET, NONE)
    assert found[a].metrics["us_control_caution"] is True


def test_board_appointment_right_meets_the_uk_test_and_eu_criterion_a():
    k = Kit()
    x = _listed(k, "x")
    c = k.company("c")
    k.controls(x, c, "appointment")
    f = _run(k)[c]
    assert _tests(f) == (NONE, MET, NONE)
    assert f.metrics["eu_control_criteria"] == "(a)" and f.metrics["us_control_caution"] is True


def test_significant_influence_and_directorship_are_reported_apart():
    k = Kit()
    x = _listed(k, "x", person=False)
    p = _listed(k, "p")
    d, e = k.company("d"), k.company("e")
    k.controls(x, d, "influence")
    k.director(p, e)
    found = _run(k)
    assert _tests(found[d]) == (NONE, NOT_MET, NONE)
    assert found[d].metrics["uk_control_to_assess"] is True and found[d].variant == "control"
    assert found[e].variant == "director" and found[e].metrics["director_links"] == 1
    assert found[e].pattern_strength < found[d].pattern_strength


def test_consolidation_is_eu_criterion_g():
    k = Kit()
    x = _listed(k, "x", person=False)
    c = k.company("c")
    k.consolidates(x, c)
    f = _run(k)[c]
    assert f.metrics["eu_control_criteria"] == "(g)" and f.metrics["consolidation_links"] == 1


# seeds: each regime its own list -------------------------------------------------------------


def test_each_regime_uses_its_own_list():
    k = Kit()
    us = k.company("ofac-T0000001", topics=("sanction",), dataset="us_ofac_sdn")
    k.sanction(us, "us_ofac_sdn")
    uk = k.company("uksl-gT0000001", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(uk, "gb_fcdo_sanctions", provisions=("Asset freeze", "Travel ban"))
    ban = k.person("uksl-gT0000002", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(ban, "gb_fcdo_sanctions", provisions=("Travel ban",))
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(us, a, "75-100")
    k.owns(uk, b, "75-100")
    k.owns(ban, c, "75-100")
    found = _run(k)
    assert _tests(found[a]) == (MET, NONE, NONE) and found[a].metrics["lists"] == "us"
    assert _tests(found[b]) == (NONE, MET, NONE) and found[b].metrics["lists"] == "uk"
    assert c not in found  # a travel ban alone seeds no ownership test


def test_ended_designation_seeds_nothing_and_listed_targets_are_skipped():
    k = Kit()
    old = k.company("eufsf-T0000001", topics=("sanction",), dataset="eu_fsf")
    k.sanction(old, "eu_fsf", end="2025-12-31")
    x = _listed(k, "x")
    a, listed_too = k.company("a"), k.company("lt", topics=("sanction",))
    k.owns(old, a, "75-100")
    k.owns(x, listed_too, "75-100")
    assert _run(k) == {}


def test_missing_upper_bound_counts_as_100_and_is_reported():
    k = Kit()
    x = _listed(k, "x")
    e = k.company("e")
    rid = k.owns(x, e, "25-50")
    record = next(r for r in k.records if r["id"] == rid)
    del record["nr"]["share_pct_max"]
    f = _run(k)[e]
    assert f.metrics["unbounded"] is True
    assert _tests(f) == (OPEN, OPEN, OPEN)


def test_small_holdings_that_meet_no_test_are_left_out():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:20")
    k.owns(x, b, "exact:30")
    k.owns(b, c, "exact:40")  # 12 percent through B
    found = _run(k)
    assert set(found) == {b} and _tests(found[b]) == (NOT_MET, NOT_MET, NOT_MET)
    # C's 12 percent runs through B, which does not pass the test: no listed holding reaches C
    assert set(_run(k, min_reported_share=10.0)) == {a, b}


def test_registry_alert_about_a_real_organisation_is_a_structural_pattern():
    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    listed = k.company(
        "uksl-gT0000001", "Test Listed Ltd", topics=("sanction",), dataset="gb_fcdo_sanctions"
    )
    k.sanction(listed, "gb_fcdo_sanctions", provisions=("Asset freeze",))
    k.owns(listed, real_co, "75-100")
    [alert] = detect(k.records, {"sanctions_exposure": se.Params()}).alerts
    assert alert["wording_class"] == "structural_pattern"
    assert alert["data_flags"]["involves_real_entities"] is True
    assert alert["headline"] == (
        "Organisation with recorded ownership or control links to parties on the UK Sanctions List"
    )
    summary = alert["explanation"]["summary"]
    assert se.RESULT[("uk", MET)].format(list="the UK Sanctions List") in summary
    assert se.CLOSING in summary and "US test" not in summary
    assert alert["priority"] == "high"


def test_ended_links_count_no_more():
    """A resigned listed director and a listed owner who sold are history (OFAC FAQ 402: below
    50 percent an entity "is no longer considered automatically to be a blocked entity")."""
    k = Kit()
    x = _listed(k, "x")
    resigned, sold, kept = k.company("resigned"), k.company("sold"), k.company("kept")
    k.director(x, resigned, start="2019-01-01", end="2026-02-28")
    k.owns(x, sold, "75-100", start="2019-01-01", end="2026-05-31")
    k.owns(x, kept, "75-100", start="2019-01-01", end="2026-12-31")  # ends after the window
    assert set(_run(k)) == {kept}


def test_uk_nominee_holdings_and_entries_without_provisions():
    k = Kit()
    x = _listed(k, "x")
    n = k.company("n")
    k.owns(x, n, "75-100", nominee=True)
    f = _run(k)[n]
    assert _tests(f) == (MET, NOT_MET, MET) and f.metrics["uk_nominee_holdings"] == 1
    assert se.UK_NOMINEE in f.metrics["assessment"]
    k2 = Kit()
    entry = k2.company("uksl-gT0000005", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k2.sanction(entry, "gb_fcdo_sanctions")  # the list entry records no provisions
    m = k2.company("m")
    k2.owns(entry, m, "75-100")
    g = _run(k2)[m]
    assert _tests(g) == (NONE, OPEN, NONE) and g.metrics["uk_measures_unknown"] is True
    assert se.UK_UNKNOWN in g.metrics["assessment"]


def test_the_assessment_names_control_left_unassessed_and_eu_criteria():
    k = Kit()
    uk = k.company("uksl-gT0000006", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(uk, "gb_fcdo_sanctions", provisions=("Asset freeze",))
    eu = k.company("eufsf-T0000002", topics=("sanction",), dataset="eu_fsf")
    k.sanction(eu, "eu_fsf")
    d, e = k.company("d"), k.company("e")
    k.controls(uk, d, "influence")
    k.controls(eu, e, "appointment")
    found = _run(k)
    text_d, text_e = found[d].metrics["assessment"], found[e].metrics["assessment"]
    assert se.UK_CONTROL.format(list="the UK Sanctions List") in text_d
    assert "EU control criterion (a)" in text_e and found[e].metrics["lists_text"] == (
        "the EU consolidated list"
    )
    assert _tests(found[e]) == (NONE, NONE, NONE)  # no ownership test applies, yet it is reported


def test_the_stricter_option_withholds_registry_alerts_about_real_organisations():
    from kit import WINDOW, source_of
    from neonradar_detect import catalog, runner

    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    k.owns(_listed(k, "lst", person=False), real_co, "75-100")
    result = runner.run_detection(
        source_of(k.records),
        {"sanctions_exposure": se.Params()},
        WINDOW,
        catalog.load(),
        run_id="run-20261102T090000-0002",
        created_at=WINDOW.end,
        real_registry_alerts=False,
    )
    assert result.alerts == [] and result.summary["withheld"]["registry_on_real"] == 1
```

## M3.5f Extended typologies: `formation_agent_cluster`, `recycled_directors`, `pep_exposure`, `cash_commingling`

The detectors, their typology files (keep the repository's `owner`, `status` and `approved_by` lines, 2.10) and their test files. 10 verbatim files (PHASE-3.md M3.5f).

### `detect/src/neonradar_detect/detectors/formation_agent_cluster.py`

Verbatim. Python, 192 lines. SHA-256 `eac90a17a8f9c8b28644000e3138e85b97f44e9788faea865e5edea4046de26c`.

```python
"""formation_agent_cluster 0.1.0: one agent behind a burst of company formations whose officers
recur across the companies (PHASE-1.md 7.2 extended entry; `typology-detection-definitions.md`
section 11; PHASE-3.md 7.3.11).

Registry evidence only. Candidates are the agents with REPRESENTS relationships to at least
`min_companies` organisations. An agent qualifies when at least `min_companies` of its clients
were incorporated within `window_days` of each other (the largest such set is the burst) and at
least `min_shared_officers` people or organisations are current directors (no end date, or one
after the end of the window) of two or more burst companies.
The strength adds the share of burst companies with a shared officer, the share registered at one
of the agent's own addresses, nominee officers among the shared ones, and payments among the burst
companies' accounts (only when every burst company is synthetic, R-REAL). Company formation is a
lawful trade: the alert describes a shape, and an ACSP name or an AML supervisor in the register
(not in C2 1.2.0) would be context, never a trigger.

pattern_strength = 0.3 * min(1, burst / (3 * min_companies)) + 0.25 * share with a shared officer
+ 0.15 * share at the agent's address + 0.15 * (a shared officer is a nominee)
+ 0.15 * min(1, paying pairs / 3).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, Hub, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "formation_agent_cluster"
VERSION = "0.1.0"
QUERIES = (
    "entities.cypher",
    "hubs.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
)


@dataclass(frozen=True, slots=True)
class Params:
    min_companies: int = 10
    window_days: int = 30
    min_shared_officers: int = 2
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def incorporation_burst(members: list[str], entities: dict[str, EntityRow], days: int) -> list[str]:
    """The largest set of `members` incorporated within `days` of the first of them (earliest set
    on a tie), in date order."""
    dated = sorted(
        (date.fromisoformat(entities[m].incorporation_date), m)
        for m in members
        if len(entities[m].incorporation_date) == 10
    )
    best: list[str] = []
    j = 0
    for i, (start, _) in enumerate(dated):
        while j < len(dated) and dated[j][0] <= start + timedelta(days=days):
            j += 1
        if j - i > len(best):
            best = [m for _, m in dated[i:j]]
    return best


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    hubs = source.hubs("REPRESENTS", p.min_companies, p.max_candidates)
    findings = []
    for hub in hubs:
        f = _evaluate(hub, source, p, window)
        if f is not None:
            findings.append(f)
    return DetectorOutput(findings, {"candidates": len(hubs)})


def _evaluate(hub: Hub, source: Source, p: Params, window: Window) -> Finding | None:
    rep_of = {x.target: x for x in hub.links}
    clients = sorted(rep_of)
    entities = source.entities([*clients, hub.hub])
    burst = incorporation_burst(clients, entities, p.window_days)
    if len(burst) < p.min_companies:
        return None
    directors = source.links_into(burst, ("DIRECTOR_OF",))
    as_of = window.end.date().isoformat()
    by_officer: dict[str, list[LinkRow]] = defaultdict(list)
    for c in burst:
        for d in directors.get(c, []):
            if d.current(as_of):
                by_officer[d.source].append(d)
    shared = {o: links for o, links in by_officer.items() if len({x.target for x in links}) >= 2}
    if len(shared) < p.min_shared_officers:
        return None
    with_shared = {x.target for links in shared.values() for x in links}
    nominee = any(x.is_nominee for links in shared.values() for x in links)
    agent_addresses = {
        x.target for x in source.links_from([hub.hub], ("HAS_ADDRESS",)).get(hub.hub, [])
    }
    registered = source.links_from(burst, ("HAS_ADDRESS",))
    at_agent = {
        c: x
        for c in burst
        for x in registered.get(c, [])
        if x.role == "registered" and x.target in agent_addresses
    }
    pairs: set[tuple[str, str]] = set()
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[c].synthetic for c in burst):
        for c, links in source.links_from(burst, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = c
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
        pairs = {
            (min(holder_of[a], holder_of[b]), max(holder_of[a], holder_of[b]))
            for _, a, b in paying
            if holder_of[a] != holder_of[b]
        }
    n = len(burst)
    strength = clip01(
        0.3 * min(1.0, n / (3 * p.min_companies))
        + 0.25 * len(with_shared) / n
        + 0.15 * len(at_agent) / n
        + (0.15 if nominee else 0.0)
        + 0.15 * min(1.0, len(pairs) / 3)
    )
    shown = [*sorted(with_shared, key=burst.index), *(c for c in burst if c not in with_shared)]
    shown = shown[: p.max_evidence_companies]
    shown_set = set(shown)
    officer_links = sorted(
        (x for links in shared.values() for x in links if x.target in shown_set),
        key=lambda x: x.rel_id,
    )
    address_links = sorted(
        (x for c, x in at_agent.items() if c in shown_set), key=lambda x: x.rel_id
    )
    pay_edges = sorted(
        e
        for e, a, b in paying
        if holder_of[a] in shown_set and holder_of[b] in shown_set and holder_of[a] != holder_of[b]
    )
    pay_set = set(pay_edges)
    pay_nodes = {x for e, a, b in paying if e in pay_set for x in (a, b)}
    first, last = entities[burst[0]].incorporation_date, entities[burst[-1]].incorporation_date
    metrics = {
        "clients": len(clients),
        "incorporated_in_burst": n,
        "burst_first": first,
        "burst_last": last,
        "window_days": p.window_days,
        "shared_officers": len(shared),
        "companies_with_shared_officer": len(with_shared),
        "at_agent_address": len(at_agent),
        "nominee_officers": sum(1 for links in shared.values() if any(x.is_nominee for x in links)),
        "paying_pairs": len(pairs),
        "companies_shown": len(shown),
    }
    steps: list[tuple[str, ...]] = [tuple(sorted(rep_of[c].rel_id for c in shown))]
    if officer_links:
        steps.append(tuple(x.rel_id for x in officer_links))
    if address_links:
        steps.append(tuple(x.rel_id for x in address_links))
    if pay_edges:
        steps.append(tuple(pay_edges))
    nodes = {
        hub.hub,
        *shown,
        *(x.source for x in officer_links),
        *(x.target for x in address_links),
        *pay_nodes,
    }
    edges = (
        {rep_of[c].rel_id for c in shown}
        | {x.rel_id for x in officer_links}
        | {x.rel_id for x in address_links}
    )
    return Finding(
        typology=SLUG,
        variant="",
        anchor=hub.hub,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges | pay_set)),
        subjects=(Subject(hub.hub, "agent"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
```

### `detect/src/neonradar_detect/detectors/recycled_directors.py`

Verbatim. Python, 228 lines. SHA-256 `252d1fea825ab830bde199cf131f433688beb15146be42cbef7049e075ae539f`.

```python
"""recycled_directors 0.1.0: one person serving as director of many unrelated companies, or
appointed to many in a short time (PHASE-1.md 7.2 extended entry; `typology-detection-
definitions.md` section 12; PHASE-3.md 7.3.12).

Registry evidence only. Candidates are the people with DIRECTOR_OF relationships to at least
min(`min_active_appointments`, `burst_appointments`) organisations. The companies are first put
into groups: two of them are in one group when one owns or consolidates the other or a common
parent owns or consolidates both, because appointments across one group are ordinary ("directors
across one group", the look-alike of section 12). A person qualifies when the active appointments
(no end date on or before the end of the window, company active) span at least
`min_active_appointments` groups, or when appointments starting within `burst_days` of each other
span at least `burst_appointments` groups. Short tenures (ended within `short_tenure_days`), a
nominee appointment, a directorship of a company owned by the person's own relative (`FAMILY_OF`
an owner, "family members with no role", Annex E) and payments among the companies (only when
all are synthetic, R-REAL) add to the strength.

The subject is a person, so on a real profile the policy withholds every finding about a real
person (R-REAL (b)); the counts appear in the run summary.

pattern_strength = 0.3 * min(1, active groups / (2 * min_active_appointments)) + 0.25 * min(1,
burst groups / (2 * burst_appointments)) + 0.15 * min(1, short tenures / 3) + 0.15 * (nominee or
family) + 0.15 * min(1, paying pairs / 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, Hub, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "recycled_directors"
VERSION = "0.1.0"
QUERIES = (
    "entities.cypher",
    "hubs.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "payments_among.cypher",
)
INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})


@dataclass(frozen=True, slots=True)
class Params:
    min_active_appointments: int = 10
    burst_appointments: int = 5
    burst_days: int = 30
    short_tenure_days: int = 90
    max_evidence_companies: int = 100
    max_candidates: int = 50_000


def _active(e: EntityRow) -> bool:
    return not e.dissolution_date and e.status.casefold() not in INACTIVE


def groups(companies: list[str], owns_into: dict[str, list[LinkRow]]) -> dict[str, str]:
    """Each company's group: the smallest company id reachable through ownership or consolidation
    between the companies or through a common parent."""
    parent = {c: c for c in companies}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_parent: dict[str, list[str]] = {}
    for c in companies:
        for link in owns_into.get(c, []):
            if link.source in parent:
                union(link.source, c)
            by_parent.setdefault(link.source, []).append(c)
    for children in by_parent.values():
        for other in children[1:]:
            union(children[0], other)
    return {c: find(c) for c in companies}


def _span(links: list[LinkRow], group_of: dict[str, str], days: int) -> list[LinkRow]:
    """The appointments starting within `days` of each other that span the most groups."""
    dated = sorted(
        (date.fromisoformat(x.start_date), x.rel_id, x) for x in links if len(x.start_date) == 10
    )
    best: list[LinkRow] = []
    best_groups = 0
    j = 0
    for i, (start, _, _) in enumerate(dated):
        while j < len(dated) and dated[j][0] <= start + timedelta(days=days):
            j += 1
        chosen = [x for _, _, x in dated[i:j]]
        n = len({group_of[x.target] for x in chosen})
        if n > best_groups:
            best, best_groups = chosen, n
    return best


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    hubs = source.hubs(
        "DIRECTOR_OF", min(p.min_active_appointments, p.burst_appointments), p.max_candidates
    )
    findings = []
    for hub in hubs:
        f = _evaluate(hub, source, p, window)
        if f is not None:
            findings.append(f)
    return DetectorOutput(findings, {"candidates": len(hubs)})


def _evaluate(hub: Hub, source: Source, p: Params, window: Window) -> Finding | None:
    companies = sorted({x.target for x in hub.links})
    entities = source.entities([hub.hub, *companies])
    if "Person" not in entities[hub.hub].labels:
        return None
    as_of = window.end.date().isoformat()
    owns_into = source.links_into(companies, ("OWNS", "CONSOLIDATES"))
    group_of = groups(companies, owns_into)
    active = [
        x
        for x in hub.links
        if not (x.end_date and x.end_date <= as_of) and _active(entities[x.target])
    ]
    active_groups = len({group_of[x.target] for x in active})
    burst = _span(list(hub.links), group_of, p.burst_days)
    burst_groups = len({group_of[x.target] for x in burst})
    if active_groups < p.min_active_appointments and burst_groups < p.burst_appointments:
        return None
    short = [
        x
        for x in hub.links
        if len(x.start_date) == 10
        and len(x.end_date) == 10
        and (date.fromisoformat(x.end_date) - date.fromisoformat(x.start_date)).days
        <= p.short_tenure_days
    ]
    nominee = [x for x in hub.links if x.is_nominee]
    relatives = {
        x.target for x in source.links_from([hub.hub], ("FAMILY_OF",)).get(hub.hub, [])
    } | {x.source for x in source.links_into([hub.hub], ("FAMILY_OF",)).get(hub.hub, [])}
    family = sorted(
        (
            o
            for c in companies
            for o in owns_into.get(c, [])
            if o.rel_type == "OWNS" and o.source in relatives
        ),
        key=lambda x: x.rel_id,
    )
    pairs: set[tuple[str, str]] = set()
    paying: list[tuple[str, str, str]] = []
    holder_of: dict[str, str] = {}
    if all(entities[c].synthetic for c in companies):
        for c, links in source.links_from(companies, ("HOLDS_ACCOUNT",)).items():
            for x in links:
                holder_of[x.target] = c
        if holder_of:
            paying = source.payments_among(sorted(holder_of), window.start, window.end)
        pairs = {
            (min(holder_of[a], holder_of[b]), max(holder_of[a], holder_of[b]))
            for _, a, b in paying
            if holder_of[a] != holder_of[b]
        }
    strength = clip01(
        0.3 * min(1.0, active_groups / (2 * p.min_active_appointments))
        + 0.25 * min(1.0, burst_groups / (2 * p.burst_appointments))
        + 0.15 * min(1.0, len(short) / 3)
        + (0.15 if nominee or family else 0.0)
        + 0.15 * min(1.0, len(pairs) / 3)
    )
    ordered = sorted(hub.links, key=lambda x: (x not in burst, x not in active, x.rel_id))
    shown = ordered[: p.max_evidence_companies]
    shown_targets = {x.target for x in shown}
    pay_edges = sorted(
        e
        for e, a, b in paying
        if holder_of[a] in shown_targets
        and holder_of[b] in shown_targets
        and holder_of[a] != holder_of[b]
    )
    pay_set = set(pay_edges)
    family_shown = [x for x in family if x.target in shown_targets]
    metrics = {
        "appointments": len(hub.links),
        "active_appointments": len(active),
        "active_groups": active_groups,
        "burst_appointments": len(burst),
        "burst_groups": burst_groups,
        "burst_days": p.burst_days,
        "short_tenures": len(short),
        "nominee_appointments": len(nominee),
        "relative_owned_companies": len({x.target for x in family}),
        "paying_pairs": len(pairs),
        "companies_shown": len(shown_targets),
    }
    steps: list[tuple[str, ...]] = []
    if burst:
        steps.append(tuple(sorted(x.rel_id for x in burst if x.target in shown_targets)))
    rest = sorted(x.rel_id for x in shown if x not in burst)
    if rest:
        steps.append(tuple(rest))
    if family_shown:
        steps.append(tuple(x.rel_id for x in family_shown))
    if pay_edges:
        steps.append(tuple(pay_edges))
    nodes = {hub.hub, *shown_targets, *(x.source for x in family_shown)}
    nodes |= {x for e, a, b in paying if e in pay_set for x in (a, b)}
    edges = {x.rel_id for x in shown} | {x.rel_id for x in family_shown} | pay_set
    return Finding(
        typology=SLUG,
        variant="burst" if burst_groups >= p.burst_appointments else "many_boards",
        anchor=hub.hub,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=(Subject(hub.hub, "director"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=bool(pay_edges),
    )
```

### `detect/src/neonradar_detect/detectors/pep_exposure.py`

Verbatim. Python, 358 lines. SHA-256 `33accedb373719d63ec7d7030eb2497138b9d9014bcdfd0df6240408942ea313`.

```python
"""pep_exposure 0.1.0: an organisation that a politically exposed person, a family member of one
or a close associate owns, controls or directs, directly or through up to three companies
(PHASE-1.md 7.2 extended entry; `typology-detection-definitions.md` section 13; PHASE-3.md
7.3.13).

Registry evidence only, and only relationships that still hold at the end of the window (no end
date, or a later one). The people it starts from:

- every :PEP person in scope: in office (a HOLDS_POSITION with no end date, or one ending on or
  after the end of the window), out of office for at most `after_office_months` (MLR 2017 reg
  35(9): "at least 12 months"), or with no recorded position (then `office_dates_unknown`, since
  missing end dates make former PEPs look current);
- while the PEP is in office (or the dates are unknown), the family members one FAMILY_OF hop
  away whose relationship to the PEP is in `family_relationships` (reg 35(12)(b) and FCA FG25/3:
  spouse or civil partner, children and their spouses or civil partners, parents, siblings). FtM
  names the relative from the person's side ("e.g. 'mother', where `relative` is the mother of
  `person`"), so a link whose relative is the PEP is turned round first: a PEP recorded as
  someone's mother makes that someone the PEP's child, and a PEP recorded as someone's son-in-law
  makes that someone a parent-in-law, who is not in the list;
- while the PEP is in office, the people one ASSOCIATE_OF hop away whose relationship is in
  `associate_relationships`, or who hold OWNS or CONTROLS into a legal entity the PEP also holds
  into: reg 35(12)(c) counts "joint beneficial ownership of a legal entity" or "any other close
  business relations". Reg 35(11): the firm "is no longer required to apply" the measures to
  family members and associates once the PEP leaves office;
- every :RCA person as the source data gives it, with the office of the PEPs it is linked to by
  FAMILY_OF or ASSOCIATE_OF (none linked: unknown), and no start when every linked PEP has left
  office (reg 35(11)).

From each of them, up to `ownership_control_hops` OWNS, CONTROLS or DIRECTOR_OF relationships
lead to organisations; every organisation reached is a finding, with the PEP, the family or
associate link and the paths in its evidence. Being a PEP "does not prejudge a link to criminal
activities" (FATF 2013, Annex 1): the alert says only which records connect the organisation to a
public function. Every finding names people in its evidence, so on a real profile R-REAL (c)
withholds it (PHASE-3.md 7.1.4).

pattern_strength = 0.35 * relation (PEP 1, family 0.7, associate or RCA 0.6) + 0.3 * proximity
(1 - (hops - 1) / ownership_control_hops) + 0.2 * first link (a majority holding or appointment
right 1, other ownership or control 0.7, a directorship 0.5) + 0.15 * office (in office 1, unknown
0.8, former 0.5), less 0.1 when every position of the PEP is in `domestic_countries` (reg 35(3A):
a domestic PEP starts from a lower risk).
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "pep_exposure"
VERSION = "0.1.0"
QUERIES = ("entities.cypher", "flagged_ids.cypher", "links_from.cypher", "links_into.cypher")
FAMILY = (
    "spouse",
    "civil partner",
    "husband",
    "wife",
    "child",
    "son",
    "daughter",
    "child's spouse",
    "child's civil partner",
    "son-in-law",
    "daughter-in-law",
    "parent",
    "father",
    "mother",
    "sibling",
    "brother",
    "sister",
)
# What the person is to the PEP when the PEP is the `relative` of a FAMILY_OF: the relationship
# names the PEP from the person's side, so it is turned round. In-laws turn into parents-in-law.
REVERSE = {
    "spouse": "spouse",
    "civil partner": "civil partner",
    "husband": "wife",
    "wife": "husband",
    "child": "parent",
    "son": "parent",
    "daughter": "parent",
    "parent": "child",
    "father": "child",
    "mother": "child",
    "sibling": "sibling",
    "brother": "sibling",
    "sister": "sibling",
    "child's spouse": "parent-in-law",
    "child's civil partner": "parent-in-law",
    "son-in-law": "parent-in-law",
    "daughter-in-law": "parent-in-law",
}
ASSOCIATES = ("business partner", "business associate", "co-owner", "joint owner")
RELATION_SCORE = {"pep": 1.0, "family": 0.7, "associate": 0.6, "rca": 0.6}
OFFICE_SCORE = {"in office": 1.0, "unknown": 0.8, "former": 0.5}


@dataclass(frozen=True, slots=True)
class Params:
    family_relationships: tuple[str, ...] = FAMILY
    associate_relationships: tuple[str, ...] = ASSOCIATES
    associate_hops: int = 1
    ownership_control_hops: int = 3
    after_office_months: int = 12
    domestic_countries: tuple[str, ...] = ("gb",)
    max_paths: int = 1_000
    max_steps: int = 12


@dataclass(frozen=True, slots=True)
class Start:
    person: str
    relation: str  # pep | family | associate | rca
    pep: str  # the PEP behind it ("" for an RCA given as such)
    link: LinkRow | None  # the family or associate link
    office: str  # in office | former | unknown


def _months_before(day: date, months: int) -> date:
    y, m = divmod(day.year * 12 + day.month - 1 - months, 12)
    return date(y, m + 1, min(day.day, 28))


def office(positions: list[LinkRow], as_of: date, months: int) -> str | None:
    """`in office`, `former` (left within `months`), `unknown` (no position), or None (left
    earlier, out of scope)."""
    if not positions:
        return "unknown"
    ends = []
    for x in positions:
        if not x.end_date or x.end_date >= as_of.isoformat():
            return "in office"
        ends.append(x.end_date)
    return "former" if max(ends) >= _months_before(as_of, months).isoformat() else None


def _normal(relationship: str) -> str:
    return " ".join(relationship.casefold().replace("_", " ").split())


def relation_to_pep(link: LinkRow, pep: str) -> str:
    """What the other person of a FAMILY_OF is to `pep`, in the normal form of `_normal`."""
    word = _normal(link.role)
    return word if link.source == pep else REVERSE.get(word, "")


def _holdings(source: Source, ids: list[str], as_of: str) -> dict[str, set[str]]:
    """The legal entities each id holds into through a current OWNS or CONTROLS."""
    return {
        i: {x.target for x in links if x.current(as_of)}
        for i, links in source.links_from(ids, ("OWNS", "CONTROLS")).items()
    }


def starts(source: Source, p: Params, as_of: date) -> tuple[list[Start], dict[str, list[LinkRow]]]:
    day = as_of.isoformat()
    peps = source.flagged_ids("PEP")
    positions = source.links_from(peps, ("HOLDS_POSITION",))
    family_set = {_normal(x) for x in p.family_relationships}
    associate_set = {_normal(x) for x in p.associate_relationships}
    kinds = ("FAMILY_OF", "ASSOCIATE_OF") if p.associate_hops >= 1 else ("FAMILY_OF",)
    outgoing = source.links_from(peps, kinds)
    incoming = source.links_into(peps, kinds)
    status_of = {pep: office(positions.get(pep, []), as_of, p.after_office_months) for pep in peps}
    links_of = {
        pep: sorted(
            (x for x in outgoing.get(pep, []) + incoming.get(pep, []) if x.current(day)),
            key=lambda x: x.rel_id,
        )
        for pep in peps
    }
    associates = sorted(
        {
            x.target if x.source == pep else x.source
            for pep in peps
            for x in links_of[pep]
            if x.rel_type == "ASSOCIATE_OF"
        }
    )
    held = _holdings(source, sorted(set(peps) | set(associates)), day)
    out: list[Start] = []
    for pep in peps:
        status = status_of[pep]
        if status is None:
            continue
        out.append(Start(pep, "pep", pep, None, status))
        if status == "former":
            continue  # reg 35(11): family and associates only while the PEP holds office
        for x in links_of[pep]:
            other = x.target if x.source == pep else x.source
            if x.rel_type == "ASSOCIATE_OF":
                joint = held.get(other, set()) & held.get(pep, set())
                if _normal(x.role) in associate_set or joint:
                    out.append(Start(other, "associate", pep, x, status))
            elif relation_to_pep(x, pep) in family_set:
                out.append(Start(other, "family", pep, x, status))
    rcas = source.flagged_ids("RCA")
    rca_links = {
        k: [x for x in v if x.current(day)]
        for k, v in source.links_from(rcas, ("FAMILY_OF", "ASSOCIATE_OF")).items()
    }
    for k, v in source.links_into(rcas, ("FAMILY_OF", "ASSOCIATE_OF")).items():
        rca_links.setdefault(k, []).extend(x for x in v if x.current(day))
    for rca in rcas:
        linked = sorted(
            {x.target if x.source == rca else x.source for x in rca_links.get(rca, [])} & set(peps)
        )
        statuses = {status_of[pep] for pep in linked}
        if not linked:
            out.append(Start(rca, "rca", "", None, "unknown"))
        elif "in office" in statuses:
            out.append(Start(rca, "rca", "", None, "in office"))
        elif "unknown" in statuses:
            out.append(Start(rca, "rca", "", None, "unknown"))
        # every linked PEP has left office: reg 35(11), no start
    return out, positions


def _first_link_score(link: LinkRow) -> float:
    if link.rel_type == "DIRECTOR_OF":
        return 0.5
    if link.rel_type == "CONTROLS" and link.control_type == "appointment":
        return 1.0
    low = link.share_min if link.share_min is not None else 0.0
    if low > 50 or (low == 50 and link.share_min_exclusive):
        return 1.0
    return 0.7


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date()
    people, positions = starts(source, p, as_of)
    links: dict[str, LinkRow] = {}
    frontier = sorted({s.person for s in people})
    seen = set(frontier)
    day = as_of.isoformat()
    for _ in range(p.ownership_control_hops):
        if not frontier:
            break
        nxt = set()
        for rows in source.links_from(frontier, ("OWNS", "CONTROLS", "DIRECTOR_OF")).values():
            for x in rows:
                if not x.current(day):
                    continue
                links[x.rel_id] = x
                if x.target not in seen:
                    seen.add(x.target)
                    nxt.add(x.target)
        frontier = sorted(nxt)
    out_links: dict[str, list[LinkRow]] = defaultdict(list)
    for x in sorted(links.values(), key=lambda x: x.rel_id):
        out_links[x.source].append(x)
    position_ids = sorted({x.target for rows in positions.values() for x in rows})
    entities = source.entities(sorted(seen | set(position_ids) | {s.pep for s in people if s.pep}))
    reached: dict[str, list[tuple[Start, list[LinkRow]]]] = defaultdict(list)
    for s in people:
        for target, path in _paths(s.person, out_links, p.ownership_control_hops, p.max_paths):
            if "Organization" in entities[target].labels:
                reached[target].append((s, path))
    findings = []
    for target in sorted(reached):
        if "PEP" in entities[target].labels:
            continue
        findings.append(_finding(target, reached[target], positions, entities, p))
    return DetectorOutput(findings, {"starts": len(people), "links": len(links)})


def _paths(
    start: str, out_links: dict[str, list[LinkRow]], max_hops: int, limit: int
) -> Iterator[tuple[str, list[LinkRow]]]:
    """Simple paths from `start` of 1 to `max_hops` relationships, breadth first."""
    found = 0
    queue: deque[tuple[str, list[LinkRow], frozenset[str]]] = deque(
        [(start, [], frozenset({start}))]
    )
    while queue:
        node, path, visited = queue.popleft()
        for x in out_links.get(node, []):
            if x.target in visited:
                continue
            grown = [*path, x]
            yield x.target, grown
            found += 1
            if found >= limit:
                return
            if len(grown) < max_hops:
                queue.append((x.target, grown, visited | {x.target}))


def _finding(
    target: str,
    found: list[tuple[Start, list[LinkRow]]],
    positions: dict[str, list[LinkRow]],
    entities: dict[str, EntityRow],
    p: Params,
) -> Finding:
    def score(item: tuple[Start, list[LinkRow]]) -> tuple[float, int, str]:
        s, path = item
        return (-RELATION_SCORE[s.relation], len(path), s.person)

    ordered = sorted(found, key=lambda item: (score(item), tuple(x.rel_id for x in item[1])))
    best, best_path = ordered[0]
    hops = len(best_path)
    domestic = False
    if best.pep:
        countries = {c for x in positions.get(best.pep, []) for c in entities[x.target].countries}
        domestic = bool(countries) and countries <= set(p.domestic_countries)
    strength = clip01(
        0.35 * RELATION_SCORE[best.relation]
        + 0.3 * (1 - (hops - 1) / p.ownership_control_hops)
        + 0.2 * _first_link_score(best_path[0])
        + 0.15 * OFFICE_SCORE[best.office]
        - (0.1 if domestic else 0.0)
    )
    shown = ordered[: p.max_steps]
    edges: set[str] = set()
    nodes: set[str] = {target}
    steps: list[tuple[str, ...]] = []
    for s, path in shown:
        step = tuple(x.rel_id for x in path)
        if s.link is not None:
            step = (s.link.rel_id, *step)
        steps.append(step)
        edges.update(step)
        nodes.update({s.person, *(x.target for x in path)})
        if s.pep:
            nodes.add(s.pep)
    peps = sorted({s.pep for s, _ in found if s.pep})
    metrics = {
        "relation": best.relation,
        "office": best.office,
        "office_dates_unknown": best.office == "unknown",
        "domestic": domestic,
        "shortest_path": min(len(path) for _, path in found),
        "paths": len(found),
        "peps": len(peps),
        "first_link": best_path[0].rel_type,
        "family_relationship": relation_to_pep(best.link, best.pep)
        if best.link is not None and best.relation == "family"
        else "",
    }
    return Finding(
        typology=SLUG,
        variant=best.relation,
        anchor=target,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=(Subject(target, "exposed_entity"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=False,
    )
```

### `detect/src/neonradar_detect/detectors/cash_commingling.py`

Verbatim. Python, 214 lines. SHA-256 `d2c84f85a917d956566684cb8c976d54232bb9948d237097b3b80d07cf6e8043`.

```python
"""cash_commingling 0.1.0: a business banking far more cash than similar businesses in its area,
with money moving on to its own people (PHASE-1.md 7.2 extended entry; `typology-detection-
definitions.md` section 14; PHASE-3.md 7.3.14).

"The volume of currency in a restaurant used to launder money will most likely be higher in
comparison with similar restaurants in the area" (FFIEC). For each company with cash deposits in
`currency` in the window, the peer group is the other companies of the same sector and the same
area (the postcode district of the registered address, or its city when there is no postcode). A
company with at least `min_peers` peers and at least `min_window_amount` banked qualifies when its
cash in the window is at least `min_ratio` times the median of its peers'. The strength adds the
change over time (the daily mean of the last `change_days` of the window against the
`prior_days` before them, when at least `change_days` of earlier data exist), the share of its
outflows in the window paid to accounts of its owners, directors or their relatives, and cash
banked on Sundays (London time; C2 has no opening hours, so this is a weak proxy).

The generator's calibration is the only benchmark in synthetic data, so the peer comparison is
circular there (section 14, "misleading alerts"); the evaluation report says so.

pattern_strength = 0.4 * min(1, ratio / (2 * min_ratio)) + 0.2 * min(1, max(0, change - 1) / 2)
+ 0.25 * min(1, related-party share / related_party_share) + 0.15 * min(1, 4 * Sunday share).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import CashProfile, Pay
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "cash_commingling"
VERSION = "0.1.0"
QUERIES = (
    "cash_profiles.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "paid_time_range.cypher",
    "payments_from.cypher",
    "payments_into.cypher",
)
LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True, slots=True)
class Params:
    currency: str = "GBP"
    min_peers: int = 5
    min_ratio: float = 3.0
    min_window_amount: float = 10000.0
    change_days: int = 90
    prior_days: int = 365
    related_party_share: float = 0.5
    max_candidates: int = 200_000


def area(profile: CashProfile) -> str:
    """The postcode district (outward code), else the city, else ""."""
    code = profile.postal_code.strip().upper()
    if code:
        return code.split()[0] if " " in code else code[:-3]
    return profile.city.strip().casefold()


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    span = source.paid_time_range()
    if span is None:
        return DetectorOutput([], {"profiles": 0})
    profiles = source.cash_profiles(
        window.start, window.start, window.end, p.currency, p.max_candidates
    )
    groups: dict[tuple[str, str], list[CashProfile]] = defaultdict(list)
    for x in profiles:
        if x.sector and area(x):
            groups[(x.sector, area(x))].append(x)
    flagged: list[tuple[CashProfile, float, int]] = []
    for members in groups.values():
        if len(members) < p.min_peers + 1:
            continue
        for x in members:
            peers = [y.window_pence for y in members if y.holder != x.holder]
            median = statistics.median(peers)
            if median <= 0 or x.window_pence < p.min_window_amount * 100:
                continue
            ratio = x.window_pence / median
            if ratio >= p.min_ratio:
                flagged.append((x, ratio, len(peers)))
    changes: dict[str, float] = {}
    if flagged:
        recent_start = window.end - timedelta(days=p.change_days)
        prior_start = max(recent_start - timedelta(days=p.prior_days), span[0])
        covered = (recent_start - prior_start).total_seconds() / 86400
        if covered >= p.change_days:
            for row in source.cash_profiles(
                prior_start, recent_start, window.end, p.currency, p.max_candidates
            ):
                if row.prior_pence > 0:
                    changes[row.holder] = (row.window_pence / p.change_days) / (
                        row.prior_pence / covered
                    )
    findings = [
        _finding(x, ratio, peers, changes.get(x.holder), source, p, window)
        for x, ratio, peers in sorted(flagged, key=lambda f: f[0].holder)
    ]
    return DetectorOutput(findings, {"profiles": len(profiles), "peer_groups": len(groups)})


def _finding(
    x: CashProfile,
    ratio: float,
    peers: int,
    change: float | None,
    source: Source,
    p: Params,
    window: Window,
) -> Finding:
    deposits = sorted(
        (
            d
            for pays in source.payments_into(x.accounts, window.start, window.end).values()
            for d in pays
            if d.channel == "cash_deposit" and d.currency == p.currency
        ),
        key=lambda d: (d.ts, d.edge_id),
    )
    owners = [
        y for rows in source.links_into([x.holder], ("OWNS", "DIRECTOR_OF")).values() for y in rows
    ]
    people = sorted({y.source for y in owners})
    family = source.links_from(people, ("FAMILY_OF",))
    family_in = source.links_into(people, ("FAMILY_OF",))
    relatives = {y.target for rows in family.values() for y in rows} | {
        y.source for rows in family_in.values() for y in rows
    }
    related = sorted(set(people) | relatives)
    holdings = source.links_from(related, ("HOLDS_ACCOUNT",))
    related_accounts = {y.target for rows in holdings.values() for y in rows}
    outflows: list[Pay] = sorted(
        (
            y
            for pays in source.payments_from(x.accounts, window.start, window.end).values()
            for y in pays
        ),
        key=lambda y: (y.ts, y.edge_id),
    )
    to_related = [y for y in outflows if y.counterparty in related_accounts]
    out_total = sum(y.amount for y in outflows)
    related_share = sum(y.amount for y in to_related) / out_total if out_total > 0 else 0.0
    sunday = (
        sum(1 for d in deposits if d.ts.astimezone(LONDON).weekday() == 6) / len(deposits)
        if deposits
        else 0.0
    )
    strength = clip01(
        0.4 * min(1.0, ratio / (2 * p.min_ratio))
        + 0.2 * (min(1.0, max(0.0, change - 1) / 2) if change is not None else 0.0)
        + 0.25 * min(1.0, related_share / p.related_party_share)
        + 0.15 * min(1.0, 4 * sunday)
    )
    metrics = {
        "cash_amount": round(x.window_pence / 100, 2),
        "cash_deposits": x.window_deposits,
        "currency": p.currency,
        "peers": peers,
        "peer_ratio": round(ratio, 2),
        "sector": x.sector,
        "area": area(x),
        "change_ratio": round(change, 2) if change is not None else -1,
        "related_party_share": round(related_share, 4),
        "sunday_share": round(sunday, 4),
    }
    subjects = [Subject(x.holder, "business")] + [
        Subject(a, "receiving_account") for a in x.accounts
    ]
    deposit_edges = tuple(d.edge_id for d in deposits)
    related_edges = tuple(y.edge_id for y in to_related)
    branches = {d.counterparty for d in deposits}
    holding_links = sorted(
        (
            y
            for rows in holdings.values()
            for y in rows
            if y.target in {z.counterparty for z in to_related}
        ),
        key=lambda y: y.rel_id,
    )
    nodes = {
        x.holder,
        *x.accounts,
        *branches,
        *(y.counterparty for y in to_related),
        *(y.source for y in holding_links),
    }
    edges = set(deposit_edges) | set(related_edges)
    steps: list[tuple[str, ...]] = [deposit_edges]
    if related_edges:
        steps.append(related_edges)
    ends = [d.ts for d in deposits] + [y.ts for y in to_related]
    return Finding(
        typology=SLUG,
        variant="",
        anchor=x.accounts[0],
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=tuple(subjects),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=(min(ends), max(ends)),
        activity=True,
    )
```

### `detect/typologies/formation_agent_cluster.yaml`

Verbatim. YAML, 64 lines. SHA-256 `533960491ac9bf6469faf9ebd7b13a897dc96050e7d7d67cd14d759df130c227`.

```yaml
slug: formation_agent_cluster
name: Formation agent cluster
shape_name: one agent behind a burst of company formations
version: 0.1.0
status: draft
tier: extended
owner: '@TODO'
approved_by: null
summary: One agent behind a burst of company formations whose officers recur across the companies.
doc: docs/typologies/formation-agent-cluster.md
citations:
- fatf_tcsp_2010
- fatf_pml_2018
- fincen_fin_2006_g014
- ca_acsp_s1098a_2006
graph_pattern: >-
  An agent with REPRESENTS to at least ten companies incorporated within 30 days of each other and at least two
  officers directing two or more of them.
parameters:
  min_companies:
    default: 10
    min: 1
    max: 100
  window_days:
    default: 30
    min: 1
    max: 300
  min_shared_officers:
    default: 2
    min: 1
    max: 20
  max_evidence_companies:
    default: 100
    min: 1
    max: 1000
  max_candidates:
    default: 50000
    min: 1
    max: 500000
metrics:
- clients
- incorporated_in_burst
- burst_first
- burst_last
- window_days
- shared_officers
- companies_with_shared_officer
- at_agent_address
- nominee_officers
- paying_pairs
- companies_shown
wording:
  headline_structural: >-
    One agent behind {incorporated_in_burst} companies incorporated within {window_days} days, with {shared_officers}
    officers shared across them
  headline_synthetic: >-
    Synthetic scenario: one agent behind {incorporated_in_burst} companies incorporated within {window_days} days,
    with {shared_officers} officers shared across them
false_positives:
- Corporate groups formed in one go by their agent
- Busy lawful formation agents
synthetic_support: medium
generator_scenario: formation_agent_cluster
detector: neonradar_detect.detectors.formation_agent_cluster
```

### `detect/typologies/recycled_directors.yaml`

Verbatim. YAML, 72 lines. SHA-256 `bf8edd0145de53a9fdae53dbb4c9b92226ac013affdf2344f3426918994b2bce`.

```yaml
slug: recycled_directors
name: Recycled directors
shape_name: one person directing many companies
version: 0.1.0
status: draft
tier: extended
owner: '@TODO'
approved_by: null
summary: One person serving as director of many unrelated companies, or appointed to many in a short time.
doc: docs/typologies/recycled-directors.md
citations:
- fatf_egmont_concealment_2018
- europol_efecta_2023
- fatf_pml_2018
- ca_director_idv_s167m_2006
graph_pattern: >-
  A Person with active DIRECTOR_OF across at least ten ownership groups, or appointments across at least five groups
  within 30 days.
parameters:
  min_active_appointments:
    default: 10
    min: 1
    max: 100
  burst_appointments:
    default: 5
    min: 1
    max: 50
  burst_days:
    default: 30
    min: 1
    max: 300
  short_tenure_days:
    default: 90
    min: 1
    max: 900
  max_evidence_companies:
    default: 100
    min: 1
    max: 1000
  max_candidates:
    default: 50000
    min: 1
    max: 500000
metrics:
- appointments
- active_appointments
- active_groups
- burst_appointments
- burst_groups
- burst_days
- short_tenures
- nominee_appointments
- relative_owned_companies
- paying_pairs
- companies_shown
wording:
  headline_structural: One person recorded as director of {active_groups} unrelated active companies
  headline_synthetic: 'Synthetic scenario: one person recorded as director of {active_groups} unrelated active companies'
  variants:
    burst:
      headline_structural: One person appointed director of {burst_groups} unrelated companies within {burst_days}
        days
      headline_synthetic: >-
        Synthetic scenario: one person appointed director of {burst_groups} unrelated companies within {burst_days}
        days
false_positives:
- Professional directors of funds
- Company secretaries
- Directors across one group
synthetic_support: medium
generator_scenario: recycled_directors
detector: neonradar_detect.detectors.recycled_directors
```

### `detect/typologies/pep_exposure.yaml`

Verbatim. YAML, 113 lines. SHA-256 `05ab25dfce63116ebd61fa41890919a1c13404d48877fdc363e6707a0a199e0d`.

```yaml
slug: pep_exposure
name: PEP exposure
shape_name: links to a person listed as politically exposed
version: 0.1.0
status: draft
tier: extended
owner: '@TODO'
approved_by: null
summary: >-
  An organisation that a politically exposed person, a family member or a close associate owns, controls or directs,
  directly or through up to three companies.
doc: docs/typologies/pep-exposure.md
citations:
- fatf_peps_2013
- mlr_2017_reg_35
- fca_fg25_3
- fatf_recommendations_2026
graph_pattern: >-
  A :PEP person in scope (or a family member one FAMILY_OF hop away or an associate one ASSOCIATE_OF hop away while
  the PEP holds office, or an :RCA person), then one to three OWNS, CONTROLS or DIRECTOR_OF relationships to an
  organisation.
parameters:
  family_relationships:
    default:
    - spouse
    - civil partner
    - husband
    - wife
    - child
    - son
    - daughter
    - child's spouse
    - child's civil partner
    - son-in-law
    - daughter-in-law
    - parent
    - father
    - mother
    - sibling
    - brother
    - sister
  associate_relationships:
    default:
    - business partner
    - business associate
    - co-owner
    - joint owner
  associate_hops:
    default: 1
    min: 0
    max: 1
  ownership_control_hops:
    default: 3
    min: 1
    max: 4
  after_office_months:
    default: 12
    min: 12
    max: 240
  domestic_countries:
    default:
    - gb
  max_paths:
    default: 1000
    min: 1
    max: 10000
  max_steps:
    default: 12
    min: 1
    max: 120
metrics:
- relation
- office
- office_dates_unknown
- domestic
- shortest_path
- paths
- peps
- first_link
- family_relationship
wording:
  headline_structural: >-
    Organisation within {shortest_path|n:recorded link} of a person listed as politically exposed
  headline_synthetic: >-
    Synthetic scenario: organisation within {shortest_path|n:recorded link} of a person listed as politically exposed
  variants:
    family:
      headline_structural: >-
        Organisation within {shortest_path|n:recorded link} of a relative of a person listed as politically exposed
      headline_synthetic: >-
        Synthetic scenario: organisation within {shortest_path|n:recorded link} of a relative of a person listed as
        politically exposed
    associate:
      headline_structural: >-
        Organisation within {shortest_path|n:recorded link} of a close associate of a person listed as politically
        exposed
      headline_synthetic: >-
        Synthetic scenario: organisation within {shortest_path|n:recorded link} of a close associate of a person
        listed as politically exposed
    rca:
      headline_structural: >-
        Organisation within {shortest_path|n:recorded link} of a person listed as a relative or close associate of
        a politically exposed person
      headline_synthetic: >-
        Synthetic scenario: organisation within {shortest_path|n:recorded link} of a person listed as a relative or
        close associate of a politically exposed person
false_positives:
- Ordinary family businesses of public office holders
- People long out of office
- Homonyms
synthetic_support: medium
generator_scenario: pep_exposure
detector: neonradar_detect.detectors.pep_exposure
```

### `detect/typologies/cash_commingling.yaml`

Verbatim. YAML, 74 lines. SHA-256 `f41fb7eec70dca0de03c1a8309f623a677e5272e99d1421f91cd407505fec77d`.

```yaml
slug: cash_commingling
name: Cash commingling
shape_name: cash banked far above similar businesses
version: 0.1.0
status: draft
tier: extended
owner: '@TODO'
approved_by: null
summary: >-
  A business banking far more cash than similar businesses in its area, with money moving on to its own people.
doc: docs/typologies/cash-commingling.md
citations:
- ffiec_cash_intensive
- ffiec_appendix_f
- europol_efecta_2023
graph_pattern: >-
  Cash deposits into a Company's accounts at least three times the median of at least five peers of the same sector
  and postcode district.
parameters:
  currency:
    default: GBP
  min_peers:
    default: 5
    min: 1
    max: 50
  min_ratio:
    default: 3.0
    min: 1.0
    max: 20.0
  min_window_amount:
    default: 10000.0
    min: 0.0
    max: 100000.0
  change_days:
    default: 90
    min: 1
    max: 900
  prior_days:
    default: 365
    min: 1
    max: 3650
  related_party_share:
    default: 0.5
    min: 0.0
    max: 1.0
  max_candidates:
    default: 200000
    min: 1
    max: 2000000
metrics:
- cash_amount
- cash_deposits
- currency
- peers
- peer_ratio
- sector
- area
- change_ratio
- related_party_share
- sunday_share
wording:
  headline_structural: >-
    Cash banked at {peer_ratio} times the median of {peers} similar businesses in the area, {cash_amount|money}
    in total
  headline_synthetic: >-
    Synthetic scenario: cash banked at {peer_ratio} times the median of {peers} similar businesses in the area,
    {cash_amount|money} in total
false_positives:
- Busy or growing businesses
- A new site or branch
- Communities that prefer cash
synthetic_support: medium
generator_scenario: cash_commingling
detector: neonradar_detect.detectors.cash_commingling
```

### `detect/tests/test_detector_extended_registry.py`

Verbatim. Python, 264 lines. SHA-256 `28c245b4b1e28d3fe55000f2768efc62f7808fed492591e6d10bbc4a35797a72`.

```python
from datetime import UTC, date, datetime, timedelta

from kit import Kit, detect, source_of
from neonradar_detect.detectors import formation_agent_cluster as fa
from neonradar_detect.detectors import pep_exposure as pe
from neonradar_detect.detectors import recycled_directors as rd
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(module, k: Kit, **overrides):
    return {
        f.anchor: f
        for f in module.run(source_of(k.records), module.Params(**overrides), WINDOW).findings
    }


# formation_agent_cluster ---------------------------------------------------------------------


def _agency(
    k: Kit, name: str, *, spread_days: int = 1, shared: int = 2, n: int = 12
) -> tuple[str, list[str]]:
    office = k.address(f"{name}-office")
    agent = k.company(f"{name}-agent", address=office)
    clients = []
    for i in range(n):
        incorporated = (date(2025, 3, 1) + timedelta(days=i * spread_days)).isoformat()
        c = k.company(
            f"{name}-c{i:02d}", incorporated=incorporated, address=office if i < 6 else ""
        )
        k.represents(agent, c)
        clients.append(c)
    for s in range(shared):
        officer = k.person(f"{name}-officer{s}")
        for c in clients[s * 4 : s * 4 + 4]:
            k.director(officer, c, nominee=s == 0)
    return agent, clients


def test_agent_behind_a_burst_with_shared_officers_and_payments():
    k = Kit()
    agent, clients = _agency(k, "fac")
    accts = [k.account(f"fac{i}", c) for i, c in enumerate(clients[:4])]
    for a, b in ((0, 1), (1, 2), (2, 3)):
        k.pay(accts[a], accts[b], 25000, f"2026-02-0{a + 2}T10:00")
    [f] = _run(fa, k).values()
    assert f.anchor == agent and [s.role for s in f.subjects] == ["agent"]
    m = f.metrics
    assert (
        m["incorporated_in_burst"],
        m["shared_officers"],
        m["companies_with_shared_officer"],
    ) == (12, 2, 8)
    assert (m["at_agent_address"], m["nominee_officers"], m["paying_pairs"]) == (6, 1, 3)
    assert f.activity and f.pattern_strength == round(
        0.3 * 12 / 30 + 0.25 * 8 / 12 + 0.15 * 6 / 12 + 0.15 + 0.15, 4
    )


def test_spread_out_formations_or_one_shared_officer_are_not_a_cluster():
    k = Kit()
    _agency(k, "slow", spread_days=30)
    _agency(k, "solo", shared=1)
    assert _run(fa, k) == {}


# recycled_directors --------------------------------------------------------------------------


def test_many_unrelated_boards_but_not_one_group():
    k = Kit()
    busy = k.person("busy")
    for i in range(10):
        k.director(busy, k.company(f"u{i}"), start=f"20{15 + i % 8}-0{1 + i % 9}-01")
    group_man = k.person("group")
    hold = k.company("hold")
    k.director(group_man, hold, start="2018-01-01")
    for i in range(11):
        sub = k.company(f"sub{i}")
        k.owns(hold, sub)
        k.director(group_man, sub, start="2018-01-01")
    found = _run(rd, k)
    assert set(found) == {busy}  # twelve boards in one group are one group
    f = found[busy]
    assert f.variant == "many_boards" and f.metrics["active_groups"] == 10
    assert [s.role for s in f.subjects] == ["director"]


def test_burst_of_short_appointments_and_a_relative_owner():
    k = Kit()
    straw = k.person("straw")
    brother = k.person("bro")
    k.family(straw, brother, "sibling")
    companies = [k.company(f"s{i}", incorporated="2025-05-01") for i in range(5)]
    for i, c in enumerate(companies):
        k.director(straw, c, start=f"2025-05-{2 + i:02d}", end=f"2025-07-{2 + i:02d}")
    k.owns(brother, companies[0])
    [f] = _run(rd, k).values()
    m = f.metrics
    assert f.variant == "burst" and (
        m["burst_groups"],
        m["short_tenures"],
        m["relative_owned_companies"],
    ) == (5, 5, 1)
    assert m["active_groups"] == 0 and brother in f.node_ids


# pep_exposure --------------------------------------------------------------------------------


def _pep(k: Kit, name: str, *, end: str = "", country: str = "zz") -> str:
    pep = k.person(name, topics=("role.pep",))
    k.occupancy(pep, k.position(f"{name}-post", country=country), start="2019-01-01", end=end)
    return pep


def test_pep_holdings_through_companies():
    k = Kit()
    pep = _pep(k, "minister")
    a, b = k.company("pa"), k.company("pb")
    k.owns(pep, a, "75-100")
    k.owns(a, b, "25-50")
    found = _run(pe, k)
    assert (
        set(found) == {a, b}
        and found[a].variant == "pep"
        and found[a].metrics["office"] == "in office"
    )
    assert found[a].pattern_strength == round(0.35 + 0.3 + 0.2 + 0.15, 4)
    assert found[b].metrics["shortest_path"] == 2 and pep in found[b].node_ids
    assert found[b].pattern_strength == round(0.35 + 0.3 * (1 - 1 / 3) + 0.2 + 0.15, 4)


def test_family_while_in_office_only_and_former_peps_for_twelve_months():
    k = Kit()
    pep = _pep(k, "mayor")
    spouse, cousin = k.person("spouse"), k.person("cousin")
    k.family(pep, spouse, "spouse")
    k.family(pep, cousin, "cousin")
    c, d, own = k.company("sc"), k.company("cc"), k.company("own")
    k.owns(spouse, c)
    k.owns(cousin, d)
    k.director(pep, own)
    found = _run(pe, k)
    assert set(found) == {c, own} and found[c].variant == "family"
    assert (
        found[c].metrics["family_relationship"] == "spouse"
        and found[own].metrics["first_link"] == "DIRECTOR_OF"
    )
    k2 = Kit()
    left = _pep(k2, "left", end="2025-12-31")  # left office six months before the end of the window
    spouse2 = k2.person("spouse2")
    k2.family(left, spouse2, "spouse")
    e, g = k2.company("e"), k2.company("g")
    k2.owns(left, e)
    k2.owns(spouse2, g)
    found2 = _run(pe, k2)
    assert set(found2) == {e} and found2[e].metrics["office"] == "former"
    k3 = Kit()
    long_gone = _pep(k3, "gone", end="2024-12-31")  # eighteen months before the end of the window
    h = k3.company("h")
    k3.owns(long_gone, h)
    assert _run(pe, k3) == {}
    assert set(_run(pe, k3, after_office_months=24)) == {h}


def test_family_links_are_read_from_the_relatives_side():
    """FtM names the relative from the person's side: a PEP recorded as someone's mother makes
    that someone the PEP's child; a PEP recorded as someone's son-in-law makes that someone a
    parent-in-law, outside reg 35(12)(b); a bare "partner" is not in the default list."""
    k = Kit()
    pep = _pep(k, "judge")
    child, in_law, partner = k.person("child"), k.person("inlaw"), k.person("partner")
    k.family(child, pep, "mother")
    k.family(in_law, pep, "son-in-law")
    k.family(pep, partner, "partner")
    c, i, q = k.company("child-co"), k.company("inlaw-co"), k.company("partner-co")
    k.owns(child, c)
    k.owns(in_law, i)
    k.owns(partner, q)
    found = _run(pe, k)
    assert set(found) == {c} and found[c].variant == "family"
    assert found[c].metrics["family_relationship"] == "child"  # what the person is to the PEP


def test_associates_need_business_relations_or_a_joint_holding_and_links_must_be_current():
    k = Kit()
    pep = _pep(k, "senator")
    friend, partner = k.person("friend"), k.person("joint")
    k.associate(pep, friend, "friend")
    k.associate(pep, partner, "friend")
    joint = k.company("joint-co")
    k.owns(pep, joint, "25-50")
    k.owns(partner, joint, "25-50")
    f_co, p_co, old = k.company("friend-co"), k.company("joint-other"), k.company("old-board")
    k.owns(friend, f_co)
    k.owns(partner, p_co)
    k.director(pep, old, start="2018-01-01", end="2025-03-31")  # resigned before the window ends
    found = _run(pe, k)
    assert set(found) == {joint, p_co} and found[p_co].variant == "associate"


def test_rca_follows_the_office_of_the_pep_it_is_linked_to():
    k = Kit()
    former = _pep(k, "ex", end="2023-06-30")
    current = _pep(k, "now")
    rca_old = k.person("rca-old", topics=("role.rca",))
    rca_new = k.person("rca-new", topics=("role.rca",))
    k.family(former, rca_old, "sibling")
    k.associate(current, rca_new, "adviser")
    a, b = k.company("rca-old-co"), k.company("rca-new-co")
    k.owns(rca_old, a)
    k.owns(rca_new, b)
    found = _run(pe, k)
    assert a not in found  # reg 35(11): the linked PEP left office
    assert found[b].variant == "rca" and found[b].metrics["office"] == "in office"


def test_associates_rca_and_domestic_peps():
    k = Kit()
    pep = _pep(k, "envoy", country="gb")
    partner = k.person("partner")
    k.associate(pep, partner, "business partner")
    a = k.company("assoc-co")
    k.owns(partner, a, "50-75")
    rca = k.person("rca", topics=("role.rca",))
    r = k.company("rca-co")
    k.controls(rca, r, "appointment")
    found = _run(pe, k)
    assert found[a].variant == "associate" and found[a].metrics["domestic"] is True
    assert found[a].pattern_strength == round(0.35 * 0.6 + 0.3 + 0.2 + 0.15 - 0.1, 4)
    assert found[r].variant == "rca" and found[r].metrics["office_dates_unknown"] is True


def test_a_real_person_as_subject_is_withheld():
    k = Kit()
    real_person = k.person("gbch-p-T0000003", "Test Person", real=True)
    for i in range(10):
        k.director(real_person, k.company(f"board{i}"), start=f"201{i}-01-01")
    result = detect(k.records, {"recycled_directors": rd.Params()})
    assert result.alerts == []
    assert result.summary["withheld"] == {
        "activity_on_real": 0,
        "real_person_subject": 1,
        "real_person_evidence": 0,
        "registry_on_real": 0,
    }


def test_an_agent_whose_kind_the_source_does_not_state_is_withheld():
    """An ICIJ intermediary may be a person: as the subject of a real-data finding it is withheld
    like a person (R-REAL (b))."""
    k = Kit()
    agent = k.legal_entity("icij-T0000001", "Test Intermediary", dataset="icij_offshore_leaks")
    officers = [k.person("io0"), k.person("io1")]
    for i in range(12):
        c = k.company(f"ic{i:02d}", incorporated=(date(2025, 3, 1) + timedelta(days=i)).isoformat())
        k.represents(agent, c)
        if i < 8:
            k.director(officers[i // 4], c)
    result = detect(k.records, {"formation_agent_cluster": fa.Params()})
    assert result.alerts == [] and result.summary["withheld"]["real_person_subject"] == 1
```

### `detect/tests/test_detector_cash_commingling.py`

Verbatim. Python, 76 lines. SHA-256 `fb23578911824fbb399b4890da399571e701d86bfe16b45d467b0d886d4c152f`.

```python
from datetime import UTC, date, datetime, timedelta

from kit import Kit, source_of
from neonradar_detect.detectors import cash_commingling as cc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 4, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return cc.run(source_of(k.records), cc.Params(**overrides), WINDOW).findings


def _restaurant(
    k: Kit,
    name: str,
    postcode: str,
    weekly: float,
    *,
    sunday: bool = False,
    sector: str = "restaurant",
):
    branch = "syn-fx-acct-branch"
    addr = k.address_at(f"{name}-addr", f"1 {name} Road, {postcode}", postcode)
    co = k.company(name, sector=sector, address=addr)
    acct = k.account(name, co)
    day = date(2026, 1, 5)  # a Monday
    while day < date(2026, 4, 1):
        when = day + timedelta(days=6 if sunday else 1)
        if when < date(2026, 4, 1):
            k.pay(branch, acct, weekly, f"{when.isoformat()}T16:00", channel="cash_deposit")
        day += timedelta(days=7)
    return co, acct


def _town(k: Kit) -> None:
    k.account("branch", k.company("bank"), kind="cash_ledger")
    k.history("2025-01-02T10:00")
    for i, weekly in enumerate((900, 1000, 1100, 950, 1050)):
        _restaurant(k, f"peer{i}", "QQ1 2AB", weekly)


def test_front_business_against_its_peers():
    k = Kit()
    _town(k)
    front, acct = _restaurant(k, "front", "QQ1 9ZZ", 5000, sunday=True)
    owner = k.person("owner")
    k.owns(owner, front)
    own_acct = k.account("owner", owner)
    for m in (1, 2, 3):
        k.pay(acct, own_acct, 15000, f"2026-0{m}-27T12:00")
    k.pay(acct, k.account("supplier", k.company("supplier")), 5000, "2026-02-10T12:00")
    [f] = _run(k)
    assert f.anchor == acct and [s.role for s in f.subjects] == ["business", "receiving_account"]
    m = f.metrics
    ratio = 12 * 5000 / (13 * 1000)  # twelve Sundays against the peers' median of thirteen Tuesdays
    assert (m["peers"], m["peer_ratio"], m["area"], m["sector"]) == (
        5,
        round(ratio, 2),
        "QQ1",
        "restaurant",
    )
    assert (m["related_party_share"], m["sunday_share"], m["change_ratio"]) == (0.9, 1.0, -1)
    assert f.pattern_strength == round(0.4 * ratio / 6 + 0.25 + 0.15, 4)
    assert len(f.steps) == 2 and len(f.steps[1]) == 3


def test_peers_must_share_sector_and_area():
    k = Kit()
    _town(k)
    _restaurant(k, "far", "QQ7 1AA", 5000)  # another district: no peers there
    _restaurant(k, "shop", "QQ1 3CD", 5000, sector="retail")  # another sector
    assert _run(k) == []
    _restaurant(k, "busy", "QQ1 4EF", 2500)  # 2.5 times the median
    assert _run(k) == []
    assert len(_run(k, min_ratio=2.5)) == 1
```

## M3.6 Evaluation harness and the CI gate

The evaluation package, the evaluation run behind `neonradar eval`, their tests, the seeds and the CI baseline. 13 verbatim files (PHASE-3.md M3.6).

### `detect/src/neonradar_detect/evaluation/__init__.py`

Verbatim. Python, 1 lines. SHA-256 `efc477c61ea9529412959ad2944d24aecf1ac0a35c0e6477224bf789246ea310`.

```python
"""The detection evaluation: matching, metrics, the harness and the report (PHASE-3.md 7.6)."""
```

### `detect/src/neonradar_detect/evaluation/match.py`

Verbatim. Python, 214 lines. SHA-256 `37e938652def94e9f6686af385841375f537192c4da1fadedafff6b642039e99`.

```python
"""Match alerts to planted scenarios and count them (PHASE-3.md 7.6.2).

The rules follow `evaluation-alerting.md` sections 1.3 and 1.4: an alert is compared only with
scenarios of its own typology; payment typologies by the overlap (intersection over union) of the
alert's PAID edge ids with the scenario's labelled payments (for a look-alike, the share of the
alert's PAID edges that the look-alike labelled, because look-alikes recur: an alert on one
month's rent collection is a look-alike hit), chain typologies by the overlap of
the alert's evidence nodes with the scenario's chain participants, exposure typologies by the same
exposed subject with the planted listed party among the evidence nodes, hub typologies by the same
hub. Pairs at or above `min_iou` are assigned one to one, best overlap first, ties broken by alert
id and then scenario id. Every alert then counts as exactly one of `true`, `duplicate` (it
overlaps an illicit scenario another alert took), `lookalike`, `partial` (it overlaps an illicit
scenario of its own typology, but below `min_iou`), `other` (it matches nothing of its own
typology but shares a labelled payment or participant with a scenario of another typology: a
factory address with nominee directors is also a recycled-director shape) or `background`.
Precision counts `true` alerts only; the other kinds are reported beside it.

An exposure scenario can expose several organisations (a listed owner's company and the companies
it owns in turn), and each is a correct alert of its own. So exposure scenarios are matched per
exposed organisation: each labelled `exposed_entity` is one unit, alerts take units one to one,
and the scenario counts as detected when an alert takes one of its core units.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

RULES_VERSION = "1"


@dataclass(frozen=True, slots=True)
class Rule:
    kind: str  # payment | chain | exposure | hub
    roles: frozenset[str] = (
        frozenset()
    )  # chain: participant roles compared; hub/exposure: the subject role
    party_roles: frozenset[str] = (
        frozenset()
    )  # exposure: roles that must appear among evidence nodes


RULES: dict[str, Rule] = {
    "structuring": Rule("payment"),
    "rapid_pass_through": Rule("payment"),
    "layering_chain": Rule("payment"),
    "circular_flow": Rule("payment"),
    "fan_in_collection": Rule("payment"),
    "fan_out_distribution": Rule("payment"),
    "dormant_reactivation": Rule("payment"),
    "cash_commingling": Rule("payment"),
    "shell_chain": Rule(
        "chain",
        frozenset({"owned_company", "layer", "top_owner", "nominee", "professional_director"}),
    ),
    "sanctions_exposure": Rule(
        "exposure", frozenset({"exposed_entity"}), frozenset({"listed_owner"})
    ),
    "pep_exposure": Rule("exposure", frozenset({"exposed_entity"}), frozenset({"pep"})),
    "mass_registration_address": Rule("hub", frozenset({"registered_address"})),
    "formation_agent_cluster": Rule("hub", frozenset({"agent"})),
    "recycled_directors": Rule("hub", frozenset({"director"})),
}


@dataclass(frozen=True, slots=True)
class AlertView:
    alert_id: str
    typology: str
    edge_ids: frozenset[str]
    node_ids: frozenset[str]
    subjects: Mapping[str, str]  # entity id -> role


@dataclass(frozen=True, slots=True)
class ScenarioView:
    scenario_id: str
    typology: str
    is_lookalike: bool
    tx_ids: frozenset[str]
    participants: Mapping[str, str]  # entity id -> role
    core: frozenset[str] = frozenset()  # participants with is_core true


@dataclass(slots=True)
class Outcome:
    typology: str
    alerts: int = 0
    true: int = 0
    duplicate: int = 0
    lookalike: int = 0
    partial: int = 0
    other: int = 0
    background: int = 0
    planted: int = 0
    detected: int = 0
    lookalikes: int = 0
    lookalikes_alerted: int = 0
    labelled_payments: int = 0
    covered_payments: int = 0
    matches: dict[str, str] = field(default_factory=dict)  # alert id -> scenario id
    kinds: dict[str, str] = field(default_factory=dict)  # alert id -> kind (module docstring)


def iou(a: frozenset[str] | set[str], b: frozenset[str] | set[str]) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _ids(members: Mapping[str, str], roles: frozenset[str]) -> set[str]:
    return {i for i, r in members.items() if r in roles}


def overlap(
    alert: AlertView, scenario: ScenarioView, payment_ids: frozenset[str], unit: str = ""
) -> float:
    rule = RULES[scenario.typology]
    if rule.kind == "payment":
        paid = alert.edge_ids & payment_ids
        if scenario.is_lookalike:
            # a look-alike recurs (rent every month): one recurrence caught is a hit
            return len(paid & scenario.tx_ids) / len(paid) if paid else 0.0
        return iou(paid, scenario.tx_ids)
    if rule.kind == "chain":
        return iou(set(alert.node_ids), _ids(scenario.participants, rule.roles))
    if rule.kind == "exposure":
        parties = _ids(scenario.participants, rule.party_roles)
        found = unit in _ids(alert.subjects, rule.roles)
        return 1.0 if found and parties and parties <= alert.node_ids else 0.0
    same = _ids(alert.subjects, rule.roles) == _ids(scenario.participants, rule.roles)
    return 1.0 if same and _ids(alert.subjects, rule.roles) else 0.0


def _units(scenario: ScenarioView) -> list[tuple[str, str, bool]]:
    """(unit id, exposed entity, core) for an exposure scenario; one unit for any other."""
    rule = RULES[scenario.typology]
    if rule.kind != "exposure":
        return [(scenario.scenario_id, "", True)]
    exposed = sorted(_ids(scenario.participants, rule.roles))
    core = scenario.core or frozenset(exposed)
    return [(f"{scenario.scenario_id}#{e}", e, e in core) for e in exposed]


def evaluate(
    typology: str,
    alerts: Sequence[AlertView],
    scenarios: Sequence[ScenarioView],
    payment_ids: frozenset[str],
    min_iou: float = 0.5,
) -> Outcome:
    if typology not in RULES:
        raise KeyError(f"no matching rule for {typology}")
    al = sorted((a for a in alerts if a.typology == typology), key=lambda a: a.alert_id)
    sc = sorted((s for s in scenarios if s.typology == typology), key=lambda s: s.scenario_id)
    look = {s.scenario_id for s in sc if s.is_lookalike}
    units = [(uid, s, entity, core) for s in sc for uid, entity, core in _units(s)]
    owner = {uid: s.scenario_id for uid, s, _, _ in units}
    scored = [
        (overlap(a, s, payment_ids, entity), a.alert_id, uid)
        for a in al
        for uid, s, entity, _ in units
    ]
    partly = {aid for o, aid, uid in scored if 0 < o < min_iou and owner[uid] not in look}
    pairs = sorted((p for p in scored if p[0] >= min_iou), key=lambda p: (-p[0], p[1], p[2]))
    match: dict[str, str] = {}
    taken: set[str] = set()
    for _, aid, uid in pairs:
        if aid not in match and uid not in taken:
            match[aid] = uid
            taken.add(uid)
    near: dict[str, set[str]] = {}
    for _, aid, uid in pairs:
        near.setdefault(aid, set()).add(owner[uid])
    others = [s for s in scenarios if s.typology != typology]
    other_edges = set().union(*(s.tx_ids for s in others)) if others else set()
    other_nodes = set().union(*(set(s.participants) for s in others)) if others else set()
    out = Outcome(typology, alerts=len(al))
    counts: Counter[str] = Counter()
    for a in al:
        if a.alert_id in match:
            kind = "lookalike" if owner[match[a.alert_id]] in look else "true"
        elif near.get(a.alert_id, set()) - look:
            kind = "duplicate"
        elif near.get(a.alert_id):
            kind = "lookalike"
        elif a.alert_id in partly:
            kind = "partial"
        elif a.edge_ids & other_edges or (a.node_ids | set(a.subjects)) & other_nodes:
            kind = "other"
        else:
            kind = "background"
        counts[kind] += 1
        out.kinds[a.alert_id] = kind
    out.true, out.duplicate = counts["true"], counts["duplicate"]
    out.lookalike, out.partial = counts["lookalike"], counts["partial"]
    out.other, out.background = counts["other"], counts["background"]
    detected = {owner[uid] for uid, _, _, core in units if core and uid in taken}
    illicit = [s for s in sc if not s.is_lookalike]
    out.planted = len(illicit)
    out.detected = sum(1 for s in illicit if s.scenario_id in detected)
    out.lookalikes = len(look)
    out.lookalikes_alerted = len(look & {owner[uid] for uid in taken})
    out.matches = {aid: owner[uid] for aid, uid in match.items()}
    if RULES[typology].kind == "payment":
        by_id = {a.alert_id: a for a in al}
        matched_edges: set[str] = set()
        for aid, sid in out.matches.items():
            if sid not in look:
                matched_edges |= by_id[aid].edge_ids
        labelled = set().union(*(s.tx_ids for s in illicit)) if illicit else set()
        out.labelled_payments = len(labelled)
        out.covered_payments = len(labelled & matched_edges)
    return out
```

### `detect/src/neonradar_detect/evaluation/metrics.py`

Verbatim. Python, 156 lines. SHA-256 `60bfa057f72a210612fd9649f6f46069cf28ff7df971ccbad99df3536beef2a1`.

```python
"""Per-typology figures over several generator seeds (PHASE-3.md 7.6.3).

Following `evaluation-alerting.md` 2.3: scenarios of one seed share background activity, so the
figures carry two 95 percent intervals, the pooled Wilson interval over all scenarios (or alerts)
and a t interval over the per-seed rates, and the headline is the wider of the two. A rate with
nothing to count (no planted scenarios, or no alerts) is None and is published as "n = 0".
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from neonradar_detect.evaluation.match import Outcome
from neonradar_detect.evaluation.stats import wilson_interval

# two-sided 95 percent quantiles of Student's t, by degrees of freedom
T_975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}

Interval = tuple[float, float]


def t_interval(values: Sequence[float]) -> Interval | None:
    """Mean of per-seed rates plus or minus t * s / sqrt(n), clipped to [0, 1]; None below two
    seeds."""
    n = len(values)
    if n < 2:
        return None
    mean = statistics.fmean(values)
    half = T_975.get(n - 1, 1.960) * statistics.stdev(values) / math.sqrt(n)
    return max(0.0, mean - half), min(1.0, mean + half)


def wider(a: Interval | None, b: Interval | None) -> Interval | None:
    if a is None or b is None:
        return a or b
    return a if (a[1] - a[0]) >= (b[1] - b[0]) else b


@dataclass(frozen=True, slots=True)
class Rate:
    k: int
    n: int
    value: float | None
    wilson: Interval | None
    across_seeds: Interval | None
    headline: Interval | None
    seeds_counted: int


def rate(pairs: Sequence[tuple[int, int]]) -> Rate:
    """`pairs` holds (k, n) per seed; seeds with n = 0 do not enter the across-seed interval."""
    k = sum(x for x, _ in pairs)
    n = sum(y for _, y in pairs)
    per_seed = [x / y for x, y in pairs if y > 0]
    w = wilson_interval(k, n) if n > 0 else None
    t = t_interval(per_seed)
    return Rate(k, n, k / n if n else None, w, t, wider(w, t), len(per_seed))


@dataclass(frozen=True, slots=True)
class Figures:
    typology: str
    seeds: int
    recall: Rate
    precision: Rate
    alerts: int
    true: int
    duplicate: int
    lookalike: int
    partial: int
    other: int
    background: int
    lookalikes: int
    lookalikes_alerted: int
    payment_coverage: float | None
    seed_recall: tuple[float, float, float] | None  # minimum, median, maximum


def figures(per_seed: Mapping[int, Mapping[str, Outcome]], typology: str) -> Figures:
    rows = [per_seed[s][typology] for s in sorted(per_seed) if typology in per_seed[s]]
    recall = rate([(o.detected, o.planted) for o in rows])
    precision = rate([(o.true, o.alerts) for o in rows])
    labelled = sum(o.labelled_payments for o in rows)
    covered = sum(o.covered_payments for o in rows)
    seed_rates = sorted(o.detected / o.planted for o in rows if o.planted)
    spread = (seed_rates[0], statistics.median(seed_rates), seed_rates[-1]) if seed_rates else None
    return Figures(
        typology,
        len(rows),
        recall,
        precision,
        sum(o.alerts for o in rows),
        sum(o.true for o in rows),
        sum(o.duplicate for o in rows),
        sum(o.lookalike for o in rows),
        sum(o.partial for o in rows),
        sum(o.other for o in rows),
        sum(o.background for o in rows),
        sum(o.lookalikes for o in rows),
        sum(o.lookalikes_alerted for o in rows),
        covered / labelled if labelled else None,
        spread,
    )


def macro(all_figures: Sequence[Figures]) -> dict[str, float | int | None]:
    """Unweighted means over typologies; F1 is the mean of per-typology F1
    (`evaluation-alerting.md` 1.5)."""
    recalls = [f.recall.value for f in all_figures if f.recall.value is not None]
    precisions = [f.precision.value for f in all_figures if f.precision.value is not None]
    f1s = []
    for f in all_figures:
        r, p = f.recall.value, f.precision.value
        if r is not None and p is not None:
            f1s.append(0.0 if r + p == 0 else 2 * r * p / (r + p))
    return {
        "typologies": len(all_figures),
        "macro_recall": statistics.fmean(recalls) if recalls else None,
        "macro_precision": statistics.fmean(precisions) if precisions else None,
        "macro_precision_typologies": len(precisions),
        "macro_f1": statistics.fmean(f1s) if f1s else None,
    }
```

### `detect/src/neonradar_detect/evaluation/stats.py`

Verbatim. Python, 26 lines. SHA-256 `303986ece509ce4d4d88aa0e2d5fdd4db3752b743130a2546fe43ca3c8ede42b`.

```python
"""Wilson score interval for the published detection figures (PHASE-3.md 3.4).

The same formula and worked example as `neonradar_resolve.stats` (PHASE-2.md 3.4). It is repeated
here so that `neonradar_detect` does not depend on `neonradar_resolve`, which brings Splink, DuckDB
and PyArrow.
"""

from __future__ import annotations

import math

Z_95 = 1.959963984540054  # two-sided 95 percent normal quantile


def wilson_interval(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (Wilson 1927)."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n and n > 0")
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = (z / denominator) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high
```

### `detect/src/neonradar_detect/evaluation/harness.py`

Verbatim. Python, 142 lines. SHA-256 `ae69f6495309547875596057045d2444da00d1b21097c80a40dceca3dbbac34b`.

```python
"""One world's alerts against its labels (PHASE-3.md 7.6.2).

The harness reads label files v2 (7.2.8) with its own small reader, because `neonradar_detect`
never imports the generator (`synthetic-transactions.md` 6.2: generator and detectors stay
independent). `evaluate_world` matches every typology's alerts with `match.evaluate` and also
counts true alerts per priority band, so the report can show whether the queue order helps
(`evaluation-alerting.md` 0, answer 7).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_detect.evaluation.match import AlertView, Outcome, ScenarioView, evaluate

LABEL_SCHEMA_MAJOR = "2"
BANDS = ("high", "medium", "low")


def read_label_csv(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """The `# key: value` header lines of a label CSV, and its rows."""
    header: dict[str, str] = {}
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            key, _, value = line[1:].partition(":")
            header[key.strip()] = value.strip()
        else:
            lines.append(line)
    return header, list(csv.DictReader(lines))


def _flag(value: str) -> bool:
    if value not in ("true", "false"):
        raise ValueError(f"not a label boolean: {value!r}")
    return value == "true"


def scenario_views(label_dir: Path) -> list[ScenarioView]:
    """Scenarios with their labelled payments and participants, in scenario id order."""
    tables = {}
    for name in ("scenarios", "transactions", "participants"):
        header, rows = read_label_csv(label_dir / f"{name}.csv")
        if header.get("synthetic") != "true":
            raise ValueError(f"{name}.csv does not say it is synthetic")
        if header.get("label_schema", "").split(".")[0] != LABEL_SCHEMA_MAJOR:
            raise ValueError(f"{name}.csv has label schema {header.get('label_schema')!r}")
        tables[name] = rows
    tx: dict[str, set[str]] = {}
    for row in tables["transactions"]:
        tx.setdefault(row["scenario_id"], set()).add(row["tx_id"])
    members: dict[str, dict[str, str]] = {}
    core: dict[str, set[str]] = {}
    for row in tables["participants"]:
        members.setdefault(row["scenario_id"], {})[row["object_id"]] = row["role"]
        if _flag(row["is_core"]):
            core.setdefault(row["scenario_id"], set()).add(row["object_id"])
    return [
        ScenarioView(
            row["scenario_id"],
            row["typology"],
            _flag(row["is_lookalike"]),
            frozenset(tx.get(row["scenario_id"], ())),
            members.get(row["scenario_id"], {}),
            frozenset(core.get(row["scenario_id"], ())),
        )
        for row in sorted(tables["scenarios"], key=lambda r: r["scenario_id"])
    ]


def alert_views(alerts: Iterable[Mapping[str, Any]]) -> list[AlertView]:
    """C4 alerts as the matcher sees them."""
    return [
        AlertView(
            a["alert_id"],
            a["typology"],
            frozenset(a["evidence"]["edge_ids"]),
            frozenset(a["evidence"]["node_ids"]),
            {s["entity_id"]: s["role"] for s in a["subjects"]},
        )
        for a in alerts
    ]


@dataclass(slots=True)
class WorldResult:
    seed: int
    outcomes: dict[str, Outcome]
    bands: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)


def evaluate_world(
    seed: int,
    alerts: Sequence[Mapping[str, Any]],
    scenarios: Sequence[ScenarioView],
    payment_ids: frozenset[str],
    typologies: Sequence[str],
    min_iou: float = 0.5,
) -> WorldResult:
    """Outcomes per typology, and (true alerts, alerts) per priority band."""
    views = alert_views(alerts)
    priority = {a["alert_id"]: a["priority"] for a in alerts}
    result = WorldResult(seed, {})
    for slug in typologies:
        outcome = evaluate(slug, views, scenarios, payment_ids, min_iou)
        result.outcomes[slug] = outcome
        per_band = {}
        for band in BANDS:
            ids = [aid for aid in outcome.kinds if priority[aid] == band]
            per_band[band] = (sum(1 for aid in ids if outcome.kinds[aid] == "true"), len(ids))
        result.bands[slug] = per_band
    return result


def counts(outcome: Outcome) -> dict[str, int]:
    """The exact counts the CI baseline pins (`eval/baselines/ci.json`, M3.6)."""
    return {
        "alerts": outcome.alerts,
        "true": outcome.true,
        "duplicate": outcome.duplicate,
        "lookalike": outcome.lookalike,
        "partial": outcome.partial,
        "other": outcome.other,
        "background": outcome.background,
        "planted": outcome.planted,
        "detected": outcome.detected,
        "lookalikes": outcome.lookalikes,
        "lookalikes_alerted": outcome.lookalikes_alerted,
    }


def pooled_bands(results: Sequence[WorldResult], typology: str) -> dict[str, tuple[int, int]]:
    """(true alerts, alerts) per priority band, summed over seeds."""
    out = {}
    for band in BANDS:
        pairs = [r.bands[typology][band] for r in results if typology in r.bands]
        out[band] = (sum(k for k, _ in pairs), sum(n for _, n in pairs))
    return out
```

### `detect/src/neonradar_detect/evaluation/report.py`

Verbatim. Python, 135 lines. SHA-256 `38586762083953be880e5fbf31f33681e7a5acda11e6e82d081885d277391edb`.

```python
"""The published detection figures: one Markdown table and its JSON twin (PHASE-3.md 7.6.4).

The text below the table is fixed (7.6.4): it says what each column counts and what the figures
do not show. Rates with nothing to count print "n = 0", never 0 or 1
(`evaluation-alerting.md` 1.5). Numbers are rounded for display only; the JSON keeps the counts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from neonradar_detect.evaluation.metrics import Figures, Interval, Rate, macro

READING_NOTES = (
    "How to read this table. Recall counts planted scenarios: a scenario is detected when an "
    "alert of its own typology matches it (PHASE-3.md 7.6.2). Precision counts alerts: true "
    "alerts divided by all alerts of the typology, so duplicates, look-alike hits, partial "
    "overlaps, alerts on other typologies' scenarios and alerts on background activity all count "
    "against it. Each interval is the wider of the pooled Wilson 95 percent interval and a t "
    "interval across seeds. The high and medium column is precision among the alerts the queue "
    "puts first. Look-alikes alerted counts planted benign look-alikes that drew an alert."
)
LIMITATIONS = (
    "What these figures do not show. Every scenario, look-alike and payment is synthetic and was "
    "written by the same team that wrote the detectors, so the figures measure how well the "
    "detectors find NeonRadar's own definitions of each pattern, not how they would perform on "
    "real data. The similar businesses that `cash_commingling` compares a business with were made "
    "by the same generator, so for that typology the comparison is circular. Precision depends on "
    "how many scenarios and look-alikes were planted, so it says nothing about alert volumes in a "
    "bank. A pattern match is not evidence of wrongdoing."
)


@dataclass(frozen=True, slots=True)
class ReportMeta:
    title: str
    split: str  # "dev" or "test"
    seeds: tuple[int, ...]
    engine: str  # "neo4j" or "memory"
    generated_at: str
    profile: str
    generator_version: str
    label_schema: str
    rules_version: str
    params_sha256: str
    detectors: Mapping[str, str]  # slug -> detector version


def _num(value: float) -> str:
    return f"{value:.2f}"


def fmt_rate(rate: Rate) -> str:
    if rate.value is None:
        return "n = 0"
    return f"{_num(rate.value)} ({rate.k}/{rate.n})"


def fmt_interval(interval: Interval | None) -> str:
    if interval is None:
        return ""
    return f"[{_num(interval[0])}, {_num(interval[1])}]"


def fmt_pair(k: int, n: int) -> str:
    return "n = 0" if n == 0 else f"{_num(k / n)} ({k}/{n})"


def high_medium(bands: Mapping[str, tuple[int, int]]) -> tuple[int, int]:
    k = bands["high"][0] + bands["medium"][0]
    n = bands["high"][1] + bands["medium"][1]
    return k, n


def markdown(
    figures: Sequence[Figures], bands: Mapping[str, Mapping[str, tuple[int, int]]], meta: ReportMeta
) -> str:
    seeds = ", ".join(str(s) for s in meta.seeds)
    lines = [
        f"# {meta.title}",
        "",
        f"Split: {meta.split}. Seeds: {seeds}. Profile: `{meta.profile}`. Engine: {meta.engine}. "
        f"Generated {meta.generated_at}.",
        f"Generator {meta.generator_version}, label schema {meta.label_schema}, matching rules "
        f"{meta.rules_version}, parameters `{meta.params_sha256[:12]}`.",
        "",
        "| Typology | Recall | 95% interval | Precision | 95% interval | Precision, high and "
        "medium | True / dup / look-alike / partial / other / background | Look-alikes alerted |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in figures:
        hk, hn = high_medium(bands[f.typology])
        kinds = (
            f"{f.true} / {f.duplicate} / {f.lookalike} / {f.partial} / {f.other} / {f.background}"
        )
        lines.append(
            f"| `{f.typology}` | {fmt_rate(f.recall)} | {fmt_interval(f.recall.headline)} | "
            f"{fmt_rate(f.precision)} | {fmt_interval(f.precision.headline)} | "
            f"{fmt_pair(hk, hn)} | {kinds} | {f.lookalikes_alerted}/{f.lookalikes} |"
        )
    m = macro(figures)
    mr, mp, mf = m["macro_recall"], m["macro_precision"], m["macro_f1"]
    lines += [
        "",
        f"Macro recall {_num(mr) if mr is not None else 'n = 0'}, macro precision "
        f"{_num(mp) if mp is not None else 'n = 0'} over {m['macro_precision_typologies']} "
        f"typologies with alerts, macro F1 {_num(mf) if mf is not None else 'n = 0'} (the mean "
        f"of per-typology F1) over {m['typologies']} typologies.",
        "",
        READING_NOTES,
        "",
        LIMITATIONS,
        "",
    ]
    return "\n".join(lines)


def to_json(
    figures: Sequence[Figures], bands: Mapping[str, Mapping[str, tuple[int, int]]], meta: ReportMeta
) -> dict[str, Any]:
    return {
        "meta": {**asdict(meta), "seeds": list(meta.seeds), "detectors": dict(meta.detectors)},
        "typologies": {
            f.typology: {
                **{k: v for k, v in asdict(f).items() if k not in ("recall", "precision")},
                "recall": asdict(f.recall),
                "precision": asdict(f.precision),
                "bands": {b: list(v) for b, v in bands[f.typology].items()},
            }
            for f in figures
        },
        "macro": macro(figures),
    }
```

### `cli/src/neonradar_cli/evaluate.py`

Verbatim. Python, 229 lines. SHA-256 `37c0906a688d3472d4bd029c2ed1b6a9b588fc36289e529e661c72b5294aa1d4`.

```python
"""The evaluation run behind `neonradar eval run` and `neonradar eval check` (PHASE-3.md 7.6.1).

For each seed: a world, its overlay, the label files written and read back, a Source over base
plus overlay, the catalog's detectors with the profile's parameters, and the matcher. The Source
comes from `source_factory`: in memory (`memory_source`, the oracle) by default, or the Neo4j
factory of the CLI, which writes the records, loads them and returns a `Neo4jSource`. Names never
change a structural draw (7.2.1), so the counts depend only on the code, the seed and the settings.

A holdout seed runs only with `allow_holdout=True`, which the CLI passes after its own checks (a
terminal, not CI, the freeze, M3.6 and M3.11): `run_seed` refuses the split `test`, and any seed
that `eval/seeds.yaml` lists under `test.seeds` whatever the split, so a caller that bypasses the
CLI cannot generate a holdout world by accident (G11).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from neonradar_detect import catalog as catalog_mod
from neonradar_detect import runner
from neonradar_detect.catalog import Typology
from neonradar_detect.evaluation import harness, metrics
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource
from neonradar_detect.source import Source, Window
from neonradar_ingest.synth import labels, overlay, world, writer
from neonradar_ingest.synth.background import BackgroundConfig
from neonradar_ingest.synth.ctx import NameSource

Record = dict[str, Any]
SourceFactory = Callable[[list[Record]], Source]


@dataclass(frozen=True, slots=True)
class EvalSettings:
    """What a synthetic evaluation profile fixes (`ingest/profiles/synth-eval.yaml`, 7.11)."""

    profile: str
    world: world.WorldConfig
    start: date
    end: date
    illicit: int
    lookalikes: int
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    typologies: tuple[str, ...] = tuple(overlay.SCENARIOS)
    overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    created_at: datetime = datetime(2026, 11, 2, tzinfo=UTC)

    @property
    def window(self) -> Window:
        return Window(
            datetime.combine(self.start, datetime.min.time(), UTC),
            datetime.combine(self.end, datetime.min.time(), UTC),
        )


@dataclass(slots=True)
class SeedRun:
    seed: int
    result: harness.WorldResult
    summary: dict[str, Any]
    record_sha256: str
    counts: dict[str, int]
    seconds: dict[str, float]
    alert_ids: tuple[str, ...] = ()
    alerts: tuple[dict[str, Any], ...] = ()


def memory_source(records: list[Record]) -> Source:
    return MemSource(from_records(records))


def overlay_config(settings: EvalSettings, seed: int, split: str) -> overlay.OverlayConfig:
    return overlay.OverlayConfig(
        seed,
        start=settings.start,
        end=settings.end,
        split=split,
        illicit=settings.illicit,
        lookalikes=settings.lookalikes,
        typologies=settings.typologies,
        background=settings.background,
    )


def detector_params(
    cat: Mapping[str, Typology], overrides: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        slug: catalog_mod.params_for(cat[slug], module, overrides.get(slug))
        for slug, module in runner.detectors(cat).items()
    }


def run_id(settings: EvalSettings, split: str, seed: int) -> str:
    """A C4 run id (`run-<UTC yyyymmddThhmmss>-<4 hex>`) fixed by the settings and the seed."""
    tag = hashlib.sha256(f"{settings.profile}|{split}|{seed}".encode()).hexdigest()[:4]
    return f"run-{settings.created_at:%Y%m%dT%H%M%S}-{tag}"


SEEDS_FILE = Path("eval/seeds.yaml")


def holdout_seeds(path: Path = SEEDS_FILE) -> frozenset[int]:
    """The seeds `eval/seeds.yaml` lists under `test.seeds` (none until M3.11 draws them)."""
    if not path.exists():
        return frozenset()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(int(s) for s in (data.get("test") or {}).get("seeds") or [])


def run_seed(
    seed: int,
    settings: EvalSettings,
    names: NameSource,
    cat: Mapping[str, Typology],
    split: str,
    workdir: Path,
    source_factory: SourceFactory = memory_source,
    *,
    allow_holdout: bool = False,
    seeds_file: Path = SEEDS_FILE,
) -> SeedRun:
    if split not in ("dev", "test"):
        raise ValueError(f"unknown split {split}")
    if (split == "test" or seed in holdout_seeds(seeds_file)) and not allow_holdout:
        raise PermissionError("a holdout seed runs only through `eval run --split test` (G11)")
    t0 = time.perf_counter()
    base = world.generate(seed, settings.world, names)
    ov = overlay.generate(
        base, {"nr_synthetic": "synthetic"}, overlay_config(settings, seed, split), names
    )
    records = base + ov.records
    text = writer.record_lines(records)
    digest = labels.sha256(text)
    label_dir = workdir / f"seed-{seed}" / "labels"
    labels.write(
        label_dir,
        labels.files(
            ov.labels,
            seed=seed,
            record_sha256={"records": digest},
            generator_version=writer.GENERATOR_VERSION,
        ),
    )
    scenarios = harness.scenario_views(label_dir)
    t1 = time.perf_counter()
    source = source_factory(records)
    t2 = time.perf_counter()
    params = detector_params(cat, settings.overrides)
    detection = runner.run_detection(
        source,
        params,
        settings.window,
        cat,
        run_id=run_id(settings, split, seed),
        created_at=settings.created_at,
    )
    t3 = time.perf_counter()
    payments = frozenset(ov.payments)
    result = harness.evaluate_world(
        seed, detection.alerts, scenarios, payments, list(runner.detectors(cat))
    )
    return SeedRun(
        seed,
        result,
        detection.summary,
        digest,
        {"records": len(records), "payments": len(payments), "alerts": len(detection.alerts)},
        {
            "generate": round(t1 - t0, 1),
            "graph": round(t2 - t1, 1),
            "detect": round(t3 - t2, 1),
        },
        tuple(a["alert_id"] for a in detection.alerts),
        tuple(detection.alerts),
    )


def figures(
    runs: Sequence[SeedRun], typologies: Sequence[str]
) -> tuple[list[metrics.Figures], dict[str, dict[str, tuple[int, int]]]]:
    per_seed = {r.seed: r.result.outcomes for r in runs}
    results = [r.result for r in runs]
    return (
        [metrics.figures(per_seed, slug) for slug in typologies],
        {slug: harness.pooled_bands(results, slug) for slug in typologies},
    )


def baseline(run: SeedRun) -> dict[str, Any]:
    """The CI baseline of one seed: exact counts per typology (`eval/baselines/ci.json`)."""
    return {
        "seed": run.seed,
        "rules_version": "1",
        "typologies": {
            slug: harness.counts(outcome) for slug, outcome in sorted(run.result.outcomes.items())
        },
    }


def compare(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(differences, pending). A difference is a count of a typology that ran which its baseline
    row does not have, or a typology that ran without a row (so a new detector lands with its
    row); `pending` lists the baseline rows whose typology has no detector yet (M3.5)."""
    out = []
    if actual.get("seed") != expected.get("seed"):
        out.append(f"seed {actual.get('seed')} != {expected.get('seed')}")
    got, want = actual["typologies"], expected["typologies"]
    for slug in sorted(got):
        if slug not in want:
            out.append(f"{slug}: no baseline row")
            continue
        for key in sorted(set(want[slug]) | set(got[slug])):
            if got[slug].get(key) != want[slug].get(key):
                out.append(f"{slug}.{key}: {got[slug].get(key)} != {want[slug].get(key)}")
    return out, sorted(set(want) - set(got))


def small(settings: EvalSettings, **world_changes: Any) -> EvalSettings:
    """The same settings with a smaller world (tests)."""
    return replace(settings, world=replace(settings.world, **world_changes))
```

### `detect/tests/test_evaluation_match.py`

Verbatim. Python, 151 lines. SHA-256 `6b24744edd56f8432533eb9011ffda32c9410eb0fc9e6e8062d99b45dccc1736`.

```python
import pytest
from neonradar_detect.evaluation.match import AlertView, ScenarioView, evaluate, iou
from neonradar_detect.evaluation.metrics import figures, macro, rate, t_interval
from neonradar_detect.evaluation.stats import wilson_interval


def _a(aid, typ, edges=(), nodes=(), subjects=None):
    return AlertView(aid, typ, frozenset(edges), frozenset(nodes), subjects or {})


def _s(sid, typ, tx=(), parts=None, look=False):
    return ScenarioView(sid, typ, look, frozenset(tx), parts or {})


def test_wilson_and_t():
    assert [round(x, 4) for x in wilson_interval(180, 200)] == [0.8506, 0.9343]
    lo, hi = wilson_interval(92, 100)
    assert (round(lo, 3), round(hi, 3)) == (0.850, 0.959)
    t = t_interval([1.0, 0.9, 1.0, 0.8, 0.9, 1.0, 0.9, 0.9, 1.0, 0.8])
    assert (round(t[0], 3), round(t[1], 3)) == (0.864, 0.976)
    r = rate(
        [
            (10, 10),
            (9, 10),
            (10, 10),
            (8, 10),
            (9, 10),
            (10, 10),
            (9, 10),
            (9, 10),
            (10, 10),
            (8, 10),
        ]
    )
    assert r.k == 92 and r.headline == r.across_seeds  # the t interval is wider here
    assert rate([(0, 0)]).value is None and rate([(0, 0)]).headline is None


def test_payment_matching_counts_every_kind():
    pay = frozenset({f"p{i}" for i in range(40)})
    scenarios = [
        _s("s1", "circular_flow", ["p0", "p1", "p2", "p3"]),
        _s("s2", "circular_flow", ["p10", "p11", "p12"]),
        _s("s3", "circular_flow", ["p20", "p21"], look=True),
        _s("s4", "circular_flow", ["p30", "p31", "p32", "p33"]),
    ]
    alerts = [
        _a(
            "a1", "circular_flow", ["p0", "p1", "p2", "p3", "acct-x"]
        ),  # exact on s1 (non-PAID ids ignored)
        _a("a2", "circular_flow", ["p0", "p1", "p2"]),  # also s1: duplicate
        _a("a3", "circular_flow", ["p20", "p21"]),  # look-alike
        _a("a4", "circular_flow", ["p38", "p39"]),  # background
        _a("a5", "circular_flow", ["p30"]),  # IoU 0.25 with s4: not a match, partial
        _a("a6", "circular_flow", ["p35", "p36"]),  # a layering chain's payments: other
        _a("b1", "layering_chain", ["p10", "p11", "p12"]),  # other typology: ignored here
    ]
    scenarios.append(_s("t1", "layering_chain", ["p35", "p36", "p37"]))
    out = evaluate("circular_flow", alerts, scenarios, pay)
    assert (
        out.alerts,
        out.true,
        out.duplicate,
        out.lookalike,
        out.partial,
        out.other,
        out.background,
    ) == (6, 1, 1, 1, 1, 1, 1)
    assert (out.planted, out.detected, out.lookalikes, out.lookalikes_alerted) == (3, 1, 1, 1)
    assert out.kinds == {
        "a1": "true",
        "a2": "duplicate",
        "a3": "lookalike",
        "a4": "background",
        "a5": "partial",
        "a6": "other",
    }
    assert (out.labelled_payments, out.covered_payments) == (11, 4)
    assert iou({"a"}, {"a", "b"}) == 0.5


def test_best_overlap_wins_and_ties_break_by_id():
    pay = frozenset({"p1", "p2", "p3", "p4"})
    scenarios = [_s("s1", "structuring", ["p1", "p2", "p3", "p4"])]
    alerts = [
        _a("a2", "structuring", ["p1", "p2", "p3", "p4"]),
        _a("a1", "structuring", ["p1", "p2", "p3", "p4"]),
    ]
    out = evaluate("structuring", alerts, scenarios, pay)
    assert out.matches == {"a1": "s1"} and out.kinds["a2"] == "duplicate"


def test_chain_exposure_and_hub_kinds():
    chain = _s(
        "c1",
        "shell_chain",
        parts={"co1": "owned_company", "co2": "layer", "co3": "layer", "p1": "top_owner"},
    )
    out = evaluate(
        "shell_chain", [_a("x", "shell_chain", nodes=["co1", "co2", "co3"])], [chain], frozenset()
    )
    assert out.true == 1  # IoU 3/4
    exp = _s("e1", "sanctions_exposure", parts={"t": "exposed_entity", "s": "listed_owner"})
    ok = _a("y", "sanctions_exposure", nodes=["t", "s", "m"], subjects={"t": "exposed_entity"})
    miss = _a("z", "sanctions_exposure", nodes=["t", "m"], subjects={"t": "exposed_entity"})
    assert evaluate("sanctions_exposure", [ok], [exp], frozenset()).true == 1
    assert evaluate("sanctions_exposure", [miss], [exp], frozenset()).background == 1
    chain_exp = ScenarioView(
        "e2",
        "sanctions_exposure",
        False,
        frozenset(),
        {"t": "exposed_entity", "mid": "exposed_entity", "s": "listed_owner"},
        frozenset({"t", "s"}),
    )
    two = [
        _a("y1", "sanctions_exposure", nodes=["t", "s", "mid"], subjects={"t": "exposed_entity"}),
        _a("y2", "sanctions_exposure", nodes=["mid", "s"], subjects={"mid": "exposed_entity"}),
    ]
    out = evaluate("sanctions_exposure", two, [chain_exp], frozenset())
    assert (out.true, out.duplicate, out.detected) == (
        2,
        0,
        1,
    )  # each exposed organisation is a unit
    only_mid = evaluate("sanctions_exposure", two[1:], [chain_exp], frozenset())
    assert (only_mid.true, only_mid.detected) == (1, 0)  # the core unit was missed
    hub = _s("h1", "mass_registration_address", parts={"addr": "registered_address"})
    out = evaluate(
        "mass_registration_address",
        [_a("w", "mass_registration_address", subjects={"addr": "registered_address"})],
        [hub],
        frozenset(),
    )
    assert out.true == 1 and out.detected == 1


def test_figures_and_macro():
    from neonradar_detect.evaluation.match import Outcome

    per_seed = {
        1: {"structuring": Outcome("structuring", alerts=12, true=9, planted=10, detected=9)},
        2: {"structuring": Outcome("structuring", alerts=0, true=0, planted=10, detected=0)},
    }
    f = figures(per_seed, "structuring")
    assert f.recall.k == 9 and f.recall.n == 20 and f.precision.seeds_counted == 1
    assert f.seed_recall == (0.0, 0.45, 0.9)
    m = macro([f])
    assert m["macro_recall"] == pytest.approx(0.45) and m["macro_f1"] == pytest.approx(
        2 * 0.45 * 0.75 / 1.2
    )
```

### `detect/tests/test_evaluation_harness.py`

Verbatim. Python, 125 lines. SHA-256 `8f2d44080ad51f4f6e20e8acc0d9d2e89df934f2b83eaee41dfb1145062ec8d6`.

```python
from pathlib import Path

import pytest
from neonradar_detect.evaluation import harness, metrics, report

HEAD = "# synthetic: true\n# label_schema: 2.0.0\n"
SCENARIOS = (
    "scenario_id,typology,variant,is_lookalike,start_ts,end_ts,participants,difficulty,split,"
    "n_transactions,n_accounts,n_entities,n_relationships\n"
    "scn-000001,circular_flow,same_account,false,,,,easy,dev,3,3,3,0\n"
    "scn-000002,circular_flow,refund,true,,,,,dev,2,2,2,0\n"
)
TRANSACTIONS = (
    "tx_id,scenario_id,typology,step,role,is_illicit,variant,is_lookalike,is_core\n"
    "p1,scn-000001,circular_flow,1,hop,true,same_account,false,true\n"
    "p2,scn-000001,circular_flow,2,hop,true,same_account,false,true\n"
    "p3,scn-000001,circular_flow,3,hop,true,same_account,false,true\n"
    "r1,scn-000002,circular_flow,1,payment,false,refund,true,true\n"
    "r2,scn-000002,circular_flow,2,refund,false,refund,true,true\n"
)
PARTICIPANTS = (
    "scenario_id,object_kind,object_id,role,is_core\n"
    "scn-000001,account,a1,origin,true\n"
    "scn-000002,account,b1,origin,true\n"
)


def _labels(tmp_path: Path, schema: str = "2.0.0") -> Path:
    head = HEAD.replace("2.0.0", schema)
    for name, body in (
        ("scenarios", SCENARIOS),
        ("transactions", TRANSACTIONS),
        ("participants", PARTICIPANTS),
    ):
        (tmp_path / f"{name}.csv").write_text(head + body, encoding="utf-8")
    return tmp_path


def _alert(aid: str, edges: list[str], priority: str = "high") -> dict:
    return {
        "alert_id": aid,
        "typology": "circular_flow",
        "priority": priority,
        "evidence": {"edge_ids": edges, "node_ids": ["a1"]},
        "subjects": [{"entity_id": "a1", "role": "origin"}],
    }


def test_scenario_views_read_labels_v2(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    assert [v.scenario_id for v in views] == ["scn-000001", "scn-000002"]
    assert views[0].tx_ids == {"p1", "p2", "p3"} and views[0].core == {"a1"}
    assert views[1].is_lookalike and views[1].participants == {"b1": "origin"}


def test_labels_of_another_major_schema_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="label schema"):
        harness.scenario_views(_labels(tmp_path, "3.0.0"))


def test_evaluate_world_counts_kinds_and_bands(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    payments = frozenset({"p1", "p2", "p3", "r1", "r2", "x1", "x2"})
    alerts = [
        _alert("alr-a", ["p1", "p2", "p3"]),
        _alert("alr-b", ["p1", "p2", "p3", "x1"], "medium"),
        _alert("alr-c", ["r1", "r2"], "low"),
        _alert("alr-d", ["x1", "x2"], "low"),
    ]
    result = harness.evaluate_world(1, alerts, views, payments, ["circular_flow"])
    outcome = result.outcomes["circular_flow"]
    assert harness.counts(outcome) == {
        "alerts": 4,
        "true": 1,
        "duplicate": 1,
        "lookalike": 1,
        "partial": 0,
        "other": 0,
        "background": 1,
        "planted": 1,
        "detected": 1,
        "lookalikes": 1,
        "lookalikes_alerted": 1,
    }
    assert result.bands["circular_flow"] == {"high": (1, 1), "medium": (0, 1), "low": (0, 2)}
    pooled = harness.pooled_bands([result, result], "circular_flow")
    assert pooled["high"] == (2, 2) and pooled["low"] == (0, 4)


def test_report_renders_rates_intervals_and_fixed_text(tmp_path: Path) -> None:
    views = harness.scenario_views(_labels(tmp_path))
    payments = frozenset({"p1", "p2", "p3", "r1", "r2"})
    results = [
        harness.evaluate_world(
            seed, [_alert("alr-a", ["p1", "p2", "p3"])], views, payments, ["circular_flow"]
        )
        for seed in (1, 2)
    ]
    figures = [metrics.figures({r.seed: r.outcomes for r in results}, "circular_flow")]
    bands = {"circular_flow": harness.pooled_bands(results, "circular_flow")}
    meta = report.ReportMeta(
        "Detection evaluation (development)",
        "dev",
        (1, 2),
        "memory",
        "2026-11-02T09:00:00Z",
        "synth-eval",
        "1.0.0",
        "2.0.0",
        "1",
        "0" * 64,
        {"circular_flow": "0.2.0"},
    )
    text = report.markdown(figures, bands, meta)
    assert "| `circular_flow` | 1.00 (2/2) | [0.34, 1.00] | 1.00 (2/2) | [0.34, 1.00] |" in text
    assert "1.00 (2/2) | 2 / 0 / 0 / 0 / 0 / 0 | 0/2 |" in text
    assert report.READING_NOTES in text and report.LIMITATIONS in text
    data = report.to_json(figures, bands, meta)
    assert data["typologies"]["circular_flow"]["recall"]["k"] == 2
    assert data["typologies"]["circular_flow"]["bands"]["high"] == [2, 2]


def test_an_empty_rate_prints_n_zero() -> None:
    empty = metrics.rate([(0, 0), (0, 0)])
    assert report.fmt_rate(empty) == "n = 0" and report.fmt_interval(empty.headline) == ""
```

### `detect/tests/test_world_parity.py`

Verbatim. Python, 34 lines. SHA-256 `2b86f973d2ceab6733f98b295b2fe81bd20236a382860cab163a52f42b4af4c4`.

```python
"""The two Sources give the same detection results on a generated world (PHASE-3.md 7.1.5)."""

from datetime import date
from pathlib import Path

import pytest
from neonradar_cli import evaluate
from neonradar_detect import catalog
from neonradar_ingest.synth import world
from neonradar_ingest.synth.namesource import default_names

pytestmark = pytest.mark.integration

SETTINGS = evaluate.EvalSettings(
    "synth-eval",
    world.WorldConfig(companies=80, people=120, agent_every=40, professional_every=40),
    date(2025, 1, 1),
    date(2026, 7, 1),
    illicit=1,
    lookalikes=1,
    overrides={"mass_registration_address": {"top_share": 0.0}},
)


def test_alerts_and_counts_are_identical(tmp_path: Path, neo4j_source_factory) -> None:  # type: ignore[no-untyped-def]
    cat = catalog.load()
    mem = evaluate.run_seed(5, SETTINGS, default_names(), cat, "dev", tmp_path / "m")
    neo = evaluate.run_seed(
        5, SETTINGS, default_names(), cat, "dev", tmp_path / "n", neo4j_source_factory
    )
    assert neo.record_sha256 == mem.record_sha256
    assert neo.alert_ids == mem.alert_ids and mem.alert_ids
    assert neo.summary["typologies"] == mem.summary["typologies"]
    assert evaluate.baseline(neo) == evaluate.baseline(mem)
```

### `cli/tests/test_eval_run.py`

Verbatim. Python, 65 lines. SHA-256 `af863b26cdbadb83077ba31772f6d3fe6f91215f69e5da8361426ea552290599`.

```python
import re
from datetime import date
from pathlib import Path

import pytest
from neonradar_cli import evaluate
from neonradar_detect import catalog, runner
from neonradar_ingest.synth import world
from neonradar_ingest.synth.namesource import default_names

SETTINGS = evaluate.EvalSettings(
    "synth-eval",
    world.WorldConfig(companies=60, people=90, agent_every=30, professional_every=30),
    date(2025, 1, 1),
    date(2026, 7, 1),
    illicit=1,
    lookalikes=1,
    overrides={"mass_registration_address": {"top_share": 0.0}},
)


def test_a_seed_run_is_deterministic_and_complete(tmp_path: Path) -> None:
    cat = catalog.load()
    a = evaluate.run_seed(3, SETTINGS, default_names(), cat, "dev", tmp_path / "a")
    b = evaluate.run_seed(3, SETTINGS, default_names(), cat, "dev", tmp_path / "b")
    assert a.record_sha256 == b.record_sha256
    assert evaluate.baseline(a) == evaluate.baseline(b)
    assert [x["alert_id"] for x in a.alerts] == list(a.alert_ids)
    assert re.fullmatch(r"run-\d{8}T\d{6}-[0-9a-f]{4}", a.alerts[0]["run_id"])
    slugs = list(runner.detectors(cat))
    assert list(a.result.outcomes) == slugs
    assert all(o.planted == 1 and o.lookalikes == 1 for o in a.result.outcomes.values())
    assert (tmp_path / "a" / "seed-3" / "labels" / "manifest.json").exists()
    figures, bands = evaluate.figures([a], slugs)
    assert [f.typology for f in figures] == slugs and set(bands) == set(slugs)


def test_holdout_seeds_need_the_cli(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="G11"):
        evaluate.run_seed(3, SETTINGS, default_names(), catalog.load(), "test", tmp_path)
    seeds = tmp_path / "seeds.yaml"  # once M3.11 has drawn them, the split no longer matters
    seeds.write_text("test:\n  seeds: [3]\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="G11"):
        evaluate.run_seed(
            3, SETTINGS, default_names(), catalog.load(), "dev", tmp_path, seeds_file=seeds
        )
    assert not (tmp_path / "seed-3").exists()


def test_compare_reports_every_difference(tmp_path: Path) -> None:
    run = evaluate.run_seed(4, SETTINGS, default_names(), catalog.load(), "dev", tmp_path)
    base = evaluate.baseline(run)
    assert evaluate.compare(base, base) == ([], [])
    slug = sorted(base["typologies"])[0]  # whichever detectors have merged
    changed = {**base, "typologies": {**base["typologies"]}}
    changed["typologies"][slug] = {**base["typologies"][slug], "true": -1}
    assert evaluate.compare(base, changed) == (
        [f"{slug}.true: {base['typologies'][slug]['true']} != -1"],
        [],
    )
    first = sorted(base["typologies"])[0]
    missing = {**base, "typologies": dict(list(base["typologies"].items())[1:])}
    assert evaluate.compare(base, missing) == ([f"{first}: no baseline row"], [])
    fewer = {**base, "typologies": dict(list(base["typologies"].items())[1:])}
    assert evaluate.compare(fewer, base) == ([], [first])
```

### `eval/seeds.yaml`

Verbatim. YAML, 12 lines. SHA-256 `7178c29d195c13f7bf6019487f6c165e1ea6a3fa6bacd7d472b82679063f4e4a`.

```yaml
# eval/seeds.yaml: the seeds of the detection evaluation (PHASE-3.md 7.6.1)
version: 1
profile: synth-eval
dev:
  seeds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]   # development: tuning and development figures, anyone may run them
ci:
  seed: 1                                  # the CI gate, with eval/baselines/ci.json
test:
  seeds: []                                # the holdout: ten seeds drawn by the tech lead after the freeze (M3.11)
  drawn_by: null
  drawn_at: null
  freeze: eval/freeze.json
```

### `eval/baselines/ci.json`

Verbatim. JSON, 188 lines. SHA-256 `f0cf2486a9fed789a0ec2a59fd4b979231ed65d908af7ac6e99df8d2866ff31b`.

```json
{
  "rules_version": "1",
  "seed": 1,
  "typologies": {
    "cash_commingling": {
      "alerts": 12,
      "background": 2,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 0,
      "lookalikes": 10,
      "lookalikes_alerted": 0,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 10
    },
    "circular_flow": {
      "alerts": 10,
      "background": 0,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 0,
      "lookalikes": 10,
      "lookalikes_alerted": 0,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 10
    },
    "dormant_reactivation": {
      "alerts": 18,
      "background": 4,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 3,
      "lookalikes": 10,
      "lookalikes_alerted": 3,
      "other": 1,
      "partial": 0,
      "planted": 10,
      "true": 10
    },
    "fan_in_collection": {
      "alerts": 19,
      "background": 0,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 4,
      "lookalikes": 10,
      "lookalikes_alerted": 4,
      "other": 3,
      "partial": 2,
      "planted": 10,
      "true": 10
    },
    "fan_out_distribution": {
      "alerts": 9,
      "background": 0,
      "detected": 9,
      "duplicate": 0,
      "lookalike": 0,
      "lookalikes": 10,
      "lookalikes_alerted": 0,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 9
    },
    "formation_agent_cluster": {
      "alerts": 13,
      "background": 0,
      "detected": 8,
      "duplicate": 0,
      "lookalike": 5,
      "lookalikes": 10,
      "lookalikes_alerted": 5,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 8
    },
    "layering_chain": {
      "alerts": 28,
      "background": 0,
      "detected": 8,
      "duplicate": 0,
      "lookalike": 6,
      "lookalikes": 10,
      "lookalikes_alerted": 6,
      "other": 14,
      "partial": 0,
      "planted": 10,
      "true": 8
    },
    "mass_registration_address": {
      "alerts": 23,
      "background": 3,
      "detected": 7,
      "duplicate": 0,
      "lookalike": 9,
      "lookalikes": 10,
      "lookalikes_alerted": 9,
      "other": 4,
      "partial": 0,
      "planted": 10,
      "true": 7
    },
    "pep_exposure": {
      "alerts": 25,
      "background": 0,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 0,
      "lookalikes": 10,
      "lookalikes_alerted": 0,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 25
    },
    "rapid_pass_through": {
      "alerts": 20,
      "background": 5,
      "detected": 8,
      "duplicate": 0,
      "lookalike": 3,
      "lookalikes": 10,
      "lookalikes_alerted": 3,
      "other": 4,
      "partial": 0,
      "planted": 10,
      "true": 8
    },
    "recycled_directors": {
      "alerts": 55,
      "background": 3,
      "detected": 9,
      "duplicate": 0,
      "lookalike": 5,
      "lookalikes": 10,
      "lookalikes_alerted": 5,
      "other": 38,
      "partial": 0,
      "planted": 10,
      "true": 9
    },
    "sanctions_exposure": {
      "alerts": 22,
      "background": 0,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 5,
      "lookalikes": 10,
      "lookalikes_alerted": 5,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 17
    },
    "shell_chain": {
      "alerts": 19,
      "background": 5,
      "detected": 9,
      "duplicate": 0,
      "lookalike": 5,
      "lookalikes": 10,
      "lookalikes_alerted": 5,
      "other": 0,
      "partial": 0,
      "planted": 10,
      "true": 9
    },
    "structuring": {
      "alerts": 15,
      "background": 0,
      "detected": 10,
      "duplicate": 0,
      "lookalike": 3,
      "lookalikes": 10,
      "lookalikes_alerted": 3,
      "other": 2,
      "partial": 0,
      "planted": 10,
      "true": 10
    }
  }
}
```

## M3.10 Documentation, ADRs and the Assignment 4 kit

The Assignment 4 brief for the interns. 1 verbatim file (PHASE-3.md M3.10).

### `docs/team/assignment-4.md`

Verbatim. Markdown, 71 lines. SHA-256 `cdc8bca699d8ce54afddac84f68599f58ea8443fd17eb608bd63a5ba5763aa63`.

````markdown
# Assignment 4: one test case, written by you

Due Friday 6 November 2026. Presented at the teach-back on Thursday 12 November 2026.

In Assignment 2 you checked the explainer of one typology against its sources. Now you write one
more test case for that typology's detector, by hand, and explain why its expected answer is
right. The typology researchers approved the existing tests before the detectors were written;
yours is the first test that someone writes after seeing the detector run.

## What to do

1. Read your typology's section of `docs/build/PHASE-3.md` (7.3), its explainer in
   `docs/typologies/`, its detector in `detect/src/neonradar_detect/detectors/<slug>.py` and its
   tests in `detect/tests/test_detector_<slug>.py` (`formation_agent_cluster`,
   `recycled_directors` and `pep_exposure` share `detect/tests/test_detector_extended_registry.py`).
   You do not change that file: your case goes in a file of its own (step 3).
2. Find a case the tests do not cover: a value just inside or just outside a threshold, a
   look-alike the generator does not plant, or a combination the definition says nothing about.
   Before you run anything, write down whether the detector should find it and why, citing the
   definition (PHASE-3.md 7.3) or a key from `docs/sources/bibliography.yaml`.
3. Build the case with the test kit (`detect/tests/kit.py`) in a new file
   `detect/tests/test_a4_<slug>_<handle>.py`, where `<handle>` is your GitHub handle without the
   `@`. Use the template below: one test function, at most 40 lines, synthetic records only.
4. Run it in memory and on Neo4j:
   `uv run pytest detect/tests/test_a4_<slug>_<handle>.py -q` and
   `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_a4_<slug>_<handle>.py -q`.
5. If the detector disagrees with your expected answer, do not change your answer to make the
   test pass. Keep the test, mark it `@pytest.mark.xfail(strict=True, reason="...")`, and explain
   in the pull request why you think the detector, the definition or your case is wrong. The
   typology researcher decides before the detection freeze on Monday 9 November.
6. Open a pull request labelled `assignment-4` and `typology`, with your reasoning in its
   description, and ask the typology researcher for a review.

## Rules

- You may use AI help to understand the code, but you write the case and its reasoning
  yourself, and you must be able to explain every line. Claude Code does not write, complete or
  fix Assignment 4 cases.
- Synthetic records only. A record that must look real is built in the test with a test id and a
  test name (`gbch-co-T0000009`, "Test Holder Ltd"), as PHASE-3.md 2.9 describes.
- Change no other test and no detector in this pull request.

## Template

```python
"""Assignment 4: <one line on what this case checks>.

Expected: <found or not found>, because <the definition or the source, with its key>.
"""

from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import <slug> as det
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def test_<what_it_checks>() -> None:
    k = Kit()
    # build the case: companies, people, accounts, payments, ownership, addresses
    findings = det.run(source_of(k.records), det.Params(), WINDOW).findings
    assert ...
```

## At the teach-back (five minutes)

Draw the case as a picture of three to six nodes. Say what you expected and why, and what the
detector did. If they disagreed, say who you think is right, and what the typology researcher
decided.
````
