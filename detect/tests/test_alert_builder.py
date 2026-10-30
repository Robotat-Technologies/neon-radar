from kit import WINDOW, Kit, detect, source_of
from neonradar_detect import catalog, runner
from neonradar_detect.detectors import circular_flow
from neonradar_detect.wording_lint import violations


def _cycle(k: Kit, tag: str, holders: list[str] | None = None) -> None:
    accts = [
        k.account(f"{tag}{i}", holders[i] if holders else k.company(f"{tag}{i}")) for i in range(4)
    ]
    for i, (a, b) in enumerate(zip(accts, accts[1:] + accts[:1], strict=True)):
        k.pay(a, b, 50000 - 500 * i, f"2026-03-0{2 + i}T10:00")


def texts(alert: dict) -> list[str]:
    return [
        alert["headline"],
        alert["explanation"]["summary"],
        *(s["text"] for s in alert["explanation"]["steps"]),
    ]


def test_synthetic_alert_text_passes_the_lint_and_ids_are_stable():
    k = Kit()
    _cycle(k, "c")
    result = detect(k.records, {"circular_flow": circular_flow.Params()})
    [alert] = result.alerts
    captions = tuple(s["caption"] for s in alert["subjects"])
    assert alert["wording_class"] == "synthetic_scenario"
    assert alert["headline"].startswith("Synthetic scenario: ") and len(alert["headline"]) <= 140
    assert all(len(s["text"]) <= 280 for s in alert["explanation"]["steps"])
    for text in texts(alert):
        assert violations(text, captions) == [], text
    assert alert["explanation"]["steps"][0]["text"].endswith("on 2 March 2026.")
    assert alert["evidence"]["query"]["parameters"]["edge_ids"] == alert["evidence"]["edge_ids"]
    again = detect(k.records, {"circular_flow": circular_flow.Params()})
    assert [a["alert_id"] for a in again.alerts] == [alert["alert_id"]]


def test_r_real_withholds_activity_on_a_real_entity():
    """PHASE-1.md M1.9b case F under R-REAL: the cycle through a real company's synthetic
    account is found, then withheld and counted (G12)."""
    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    _cycle(k, "r", holders=[real_co, *(k.company(f"other{i}") for i in range(3))])
    result = detect(k.records, {"circular_flow": circular_flow.Params()})
    assert result.alerts == []
    assert result.summary["withheld"] == {
        "activity_on_real": 1,
        "real_person_subject": 0,
        "real_person_evidence": 0,
        "registry_on_real": 0,
    }
    per = result.summary["typologies"]["circular_flow"]
    assert per["findings"] == 1 and per["alerts"] == 0


def test_r_real_names_no_real_person_anywhere():
    """No alert names a real person (G12, rules (b) and (c)): a person, or a legal entity whose
    kind the source does not state, is withheld as a subject and in the evidence; a registry
    finding whose evidence names only organisations is emitted unless the stricter option is on;
    a PAID in the evidence makes a finding rest on payments (rule (a))."""
    from neonradar_detect import policy
    from neonradar_detect.model import EdgeInfo, Finding, NodeInfo, Subject

    kinds = {
        "person": {"Entity", "LegalEntity", "Person"},
        "entity": {"Entity", "LegalEntity"},
        "company": {"Entity", "LegalEntity", "Organization", "Company"},
    }

    def node(nid: str, kind: str, synthetic: bool = False) -> NodeInfo:
        dataset = "nr_synthetic" if synthetic else "gb_companies_house"
        return NodeInfo(nid, frozenset(kinds[kind]), f"Test {nid}", synthetic, (dataset,))

    nodes = {
        n.id: n
        for n in (
            node("p", "person"),
            node("le", "entity"),
            node("co", "company"),
            node("parent", "company"),
            node("syn", "company", synthetic=True),
        )
    }
    edges = {
        "o1": EdgeInfo("o1", "OWNS", "parent", "co", False),
        "o2": EdgeInfo("o2", "OWNS", "p", "co", False),
        "o3": EdgeInfo("o3", "OWNS", "le", "co", False),
        "pay": EdgeInfo("pay", "PAID", "syn", "co", True),
    }

    def decide(
        subject: str, node_ids: tuple[str, ...], edge_ids: tuple[str, ...], **kw: bool
    ) -> policy.Decision:
        f = Finding("t", "", subject, node_ids, edge_ids, (Subject(subject, "x"),), {}, 0.5, ())
        return policy.decide(f, policy.data_flags(f, nodes, edges), nodes, edges, **kw)

    d = policy.Decision
    assert decide("co", ("co", "parent"), ("o1",)) is d.EMIT
    assert decide("co", ("co", "parent"), ("o1",), registry_on_real=False) is d.REGISTRY_ON_REAL
    assert decide("co", ("co", "p"), ("o2",)) is d.REAL_PERSON_EVIDENCE
    assert decide("co", ("co", "le"), ("o3",)) is d.REAL_PERSON_EVIDENCE
    assert decide("p", ("p",), ()) is d.REAL_PERSON_SUBJECT
    assert decide("le", ("le",), ()) is d.REAL_PERSON_SUBJECT
    assert decide("co", ("co", "syn"), ("pay",)) is d.ACTIVITY_ON_REAL


