"""Flag topics, listed and leaked records (PHASE-2.md 7.1.1, M2.10a deliverable 3).

A record's flag topics are its topics that are not purely descriptive; a record is listed when
it has one. Every topic outside the descriptive set counts as a flag, including a topic
FollowTheMoney adds later, and a test fails when FollowTheMoney's vocabulary has a topic that
neither set names, so that a human classifies it (G8).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

DESCRIPTIVE_TOPICS = frozenset(
    {"corp.public", "fin", "gov", "pol.party", "pol.union", "rel", "mil"}
)
DESCRIPTIVE_PREFIXES = ("fin.", "gov.")
# The FollowTheMoney 4.11 topics that are flags (7.1.1), named so that the test notices new ones.
FLAG_TOPICS = frozenset(
    {
        "asset.frozen", "corp.clone", "corp.disqual", "corp.offshore", "corp.shell", "crime",
        "crime.boss", "crime.cyber", "crime.env", "crime.fin", "crime.fraud", "crime.terror",
        "crime.theft", "crime.traffick", "crime.traffick.drug", "crime.traffick.human",
        "crime.war", "debarment", "export.control", "export.control.linked", "export.risk",
        "forced.labor", "geo.risk", "invest.ban", "invest.risk", "mare.detained", "mare.shadow",
        "mare.sts", "poi", "reg.action", "reg.warn", "role.acct", "role.act", "role.civil",
        "role.diplo", "role.journo", "role.judge", "role.lawyer", "role.lobby", "role.oligarch",
        "role.pep", "role.pep.frmr", "role.pep.intl", "role.pep.natl", "role.pol", "role.rca",
        "role.spy", "sanction", "sanction.control", "sanction.counter", "sanction.linked",
        "wanted",
    }
)  # fmt: skip
SYNTHETIC_KINDS = frozenset({"list", "leak"})  # nr.synthetic_kind values that change the kind


def is_descriptive(topic: str) -> bool:
    return topic in DESCRIPTIVE_TOPICS or topic.startswith(DESCRIPTIVE_PREFIXES)


def flag_topics(topics: Iterable[str]) -> frozenset[str]:
    """The topics that are not purely descriptive (7.1.1)."""
    return frozenset(t for t in topics if not is_descriptive(t))


def is_listed(topics: Iterable[str]) -> bool:
    return bool(flag_topics(topics))


def record_kind(dataset_kind: str, nr: Mapping[str, object] | None) -> str:
    """The dataset's kind; a synthetic record whose `nr.synthetic_kind` is list or leak takes it."""
    synthetic_kind = (nr or {}).get("synthetic_kind")
    if dataset_kind == "synthetic" and synthetic_kind in SYNTHETIC_KINDS:
        return str(synthetic_kind)
    return dataset_kind


def is_leaked(kind: str) -> bool:
    return kind == "leak"
