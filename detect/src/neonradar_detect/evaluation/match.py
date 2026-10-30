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
