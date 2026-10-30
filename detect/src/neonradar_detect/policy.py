"""Data flags (C4) and the real-data detection rule R-REAL (PHASE-3.md 2.1, G12; 7.1.4).

`data_flags` implements the C4 definitions exactly: a node is involved when it is an evidence node,
a subject, or a holder of an evidence account. `decide` applies R-REAL on every instance, in this
order, and the first rule that applies gives the reason:

(a) a finding that rests on payments (the detector says so, or a PAID relationship is in its
    evidence) and involves a non-synthetic node is withheld, because every payment in NeonRadar
    is synthetic and says nothing about a real entity;
(b) a finding whose subjects include a non-synthetic person is withheld;
(c) a finding whose other involved nodes include a non-synthetic person is withheld, so that no
    alert names a real person anywhere (data protection by design, `typology-detection-
    definitions.md` 16.5);
(d) with `registry_on_real=False` (`access.real_registry_alerts: false`, the stricter option of
    PHASE-3.md 1.2), every other finding that involves a non-synthetic node is withheld too.

A person is a `:LegalEntity` that is not an `:Organization`: a `:Person`, or a legal entity whose
kind the source does not state (ICIJ officers and intermediaries), which may be a person.
Withheld findings are counted in the run summary by reason and typology, never stored or shown.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from neonradar_detect.model import EdgeInfo, Finding, NodeInfo


class Decision(StrEnum):
    EMIT = "emit"
    ACTIVITY_ON_REAL = "activity_on_real"
    REAL_PERSON_SUBJECT = "real_person_subject"
    REAL_PERSON_EVIDENCE = "real_person_evidence"
    REGISTRY_ON_REAL = "registry_on_real"


@dataclass(frozen=True, slots=True)
class DataFlags:
    involves_real_entities: bool
    synthetic_activity: bool
    datasets: tuple[str, ...]

    @property
    def wording_class(self) -> str:
        return "structural_pattern" if self.involves_real_entities else "synthetic_scenario"


def involved_ids(finding: Finding, nodes: Mapping[str, NodeInfo]) -> list[str]:
    """Evidence nodes, subjects and the holders of evidence accounts, sorted."""
    ids = set(finding.node_ids) | {s.entity_id for s in finding.subjects}
    for node_id in finding.node_ids:
        info = nodes[node_id]
        if "Account" in info.labels:
            ids.update(info.holders)
    return sorted(ids)


def may_be_person(info: NodeInfo) -> bool:
    """A `:Person`, or a `:LegalEntity` of unstated kind: anything legal that is not an
    organisation."""
    return "LegalEntity" in info.labels and "Organization" not in info.labels


def rests_on_payments(finding: Finding, edges: Mapping[str, EdgeInfo]) -> bool:
    return finding.activity or any(edges[e].type == "PAID" for e in finding.edge_ids)


def data_flags(
    finding: Finding, nodes: Mapping[str, NodeInfo], edges: Mapping[str, EdgeInfo]
) -> DataFlags:
    involved = involved_ids(finding, nodes)
    missing = [i for i in involved if i not in nodes]
    if missing:
        raise KeyError(f"no node information for {len(missing)} involved ids")
    involves_real = any(not nodes[i].synthetic for i in involved)
    synthetic_activity = all(edges[e].synthetic for e in finding.edge_ids)
    datasets = sorted({d for i in involved for d in nodes[i].datasets})
    return DataFlags(involves_real, synthetic_activity, tuple(datasets))


def decide(
    finding: Finding,
    flags: DataFlags,
    nodes: Mapping[str, NodeInfo],
    edges: Mapping[str, EdgeInfo],
    *,
    registry_on_real: bool = True,
) -> Decision:
    if flags.involves_real_entities and rests_on_payments(finding, edges):
        return Decision.ACTIVITY_ON_REAL
    subjects = {s.entity_id for s in finding.subjects}
    if any(not nodes[s].synthetic and may_be_person(nodes[s]) for s in sorted(subjects)):
        return Decision.REAL_PERSON_SUBJECT
    for node_id in involved_ids(finding, nodes):
        info = nodes[node_id]
        if node_id not in subjects and not info.synthetic and may_be_person(info):
            return Decision.REAL_PERSON_EVIDENCE
    if flags.involves_real_entities and not registry_on_real:
        return Decision.REGISTRY_ON_REAL
    return Decision.EMIT
