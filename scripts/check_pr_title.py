#!/usr/bin/env python3
"""Check that a pull request title follows Conventional Commits (docs/build/PHASE-1.md 2.3).

    python3 scripts/check_pr_title.py "ci(ci): add the CI workflows [M1.6]"

Exits 0 when the title matches, 1 otherwise. Standard library only.
"""

import argparse
import re
import sys

TITLE_PATTERN = re.compile(r"^(feat|fix|docs|test|refactor|build|ci|chore)(\([a-z0-9-]+\))?!?: .+$")


def title_ok(title: str) -> bool:
    return TITLE_PATTERN.fullmatch(title) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that a pull request title is 'type(scope): summary' "
        "(Conventional Commits, PHASE-1.md 2.3)."
    )
    parser.add_argument("title", help="the pull request title")
    args = parser.parse_args(argv)
    if title_ok(args.title):
        print(f"check_pr_title: OK: {args.title}")
        return 0
    print(
        f"check_pr_title: FAIL: {args.title!r} is not 'type(scope): summary'. Types: feat, fix, "
        "docs, test, refactor, build, ci, chore; the scope is optional and lower case. "
        "Example: 'ci(ci): add the CI workflows [M1.6]'."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
