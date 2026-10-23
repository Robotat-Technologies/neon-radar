"""Every alert the runner builds validates against C4 1.0.0 (PHASE-3.md M3.2 deliverable 8; C4 is
unchanged in Phase 3, 5.3): the cases of `test_alert_builder.py` and every alert of a small
generated world run in memory. `wording_class` is `synthetic_scenario` exactly when
`involves_real_entities` is false, and every alert carries the evidence query's hash (A1) and
an evidence window key (A2)."""

import dataclasses
from datetime import UTC, datetime
from typing import Any

import worlds
from kit import WINDOW, Kit, detect, source_of
from test_alert_builder import _cycle

from neonradar_contracts.alert import Alert
from neonradar_detect import alerts, catalog, policy, runner, runs, wording
from neonradar_detect.detectors import circular_flow
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource

RUN_ID = "run-20261102T090000-0001"
CREATED = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def check(built: list[dict[str, Any]]) -> list[Alert]:
    """Validate as `detect run` does once the evidence query's hash is set (A1)."""
    out = []
    for item in built:
        item = {**item, "detector": {**item["detector"], "query_sha256": runs.EVIDENCE_SHA256}}
        alert = Alert.model_validate(item)
        assert (alert.wording_class == "synthetic_scenario") is (
            not alert.data_flags.involves_real_entities
        )
        assert "window" in item["evidence"]
        out.append(alert)
    return out


def test_the_alert_builder_cases_validate() -> None:
    k = Kit()
    _cycle(k, "c")
    [alert] = check(detect(k.records, {"circular_flow": circular_flow.Params()}).alerts)
    assert alert.evidence.window is not None and alert.wording_class == "synthetic_scenario"
    real = Kit()
    holder = real.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    _cycle(real, "r", holders=[holder, *(real.company(f"other{i}") for i in range(3))])
    result = detect(real.records, {"circular_flow": circular_flow.Params()})
    assert check(result.alerts) == [] and result.summary["withheld"]["activity_on_real"] == 1


def test_a_masked_caption_and_a_finding_without_a_window_validate() -> None:
    k = Kit()
    _cycle(k, "m")
    cat = catalog.load()
    source = source_of(k.records)
    [finding] = circular_flow.run(source, circular_flow.Params(), WINDOW).findings
    finding = dataclasses.replace(finding, window=None)
    edges = source.edge_info(finding.edge_ids)
    nodes = source.node_info(sorted(alerts.edge_ends(edges) | set(finding.node_ids)))
    first = edges[finding.steps[0][0]].source
    nodes[first] = dataclasses.replace(nodes[first], caption="Test Mule Transport Ltd")
    flags = policy.data_flags(finding, nodes, edges)
    typology = cat["circular_flow"]
    built = alerts.build(
        finding,
        wording.render(finding, typology, flags.wording_class, nodes, edges),
        flags,
        nodes,
        detector_module=circular_flow.__name__,
        detector_version=circular_flow.VERSION,
        typology_version=typology.version,
        query_sha256=runs.EVIDENCE_SHA256,
        run_id=RUN_ID,
        created_at=CREATED,
        doc_path=typology.doc,
        citations=typology.citations,
        false_positives=typology.false_positives,
    )
    [alert] = check([built])
    assert alert.evidence.window is None  # A2: the key is there, null


def test_every_alert_of_a_small_world_validates() -> None:
    cat = catalog.load()
    params = {
        slug: catalog.params_for(cat[slug], module)
        for slug, module in runner.detectors(cat).items()
    }
    result = runner.run_detection(
        MemSource(from_records(worlds.small_world())),
        params,
        worlds.WINDOW,
        cat,
        run_id=RUN_ID,
        created_at=CREATED,
        query_sha256={slug: runs.EVIDENCE_SHA256 for slug in params},
    )
    found = check(result.alerts)
    assert found, "the small world gives no alert"
    assert runs.validate(result.alerts) == found
    assert {a.data_flags.involves_real_entities for a in found} == {False}
