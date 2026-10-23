"""Every Splink level label has investigator wording in 7.2 (PHASE-2.md M2.10c deliverable 4).

Reads the committed settings of M2.10b, so a new comparison level fails here until 7.2 and
`neonradar_graph.wording.LEVEL_WORDS` give it words.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neonradar_graph.wording import LEVEL_WORDS
from neonradar_resolve.models import level_labels

MODELS = Path(__file__).resolve().parents[1] / "models"


@pytest.mark.parametrize("kind", ["person", "org"])
def test_every_level_label_has_words(kind: str) -> None:
    settings = json.loads((MODELS / f"{kind}.settings.json").read_text(encoding="utf-8"))
    labels = level_labels(settings)
    assert labels, kind
    missing = [
        (comparison, label)
        for comparison, levels in sorted(labels.items())
        for label in levels.values()
        if (comparison, label) not in LEVEL_WORDS
    ]
    assert missing == []


def test_every_word_entry_belongs_to_a_model() -> None:
    known = set()
    for kind in ("person", "org"):
        settings = json.loads((MODELS / f"{kind}.settings.json").read_text(encoding="utf-8"))
        known |= {(c, label) for c, ls in level_labels(settings).items() for label in ls.values()}
    assert set(LEVEL_WORDS) == known
