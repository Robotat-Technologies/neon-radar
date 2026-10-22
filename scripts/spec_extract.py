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
the SHA-256 of the repository's file, the milestone and the reason. Test files, the CI baseline
and the freeze file never deviate. `update` writes the repository's current file into its code
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
NEVER_DEVIATE = ("eval/baselines/", "eval/freeze.json")
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
