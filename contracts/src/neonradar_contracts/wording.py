"""Canonical wording (PHASE-1.md 7.1, guardrail G5): the disclaimers and the forbidden patterns.

The texts live in contracts/wording/. The disclaimers are verbatim from 7.1 and are served by
the API (`MetaResponse.disclaimers`); an alert names its disclaimer by id (`disclaimer_id`).
The forbidden patterns apply to NeonRadar's own entity-facing wording: typology wording
templates, rendered alert text and, from Phase 4, the copilot's answer templates. They do not
apply to the disclaimers or to documentation, which discuss money laundering as a subject.
scripts/check_wording.py reads the same file with the standard library only.
"""

import re
import unicodedata
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Literal, get_args

# The workspace installs members editable, so the folder sits next to this package's src/.
WORDING_DIR = Path(__file__).resolve().parents[2] / "wording"
FORBIDDEN_TERMS_FILE = WORDING_DIR / "forbidden-terms.txt"

# 7.1: "synthetic scenario" may appear only in an alert whose wording class is
# synthetic_scenario (every evidence node, subject and evidence-account holder is synthetic).
# Match it through `says_synthetic_scenario`, which normalises the text first.
SYNTHETIC_PHRASE = re.compile(r"\bsynthetic[\s_-]+scenario", re.IGNORECASE)

DisclaimerId = Literal["standing-v1", "synthetic-demo-v1", "real-data-v1"]
DISCLAIMER_IDS: tuple[DisclaimerId, ...] = get_args(DisclaimerId)


def load_disclaimer(disclaimer_id: DisclaimerId) -> str:
    """The disclaimer text, exactly as in 7.1 (the file's final newline removed)."""
    if disclaimer_id not in DISCLAIMER_IDS:
        raise ValueError(f"unknown disclaimer id {disclaimer_id!r}")
    return (WORDING_DIR / f"{disclaimer_id}.txt").read_text(encoding="utf-8").rstrip("\n")


def normalize(text: str) -> str:
    """NFKC without format characters (Unicode category Cf: soft hyphen, zero-width space, word
    joiner, direction marks), so fullwidth or mathematical letters and invisible characters
    cannot hide a term from the lint or the phrase check."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(char for char in text if unicodedata.category(char) != "Cf")


def says_synthetic_scenario(text: str) -> bool:
    """Whether `text` says "synthetic scenario" (`SYNTHETIC_PHRASE` on the normalised text)."""
    return SYNTHETIC_PHRASE.search(normalize(text)) is not None


def parse_patterns(text: str) -> tuple[re.Pattern[str], ...]:
    """One regular expression per line, case-insensitive; blank lines and `#` lines skipped."""
    lines = (line.strip() for line in text.splitlines())
    return tuple(re.compile(line, re.IGNORECASE) for line in lines if line and line[0] != "#")


@cache
def forbidden_patterns(path: Path = FORBIDDEN_TERMS_FILE) -> tuple[re.Pattern[str], ...]:
    """The patterns of contracts/wording/forbidden-terms.txt, compiled once per path."""
    return parse_patterns(path.read_text(encoding="utf-8"))


def find_forbidden(text: str, mask: Iterable[str] = ()) -> list[str]:
    """Every forbidden term in `text`, as `'<match>' (<pattern>)`; empty means the text passes.

    `mask` holds source values that are not NeonRadar's wording, such as entity captions and
    account numbers (7.1): each occurrence as a whole token (not inside a longer word) is
    blanked out before the check. The text and the mask are normalised first (`normalize`).
    """
    text = normalize(text)
    mask = {normalize(value) for value in mask if value}
    for value in sorted(mask, key=len, reverse=True):
        token = re.compile(rf"(?<!\w){re.escape(value)}(?!\w)")
        text = token.sub(lambda found: " " * len(found.group(0)), text)
    return [
        f"{match.group(0)!r} ({pattern.pattern})"
        for pattern in forbidden_patterns()
        for match in pattern.finditer(text)
    ]


def find_forbidden_in_name(name: str) -> list[str]:
    """The lint for snake_case identifiers shown to users (roles, slugs): `_` reads as a space."""
    return find_forbidden(name.replace("_", " "))
