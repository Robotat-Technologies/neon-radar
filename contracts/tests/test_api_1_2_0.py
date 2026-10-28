"""C3 1.2.0 models (PHASE-4.md 5.3): the copilot's request and answer, runs, shape names."""

import pytest
from neonradar_contracts.api import (
    AlertSummary,
    CopilotAnswer,
    CopilotInfo,
    CopilotRequest,
    RunDetail,
)
from pydantic import ValidationError


def test_a_request_is_bounded_and_closed() -> None:
    CopilotRequest(question="Who owns Calvane Holdings Ltd?")
    menu = CopilotRequest(
        question="Who owns Kestrow Partners?",
        template_id="owners_of",
        slots={"entity": "syn-cb-co-kestrow-gb"},
    )
    assert menu.context_entity_ids == []
    for bad in (
        {"question": ""},
        {"question": "x" * 501},
        {"question": "x", "cypher": "MATCH (n) RETURN n"},
        {"question": "x", "context_entity_ids": ["a"] * 6},
        {"question": "x", "context_entity_ids": [""]},
        {"question": "x", "template_id": "Owners Of"},
        {"question": "x", "slots": {"Entity": "x"}},
        {"question": "x", "slots": {f"s{i}x": "v" for i in range(9)}},
        {"question": "x", "slots": {"entity": "x" * 201}},
    ):
        with pytest.raises(ValidationError):
            CopilotRequest.model_validate(bad)


def test_an_answer_keeps_the_1_0_0_fields_and_adds_the_new_ones() -> None:
    old = {
        "status": "refused",
        "answer_text": "x",
        "template_id": None,
        "cypher": None,
        "parameters": None,
        "subgraph": None,
        "refusal_reason": "x",
    }
    answer = CopilotAnswer.model_validate({**old, "refusal_code": "judgement"})
    assert answer.choices == [] and answer.queries == [] and answer.model is None
    with pytest.raises(ValidationError):
        CopilotAnswer.model_validate({**old, "refusal_code": "because"})
    clarify = CopilotAnswer.model_validate({**old, "status": "needs_clarification"})
    assert clarify.status == "needs_clarification"


def test_summaries_carry_the_display_name() -> None:
    row = {
        "alert_id": "alr-d6c70222afa20b180eff",
        "typology": "circular_flow",
        "priority": "high",
        "pattern_strength": 0.7603,
        "headline": "x",
        "created_at": "2026-11-02T09:00:00Z",
        "subject_ids": ["syn-cb-co-calvane"],
        "involves_real_entities": False,
        "synthetic_activity": True,
    }
    with pytest.raises(ValidationError):
        AlertSummary.model_validate(row)
    assert AlertSummary.model_validate({**row, "display_name": "Circular flow"}).shape_name is None


def test_info_and_run_detail_shapes() -> None:
    info = CopilotInfo(
        catalog_version="0123456789ab",
        router="pattern",
        model=None,
        badge="b",
        notice="n",
        templates=[],
    )
    assert info.router == "pattern"
    detail = RunDetail.model_validate(
        {
            "run": {
                "run_id": "run-20261102T090000-0001",
                "status": "ok",
                "started_at": None,
                "finished_at": None,
                "profile": None,
                "window_start": None,
                "window_end": None,
                "typologies": [],
                "detectors": [],
                "alert_count": 0,
                "params_sha256": None,
            },
            "typologies": {},
            "alerts": 0,
            "withheld": {},
        }
    )
    assert detail.run.alert_count == 0
