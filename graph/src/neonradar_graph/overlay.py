"""Overlay loads: C2 1.2.0 loader rule L18 (PHASE-3.md M3.4).

`load_overlay` loads an overlay folder (`syn-ov-` records and `overlay.json`) onto its profile's
base and checks everything before it writes: the real-data instance only for a profile in the
`real_overlay_profiles` its caller passes after the gate (exit 3, folder unread); the record and
bridge checks (`plan_overlay`, exit 2, counts only); L17 on the default instance; every base
reference resolves (`overlay_unresolved.cypher`) to an `:Organization` without a topic
(`overlay_holders.cypher`, OD-10) (exit 1). Then `overlay_purge.cypher` and Phase 2's queries; a
holding takes the resolving query of L13, so it lands on a merged record's canonical node.
"""

import json
import re
import time
from collections import Counter
from collections.abc import Collection, Sequence
from itertools import batched
from pathlib import Path
from typing import Any

from followthemoney import model, registry
from neo4j import Driver, RoutingControl

from neonradar_contracts.graph import OVERLAY_DATASET, OVERLAY_ID_PREFIX
from neonradar_contracts.records import RecordIssue, validate_batch, validate_record
from neonradar_graph import cypher
from neonradar_graph.client import get_driver, wait_until_ready
from neonradar_graph.instances import Instance, InstanceRefused, check_records, for_database
from neonradar_graph.loader import (
    BATCH_SIZE,
    LoadError,
    LoadPlan,
    LoadReport,
    Record,
    execute_plan,
    read_input,
    require_migrated,
)
from neonradar_graph.mapping import to_node_rows, to_relationship_rows

OVERLAY_JSON = "overlay.json"
PARTIES = ("payer", "beneficiary")
MISSING = re.compile(r"points to '([^']+)', which is not in this load")  # C1 R4's message
CHECKS = (  # step 3: each query file counts the base references that fail it
    ("overlay_unresolved.cypher", "resolve to no node, directly or through a :SourceRecord"),
    ("overlay_holders.cypher", "resolve to a node that is not an :Organization without a topic"),
)


class OverlayRefused(LoadError):
    """L18 step 1 failed: nothing was read from or written to the graph (exit 2)."""

    exit_code = 2
    counts_only = True


class OverlayInstanceRefused(LoadError):
    """L18 step 2: the profile is not in `access.real_overlay_profiles` (exit 3)."""

    exit_code = 3
    counts_only = True


class OverlayUnresolved(LoadError):
    """L18 step 3: a base reference fails a check in the graph; nothing was written (exit 1)."""

    counts_only = True


def _base(value: str) -> bool:
    return not value.startswith(OVERLAY_ID_PREFIX)


def references(record: Record) -> list[tuple[str, str]]:
    """(property, id) for every value of a property that names an entity (FtM type `entity`)."""
    schema = model.get(record["schema"])
    props: dict[str, list[str]] = record["properties"]
    return [
        (name, value)
        for name, values in props.items()
        if schema is not None
        and (prop := schema.properties.get(name)) is not None
        and prop.type == registry.entity
        for value in values
    ]


def bridge_issues(records: Sequence[Record]) -> tuple[Counter[str], dict[str, set[str]]]:
    """The bridge check of L18 step 1 on records that pass C1, as counts by issue, and each
    account's base holders. Only an account holding (an Ownership with role `account holder`
    whose asset is a BankAccount of the overlay) may name a base entity, as its owner; a Payment
    may name one only as the payer or beneficiary that holds the account it names; and no
    Payment joins two accounts that base entities hold (I15, I16)."""
    accounts = {r["id"] for r in records if r["schema"] == "BankAccount"}
    holders: dict[str, set[str]] = {}
    found: Counter[str] = Counter()
    for record in records:
        props, schema = record["properties"], record["schema"]
        named = [(name, value) for name, value in references(record) if _base(value)]
        if schema == "Payment" and {name for name, _ in named} <= set(PARTIES):
            continue  # its parties are checked below, once every holding is known
        assets = props.get("asset", [])
        if (
            schema == "Ownership"
            and props.get("role") == ["account holder"]
            and {name for name, _ in named} == {"owner"}
            and len(assets) == 1
            and assets[0] in accounts
        ):
            holders.setdefault(assets[0], set()).update(value for _, value in named)
        elif named:
            found["a record other than an account holding or a payment names a base entity"] += 1
    for record in (r for r in records if r["schema"] == "Payment"):
        props = record["properties"]
        held = {
            p: {h for a in props.get(f"{p}Account", []) for h in holders.get(a, set())}
            for p in PARTIES
        }
        for party in PARTIES:
            if any(_base(v) and v not in held[party] for v in props.get(party, [])):
                found["a payment names a base entity that does not hold its account"] += 1
        if held["payer"] and held["beneficiary"]:
            found["a payment joins two accounts that base entities hold (I16)"] += 1
    return found, holders


def _refused(issues: Sequence[RecordIssue]) -> OverlayRefused:
    rules = sorted(Counter(issue.rule for issue in issues).items())
    detail = ", ".join(f"{rule}: {n}" for rule, n in rules)
    return OverlayRefused(f"{len(issues)} C1 issue(s) ({detail}); nothing was written")


