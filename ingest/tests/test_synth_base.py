"""Which base organisations may hold a synthetic account (G1; PHASE-3.md 7.2.4).

Orchestrator decision on the #74 data-guardian review, M3.3: a record with any topic never gets
an account, Companies House contributes only `gbch-co-` company records, GLEIF only `gleif-lei-`
Company or Organization records, and ICIJ, PublicBody, person, PSC and officer records never do.
Every id and name here is a test look-alike built at run time (PHASE-2.md 2.9).
"""

from pathlib import Path
from typing import Any

from neonradar_ingest.synth.base import BaseView

KINDS = {
    "gb_companies_house": "registry",
    "gleif_lei": "registry",
    "icij_offshore_leaks": "leak",
    "gb_fcdo_sanctions": "list",
    "nr_synthetic": "synthetic",
}


def record(rid: str, dataset: str, schema: str = "Company", **props: list[str]) -> dict[str, Any]:
    properties = {"name": [f"Test Company {rid[-3:]}"], **props}
    return {"id": rid, "schema": schema, "datasets": [dataset], "properties": properties}


def test_only_registry_company_records_without_topics_hold_accounts() -> None:
    records = [
        record("gbch-co-T0000301", "gb_companies_house"),
        record("gleif-lei-T0000302", "gleif_lei", "Organization"),
        record("syn-w-co-000303", "nr_synthetic"),
        record("gbch-co-T0000304", "gb_companies_house", topics=["corp.public"]),
        record("gbch-co-T0000305", "gb_companies_house", topics=["sanction"]),
        record("gleif-lei-T0000306", "gleif_lei", topics=["role.pep"]),
        record("gbch-psc-T0000307", "gb_companies_house"),
        record("gbch-off-T0000308", "gb_companies_house", "Person"),
        record("gleif-lei-T0000309", "gleif_lei", "LegalEntity"),
        record("gleif-goldencopy-T0000310", "gleif_lei"),
        record("icij-T0000311", "icij_offshore_leaks"),
        record("gbch-co-T0000312", "gb_companies_house", "PublicBody"),
        record("uksl-gT0000313", "gb_fcdo_sanctions"),
    ]
    view = BaseView.from_records(records, KINDS)
    assert [org.id for org in view.eligible] == [
        "gbch-co-T0000301", "gleif-lei-T0000302", "syn-w-co-000303",
    ]  # fmt: skip
    assert view.skipped == {
        "flagged": 3,
        "not_a_registry_company": 2,
        "not_an_organisation": 3,
        "list_or_leak_record": 2,
    }


def test_a_merged_entity_with_a_psc_record_gets_no_account(tmp_path: Path) -> None:
    """Resolution may merge a corporate PSC record into its company: no account then."""
    records = [
        record("gbch-co-T0000401", "gb_companies_house"),
        record("gbch-psc-T0000402", "gb_companies_house"),
        record("gbch-co-T0000403", "gb_companies_house"),
        record("gleif-lei-T0000404", "gleif_lei", topics=["fin"]),
    ]
    canonical = tmp_path / "canonical.csv"
    canonical.write_text(
        "record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,"
        "path_methods,features\n"
        "gbch-co-T0000401,nr-gbch-co-T0000401,org,2,anchor,,1.0,,,\n"
        "gbch-psc-T0000402,nr-gbch-co-T0000401,org,2,deterministic,,1.0,,,\n"
        "gbch-co-T0000403,nr-gbch-co-T0000403,org,2,anchor,,1.0,,,\n"
        "gleif-lei-T0000404,nr-gbch-co-T0000403,org,2,deterministic,,1.0,,,\n",
        encoding="utf-8",
    )
    view = BaseView.from_records(records, KINDS, canonical)
    assert view.eligible == []
    assert view.skipped == {"not_a_registry_company": 1, "flagged": 1}
