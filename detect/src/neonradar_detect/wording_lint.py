"""The wording lint for alert text (PHASE-3.md 7.5.2): Phase 1's patterns, Phase 2's never-write
phrases and Phase 3's conduct words.

`violations` calls Phase 1's lint (`neonradar_contracts.wording.find_forbidden` over
`contracts/wording/forbidden-terms.txt`, PHASE-1.md 7.1) with the captions masked, and adds
`PHRASES` (PHASE-2.md 7.2 rule 6) and `CONDUCT` (G5) on the same normalised, masked text. It
returns pattern texts only, never the matched words, so an error can name the pattern without
repeating the alert text (M3.2 deliverable 4). Masking follows Phase 1: each caption is blanked
where it stands as a whole token (reconciliation W2: stricter than masking any substring).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from neonradar_contracts.wording import find_forbidden, forbidden_patterns, normalize

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


def masked_text(text: str, masked: Iterable[str]) -> str:
    """`text` normalised, with every masked value blanked where it is a whole token: the text
    Phase 1's `find_forbidden` checks."""
    text = normalize(text)
    for value in sorted({normalize(v) for v in masked if v}, key=len, reverse=True):
        token = re.compile(rf"(?<!\w){re.escape(value)}(?!\w)")
        text = token.sub(lambda found: " " * len(found.group(0)), text)
    return text


def violations(text: str, masked: tuple[str, ...] = ()) -> list[str]:
    """The patterns `text` matches once the given captions are masked out: Phase 1's (as
    `find_forbidden` reports them), then `PHRASES` and `CONDUCT`."""
    hits = find_forbidden(text, masked)
    found = [
        p.pattern for p in forbidden_patterns() if any(h.endswith(f" ({p.pattern})") for h in hits)
    ]
    if hits and not found:  # never pass a text Phase 1's lint refused
        found.append("contracts/wording/forbidden-terms.txt")
    clean = masked_text(text, masked)
    found += [p.pattern for p in (*PHRASES, *CONDUCT) if p.search(clean)]
    return found