def plan_overlay(
    records: Sequence[Record], meta: dict[str, Any], profile: str
) -> tuple[LoadPlan, list[str]]:
    """L18 step 1 without a database: the rows to write and the base ids the records name."""
    if meta.get("profile") != profile:
        raise OverlayRefused(f"{OVERLAY_JSON} does not name the profile {profile} (L18)")
    prefix = sum(not str(r.get("id", "")).startswith(OVERLAY_ID_PREFIX) for r in records)
    dataset = sum(r.get("datasets") != [OVERLAY_DATASET] for r in records)
    if prefix or dataset:
        raise OverlayRefused(
            f"{prefix} record(s) without the id prefix {OVERLAY_ID_PREFIX} and {dataset} not of"
            f" the dataset {OVERLAY_DATASET} alone (L18); nothing was written"
        )
    issues = [issue for record in records for issue in validate_record(record)]
    if issues:
        raise _refused(issues)
    found, holders = bridge_issues(records)
    if found:
        detail = "; ".join(f"{text}: {n}" for text, n in sorted(found.items()))
        raise OverlayRefused(f"the bridge check failed (L18): {detail}; nothing was written")
    for issue in validate_batch(records, strict=True):  # the base counts as part of the load
        missing = MISSING.search(issue.message) if issue.rule == "R4" else None
        base_ref = missing is not None and _base(missing[1])
        if not base_ref and not (issue.rule == "R8" and holders.get(str(issue.record_id))):
            issues.append(issue)
    if issues:
        raise _refused(issues)
    nodes = to_node_rows(records)
    relationships = to_relationship_rows(records, None, {row.id for row in nodes.rows})
    if skipped := len(nodes.skipped) + len(relationships.skipped):
        raise OverlayRefused(f"{skipped} mapping issue(s) in the overlay; nothing was written")
    plan = LoadPlan(len(records), nodes.rows, relationships.rows)
    base_ids = {value for record in records for _, value in references(record) if _base(value)}
    return plan, sorted(base_ids)


def read_meta(folder: Path) -> dict[str, Any]:
    """`overlay.json` of an overlay folder (counts and settings only, never a record value)."""
    try:
        meta = json.loads((folder / OVERLAY_JSON).read_text(encoding="utf-8"))
    except OSError, ValueError:
        raise OverlayRefused(f"{folder.name}: no readable {OVERLAY_JSON} (L18)") from None
    if not isinstance(meta, dict) or not isinstance(meta.get("profile"), str):
        raise OverlayRefused(f"{OVERLAY_JSON} names no profile (L18)")
    return meta


def _failing(driver: Driver, name: str, refs: list[str], database: str, size: int) -> int:
    query = cypher.query(name)
    total = 0
    for chunk in batched(refs, size, strict=False):
        rows, _, _ = driver.execute_query(
            query, {"refs": list(chunk)}, database_=database, routing_=RoutingControl.READ
        )
        total += int(rows[0][0])
    return total


def _execute(
    driver: Driver, plan: LoadPlan, refs: list[str], report: LoadReport, database: str, size: int
) -> None:
    """Steps 3 to 5 on a connected driver."""
    require_migrated(driver, database)
    for name, failure in CHECKS:
        if count := _failing(driver, name, refs, database, size):
            raise OverlayUnresolved(
                f"{count} base reference(s) of the overlay {failure} (L18); nothing was written"
            )
    with driver.session(database=database) as session:
        removed = [
            session.run(text).consume().counters.nodes_deleted
            for text in cypher.statements("overlay_purge.cypher")
        ]
    report.overlay_removed, report.detection_results_removed = sum(removed[:-1]), removed[-1]
    execute_plan(
        driver, plan, report, database=database, replace=False, batch_size=size, synthetic=True
    )


def load_overlay(
    folder: Path,
    profile: str,
    instance: Instance,
    real_overlay_profiles: Collection[str] = (),
    *,
    driver: Driver | None = None,
    database: str | None = None,
    batch_size: int = BATCH_SIZE,
    timeout_s: float = 30.0,
) -> LoadReport:
    """Load one overlay folder onto its profile's base in `instance` (L18 steps 1 to 5).
    `driver` (not closed) and `database`, which must belong to `instance`, are for tests."""
    started = time.monotonic()
    if instance is Instance.REAL and profile not in real_overlay_profiles:
        raise OverlayInstanceRefused(
            f"{profile} is not in access.real_overlay_profiles: the real-data instance takes no"
            " overlay of it (C2 L18); nothing was read"
        )
    database = database or instance.database
    if for_database(database) is not instance:
        raise InstanceRefused(f"the database does not belong to the {instance} instance (L17)")
    meta = read_meta(folder)
    loaded = read_input([folder])
    plan, refs = plan_overlay(loaded.records, meta, profile)
    if instance is Instance.DEFAULT:  # L17 on the records and manifests too
        check_records(loaded.records, instance, loaded.manifests)
    report = LoadReport(True, files=loaded.files, empty_files=loaded.empty_files)
    report.overlay_records = len(loaded.records)
    if driver is not None:
        _execute(driver, plan, refs, report, database, batch_size)
    else:
        with get_driver(instance.settings()) as owned:
            wait_until_ready(owned, timeout_s=timeout_s)
            _execute(owned, plan, refs, report, database, batch_size)
    report.duration_s = time.monotonic() - started
    return report
