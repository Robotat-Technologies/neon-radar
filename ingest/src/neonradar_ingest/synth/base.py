"""The base an overlay attaches to (PHASE-3.md 7.2.3, D3).

`BaseView.from_records` reads C1 entity records (a synthetic world, a fixture, or the records of a
real profile) and, when the profile was resolved, the resolution run's `canonical.csv`. It keeps:
every base id (so no scenario can use one), every name of a non-synthetic base record (no new name
may repeat one) and of a synthetic base record (new names avoid them where they can), the account
numbers already in use, and the eligible organisations. A merged entity counts once, through its
anchor record, and is eligible for an account only when every one of its records is a synthetic
or registry company record (`REGISTRY_ID_PREFIXES`; GLEIF only once records carry a category)
with no topic, a live status or none, and no dissolution date (G1; the M3.3 review). People are
never eligible: generated payments next to a person would be invented financial data about them.
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
# Statuses that may hold an account, an allowlist as in generator v0's join.
LIVE = frozenset({"active", "open", "registered"})
# G1 (orchestrator decision, M3.3): a registry record holds an account only as the registry's
# own company record, never a PSC, officer, relationship or other record of the same dataset.
REGISTRY_ID_PREFIXES = {"gb_companies_house": "gbch-co-", "gleif_lei": "gleif-lei-"}
# A GLEIF sole proprietor is a person; C1 records carry no EntityCategory yet (reconciliation C7).
CATEGORY_UNKNOWN = frozenset({"gleif_lei"})


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
            reason = _ineligible(by_id[anchor], [by_id.get(m) for m in members], dataset_kinds)
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
            groups.setdefault(row["canonical_id"], []).append(row["record_id"])
    out = {}
    clustered: set[str] = set()
    for canonical, members in groups.items():
        present = [m for m in members if m in by_id]  # members missing from the base stay listed
        if not present:
            continue
        anchor = (
            canonical[3:]
            if canonical.startswith("nr-") and canonical[3:] in present
            else min(present)
        )
        out[anchor] = sorted(members)
        clustered.update(present)
    for i in by_id:
        if i not in clustered:
            out[i] = [i]
    return out


def _ineligible(
    anchor: Mapping[str, Any], members: list[Mapping[str, Any] | None], kinds: Mapping[str, str]
) -> str:
    if anchor["schema"] not in ELIGIBLE_SCHEMAS:
        return "not_an_organisation"
    for m in members:
        if m is None:
            return "member_not_in_base"
        kind = kinds.get(m["datasets"][0], "")
        if kind in ("list", "leak"):
            return "list_or_leak_record"
        if kind not in ("registry", "synthetic"):
            return "unknown_dataset_kind"
        if m.get("properties", {}).get("topics"):  # any topic, not only flag topics (G1)
            return "flagged"
        prefix = REGISTRY_ID_PREFIXES.get(m["datasets"][0], "")
        if not str(m["id"]).startswith(prefix) or m["schema"] not in ELIGIBLE_SCHEMAS:
            return "not_a_registry_company"
        if m["datasets"][0] in CATEGORY_UNKNOWN:
            return "category_unknown"
        props = m.get("properties", {})
        if props.get("dissolutionDate"):
            return "dissolved"
        if any(status.strip().casefold() not in LIVE for status in props.get("status", [])):
            return "not_active"  # an allowlist: any other status fails closed
    return ""