def test_records_from_icij_carry_its_caution():
    """Phase 1's register says to show ICIJ's disclaimer with its data: an alert whose evidence
    holds an ICIJ record carries ICIJ's caution among its notes, and other alerts do not."""
    from datetime import UTC, datetime

    from neonradar_detect import alerts, policy
    from neonradar_detect.model import Finding, NodeInfo, Subject
    from neonradar_detect.wording import Rendered

    org = frozenset({"Entity", "LegalEntity", "Organization"})
    leak = NodeInfo("icij-T0000001", org, "Test Offshore Ltd", False, ("icij_offshore_leaks",))
    finding = Finding("t", "", leak.id, (leak.id,), (), (Subject(leak.id, "x"),), {}, 0.5, ())

    def notes(datasets: tuple[str, ...]) -> list[str]:
        alert = alerts.build(
            finding,
            Rendered("Test headline", "Test summary.", ()),
            policy.DataFlags(True, True, datasets),
            {leak.id: leak},
            detector_module="neonradar_detect.detectors.t",
            detector_version="0.2.0",
            typology_version="0.2.0",
            query_sha256="0" * 64,
            run_id="run-20261102T090000-0004",
            created_at=datetime(2026, 11, 2, tzinfo=UTC),
            doc_path="docs/typologies/t.md",
            citations=("icij_faq",),
            false_positives=("A test note",),
        )
        return list(alert["explanation"]["false_positive_notes"])

    caution = alerts.DATASET_NOTES["icij_offshore_leaks"]
    assert notes(("icij_offshore_leaks",)) == ["A test note", caution]
    assert notes(("gb_companies_house",)) == ["A test note"]
    assert violations(caution) == []


def test_rendering_lints_every_text_with_the_captions_masked():
    import dataclasses

    import pytest
    from neonradar_detect import wording

    k = Kit()
    _cycle(k, "m")
    cat = catalog.load()
    source = source_of(k.records)
    [finding] = circular_flow.run(source, circular_flow.Params(), WINDOW).findings
    edges = source.edge_info(finding.edge_ids)
    nodes = source.node_info(sorted({x for e in edges.values() for x in (e.source, e.target)}))
    first = edges[finding.steps[0][0]].source
    nodes[first] = dataclasses.replace(nodes[first], caption="Test Mule Transport Ltd")
    rendered = wording.render(finding, cat["circular_flow"], "synthetic_scenario", nodes, edges)
    assert rendered.steps[0][0].startswith("Test Mule Transport Ltd paid")  # a caption, masked
    bad = dict(cat["circular_flow"].wording, headline_synthetic="Synthetic scenario: layering")
    broken = {**cat, "circular_flow": dataclasses.replace(cat["circular_flow"], wording=bad)}
    with pytest.raises(wording.WordingError, match="circular_flow: the headline"):
        runner.run_detection(
            source,
            {"circular_flow": circular_flow.Params()},
            WINDOW,
            broken,
            run_id="run-20261102T090000-0003",
            created_at=WINDOW.end,
        )


def test_catalog_templates_and_parameters_match_the_detectors():
    import dataclasses

    from neonradar_detect.wording import placeholders, render_template

    cat = catalog.load()
    found = runner.detectors(cat)
    assert list(found) == [s for s in runner.ORDER if s in cat and cat[s].detector]
    for slug, module in found.items():
        t = cat[slug]
        assert t.version == module.VERSION and t.detector == module.__name__
        defaults = {
            f.name: getattr(module.Params(), f.name) for f in dataclasses.fields(module.Params)
        }
        assert {
            k: tuple(v["default"]) if isinstance(v["default"], list) else v["default"]
            for k, v in t.parameters.items()
        } == defaults
        assert catalog.params_for(t, module) == module.Params()
        pairs = [t.wording, *t.wording.get("variants", {}).values()]
        for pair in pairs:
            for key in ("headline_structural", "headline_synthetic"):
                assert placeholders(pair[key]) <= set(t.metrics), (slug, key)
                sample = {m: 1 for m in t.metrics} | {"currency": "GBP"}
                assert violations(render_template(pair[key], sample)) == [], (slug, key)
            assert pair["headline_synthetic"].startswith("Synthetic scenario: ")
        assert violations(t.shape_name) == [] and all(
            violations(x) == [] for x in t.false_positives
        )
